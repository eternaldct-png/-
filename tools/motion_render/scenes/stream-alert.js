// ギフト・フォロー演出（1:1 / 7秒：フォロー通知 → ギフト通知）キャラ: 3
window.SCENE = {
  w: 720, h: 720, dur: 7, poster: 1.4,
  bg(ctx, t) {
    const { w, h } = this;
    L.linear(ctx, w, h, ['#1d1029', '#2a1533', '#120d1f'], 110);
    L.bokeh(ctx, w, h, t, { n: 20, P: 7, colors: ['#f9a8d4', '#fcd34d', '#c4b5fd', '#fda4af'], min: 18, max: 64, alpha: 0.3, seed: 21 });
    // 配信画面っぽいUI（左上の視聴者数・右下のコメント欄）
    L.panel(ctx, 22, 22, 96, 34, 8, { fill: '#ef4444' });
    L.text(ctx, '● LIVE', 70, 46, { font: L.font(800, 17, 'Montserrat'), align: 'center', spacing: 1 });
    L.panel(ctx, 126, 22, 104, 34, 8, { fill: 'rgba(0,0,0,0.45)' });
    L.text(ctx, '👀 1,248', 178, 46, { font: L.font(700, 17, 'Montserrat'), align: 'center' });
    const comments = ['こんばんは〜！', '今日も声きれい✨', '待ってました！', '888888', 'おつかれさま〜'];
    const sc = (t / 7) * comments.length;
    ctx.save(); ctx.beginPath(); ctx.rect(430, 560, 270, 140); ctx.clip();
    for (let i = 0; i < comments.length + 3; i++) {
      const y = 700 - ((i - sc + comments.length * 2) % comments.length) * 36;
      const a = L.clamp((y - 560) / 40);
      L.text(ctx, comments[i % comments.length], 440, y, { font: L.font(700, 18), color: `rgba(255,255,255,${0.75 * a})`, shadow: 'rgba(0,0,0,0.6)', shadowBlur: 6 });
    }
    ctx.restore();
  },
  draw(ctx, t) {
    const { w, h } = this, C = 3;
    this.bg(ctx, t);

    // ── フォロー通知（0.15〜3.2秒）
    if (t < 3.3) {
      const inP = L.prog(t, 0.15, 0.75), out = L.E.inBack(L.prog(t, 2.85, 3.25));
      const pop = L.E.outBack(inP);
      // 集中線
      ctx.save(); ctx.globalAlpha = 0.5 * (1 - out) * L.clamp(inP * 2);
      ctx.translate(360, 300); ctx.scale(pop, pop);
      L.rays(ctx, 0, 0, 18, 60, 520, 'rgba(249,168,212,0.28)', t * 0.5, 0.07);
      ctx.restore();
      L.glowBlob(ctx, 360, 300, 260 * pop, 'rgba(244,114,182,0.5)', 1 - out);
      // ハートが浮かぶ
      const r = L.rng(5);
      for (let i = 0; i < 14; i++) {
        const st = 0.4 + r() * 1.6, x = 60 + r() * 600, sz = 18 + r() * 22;
        const k = L.prog(t, st, st + 1.6);
        if (k <= 0 || k >= 1) continue;
        ctx.save(); ctx.globalAlpha = Math.sin(k * Math.PI) * 0.9 * (1 - out);
        ctx.fillStyle = i % 2 ? '#f472b6' : '#fda4af';
        L.heart(ctx, x + Math.sin(k * 6 + i) * 16, 560 - k * 360, sz); ctx.fill(); ctx.restore();
      }
      // キャラ（下から飛び出す）
      const cy = L.lerp(1640, 930, pop) + out * 760;
      L.liveChar(ctx, C, 360, cy, 860, t, { glow: 'rgba(255,182,213,0.7)', glowBlur: 40 });
      L.confetti(ctx, t, 0.55, 360, 330, { n: 70, seed: 9, vmin: 350, vmax: 800 });
      // 通知カード
      const cp = L.E.outBack(L.prog(t, 0.55, 1.05));
      ctx.save(); ctx.translate(360, 545); ctx.scale(cp * (1 - out), cp * (1 - out)); ctx.translate(-360, -545);
      L.panel(ctx, 70, 470, 580, 150, 28, { fill: ['#ffffff', '#fdf2f8'], shadow: 'rgba(80,0,60,0.45)', shadowBlur: 40 });
      L.panel(ctx, 70, 470, 580, 150, 28, { stroke: '#f472b6', lineWidth: 4 });
      L.pill(ctx, 'NEW FOLLOWER', 360, 476, { font: L.font(900, 22, 'Montserrat'), bg: '#ec4899', color: '#fff', spacing: 3, padX: 24 });
      L.charText(ctx, 'フォローありがとう！', 360, 556, t, { font: L.font(900, 46), color: '#1f1029', align: 'center', t0: 0.75, stagger: 0.04, dur: 0.35, mode: 'pop' });
      L.text(ctx, '@sample_user さん', 360, 598, { font: L.font(700, 24), color: '#db2777', align: 'center', alpha: L.prog(t, 1.1, 1.4) });
      ctx.restore();
    }

    // ── ギフト通知（3.4〜6.9秒）
    if (t >= 3.3) {
      const ip = L.E.outBack(L.prog(t, 3.4, 3.95));
      const out = L.E.inBack(L.prog(t, 6.45, 6.9));
      const bx = 500 + out * 500, open = L.E.outCubic(L.prog(t, 4.35, 4.75));
      const fall = L.prog(t, 3.55, 4.0);
      const by = fall < 1 ? L.lerp(-160, 545, L.E.inQuad(fall)) : 545 - Math.abs(Math.sin(L.prog(t, 4.0, 4.35) * Math.PI)) * 40 * (1 - L.prog(t, 4.0, 4.35));
      // 光（キャラより奥）
      L.glowBlob(ctx, bx, 470, 330, 'rgba(252,211,77,0.35)', L.prog(t, 4.1, 4.6) * (1 - out));
      if (t > 4.35) {
        ctx.save(); ctx.globalCompositeOperation = 'lighter';
        ctx.globalAlpha = 0.45 * (1 - out) * (1 - 0.5 * L.prog(t, 5.2, 6.0));
        L.rays(ctx, bx, by - 50, 14, 20, 340 * open, 'rgba(253,230,138,0.5)', -t * 0.6, 0.06);
        ctx.restore();
      }
      // キャラは左からスライドイン
      const cx = L.lerp(-200, 175, ip) - out * 420;
      L.groundShadow(ctx, cx, 666, 190, 0.5);
      L.liveChar(ctx, C, cx, 668, 440, t, { glow: 'rgba(255,214,140,0.6)', glowBlur: 30 });
      // プレゼント箱（落ちてきて、ふたが開く）
      const squash = 1 + 0.12 * Math.sin(L.prog(t, 4.0, 4.3) * Math.PI);
      ctx.save(); ctx.translate(bx, by + 90); ctx.scale(squash, 1 / squash); ctx.translate(-bx, -(by + 90));
      L.panel(ctx, bx - 95, by - 50, 190, 140, 14, { fill: ['#f472b6', '#be185d'], vertical: true, shadow: 'rgba(0,0,0,0.4)' });
      ctx.fillStyle = '#facc15'; ctx.fillRect(bx - 16, by - 50, 32, 140);
      ctx.restore();
      // ふた（右上へ飛んで消える）
      ctx.save(); ctx.globalAlpha = 1 - L.prog(t, 4.6, 4.85);
      ctx.translate(bx + open * 220, by - 60 - open * 260); ctx.rotate(open * 1.4);
      L.panel(ctx, -110, -26, 220, 46, 12, { fill: ['#f9a8d4', '#ec4899'], vertical: true });
      ctx.fillStyle = '#facc15'; ctx.fillRect(-18, -26, 36, 46);
      ctx.beginPath(); ctx.ellipse(-30, -38, 30, 16, -0.4, 0, L.TAU); ctx.ellipse(30, -38, 30, 16, 0.4, 0, L.TAU); ctx.fill();
      ctx.restore();
      // 星が飛び出す
      if (t > 4.35) {
        const r = L.rng(17);
        for (let i = 0; i < 16; i++) {
          const a = -Math.PI / 2 + (r() - 0.5) * 2.4, sp = 140 + r() * 220, d = L.E.outCubic(L.prog(t, 4.35, 5.3));
          const fade = (1 - L.prog(t, 5.6, 6.3)) * (1 - out);
          ctx.fillStyle = i % 3 ? '#fde68a' : '#f9a8d4';
          L.star(ctx, bx + Math.cos(a) * sp * d, by - 50 + Math.sin(a) * sp * d * 0.8, 12 + r() * 10, 5, 5, t * 2 + i); ctx.globalAlpha = fade; ctx.fill(); ctx.globalAlpha = 1;
        }
      }
      // 文字
      const tp = L.E.outBack(L.prog(t, 4.55, 5.0));
      ctx.save(); ctx.translate(360, 96); ctx.scale(tp * (1 - out), tp * (1 - out));
      L.pill(ctx, 'GIFT', 0, -6, { font: L.font(900, 24, 'Montserrat'), bg: '#facc15', color: '#3b1d00', spacing: 6, padX: 26 });
      L.text(ctx, 'ギフトありがとう！', 0, 72, { font: L.font(900, 56), color: '#fff', align: 'center', stroke: '#be185d', strokeWidth: 12, shadow: 'rgba(0,0,0,0.4)', shadowBlur: 10 });
      ctx.restore();
      // ×10 カウンター
      const cnt = Math.min(10, Math.max(1, Math.floor(L.lerp(1, 11, L.prog(t, 5.0, 5.7)))));
      const bump = 1 + 0.25 * (1 - L.prog((t - 5.0) % 0.07, 0, 0.07)) * (t < 5.7 ? 1 : 0);
      const cp = L.E.outBack(L.prog(t, 4.9, 5.2)) * (1 - out);
      if (cp > 0) {
        ctx.save(); ctx.translate(575, 330); ctx.scale(cp * bump, cp * bump); ctx.rotate(-0.12);
        L.text(ctx, '×' + cnt, 0, 0, { font: L.font(900, 84, 'Montserrat'), align: 'center', grad: ['#fef08a', '#f59e0b'], gradV: true, gradH: 70, stroke: '#7c2d12', strokeWidth: 10 });
        ctx.restore();
      }
      L.confetti(ctx, t, 5.7, 575, 300, { n: 50, seed: 33, colors: ['#fde68a', '#facc15', '#f9a8d4', '#fff'], vmin: 250, vmax: 650, life: 1.2 });
    }
    L.vignette(ctx, w, h, 0.35);
  },
};
