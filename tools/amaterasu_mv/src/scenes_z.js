'use strict';
// ================================================================
function initScenes() {
  const pick = (arr, t) => { let r = null; for (const s of arr) if (t >= s.a && t < s.b) r = s; return r; };
  TIMELINE = {
    bg: t => { const s = pick(BGS, t); return s ? s.fn(t) : {}; },
    post: t => { const s = pick(POS, t); return s ? s.fn(t) : {}; },
    draw: (c, t) => { for (const s of SC) if (t >= s.a && t < s.b) { c.save(); s.fn(c, t); c.restore(); c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; try { c.letterSpacing = '0px'; } catch (e) { } } },
  };
}
