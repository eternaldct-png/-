// モーション動画の共通ランタイム（pv.html / liver_recruit.html などで共有）
//
// ページ側の約束:
//   <div id="stage" data-duration="62"> … <section class="scene" data-s="開始秒" data-len="長さ秒"> … </div>
//   <div id="wipeWrap"><div id="wipe"></div></div><div id="flash"></div> を #stage の最後に置く
//   このファイルを読み込んだあとにページ固有のスクリプトを書けば、そこで作った要素も動きの対象になる
//
// 再生: ブラウザで開くとプレビュー再生、?t=秒 でその時刻に固定、?render=1 は render.js が1フレームずつ撮影する
(function () {
  const PARAMS = new URLSearchParams(location.search);
  const stage = document.getElementById("stage");
  const DURATION = parseFloat(stage.dataset.duration);

  // 乱数は毎回同じ結果になるよう固定シード
  function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const rand = rng(parseInt(stage.dataset.seed || "20261010", 10));
  const lerpColor = (a, b, k) => { const pa = a.match(/\w\w/g).map(h => parseInt(h, 16)), pb = b.match(/\w\w/g).map(h => parseInt(h, 16)); return "rgb(" + pa.map((v, i) => Math.round(v + (pb[i] - v) * k)).join(",") + ")"; };

  const scenes = [...document.querySelectorAll(".scene")];
  scenes.forEach(sc => { sc.style.setProperty("--s", sc.dataset.s + "s"); sc.style.setProperty("--len", sc.dataset.len + "s"); });
  const sceneStart = el => parseFloat(el.closest(".scene").dataset.s);

  // 1文字ずつ動くテキスト: data-split="アニメ名" data-at="開始" data-step="1文字ごとの遅れ" (data-grad-from="n" でn文字目以降をグラデーション色に)
  document.querySelectorAll("[data-split]").forEach(el => {
    const chars = [...el.textContent];
    const at = parseFloat(el.dataset.at), step = parseFloat(el.dataset.step);
    const gradFrom = el.dataset.gradFrom ? parseInt(el.dataset.gradFrom, 10) : -1;
    el.textContent = "";
    chars.forEach((ch, i) => {
      const span = document.createElement("span");
      span.className = "fx " + el.dataset.split;
      span.style.setProperty("--d", (at + i * step).toFixed(3) + "s");
      span.textContent = ch;
      if (gradFrom >= 0 && i >= gradFrom) span.style.color = lerpColor("c084fc", "f472b6", (i - gradFrom) / Math.max(1, chars.length - 1 - gradFrom));
      el.appendChild(span);
    });
  });

  // 弾けるパーティクル: data-burst="個数" data-at="開始"
  document.querySelectorAll("[data-burst]").forEach(el => {
    const n = parseInt(el.dataset.burst, 10), at = parseFloat(el.dataset.at);
    const glyphs = ["♥", "★", "♥", "✦"], colors = ["#ec4899", "#f59e0b", "#a855f7", "#f472b6"];
    for (let i = 0; i < n; i++) {
      const p = document.createElement("span");
      p.className = "fx burst";
      p.textContent = glyphs[i % glyphs.length];
      p.style.color = colors[i % colors.length];
      p.style.setProperty("--a", (i * 360 / n + rand() * 12) + "deg");
      p.style.setProperty("--dist", (250 + rand() * 120) + "px");
      p.style.setProperty("--d", (at + rand() * .15) + "s");
      p.style.setProperty("--dur", "1.3s");
      p.style.setProperty("--ease", "cubic-bezier(.2,.7,.3,1)");
      el.appendChild(p);
    }
  });

  // 星空: data-stars="個数"
  document.querySelectorAll("[data-stars]").forEach(el => {
    const w = stage.offsetWidth, h = stage.offsetHeight;
    for (let i = 0; i < parseInt(el.dataset.stars, 10); i++) {
      const s = document.createElement("div");
      s.className = "star fx twinkle";
      s.style.left = (rand() * w) + "px";
      s.style.top = (rand() * (h - 180)) + "px";
      s.style.setProperty("--dur", (1.2 + rand() * 1.6) + "s");
      s.style.setProperty("--d", (-rand() * 2) + "s");
      s.style.setProperty("--it", "infinite");
      s.style.setProperty("--ease", "ease-in-out");
      el.appendChild(s);
    }
  });

  // 紙吹雪: data-confetti="個数"
  document.querySelectorAll("[data-confetti]").forEach(el => {
    const colors = ["#111", "#ec4899", "#7c3aed", "#fff", "#22d3ee"];
    for (let i = 0; i < parseInt(el.dataset.confetti, 10); i++) {
      const c = document.createElement("i");
      c.className = "fx fall";
      c.style.left = (rand() * stage.offsetWidth) + "px";
      c.style.background = colors[i % colors.length];
      c.style.setProperty("--dur", (2.4 + rand() * 1.6) + "s");
      c.style.setProperty("--d", (-rand() * 3) + "s");
      c.style.setProperty("--it", "infinite");
      c.style.setProperty("--ease", "linear");
      el.appendChild(c);
    }
  });

  // ── CSSで表せない動き（カウントアップ・タイピング・シーン切り替えのワイプ） ──
  // data-count="目標値" data-at="開始" data-dur="長さ" / data-type="文字列" data-at data-dur
  let counters = [], typers = [];
  const CUTS = scenes.slice(1).map(sc => parseFloat(sc.dataset.s));
  const CUT_TYPES = ["wipe", "flash", "wipeRev"];
  const easeOut = k => 1 - Math.pow(1 - k, 3);
  const clamp01 = k => Math.min(1, Math.max(0, k));
  const wipe = document.getElementById("wipe"), wrap = document.getElementById("wipeWrap"), flash = document.getElementById("flash");
  // ワイプの帯は画面サイズから計算（切り替えの瞬間に画面全体を覆う）
  const W = stage.offsetWidth, H = stage.offsetHeight;
  const bandH = H + 400, skew = 16, shift = bandH * Math.tan(skew * Math.PI / 180), margin = 600;
  const bandW = W + shift + margin * 2;
  const x0 = -bandW - shift / 2 - 10, x1 = W + shift / 2 + 10;
  wipe.style.top = "-200px";
  wipe.style.width = bandW + "px";
  wipe.style.height = bandH + "px";

  function renderJS(t) {
    counters.forEach(c => { c.el.textContent = Math.round(c.to * easeOut(clamp01((t - c.t0) / c.dur))).toLocaleString("ja-JP"); });
    typers.forEach(ty => { ty.el.textContent = ty.text.slice(0, Math.floor(ty.text.length * clamp01((t - ty.t0) / ty.dur))).join(""); });
    let x = -99999, rev = false, flashOp = 0;
    CUTS.forEach((c, i) => {
      const type = CUT_TYPES[i % CUT_TYPES.length];
      if (type === "flash") {
        const dt = t - c;
        if (dt >= -.1 && dt < 0) flashOp = Math.max(flashOp, (dt + .1) / .1);
        else if (dt >= 0 && dt < .35) flashOp = Math.max(flashOp, 1 - dt / .35);
      } else {
        const p = (t - (c - .22)) / .44;
        if (p >= 0 && p <= 1) { x = x0 + (x1 - x0) * p; rev = type === "wipeRev"; }
      }
    });
    wipe.style.transform = "translateX(" + x + "px) skewX(-" + skew + "deg)";
    wrap.style.transform = rev ? "scaleX(-1)" : "none";
    flash.style.opacity = flashOp;
  }

  // すべての CSS アニメーションは一時停止させておき、seek() で時刻を直接指定する
  let ANIMS = null;
  function seek(ms) {
    if (!ANIMS) {
      ANIMS = document.getAnimations();
      counters = [...document.querySelectorAll("[data-count]")].map(el => ({ el, to: parseFloat(el.dataset.count), t0: sceneStart(el) + parseFloat(el.dataset.at), dur: parseFloat(el.dataset.dur) }));
      typers = [...document.querySelectorAll("[data-type]")].map(el => ({ el, text: [...el.dataset.type], t0: sceneStart(el) + parseFloat(el.dataset.at), dur: parseFloat(el.dataset.dur) }));
    }
    ANIMS.forEach(a => { a.currentTime = ms; });
    renderJS(ms / 1000);
  }

  window.Motion = { rand, lerpColor, scenes, sceneStart };
  window.seek = seek;
  window.PV_DURATION = DURATION;
  window.pvReady = (async () => {
    // ページ固有のスクリプトが要素を作り終えてから動きを確定させる
    if (document.readyState === "loading") await new Promise(r => document.addEventListener("DOMContentLoaded", r));
    await Promise.all(["500 40px NotoJP", "700 40px NotoJP", "900 40px NotoJP", "600 40px Mont", "900 40px Mont"].map(f => document.fonts.load(f, "あA")));
    await document.fonts.ready;
    seek(0);
  })();

  window.pvReady.then(() => {
    if (PARAMS.has("render")) return;
    if (PARAMS.has("t")) { seek(parseFloat(PARAMS.get("t")) * 1000); return; }
    const start = performance.now();
    const loop = now => { seek((now - start) % (DURATION * 1000)); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  });
})();
