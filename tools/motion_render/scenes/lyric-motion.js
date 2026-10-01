// リリックモーション（16:9 / 12秒）キャラ: 1 — 歌詞はオリジナル
window.SCENE = {
  w: 1280, h: 720, dur: 12, poster: 7.4,
  draw(ctx, t) {
    const { w, h } = this, C = 1, E = L.E;
    const BEAT = 0.6;
    const bp = Math.pow(1 - ((t % BEAT) / BEAT), 3); // 拍ごとのパルス
    const fadeAll = 1 - E.inCubic(L.prog(t, 11.4, 11.95));

    L.linear(ctx, w, h, ['#050816', '#0f1d4a', '#2a1b5e'], 100);
    // 星
    const r = L.rng(42);
    for (let i = 0; i < 140; i++) {
      const x = r() * w, y = r() * h * 0.85, s = 0.6 + r() * 1.6, ph = r() * 10;
      const tw = 0.35 + 0.65 * Math.abs(Math.sin(t * (0.8 + r()) + ph));
      ctx.globalAlpha = tw * 0.8; ctx.fillStyle = '#dbeafe';
      ctx.beginPath(); ctx.arc((x - t * 6 + w) % w, y, s, 0, L.TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;
    // 流れ星
    [[3.6, 900, 60], [8.2, 1100, 30]].forEach(([st, x0, y0]) => {
      const k = L.prog(t, st, st + 0.7);
      if (k <= 0 || k >= 1) return;
      const x = x0 - k * 420, y = y0 + k * 220;
      const g = ctx.createLinearGradient(x, y, x + 140, y - 74);
      g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.strokeStyle = g; ctx.lineWidth = 3; ctx.globalAlpha = Math.sin(k * Math.PI);
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 140, y - 74); ctx.stroke(); ctx.globalAlpha = 1;
    });

    // 月（キャラの後ろ）
    L.glowBlob(ctx, 330, 250, 330 + bp * 16, 'rgba(96,165,250,0.35)');
    ctx.save(); ctx.shadowColor = 'rgba(191,219,254,0.9)'; ctx.shadowBlur = 60;
    const mg = ctx.createRadialGradient(300, 220, 10, 330, 250, 175);
    mg.addColorStop(0, '#f8fafc'); mg.addColorStop(1, '#bfdbfe');
    ctx.fillStyle = mg; ctx.beginPath(); ctx.arc(330, 250, 175, 0, L.TAU); ctx.fill(); ctx.restore();

    // キャラ（青いリムライト）
    const ci = 1;
    L.liveChar(ctx, C, 330, 790 + (1 - ci) * 80, 800, t, { period: BEAT * 4, glow: 'rgba(96,165,250,0.85)', glowBlur: 46, alpha: ci });
    // 足元の霧
    const fg = ctx.createLinearGradient(0, 560, 0, h);
    fg.addColorStop(0, 'rgba(15,29,74,0)'); fg.addColorStop(1, 'rgba(15,29,74,0.95)');
    ctx.fillStyle = fg; ctx.fillRect(0, 560, w, h - 560);

    // スペクトラム
    L.waveBars(ctx, 590, 668, 560, 60, t, { n: 56, P: BEAT * 4, color: ['#60a5fa', '#a78bfa', '#f0abfc'], alpha: 0.55 + 0.3 * bp, level: 0.7 + 0.3 * bp });

    // 歌詞
    const X = 870;
    ctx.save(); ctx.globalAlpha = fadeAll;
    const lineOut = (a, b) => ({ t: b, stagger: 0.02, dur: 0.35 });
    // 1
    if (t < 3.3) {
      L.charText(ctx, '眠れない夜を', X, 380, t, { font: L.font(900, 76), color: '#f8fafc', align: 'center', t0: 0.5, stagger: 0.12, dur: 0.5, mode: 'blur', glow: 'rgba(147,197,253,0.8)', glowBlur: 24, spacing: 12, out: lineOut(0, 2.8) });
    }
    // 2
    if (t > 2.9 && t < 6.1) {
      L.charText(ctx, 'ひとつずつ', X, 300, t, { font: L.font(700, 44), color: '#c7d2fe', align: 'center', t0: 3.0, stagger: 0.08, dur: 0.4, mode: 'rise', spacing: 20, out: lineOut(0, 5.6) });
      L.charText(ctx, '星に変えて', X, 420, t, { font: L.font(900, 92), color: '#f8fafc', align: 'center', t0: 3.6, stagger: 0.12, dur: 0.5, mode: 'pop', glow: 'rgba(147,197,253,0.8)', glowBlur: 24, spacing: 8, out: lineOut(0, 5.6) });
      // 「星」から星が舞い上がる
      const rs = L.rng(8);
      for (let i = 0; i < 14; i++) {
        const st = 3.7 + rs() * 1.2, k = L.prog(t, st, st + 1.3);
        if (k <= 0 || k >= 1) { rs(); rs(); continue; }
        const ang = -Math.PI / 2 + (rs() - 0.5) * 1.6, d = 40 + rs() * 200;
        L.sparkle(ctx, X - 175 + Math.cos(ang) * d * E.outCubic(k), 370 + Math.sin(ang) * d * E.outCubic(k), 12 * (1 - k) + 4, '#fde68a', 1 - k);
      }
    }
    // 3
    if (t > 5.7 && t < 8.9) {
      L.charText(ctx, '君に届くまで', X, 300, t, { font: L.font(700, 44), color: '#c7d2fe', align: 'center', t0: 5.8, stagger: 0.08, dur: 0.4, mode: 'rise', spacing: 20, out: lineOut(0, 8.4) });
      L.charText(ctx, '歌うよ', X, 440, t, { font: L.font(900, 120), grad: ['#93c5fd', '#e9d5ff', '#f9a8d4'], align: 'center', t0: 6.5, stagger: 0.16, dur: 0.55, mode: 'drop', spacing: 20, glow: 'rgba(196,181,253,0.7)', glowBlur: 30, wave: 6, out: lineOut(0, 8.4) });
    }
    // 4
    if (t > 8.5) {
      const ep = E.outExpo(L.prog(t, 8.7, 9.6));
      ctx.save(); ctx.translate(X, 380); ctx.scale(1.3 - 0.3 * ep + bp * 0.015, 1.3 - 0.3 * ep + bp * 0.015);
      L.text(ctx, 'ETERNAL', 0, 0, { font: L.font(900, 116, 'Montserrat'), grad: ['#bfdbfe', '#ffffff', '#f5d0fe'], align: 'center', spacing: L.lerp(40, 10, ep), alpha: ep, glow: 'rgba(147,197,253,0.9)', glowBlur: 34 });
      ctx.restore();
      const lw = 460 * E.outCubic(L.prog(t, 9.3, 10.0));
      ctx.fillStyle = 'rgba(219,234,254,0.8)'; ctx.fillRect(X - lw / 2, 412, lw, 2);
      L.charText(ctx, '永遠に', X, 476, t, { font: L.font(700, 46), color: '#e0e7ff', align: 'center', t0: 9.6, stagger: 0.18, dur: 0.6, mode: 'blur', spacing: 48 });
    }
    ctx.restore();

    // クレジットとシークバー
    ctx.globalAlpha = fadeAll * L.prog(t, 0.3, 1.0);
    L.text(ctx, '♪ Original Song  /  ETERNALd.c.t', 40, 54, { font: L.font(700, 20, 'Montserrat'), color: 'rgba(219,234,254,0.85)', spacing: 1 });
    ctx.fillStyle = 'rgba(255,255,255,0.18)'; ctx.fillRect(40, 694, 1200, 3);
    ctx.fillStyle = '#93c5fd'; ctx.fillRect(40, 694, 1200 * (t / 12), 3);
    ctx.beginPath(); ctx.arc(40 + 1200 * (t / 12), 695.5, 6, 0, L.TAU); ctx.fill();
    ctx.globalAlpha = 1;
    L.vignette(ctx, w, h, 0.5);
  },
};
