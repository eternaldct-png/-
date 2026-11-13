#!/usr/bin/env node
/* アマテラス MV レンダラー
   node render.js --stills 1,10.5,76.4 [--scale 0.5]   指定時刻の静止画 → out/stills/
   node render.js --full [--workers 4]                 全編を書き出し → out/amaterasu_mv.mp4
   node render.js --range 60 80 --name test            一部だけ（音つき）→ out/test.mp4
   node render.js --serve                              ブラウザでプレビュー（http://localhost:8765/src/）
*/
const http = require('http'), fs = require('fs'), path = require('path'), { spawn, spawnSync } = require('child_process');
const ROOT = __dirname, FPS = 30, DUR = 266.3445, OUT = path.join(ROOT, 'out');
const args = process.argv.slice(2); const has = k => args.includes(k); const val = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.woff': 'font/woff', '.mp3': 'audio/mpeg' };
function serve(port) {
  return new Promise(res => {
    const s = http.createServer((q, r) => {
      const p = path.normalize(path.join(ROOT, decodeURIComponent(q.url.split('?')[0])));
      if (!p.startsWith(ROOT)) { r.writeHead(403); return r.end(); }
      fs.readFile(p.endsWith(path.sep) ? p + 'index.html' : p, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(d); });
    }).listen(port, '127.0.0.1', () => res(s));
  });
}
async function openPage(port) {
  const { chromium } = require('playwright');
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-vsync'] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  p.on('pageerror', e => { console.error('PAGE ERROR', e.message); });
  p.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  await p.goto(`http://127.0.0.1:${port}/src/index.html`);
  await p.evaluate(() => window.ready);
  return { b, p };
}
async function renderRange(port, f0, f1, outFile) {
  const { b, p } = await openPage(port);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-vf', 'scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-g', '30',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-r', String(FPS), outFile], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    const b64 = await p.evaluate(t => window.frameJPEG(t, 0.96), f / FPS);
    if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 150 === 149) console.log(`[${path.basename(outFile)}] ${f - f0 + 1}/${f1 - f0} ${((Date.now() - t0) / (f - f0 + 1)).toFixed(0)}ms/f`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await b.close();
}
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const port = +val('--port', 8765 + Math.floor(Math.random() * 500));
  const srv = await serve(port);
  if (has('--serve')) { console.log(`http://127.0.0.1:${port}/src/index.html`); return; }
  if (has('--stills')) {
    const dir = path.join(OUT, 'stills'); fs.mkdirSync(dir, { recursive: true });
    const ts = val('--stills').split(',').map(Number); const { b, p } = await openPage(port);
    const t0 = Date.now();
    for (const t of ts) { const b64 = await p.evaluate(t => window.frameJPEG(t, 0.9), t); fs.writeFileSync(path.join(dir, `t_${t.toFixed(2).padStart(7, '0')}.jpg`), Buffer.from(b64, 'base64')); }
    console.log(`${ts.length} stills, ${((Date.now() - t0) / ts.length).toFixed(0)}ms/frame`);
    await b.close(); srv.close(); return;
  }
  if (has('--worker')) { await renderRange(port, +val('--f0'), +val('--f1'), val('--out')); srv.close(); return; }
  let f0 = 0, f1 = Math.round(DUR * FPS), name = 'amaterasu_mv';
  if (has('--range')) { const i = args.indexOf('--range'); f0 = Math.round(+args[i + 1] * FPS); f1 = Math.round(+args[i + 2] * FPS); name = val('--name', 'range'); }
  srv.close();
  const nw = +val('--workers', 4), per = Math.ceil((f1 - f0) / nw), parts = [];
  await Promise.all([...Array(nw).keys()].map(i => new Promise((res, rej) => {
    const a = f0 + i * per, z = Math.min(f1, a + per); if (a >= z) return res();
    const part = path.join(OUT, `${name}.part${i}.mp4`); parts[i] = part;
    const c = spawn(process.execPath, [__filename, '--worker', '--f0', a, '--f1', z, '--out', part], { stdio: 'inherit' });
    c.on('close', code => code ? rej(new Error('worker ' + i + ' failed')) : res());
  })));
  const list = path.join(OUT, `${name}.txt`); fs.writeFileSync(list, parts.filter(Boolean).map(p => `file '${p}'`).join('\n'));
  const final = path.join(OUT, `${name}.mp4`);
  const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-ss', String(f0 / FPS), '-t', String((f1 - f0) / FPS), '-i', path.join(ROOT, 'assets/song.mp3'),
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', final], { stdio: 'inherit' });
  if (r.status === 0) { parts.filter(Boolean).forEach(p => fs.unlinkSync(p)); fs.unlinkSync(list); console.log('done', final); }
})().catch(e => { console.error(e); process.exit(1); });
