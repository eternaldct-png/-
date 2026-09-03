// 共通: 端末判定 / ローダー / ナビ / カーソル / ページ遷移 / スクロール出現 / プレースホルダー生成
export const SITE = {
  // 既存サービスへのリンク（Cloudflare Pages の _redirects でも同じ先に飛ばしている）
  goodsUrl: 'https://kazuto-post-generator.onrender.com/goods',
  auditionUrl: 'https://kazuto-post-generator.onrender.com/audition',
  bookingUrl: 'https://eternal-interview-booking.onrender.com/',
  wpUrl: 'https://eternaldct.net',
  mail: 'eternal.d.c.t@gmail.com',
};

export const caps = (() => {
  const ua = navigator.userAgent;
  const coarse = matchMedia('(pointer: coarse)').matches;
  const mobile = coarse || /Android|iPhone|iPad|Mobile/i.test(ua);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cores = navigator.hardwareConcurrency || 4;
  const mem = navigator.deviceMemory || 4;
  // 0 = low(mobile/weak), 1 = mid, 2 = high
  let quality = 2;
  if (mobile) quality = 1;
  if (cores <= 4 && mem <= 4) quality = Math.min(quality, 1);
  if (mobile && (cores <= 4 || mem <= 3)) quality = 0;
  const dpr = Math.min(window.devicePixelRatio || 1, quality === 2 ? 2 : 1.5);
  return { mobile, reduced, quality, dpr, coarse };
})();

export function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch (e) { return false; }
}

// ── loader ────────────────────────────────
export const loader = {
  el: null, bar: null,
  set(p) { if (this.bar) this.bar.style.width = `${Math.round(p * 100)}%`; },
  done() { this.set(1); setTimeout(() => this.el && this.el.classList.add('done'), 250); },
};

// ── page transition ──────────────────────
function bindTransitions() {
  const veil = document.getElementById('veil');
  if (!veil) return;
  document.querySelectorAll('a[href]').forEach(a => {
    const href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || a.target === '_blank') return;
    if (/^https?:/.test(href) && !href.startsWith(location.origin)) return;
    a.addEventListener('click', e => {
      if (e.metaKey || e.ctrlKey) return;
      e.preventDefault();
      veil.classList.add('on');
      setTimeout(() => { location.href = href; }, 480);
    });
  });
  window.addEventListener('pageshow', () => veil.classList.remove('on'));
}

// ── cursor ────────────────────────────────
function bindCursor() {
  const c = document.getElementById('cursor');
  if (!c || caps.coarse) return;
  let x = innerWidth / 2, y = innerHeight / 2, tx = x, ty = y;
  addEventListener('pointermove', e => { tx = e.clientX; ty = e.clientY; }, { passive: true });
  const tick = () => {
    x += (tx - x) * 0.35; y += (ty - y) * 0.35;
    c.style.transform = `translate(${x}px, ${y}px) translate(-50%,-50%)`;
    requestAnimationFrame(tick);
  };
  tick();
  document.querySelectorAll('a, button, .gl-img, .pill, [data-cursor]').forEach(el => {
    el.addEventListener('pointerenter', () => c.classList.add('big'));
    el.addEventListener('pointerleave', () => c.classList.remove('big'));
  });
}

// ── reveal on scroll ─────────────────────
function bindReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) { els.forEach(e => e.classList.add('in')); return; }
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
  }, { threshold: 0.15 });
  els.forEach(e => io.observe(e));
}

export function initCommon() {
  loader.el = document.getElementById('loader');
  loader.bar = loader.el && loader.el.querySelector('.bar i');
  if (!hasWebGL()) document.documentElement.classList.add('no-webgl');
  bindTransitions();
  bindCursor();
  bindReveal();
  const here = location.pathname.replace(/index\.html$/, '');
  document.querySelectorAll('.nav a').forEach(a => {
    const p = a.getAttribute('href');
    if (p && (p === here || (p === './' && (here === '/' || here === '')) || (p !== './' && here.endsWith(p)))) a.classList.add('active');
  });
}

// ── placeholder texture (ロゴや写真が届くまでの仮画像) ──
export function placeholderCanvas(label, sub, w = 1024, h = 1280, seed = 1) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 0, w, h);
  grd.addColorStop(0, '#2c2c2c'); grd.addColorStop(1, '#0b0b0b');
  g.fillStyle = grd; g.fillRect(0, 0, w, h);
  // noise grain
  const img = g.getImageData(0, 0, w, h); const d = img.data;
  let s = seed * 9301 + 49297;
  for (let i = 0; i < d.length; i += 4) {
    s = (s * 9301 + 49297) % 233280; const n = (s / 233280 - 0.5) * 22;
    d[i] += n; d[i + 1] += n; d[i + 2] += n;
  }
  g.putImageData(img, 0, 0);
  // soft light from top-right
  const rg = g.createRadialGradient(w * 0.78, h * 0.22, 0, w * 0.78, h * 0.22, w * 0.9);
  rg.addColorStop(0, 'rgba(255,255,255,0.22)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, w, h);
  // concentric rings
  g.strokeStyle = 'rgba(255,255,255,0.14)'; g.lineWidth = 2;
  for (let r = 70; r < Math.max(w, h); r += 70) { g.beginPath(); g.arc(w * 0.7, h * 0.3, r, 0, Math.PI * 2); g.stroke(); }
  // big outlined label
  g.font = `200 ${Math.floor(w * 0.22)}px Inter, Helvetica, Arial, sans-serif`;
  g.textBaseline = 'alphabetic';
  g.fillStyle = 'rgba(255,255,255,0.10)'; g.fillText(label, w * 0.06, h * 0.82);
  g.strokeStyle = 'rgba(255,255,255,0.85)'; g.lineWidth = 5;
  g.strokeText(label, w * 0.06, h * 0.82);
  g.fillStyle = 'rgba(255,255,255,0.9)';
  g.font = `300 ${Math.floor(w * 0.035)}px "Noto Sans JP", "Hiragino Sans", sans-serif`;
  g.fillText(sub, w * 0.065, h * 0.88);
  g.fillStyle = 'rgba(255,255,255,0.5)';
  g.font = `400 ${Math.floor(w * 0.022)}px Inter, Helvetica, Arial, sans-serif`;
  g.fillText('PLACEHOLDER  —  replace with photo', w * 0.065, h * 0.92);
  return c;
}

export const lerp = (a, b, t) => a + (b - a) * t;
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
