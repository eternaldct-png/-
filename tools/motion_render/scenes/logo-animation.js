// ロゴアニメーション（16:9 / 6秒）キャラ: 5 — ∞（ETERNAL）を描くエンブレム＋社名ロゴ
window.SCENE = {
  w: 1280, h: 720, dur: 6, poster: 4.2,
  infinity(ctx, cx, cy, a, p, width) {
    const pts = [];
    for (let i = 0; i <= 240; i++) {
      const th = (i / 240) * L.TAU + Math.PI / 2;
      const d = 1 + Math.sin(th) ** 2;
      pts.push([cx + (a * Math.cos(th)) / d, cy + (a * Math.sin(th) * Math.cos(th)) / d]);
    }
    const g = ctx.createLinearGradient(cx - a, 0, cx + a, 0);
    g.addColorStop(0, '#a78bfa'); g.addColorStop(0.5, '#f0abfc'); g.addColorStop(1, '#fb7185');
    ctx.save(); ctx.shadowColor = 'rgba(240,171,252,0.8)'; ctx.shadowBlur = 18;
    L.polyline(ctx, pts, p, g, width);
    ctx.restore();
    if (p > 0 && p < 1) {
      const k = Math.min(pts.length - 1, Math.floor(p * (pts.length - 1)));
      L.sparkle(ctx, pts[k][0], pts[k][1], 16, '#fff', 1);
    }
  },
  draw(ctx, t) {
    const { w, h } = this, E = L.E, C = 5;
    L.linear(ctx, w, h, ['#08070d', '#120d1d', '#08070d'], 90);
    const end = E.inCubic(L.prog(t, 5.3, 5.85)); // 収束して消える
    const shift = E.inOutCubic(L.prog(t, 3.0, 3.7)) * (1 - end);
    const cx = L.lerp(640, 450, shift);

    // 中央の横線（最初に伸び、最後に縮む）
    const lineP = E.outExpo(L.prog(t, 0.05, 0.7)) * (1 - E.inExpo(L.prog(t, 1.0, 1.4))) + E.outExpo(L.prog(t, 5.55, 5.8)) * (1 - L.prog(t, 5.8, 6.0));
    if (lineP > 0.001) {
      const lg = ctx.createLinearGradient(640 - 500, 0, 640 + 500, 0);
      lg.addColorStop(0, 'rgba(167,139,250,0)'); lg.addColorStop(0.5, '#fff'); lg.addColorStop(1, 'rgba(251,113,133,0)');
      ctx.fillStyle = lg; ctx.fillRect(640 - 500 * lineP, 359, 1000 * lineP, 2);
    }

    ctx.save(); ctx.globalAlpha = 1 - end;
    ctx.translate(640, 360); ctx.scale(1 - end * 0.3, 1 - end * 0.9); ctx.translate(-640, -360);
    // エンブレム：リング＋∞
    const ey = 240;
    L.glowBlob(ctx, cx, ey, 220, 'rgba(167,139,250,0.25)', L.prog(t, 0.8, 1.6));
    L.ring(ctx, cx, ey, 104, E.inOutCubic(L.prog(t, 0.7, 1.5)), 3, 'rgba(255,255,255,0.85)');
    L.ring(ctx, cx, ey, 118, E.inOutCubic(L.prog(t, 0.85, 1.7)), 1.5, 'rgba(255,255,255,0.3)', Math.PI / 2);
    this.infinity(ctx, cx, ey, 78, E.inOutCubic(L.prog(t, 1.0, 2.0)), 9);

    // 社名
    const word = 'ETERNAL';
    const f = L.font(900, 92, 'Montserrat');
    const fw = L.measure(ctx, word + ' ', { font: f, spacing: 10 }) + L.measure(ctx, 'd.c.t', { font: L.font(700, 64, 'Montserrat'), spacing: 6 });
    const x0 = cx - fw / 2;
    ctx.save(); ctx.beginPath(); ctx.rect(0, 360, w, 110); ctx.clip();
    L.charText(ctx, word, x0, 450, t, { font: f, color: '#fff', t0: 1.6, stagger: 0.05, dur: 0.5, mode: 'rise', rise: 100, spacing: 10, ease: E.outCubic });
    const dx = x0 + L.measure(ctx, word + ' ', { font: f, spacing: 10 });
    L.charText(ctx, 'd.c.t', dx, 450, t, { font: L.font(700, 64, 'Montserrat'), grad: ['#c4b5fd', '#f9a8d4'], t0: 2.0, stagger: 0.06, dur: 0.5, mode: 'rise', rise: 100, spacing: 6, ease: E.outCubic });
    ctx.restore();
    // タグライン
    const tl = L.prog(t, 2.5, 3.0);
    L.text(ctx, 'MUSIC  ·  LIVE  ·  AI  ·  GOODS', cx, 512, { font: L.font(700, 22, 'Montserrat'), color: 'rgba(233,213,255,0.85)', align: 'center', spacing: L.lerp(18, 8, E.outCubic(tl)), alpha: tl });
    ctx.restore();

    // キャラ（右からリムライト付きで登場）
    const cp = E.outCubic(L.prog(t, 3.1, 3.9)) * (1 - E.inCubic(L.prog(t, 5.0, 5.4)));
    if (cp > 0) {
      const x = 1035 + (1 - cp) * 120;
      L.glowBlob(ctx, x, 380, 300, 'rgba(251,113,133,0.28)', cp);
      L.liveChar(ctx, C, x, 700, 600, t, { alpha: cp, glow: 'rgba(240,171,252,0.6)', glowBlur: 40 });
      L.groundShadow(ctx, x, 700, 280, 0.5 * cp);
    }
    // 粒子
    const r = L.rng(3);
    for (let i = 0; i < 26; i++) {
      const x = r() * w, y = r() * h, ph = r() * L.TAU;
      L.sparkle(ctx, x, y + Math.sin(t + ph) * 10, 3 + r() * 4, '#e9d5ff', 0.5 * Math.abs(Math.sin(t * 1.4 + ph)) * L.prog(t, 1.0, 2.0) * (1 - end));
    }
    L.vignette(ctx, w, h, 0.5);
  },
};
