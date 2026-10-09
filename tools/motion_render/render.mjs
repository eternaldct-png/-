// /motion の作例動画を書き出すレンダラー（Canvas で1コマずつ描いて ffmpeg で mp4 にする）
//
// 使い方（tools/motion_render で実行）:
//   node render.mjs <scene> stills 0.5,2,4   … 指定秒のコマを review/ に JPEG で書き出す（確認用）
//   node render.mjs <scene> video            … ../../src/static/motion/<scene>.mp4 と .jpg（ポスター）を書き出す
//   node render.mjs all video                … scenes/ の全作例を書き出す
//
// 必要なもの: Node.js / playwright（Chromium）/ ffmpeg / fonts/（python3 fetch_fonts.py で取得）
// 環境変数: CHROMIUM_PATH（任意の Chromium を使う場合）, CRF（画質。既定 26。小さいほど高画質・大容量）
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';

async function loadPlaywright() {
  try { return await import('playwright'); } catch {}
  // グローバルにインストールされた playwright を探す
  const { execSync } = await import('node:child_process');
  const root = execSync('npm root -g').toString().trim();
  return createRequire(root + '/')('playwright');
}

const ROOT = path.dirname(new URL(import.meta.url).pathname);
// OUT_DIR を指定すると /motion 以外（SNS投稿用など）の場所に書き出せる
const OUT = process.env.OUT_DIR ? path.resolve(process.env.OUT_DIR) : path.resolve(ROOT, '../../src/static/motion');
const [sceneArg, mode = 'stills', arg = '0'] = process.argv.slice(2);
if (!sceneArg) { console.error('usage: node render.mjs <scene|all> <stills|video> [times]'); process.exit(1); }
if (!fs.existsSync(path.join(ROOT, 'fonts', 'fonts.css'))) { console.error('fonts/ がありません。先に python3 fetch_fonts.py を実行してください'); process.exit(1); }
const scenes = sceneArg === 'all' ? fs.readdirSync(path.join(ROOT, 'scenes')).filter((f) => f.endsWith('.js')).map((f) => f.slice(0, -3)).sort() : [sceneArg];

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.webp': 'image/webp', '.ttf': 'font/ttf', '.jpg': 'image/jpeg' };
// file:// だとフォントと画像の読み込みが制限されるため、ローカルの HTTP サーバー経由で開く
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const { chromium } = await loadPlaywright();
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});

for (const scene of scenes) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1280 } });
  page.on('pageerror', (e) => console.error('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${port}/render.html?scene=${scene}`);
  await page.waitForFunction(() => window.READY || window.FAILED, null, { timeout: 60000 });
  const failed = await page.evaluate(() => window.FAILED);
  if (failed) { console.error(scene, failed); process.exitCode = 1; await page.close(); continue; }
  const info = await page.evaluate(() => window.READY);
  const frame = async (t, q) => {
    const url = await page.evaluate(([t, q]) => { window.drawAt(t); return window.grab(q); }, [t, q]);
    return Buffer.from(url.split(',')[1], 'base64');
  };

  if (mode === 'stills') {
    fs.mkdirSync(path.join(ROOT, 'review'), { recursive: true });
    for (const s of arg.split(',')) fs.writeFileSync(path.join(ROOT, 'review', `${scene}_${s}.jpg`), await frame(parseFloat(s), 0.9));
    console.log('stills', scene, arg);
  } else {
    fs.mkdirSync(OUT, { recursive: true });
    const out = path.join(OUT, `${scene}.mp4`);
    // 720p・30fps・音なし・H.264（iPhone の Safari でも再生できる形式）。faststart で読み込みながら再生を始められる
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(info.fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', process.env.CRF || '26', '-tune', 'animation', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
      '-movflags', '+faststart', '-an', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n = Math.round(info.dur * info.fps);
    for (let i = 0; i < n; i++) {
      if (!ff.stdin.write(await frame(i / info.fps, 0.94))) await new Promise((r) => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise((r) => ff.on('close', r));
    fs.writeFileSync(path.join(OUT, `${scene}.jpg`), await frame(info.poster, 0.8));
    const mb = fs.statSync(out).size / 1024 / 1024;
    console.log(`${scene}: ${n} frames, ${mb.toFixed(2)} MB${mb > 3 ? '  ⚠ 3MBを超えています（CRF を上げてください）' : ''}`);
  }
  await page.close();
}
await browser.close();
server.close();
