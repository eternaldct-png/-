// ETERNAL d.c.t プロモ映像レンダラー
// 使い方: node media/promo/render.mjs [--stills 0,5,13] [--out media/promo/out]
//   リポジトリのルートを簡易HTTPサーバーで配信し、Chromium で promo.html を開いて
//   1フレームずつ draw(t) → JPEG → ffmpeg にパイプして MP4（音声付き）を作る。
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// playwright はグローバルインストールでも見つかるよう CJS の require（NODE_PATH を参照）で読む
const { chromium } = createRequire(import.meta.url)('playwright');
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const OUT = path.resolve(opt('--out') || path.join(HERE, 'out'));
const FPS = Number(opt('--fps') || 30);
const FFMPEG = process.env.FFMPEG || execSync('python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"').toString().trim();
fs.mkdirSync(OUT, { recursive: true });

const MIME = { '.html': 'text/html', '.css': 'text/css', '.ttf': 'font/ttf', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.png': 'image/png', '.js': 'text/javascript' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => { console.error('[pageerror]', e); process.exitCode = 1; });
await page.goto(`http://127.0.0.1:${port}/media/promo/promo.html`);
await page.evaluate(() => window.ready);
const DURATION = await page.evaluate(() => window.DURATION);

const frame = (t, q) => page.evaluate(([t, q]) => { window.draw(t); return document.getElementById('c').toDataURL(q ? 'image/jpeg' : 'image/png', q || undefined); }, [t, q]);
const b64 = u => Buffer.from(u.slice(u.indexOf(',') + 1), 'base64');

const stills = opt('--stills');
if (stills) {
  for (const s of stills.split(',')) {
    fs.writeFileSync(path.join(OUT, `still_${s}.png`), b64(await frame(parseFloat(s))));
  }
  console.log('stills written to', OUT);
} else {
  const audio = path.join(HERE, 'out', 'bgm.wav');
  const mp4 = path.join(OUT, 'eternaldct_promo_60s.mp4');
  const ff = spawn(FFMPEG, [
    '-y', '-loglevel', 'warning', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    ...(fs.existsSync(audio) ? ['-i', audio, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const N = Math.round(DURATION * FPS);
  for (let i = 0; i < N; i++) {
    const buf = b64(await frame(i / FPS, 0.95));
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${N}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log('written', mp4);
}
await browser.close();
server.close();
