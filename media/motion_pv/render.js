// pv.html を1フレームずつ撮影して MP4 に書き出す
//   node media/motion_pv/render.js [出力ファイル] [--fps 30] [--from 秒] [--to 秒]
//   --stills 1,5.5,10 を付けると、指定秒の静止画（PNG）だけを書き出す
// 必要なもの: Playwright（Chromium）と ffmpeg（環境変数 FFMPEG でパス指定可）
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args.splice(i, 2)[1] : def; };
const fps = parseFloat(opt("--fps", "30"));
const from = parseFloat(opt("--from", "0"));
const toArg = opt("--to", null);
const stills = opt("--stills", null);
const out = args[0] || "motion_pv.mp4";
const ffmpegPath = process.env.FFMPEG || "ffmpeg";

(async () => {
  const browser = await chromium.launch({ args: ["--allow-file-access-from-files", "--font-render-hinting=none"] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("pageerror", e => console.error("pageerror:", e.message));
  await page.goto("file://" + path.join(__dirname, "pv.html") + "?render=1");
  await page.evaluate(() => window.pvReady);
  const shot = type => page.screenshot({ type, quality: type === "jpeg" ? 95 : undefined, clip: { x: 0, y: 0, width: 1920, height: 1080 } });

  if (stills) {
    for (const t of stills.split(",").map(Number)) {
      await page.evaluate(ms => window.seek(ms), t * 1000);
      const file = out.replace(/\.\w+$/, "") + "_" + String(t).replace(".", "_") + ".png";
      require("fs").writeFileSync(file, await shot("png"));
      console.log("still:", file);
    }
    await browser.close();
    return;
  }

  const to = toArg !== null ? parseFloat(toArg) : await page.evaluate(() => window.PV_DURATION);
  const total = Math.round((to - from) * fps);
  const ff = spawn(ffmpegPath, [
    "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "mjpeg", "-i", "-",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out,
  ], { stdio: ["pipe", "inherit", "inherit"] });
  const started = Date.now();
  for (let i = 0; i < total; i++) {
    await page.evaluate(ms => window.seek(ms), from * 1000 + i * 1000 / fps);
    const buf = await shot("jpeg");
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (i % (fps * 5) === 0) console.log(`frame ${i}/${total} (${((Date.now() - started) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  const code = await new Promise(r => ff.on("close", r));
  await browser.close();
  if (code !== 0) { console.error("ffmpeg failed:", code); process.exit(1); }
  console.log("done:", out);
})();
