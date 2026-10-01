// 新曲リリース告知ショート（9:16 / 10秒）キャラ: 1 — 曲名・日付はサンプル
window.SCENE = {
  w: 720, h: 1280, dur: 10, poster: 6.0,
  glitch(ctx, amt, seed) {
    if (amt <= 0) return;
    const r = L.rng(seed), { w, h } = this;
    for (let i = 0; i < 9; i++) {
      const y = r() * h, sh = 8 + r() * 70, dx = (r() - 0.5) * 120 * amt;
      ctx.drawImage(ctx.canvas, 0, y, w, sh, dx, y, w, sh);
    }
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.25 * amt;
    ctx.fillStyle = '#ff2bd6'; ctx.fillRect(0, r() * h, w, 6 + r() * 30);
    ctx.fillStyle = '#22d3ee'; ctx.fillRect(0, r() * h, w, 6 + r() * 30);
    ctx.restore();
  },
  rgbText(ctx, str, x, y, o, split) {
    if (split > 0) {
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      L.text(ctx, str, x - split, y, { ...o, color: 'rgba(255,43,214,0.85)', grad: null, glow: null });
      L.text(ctx, str, x + split, y, { ...o, color: 'rgba(34,211,238,0.85)', grad: null, glow: null });
      ctx.restore();
    }
    L.text(ctx, str, x, y, o);
  },
  jacket(ctx, t, x, y, s) {
    ctx.save(); ctx.translate(x, y);
    ctx.shadowColor = 'rgba(255,43,214,0.55)'; ctx.shadowBlur = 60;
    ctx.fillStyle = '#000'; ctx.fillRect(-s / 2, -s / 2, s, s); ctx.shadowBlur = 0;
    ctx.beginPath(); ctx.rect(-s / 2, -s / 2, s, s); ctx.clip();
    const g = ctx.createLinearGradient(-s / 2, -s / 2, s / 2, s / 2);
    g.addColorStop(0, '#ff2bd6'); g.addColorStop(0.5, '#7c3aed'); g.addColorStop(1, '#22d3ee');
    ctx.fillStyle = g; ctx.fillRect(-s / 2, -s / 2, s, s);
    // 同心円
    ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 3;
    for (let i = 1; i < 9; i++) { ctx.beginPath(); ctx.arc(s * 0.12, -s * 0.05, i * s * 0.07 + ((t * 30) % (s * 0.07)), 0, L.TAU); ctx.stroke(); }
    // ハーフトーン
    ctx.fillStyle = 'rgba(0,0,0,0.18)';
    for (let yy = -s / 2; yy < s / 2; yy += 14) for (let xx = -s / 2; xx < s / 2; xx += 14) {
      const k = (xx + yy + s) / (2 * s); ctx.beginPath(); ctx.arc(xx, yy, 1 + k * 4, 0, L.TAU); ctx.fill();
    }
    L.drawChar(ctx, 1, s * 0.08, s * 1.05, s * 1.5, { glow: 'rgba(255,255,255,0.5)', glowBlur: 30 });
    L.text(ctx, 'ETERNAL', -s / 2 + 24, s / 2 - 74, { font: L.font(900, s * 0.12, 'Montserrat'), color: '#fff', spacing: 2, shadow: 'rgba(0,0,0,0.35)', shadowBlur: 12 });
    L.text(ctx, 'LIGHT', -s / 2 + 24, s / 2 - 22, { font: L.font(900, s * 0.12, 'Montserrat'), color: '#fff', spacing: 2, shadow: 'rgba(0,0,0,0.35)', shadowBlur: 12 });
    L.text(ctx, 'ETERNALd.c.t', s / 2 - 20, -s / 2 + 36, { font: L.font(800, s * 0.04, 'Montserrat'), color: 'rgba(255,255,255,0.9)', align: 'right', spacing: 2 });
    ctx.restore();
  },
  draw(ctx, t) {
    const { w, h } = this, E = L.E;
    const outP = L.prog(t, 9.45, 9.95);
    L.linear(ctx, w, h, ['#07020f', '#1a0630', '#04121a'], 100);
    L.blobs(ctx, w, h, t, [
      { x: 0.2, y: 0.3, r: 0.5, color: 'rgba(255,43,214,0.35)', ax: 0.1, ay: 0.08 },
      { x: 0.8, y: 0.7, r: 0.5, color: 'rgba(34,211,238,0.28)', ax: 0.1, ay: 0.08, speed: 1 },
    ], 10);
    // 斜めのストライプ
    ctx.save(); ctx.globalAlpha = 0.07; ctx.fillStyle = '#fff';
    for (let i = -20; i < 30; i++) { const x = i * 60 + ((t * 40) % 60); ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + 20, 0); ctx.lineTo(x + 20 - 700, h); ctx.lineTo(x - 700, h); ctx.fill(); }
    ctx.restore();

    // ── NEW RELEASE（叩きつけ → 上部へ縮小）
    const slam = E.outExpo(L.prog(t, 0.15, 0.55));
    const up = E.inOutCubic(L.prog(t, 1.3, 1.9));
    const hs = L.lerp(1, 0.42, up), hy = L.lerp(560, 118, up);
    const split = (1 - L.prog(t, 0.15, 0.9)) * 18 + (Math.sin(t * 37) > 0.97 ? 8 : 0);
    ctx.save(); ctx.translate(360, hy); ctx.scale(hs * L.lerp(2.4, 1, slam), hs * L.lerp(2.4, 1, slam));
    ctx.globalAlpha = slam;
    this.rgbText(ctx, 'NEW', 0, -20, { font: L.font(900, 190, 'Montserrat'), color: '#fff', align: 'center', spacing: 4 }, split);
    this.rgbText(ctx, 'RELEASE', 0, 150, { font: L.font(900, 136, 'Montserrat'), grad: ['#ff2bd6', '#c084fc', '#22d3ee'], align: 'center', spacing: 2 }, split);
    ctx.restore();

    // ── ジャケット＋レコード
    const jp = E.outBack(L.prog(t, 1.7, 2.4));
    const vp = E.outCubic(L.prog(t, 2.4, 3.2));
    if (t > 1.7) {
      const jx = 360 - vp * 70, jy = 560 + (1 - jp) * 1100;
      // レコード
      ctx.save(); ctx.translate(jx + vp * 190, jy); ctx.rotate(t * 3);
      ctx.fillStyle = '#0a0a0a'; ctx.beginPath(); ctx.arc(0, 0, 225, 0, L.TAU); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.08)'; ctx.lineWidth = 2;
      for (let i = 0; i < 12; i++) { ctx.beginPath(); ctx.arc(0, 0, 100 + i * 10, 0, L.TAU); ctx.stroke(); }
      ctx.strokeStyle = 'rgba(255,255,255,0.22)'; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 0, 180, -0.6, 0.2); ctx.stroke();
      const lg = ctx.createLinearGradient(-70, -70, 70, 70); lg.addColorStop(0, '#ff2bd6'); lg.addColorStop(1, '#22d3ee');
      ctx.fillStyle = lg; ctx.beginPath(); ctx.arc(0, 0, 70, 0, L.TAU); ctx.fill();
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(0, 0, 8, 0, L.TAU); ctx.fill();
      ctx.restore();
      ctx.save(); ctx.translate(jx, jy); ctx.rotate((1 - jp) * 0.4 - vp * 0.03); ctx.translate(-jx, -jy);
      this.jacket(ctx, t, jx, jy, 470);
      ctx.restore();
    }

    // ── 曲情報
    const ip = L.prog(t, 3.3, 3.8);
    L.text(ctx, '1st DIGITAL SINGLE', 360, 870, { font: L.font(800, 26, 'Montserrat'), color: '#22d3ee', align: 'center', spacing: 6, alpha: ip });
    L.charText(ctx, '『ETERNAL LIGHT』', 360, 942, t, { font: L.font(900, 54), color: '#fff', align: 'center', t0: 3.5, stagger: 0.04, dur: 0.35, mode: 'pop', glow: 'rgba(255,43,214,0.6)', glowBlur: 20 });
    // 日付（タイプライター）
    const date = '20XX.11.01 RELEASE';
    const n = Math.floor(L.lerp(0, date.length + 0.99, L.prog(t, 4.3, 5.2)));
    if (n > 0) {
      const str = date.slice(0, n) + (n < date.length && Math.floor(t * 8) % 2 ? '_' : '');
      L.panel(ctx, 110, 980, 500, 66, 10, { fill: 'rgba(255,255,255,0.08)', stroke: 'rgba(255,255,255,0.35)', lineWidth: 2, alpha: L.prog(t, 4.2, 4.4) });
      L.text(ctx, str, 360, 1025, { font: L.font(800, 34, 'Montserrat'), color: '#fff', align: 'center', spacing: 3 });
    }
    L.text(ctx, '各種音楽配信サービスにて配信スタート', 360, 1100, { font: L.font(700, 26), color: 'rgba(255,255,255,0.85)', align: 'center', alpha: L.prog(t, 5.3, 5.8) });

    // ── PRE-SAVE
    const cp = E.outBack(L.prog(t, 7.2, 7.6));
    if (cp > 0) {
      const pulse = 1 + 0.035 * Math.sin((t - 7.6) * 9) * (t > 7.6 ? 1 : 0);
      ctx.save(); ctx.translate(360, 1185); ctx.scale(cp * pulse, cp * pulse);
      L.panel(ctx, -200, -40, 400, 80, 40, { fill: ['#ff2bd6', '#a855f7', '#22d3ee'], shadow: 'rgba(255,43,214,0.5)', shadowBlur: 30 });
      L.text(ctx, '▶ PRE-SAVE NOW', 0, 12, { font: L.font(900, 32, 'Montserrat'), align: 'center', spacing: 2 });
      ctx.restore();
    }

    // フラッシュとグリッチ
    const flash = Math.max(1 - L.prog(t, 0.5, 0.8), 0) * (t > 0.5 ? 1 : 0) * 0.7 + Math.max(0, 1 - L.prog(t, 1.75, 2.0)) * (t > 1.75 ? 0.35 : 0);
    if (flash > 0) { ctx.fillStyle = `rgba(255,255,255,${flash})`; ctx.fillRect(0, 0, w, h); }
    const gl = [[0.5, 0.75], [1.65, 1.85], [3.45, 3.6], [6.6, 6.75], [9.3, 10]];
    gl.forEach(([a, b], i) => { if (t >= a && t <= b) this.glitch(ctx, 1 - L.prog(t, a, b) * (i === 4 ? 0 : 1) + (i === 4 ? L.prog(t, a, b) : 0), Math.floor(t * 24) + i * 100); });
    if (outP > 0) { ctx.fillStyle = `rgba(7,2,15,${E.inCubic(outP)})`; ctx.fillRect(0, 0, w, h); }
    // 走査線
    ctx.fillStyle = 'rgba(0,0,0,0.12)';
    for (let y = 0; y < h; y += 4) ctx.fillRect(0, y, w, 1);
  },
};
