// モーション動画の共通描画ライブラリ（Canvas 2D・時刻 t から決定的に1フレームを描く）
const L = (() => {
  const TAU = Math.PI * 2;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const prog = (t, a, b) => clamp((t - a) / (b - a));

  const E = {
    linear: (x) => x,
    inQuad: (x) => x * x,
    outQuad: (x) => 1 - (1 - x) * (1 - x),
    inOutQuad: (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2),
    inCubic: (x) => x * x * x,
    outCubic: (x) => 1 - Math.pow(1 - x, 3),
    inOutCubic: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
    outQuart: (x) => 1 - Math.pow(1 - x, 4),
    outQuint: (x) => 1 - Math.pow(1 - x, 5),
    inOutQuart: (x) => (x < 0.5 ? 8 * x ** 4 : 1 - Math.pow(-2 * x + 2, 4) / 2),
    outExpo: (x) => (x === 1 ? 1 : 1 - Math.pow(2, -10 * x)),
    inExpo: (x) => (x === 0 ? 0 : Math.pow(2, 10 * x - 10)),
    inOutExpo: (x) => (x === 0 ? 0 : x === 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2),
    inOutSine: (x) => -(Math.cos(Math.PI * x) - 1) / 2,
    outBack: (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
    outBackBig: (x) => { const c1 = 2.6, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
    inBack: (x) => { const c1 = 1.70158, c3 = c1 + 1; return c3 * x * x * x - c1 * x * x; },
    outElastic: (x) => { const c4 = TAU / 3; return x === 0 ? 0 : x === 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - 0.75) * c4) + 1; },
  };

  // a〜b 秒で from→to（イージング付き）
  const anim = (t, a, b, from, to, ease = E.outCubic) => lerp(from, to, ease(prog(t, a, b)));
  // 入り（a〜a+din）と出（b-dout〜b）を持つ 0→1→0 のエンベロープ
  const env = (t, a, b, din = 0.4, dout = 0.4, eIn = E.outCubic, eOut = E.inCubic) => {
    if (t < a || t > b) return 0;
    const i = din > 0 ? eIn(prog(t, a, a + din)) : 1;
    const o = dout > 0 ? 1 - eOut(prog(t, b - dout, b)) : 1;
    return Math.min(i, o);
  };

  function rng(seed) {
    let a = seed >>> 0;
    return () => {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ── キャラクター ─────────────────────────────
  // head: 顔アイコン用の切り抜き（画像幅に対する比率）
  const CHARS = {
    1: { src: 'chars/c1.webp', head: [0.53, 0.2, 0.5] },
    2: { src: 'chars/c2.webp', head: [0.5, 0.29, 0.48] },
    3: { src: 'chars/c3.webp', head: [0.5, 0.19, 0.52] },
    4: { src: 'chars/c4.webp', head: [0.5, 0.18, 0.52] },
    5: { src: 'chars/c5.webp', head: [0.5, 0.21, 0.5] },
  };
  const images = {};

  function loadImage(src) {
    return new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im); im.onerror = () => rej(new Error('image ' + src));
      im.src = src;
    });
  }

  async function init() {
    for (const [id, c] of Object.entries(CHARS)) c.img = await loadImage(c.src);
    const faces = [
      '500 20px "Noto Sans JP"', '700 20px "Noto Sans JP"', '900 20px "Noto Sans JP"',
      '800 20px "M PLUS Rounded 1c"', '700 20px "Montserrat"', '800 20px "Montserrat"',
      '900 20px "Montserrat"', '700 20px "Zen Maru Gothic"', '400 20px "Dela Gothic One"',
    ];
    await Promise.all(faces.map((f) => document.fonts.load(f, 'あ亜A1')));
    await document.fonts.ready;
  }

  async function image(src) {
    if (!images[src]) images[src] = await loadImage(src);
    return images[src];
  }

  function charSize(id, h) {
    const im = CHARS[id].img;
    return { w: (im.width / im.height) * h, h };
  }

  // 足元中央 (x, y) を基準に、高さ h でキャラクターを描く
  function drawChar(ctx, id, x, y, h, o = {}) {
    const im = CHARS[id].img;
    const w = (im.width / im.height) * h;
    ctx.save();
    ctx.globalAlpha *= o.alpha ?? 1;
    ctx.translate(x, y);
    if (o.rot) ctx.rotate(o.rot);
    ctx.scale((o.sx ?? 1) * (o.flip ? -1 : 1), o.sy ?? 1);
    if (o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = o.glowBlur ?? 40; }
    if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = o.shadowBlur ?? 30; ctx.shadowOffsetY = o.shadowY ?? 14; }
    if (o.filter) ctx.filter = o.filter;
    ctx.drawImage(im, -w / 2, -h, w, h);
    ctx.restore();
    return w;
  }

  // 呼吸アニメーション（縦に少し伸び縮み）を加えたキャラ描画
  function liveChar(ctx, id, x, y, h, t, o = {}) {
    const period = o.period ?? 2.4;
    const ph = Math.sin((t / period) * TAU + (o.phase ?? 0));
    const sy = 1 + 0.014 * ph;
    const sx = 1 - 0.007 * ph;
    const bob = (o.bob ?? 0) * Math.sin((t / period) * TAU + (o.phase ?? 0) + 0.6);
    return drawChar(ctx, id, x, y + bob, h, { ...o, sx: (o.sx ?? 1) * sx, sy: (o.sy ?? 1) * sy });
  }

  // 円形にくり抜いた顔アイコン
  function drawHead(ctx, id, cx, cy, r, o = {}) {
    const c = CHARS[id]; const im = c.img;
    const [hx, hy, hr] = c.head;
    const sr = hr * im.width;
    const sx = hx * im.width - sr, sy = hy * im.height - sr;
    ctx.save();
    ctx.globalAlpha *= o.alpha ?? 1;
    if (o.ring) {
      ctx.beginPath(); ctx.arc(cx, cy, r + (o.ringWidth ?? 6), 0, TAU);
      ctx.fillStyle = o.ring; if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = 24; }
      ctx.fill(); ctx.shadowBlur = 0;
    }
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.closePath();
    ctx.fillStyle = o.bg ?? '#f3e8ff'; ctx.fill();
    ctx.clip();
    ctx.drawImage(im, sx, sy, sr * 2, sr * 2, cx - r, cy - r, r * 2, r * 2);
    ctx.restore();
  }

  function groundShadow(ctx, x, y, w, alpha = 0.35, color = '0,0,0') {
    ctx.save();
    const g = ctx.createRadialGradient(x, y, 0, x, y, w / 2);
    g.addColorStop(0, `rgba(${color},${alpha})`);
    g.addColorStop(1, `rgba(${color},0)`);
    ctx.fillStyle = g;
    ctx.translate(x, y); ctx.scale(1, 0.18); ctx.translate(-x, -y);
    ctx.beginPath(); ctx.arc(x, y, w / 2, 0, TAU); ctx.fill();
    ctx.restore();
  }

  // ── 文字 ─────────────────────────────────
  const font = (weight, size, family = 'Noto Sans JP') => `${weight} ${size}px "${family}", "Noto Sans JP", "Noto Color Emoji", sans-serif`;

  function setText(ctx, o) {
    ctx.font = o.font || font(700, 32);
    ctx.textAlign = o.align || 'left';
    ctx.textBaseline = o.baseline || 'alphabetic';
    ctx.letterSpacing = (o.spacing ?? 0) + 'px';
  }

  function measure(ctx, str, o = {}) {
    ctx.save(); setText(ctx, o);
    const w = ctx.measureText(str).width;
    ctx.restore();
    return w;
  }

  // o: font, color, align, baseline, spacing, alpha, stroke, strokeWidth, shadow, shadowBlur, grad([c1,c2]), glow
  function text(ctx, str, x, y, o = {}) {
    ctx.save();
    setText(ctx, o);
    ctx.globalAlpha *= o.alpha ?? 1;
    let fill = o.color || '#fff';
    if (o.grad) {
      const w = ctx.measureText(str).width;
      let x0 = x;
      if (ctx.textAlign === 'center') x0 = x - w / 2; else if (ctx.textAlign === 'right') x0 = x - w;
      const g = o.gradV ? ctx.createLinearGradient(0, y - (o.gradH ?? 60), 0, y) : ctx.createLinearGradient(x0, 0, x0 + w, 0);
      o.grad.forEach((c, i) => g.addColorStop(i / (o.grad.length - 1), c));
      fill = g;
    }
    if (o.stroke) {
      ctx.lineJoin = 'round'; ctx.miterLimit = 2;
      ctx.lineWidth = o.strokeWidth ?? 8; ctx.strokeStyle = o.stroke;
      if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = o.shadowBlur ?? 0; ctx.shadowOffsetY = o.shadowY ?? 6; ctx.shadowOffsetX = o.shadowX ?? 0; }
      ctx.strokeText(str, x, y);
      ctx.shadowColor = 'transparent';
      if (o.stroke2) { ctx.lineWidth = o.strokeWidth2 ?? 4; ctx.strokeStyle = o.stroke2; ctx.strokeText(str, x, y); }
    } else if (o.shadow) {
      ctx.shadowColor = o.shadow; ctx.shadowBlur = o.shadowBlur ?? 20; ctx.shadowOffsetY = o.shadowY ?? 0; ctx.shadowOffsetX = o.shadowX ?? 0;
    }
    if (o.glow) {
      ctx.shadowColor = o.glow; ctx.shadowBlur = o.glowBlur ?? 30;
      ctx.fillStyle = fill; ctx.fillText(str, x, y);
    }
    ctx.fillStyle = fill;
    ctx.fillText(str, x, y);
    ctx.restore();
  }

  // 1文字ずつ時間差で登場するテキスト。o.t0 開始、o.stagger 間隔、o.dur 各文字の尺、o.mode
  function charText(ctx, str, x, y, t, o = {}) {
    const chars = [...str];
    ctx.save(); setText(ctx, { ...o, align: 'left', spacing: 0 });
    const sp = o.spacing ?? 0;
    const widths = chars.map((c) => ctx.measureText(c).width + sp);
    ctx.restore();
    const total = widths.reduce((a, b) => a + b, 0) - sp;
    let cx = x;
    if (o.align === 'center') cx = x - total / 2; else if (o.align === 'right') cx = x - total;
    const t0 = o.t0 ?? 0, st = o.stagger ?? 0.05, d = o.dur ?? 0.45, mode = o.mode || 'rise';
    const out = o.out; // { t: 退場開始, stagger, dur, mode }
    chars.forEach((ch, i) => {
      const w = widths[i];
      let p = (o.ease || E.outBack)(prog(t, t0 + i * st, t0 + i * st + d));
      let a = clamp(prog(t, t0 + i * st, t0 + i * st + d * 0.6));
      if (out) {
        const q = E.inCubic(prog(t, out.t + i * (out.stagger ?? st), out.t + i * (out.stagger ?? st) + (out.dur ?? d)));
        a *= 1 - q; p = p * (1 - q) + (out.mode === 'fall' ? -q : 0);
      }
      if (a <= 0.001) { cx += w; return; }
      ctx.save();
      const mx = cx + (w - sp) / 2;
      ctx.translate(mx, y);
      if (mode === 'rise') ctx.translate(0, (1 - p) * (o.rise ?? 40));
      if (mode === 'drop') ctx.translate(0, -(1 - p) * (o.rise ?? 60));
      if (mode === 'pop') { const s = Math.max(0, p); ctx.scale(s, s); }
      if (mode === 'spin') { ctx.rotate((1 - p) * -0.8); ctx.scale(Math.max(0, p), Math.max(0, p)); }
      if (mode === 'blur') { ctx.filter = `blur(${(1 - a) * 12}px)`; ctx.scale(1 + (1 - a) * 0.6, 1 + (1 - a) * 0.6); }
      if (mode === 'slide') ctx.translate((1 - p) * (o.rise ?? 60), 0);
      if (o.wave) ctx.translate(0, Math.sin(t * (o.waveSpeed ?? 4) - i * 0.6) * o.wave);
      text(ctx, ch, 0, 0, { ...o, align: 'center', spacing: 0, alpha: (o.alpha ?? 1) * a });
      ctx.restore();
      cx += w;
    });
    return total;
  }

  // ── 図形 ─────────────────────────────────
  function rr(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function panel(ctx, x, y, w, h, r, o = {}) {
    ctx.save();
    ctx.globalAlpha *= o.alpha ?? 1;
    rr(ctx, x, y, w, h, r);
    if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = o.shadowBlur ?? 30; ctx.shadowOffsetY = o.shadowY ?? 12; }
    if (o.fill) {
      if (Array.isArray(o.fill)) {
        const g = o.vertical ? ctx.createLinearGradient(0, y, 0, y + h) : ctx.createLinearGradient(x, y, x + w, y + h);
        o.fill.forEach((c, i) => g.addColorStop(i / (o.fill.length - 1), c));
        ctx.fillStyle = g;
      } else ctx.fillStyle = o.fill;
      ctx.fill();
    }
    ctx.shadowColor = 'transparent';
    if (o.stroke) { ctx.lineWidth = o.lineWidth ?? 2; ctx.strokeStyle = o.stroke; ctx.stroke(); }
    ctx.restore();
  }

  // ラベル（角丸の帯＋文字）。中心 x, ベースライン y。幅を返す
  function pill(ctx, str, x, y, o = {}) {
    const f = o.font || font(800, 22);
    const w = measure(ctx, str, { font: f, spacing: o.spacing }) + (o.padX ?? 22) * 2;
    const size = parseInt(f.match(/(\d+)px/)[1], 10);
    const h = o.h ?? size * 1.75;
    let x0 = x - w / 2;
    if (o.align === 'left') x0 = x;
    panel(ctx, x0, y - h / 2 - size * 0.36, w, h, o.r ?? h / 2, { fill: o.bg || '#fff', stroke: o.border, lineWidth: o.borderWidth, alpha: o.alpha, shadow: o.shadow });
    text(ctx, str, x0 + w / 2, y, { font: f, color: o.color || '#000', align: 'center', spacing: o.spacing, alpha: o.alpha });
    return w;
  }

  function star(ctx, cx, cy, r1, r2, n = 5, rot = -Math.PI / 2) {
    ctx.beginPath();
    for (let i = 0; i < n * 2; i++) {
      const r = i % 2 ? r2 : r1; const a = rot + (i * Math.PI) / n;
      ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
    }
    ctx.closePath();
  }

  function heart(ctx, x, y, s) {
    ctx.beginPath();
    ctx.moveTo(x, y + s * 0.3);
    ctx.bezierCurveTo(x, y, x - s * 0.5, y - s * 0.1, x - s * 0.5, y + s * 0.25);
    ctx.bezierCurveTo(x - s * 0.5, y + s * 0.55, x - s * 0.1, y + s * 0.75, x, y + s * 0.95);
    ctx.bezierCurveTo(x + s * 0.1, y + s * 0.75, x + s * 0.5, y + s * 0.55, x + s * 0.5, y + s * 0.25);
    ctx.bezierCurveTo(x + s * 0.5, y - s * 0.1, x, y, x, y + s * 0.3);
    ctx.closePath();
  }

  // 4方向に光るきらめき
  function sparkle(ctx, x, y, s, color = '#fff', alpha = 1) {
    if (alpha <= 0 || s <= 0) return;
    ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = color;
    ctx.shadowColor = color; ctx.shadowBlur = s * 1.2;
    ctx.beginPath();
    ctx.moveTo(x, y - s);
    ctx.quadraticCurveTo(x, y, x + s, y);
    ctx.quadraticCurveTo(x, y, x, y + s);
    ctx.quadraticCurveTo(x, y, x - s, y);
    ctx.quadraticCurveTo(x, y, x, y - s);
    ctx.fill();
    ctx.restore();
  }

  function check(ctx, x, y, s, color, p = 1, width = 6) {
    if (p <= 0) return;
    const pts = [[x - s * 0.5, y], [x - s * 0.15, y + s * 0.35], [x + s * 0.55, y - s * 0.4]];
    polyline(ctx, pts, p, color, width);
  }

  function polyline(ctx, pts, p, color, width = 4) {
    let len = 0; const seg = [];
    for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); len += d; }
    let rem = len * clamp(p);
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length && rem > 0; i++) {
      const d = seg[i - 1]; const k = Math.min(1, rem / d);
      ctx.lineTo(lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k));
      rem -= d;
    }
    ctx.stroke(); ctx.restore();
  }

  function ring(ctx, cx, cy, r, p, width, color, start = -Math.PI / 2) {
    if (p <= 0) return;
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(cx, cy, r, start, start + TAU * clamp(p)); ctx.stroke(); ctx.restore();
  }

  function emoji(ctx, ch, x, y, size, o = {}) {
    ctx.save();
    ctx.globalAlpha *= o.alpha ?? 1;
    ctx.translate(x, y); if (o.rot) ctx.rotate(o.rot); if (o.scale !== undefined) ctx.scale(o.scale, o.scale);
    ctx.font = `${size}px "Noto Color Emoji"`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = o.shadowBlur ?? 16; ctx.shadowOffsetY = 6; }
    ctx.fillText(ch, 0, 0);
    ctx.restore();
  }

  // ── 背景 ─────────────────────────────────
  function linear(ctx, w, h, stops, angle = 90) {
    const a = (angle * Math.PI) / 180;
    const cx = w / 2, cy = h / 2, R = (Math.abs(Math.cos(a)) * w + Math.abs(Math.sin(a)) * h) / 2;
    const g = ctx.createLinearGradient(cx - Math.cos(a) * R, cy - Math.sin(a) * R, cx + Math.cos(a) * R, cy + Math.sin(a) * R);
    stops.forEach((c, i) => g.addColorStop(Array.isArray(c) ? c[0] : i / (stops.length - 1), Array.isArray(c) ? c[1] : c));
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  }

  // 同じ色の透明（黒い透明へのグラデーションだと中間がにごるため）
  function clear(color) {
    const m = color.match(/rgba?\(([^)]+)\)/);
    if (m) { const [r, g, b] = m[1].split(',').map((v) => v.trim()); return `rgba(${r},${g},${b},0)`; }
    if (color[0] === '#') { const n = parseInt(color.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},0)`; }
    return 'rgba(0,0,0,0)';
  }

  function glowBlob(ctx, x, y, r, color, alpha = 1) {
    if (alpha <= 0 || r <= 0) return;
    ctx.save(); ctx.globalAlpha *= alpha;
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, color); g.addColorStop(1, clear(color));
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
    ctx.restore();
  }

  // 周期 P 秒でループする、ゆっくり漂う光のかたまり
  function blobs(ctx, w, h, t, list, P = 10) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    list.forEach((b, i) => {
      const a = (t / P) * TAU * (b.speed ?? 1) + (b.phase ?? i * 1.7);
      const x = b.x * w + Math.cos(a) * (b.ax ?? 0.12) * w;
      const y = b.y * h + Math.sin(a * (b.fy ?? 1)) * (b.ay ?? 0.1) * h;
      glowBlob(ctx, x, y, b.r * Math.max(w, h), b.color, b.alpha ?? 0.6);
    });
    ctx.restore();
  }

  // 周期 P 秒でループする上昇パーティクル
  function risingParticles(ctx, w, h, t, o = {}) {
    const n = o.n ?? 40, P = o.P ?? 10, r = rng(o.seed ?? 7);
    const speedSet = o.speeds ?? [1, 2];
    ctx.save();
    for (let i = 0; i < n; i++) {
      const x0 = r() * w, ph = r(), sz = lerp(o.min ?? 1.5, o.max ?? 4, r());
      const sp = speedSet[Math.floor(r() * speedSet.length)];
      const k = (ph + (t / P) * sp) % 1;
      const y = h + 20 - k * (h + 40);
      const x = x0 + Math.sin(k * TAU * 2 + i) * (o.sway ?? 14);
      const a = Math.sin(k * Math.PI) * (o.alpha ?? 0.8);
      if (o.sparkle && i % 3 === 0) sparkle(ctx, x, y, sz * 2.4, o.color || '#fff', a);
      else { ctx.globalAlpha = a; ctx.fillStyle = o.color || '#fff'; ctx.beginPath(); ctx.arc(x, y, sz, 0, TAU); ctx.fill(); }
    }
    ctx.restore();
  }

  // ぼけた光（ボケ）。周期 P でループ
  function bokeh(ctx, w, h, t, o = {}) {
    const n = o.n ?? 18, P = o.P ?? 10, r = rng(o.seed ?? 11);
    const colors = o.colors ?? ['#ffd6a5', '#ffadad', '#bdb2ff'];
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const x = r() * w, y = r() * h, rad = lerp(o.min ?? 20, o.max ?? 70, r());
      const ph = r() * TAU, c = colors[i % colors.length];
      const dx = Math.cos((t / P) * TAU + ph) * (o.drift ?? 20), dy = Math.sin((t / P) * TAU * (i % 2 ? 1 : 2) + ph) * (o.drift ?? 20);
      const a = (o.alpha ?? 0.25) * (0.6 + 0.4 * Math.sin((t / P) * TAU * 2 + ph));
      ctx.globalAlpha = a;
      const g = ctx.createRadialGradient(x + dx, y + dy, rad * 0.55, x + dx, y + dy, rad);
      g.addColorStop(0, c); g.addColorStop(1, clear(c));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x + dx, y + dy, rad, 0, TAU); ctx.fill();
    }
    ctx.restore();
  }

  // 1点からはじける紙吹雪。t0 で発射
  function confetti(ctx, t, t0, x, y, o = {}) {
    const dt = t - t0; if (dt < 0 || dt > (o.life ?? 2.2)) return;
    const n = o.n ?? 60, r = rng(o.seed ?? 3);
    const colors = o.colors ?? ['#f472b6', '#facc15', '#60a5fa', '#34d399', '#c084fc', '#fb923c'];
    const g = o.gravity ?? 900;
    ctx.save();
    for (let i = 0; i < n; i++) {
      const ang = (o.angle ?? -Math.PI / 2) + (r() - 0.5) * (o.spread ?? Math.PI * 1.4);
      const sp = lerp(o.vmin ?? 300, o.vmax ?? 900, r());
      const drag = Math.exp(-dt * (o.drag ?? 1.6));
      const vx = Math.cos(ang) * sp, vy = Math.sin(ang) * sp;
      const k = (1 - drag) / (o.drag ?? 1.6);
      const px = x + vx * k, py = y + vy * k + 0.5 * g * dt * dt * 0.5;
      const rot = r() * TAU + dt * lerp(-8, 8, r());
      const s = lerp(o.smin ?? 8, o.smax ?? 16, r());
      ctx.globalAlpha = 1 - prog(dt, (o.life ?? 2.2) * 0.7, o.life ?? 2.2);
      ctx.fillStyle = colors[i % colors.length];
      ctx.save(); ctx.translate(px, py); ctx.rotate(rot); ctx.scale(1, Math.cos(dt * 9 + i));
      if (i % 4 === 0) { ctx.beginPath(); ctx.arc(0, 0, s * 0.4, 0, TAU); ctx.fill(); } else ctx.fillRect(-s / 2, -s * 0.3, s, s * 0.6);
      ctx.restore();
    }
    ctx.restore();
  }

  // 放射状の集中線・光線
  function rays(ctx, cx, cy, n, r0, r1, color, rot = 0, width = 0.06) {
    ctx.save(); ctx.fillStyle = color;
    for (let i = 0; i < n; i++) {
      const a = rot + (i / n) * TAU;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a - width) * r0, cy + Math.sin(a - width) * r0);
      ctx.lineTo(cx + Math.cos(a - width) * r1, cy + Math.sin(a - width) * r1);
      ctx.lineTo(cx + Math.cos(a + width) * r1, cy + Math.sin(a + width) * r1);
      ctx.lineTo(cx + Math.cos(a + width) * r0, cy + Math.sin(a + width) * r0);
      ctx.fill();
    }
    ctx.restore();
  }

  function vignette(ctx, w, h, a = 0.5) {
    const g = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.hypot(w, h) * 0.6);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
    ctx.save(); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); ctx.restore();
  }

  // 疑似オーディオスペクトラム（周期 P でループ）
  function waveBars(ctx, x, y, w, h, t, o = {}) {
    const n = o.n ?? 48, gap = o.gap ?? 3, bw = (w - gap * (n - 1)) / n, P = o.P ?? 2;
    ctx.save();
    for (let i = 0; i < n; i++) {
      const k = i / n;
      const v = 0.18 + 0.82 * Math.abs(Math.sin(t / P * TAU * 2 + k * 9) * 0.5 + Math.sin(t / P * TAU * 3 - k * 15 + 1) * 0.3 + Math.sin(t / P * TAU + k * 23) * 0.2) * (o.level ?? 1);
      const bh = Math.max(4, v * h * (1 - Math.abs(k - 0.5) * (o.taper ?? 0.8)));
      if (Array.isArray(o.color)) {
        const g = ctx.createLinearGradient(x, 0, x + w, 0); o.color.forEach((c, j) => g.addColorStop(j / (o.color.length - 1), c));
        ctx.fillStyle = g;
      } else ctx.fillStyle = o.color || '#fff';
      ctx.globalAlpha = o.alpha ?? 1;
      const bx = x + i * (bw + gap);
      if (o.mirror) rr(ctx, bx, y - bh / 2, bw, bh, bw / 2); else rr(ctx, bx, y - bh, bw, bh, bw / 2);
      ctx.fill();
    }
    ctx.restore();
  }

  // マウスカーソル
  function cursor(ctx, x, y, s = 1, pressed = 0) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s * (1 - pressed * 0.12), s * (1 - pressed * 0.12));
    ctx.beginPath();
    ctx.moveTo(0, 0); ctx.lineTo(0, 30); ctx.lineTo(7, 23); ctx.lineTo(12, 34); ctx.lineTo(17, 32); ctx.lineTo(12, 21); ctx.lineTo(22, 21); ctx.closePath();
    ctx.fillStyle = '#111'; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.5; ctx.lineJoin = 'round';
    ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = 8; ctx.shadowOffsetY = 3;
    ctx.stroke(); ctx.shadowColor = 'transparent'; ctx.fill(); ctx.stroke();
    ctx.restore();
  }

  // 手ぶれ・カメラシェイク
  function shake(t, amp, freq = 18, seed = 1) {
    return {
      x: amp * (Math.sin(t * freq + seed) * 0.6 + Math.sin(t * freq * 2.3 + seed * 3) * 0.4),
      y: amp * (Math.cos(t * freq * 1.3 + seed * 2) * 0.6 + Math.sin(t * freq * 1.9 + seed) * 0.4),
    };
  }

  // 吹き出し（角丸＋しっぽ）
  function bubble(ctx, x, y, w, h, o = {}) {
    ctx.save(); ctx.globalAlpha *= o.alpha ?? 1;
    const r = o.r ?? 22;
    rr(ctx, x, y, w, h, r);
    ctx.fillStyle = o.fill || '#fff';
    if (o.shadow) { ctx.shadowColor = o.shadow; ctx.shadowBlur = 24; ctx.shadowOffsetY = 8; }
    ctx.fill();
    if (o.tail) {
      const [tx, ty, side] = o.tail;
      ctx.beginPath();
      if (side === 'left') { ctx.moveTo(x + 4, ty - 14); ctx.lineTo(tx, ty); ctx.lineTo(x + 4, ty + 10); }
      else if (side === 'right') { ctx.moveTo(x + w - 4, ty - 14); ctx.lineTo(tx, ty); ctx.lineTo(x + w - 4, ty + 10); }
      else { ctx.moveTo(tx - 14, y + h - 4); ctx.lineTo(tx, ty); ctx.lineTo(tx + 14, y + h - 4); }
      ctx.fill();
    }
    ctx.restore();
  }

  return {
    TAU, clamp, lerp, prog, E, anim, env, rng, CHARS, init, image, charSize, drawChar, liveChar, drawHead, groundShadow,
    font, measure, text, charText, rr, panel, pill, star, heart, sparkle, check, polyline, ring, emoji,
    linear, clear, glowBlob, blobs, risingParticles, bokeh, confetti, rays, vignette, waveBars, cursor, shake, bubble,
  };
})();
