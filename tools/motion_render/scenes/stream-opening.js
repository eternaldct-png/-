// 配信オープニング・待機画面（16:9 / 10秒でつなぎ目なくループ）キャラ: 5
window.SCENE = {
  w: 1280, h: 720, dur: 10, poster: 2.2,
  draw(ctx, t) {
    const { w, h } = this, P = 10, C = 5;
    L.linear(ctx, w, h, ['#07060d', '#140814', '#0b0a1c'], 120);
    L.blobs(ctx, w, h, t, [
      { x: 0.72, y: 0.45, r: 0.42, color: 'rgba(239,68,68,0.55)', ax: 0.06, ay: 0.08 },
      { x: 0.25, y: 0.2, r: 0.4, color: 'rgba(124,58,237,0.45)', ax: 0.1, ay: 0.06, speed: 1 },
      { x: 0.5, y: 0.95, r: 0.35, color: 'rgba(236,72,153,0.35)', ax: 0.15, ay: 0.03, speed: 2 },
    ], P);

    // 遠近グリッドの床（10秒で4マス進む＝ループ）
    ctx.save();
    const hz = 470, vp = w * 0.62;
    ctx.beginPath(); ctx.rect(0, hz, w, h - hz); ctx.clip();
    const fg = ctx.createLinearGradient(0, hz, 0, h);
    fg.addColorStop(0, 'rgba(239,68,68,0)'); fg.addColorStop(1, 'rgba(239,68,68,0.55)');
    ctx.strokeStyle = fg; ctx.lineWidth = 2;
    for (let i = -16; i <= 16; i++) {
      ctx.beginPath(); ctx.moveTo(vp, hz); ctx.lineTo(vp + i * 140, h + 40); ctx.stroke();
    }
    const off = ((t / P) * 4) % 1;
    for (let i = 0; i < 9; i++) {
      const k = (i + off) / 9;
      const y = hz + Math.pow(k, 2.2) * (h - hz + 60);
      ctx.globalAlpha = k; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
    ctx.restore();
    const hzg = ctx.createLinearGradient(0, hz - 40, 0, hz + 30);
    hzg.addColorStop(0, 'rgba(239,68,68,0)'); hzg.addColorStop(0.6, 'rgba(255,120,120,0.35)'); hzg.addColorStop(1, 'rgba(239,68,68,0)');
    ctx.fillStyle = hzg; ctx.fillRect(0, hz - 40, w, 70);

    L.risingParticles(ctx, w, h, t, { n: 46, P, color: '#ffd1d1', sparkle: true, alpha: 0.7, seed: 4 });

    // キャラ背面の回転リング
    const cx = 960, cy = 315;
    ctx.save(); ctx.translate(cx, cy);
    ctx.rotate((t / P) * L.TAU);
    ctx.strokeStyle = 'rgba(255,255,255,0.18)'; ctx.lineWidth = 2; ctx.setLineDash([4, 14]);
    ctx.beginPath(); ctx.arc(0, 0, 270, 0, L.TAU); ctx.stroke();
    ctx.setLineDash([]);
    ctx.rotate(-(t / P) * L.TAU * 2);
    ctx.strokeStyle = 'rgba(239,68,68,0.7)'; ctx.lineWidth = 6; ctx.lineCap = 'round';
    for (let i = 0; i < 3; i++) { ctx.beginPath(); ctx.arc(0, 0, 230, i * L.TAU / 3, i * L.TAU / 3 + 1.1); ctx.stroke(); }
    ctx.restore();
    L.glowBlob(ctx, cx, cy + 40, 300, 'rgba(255,90,90,0.35)');

    L.groundShadow(ctx, cx, 650, 320, 0.6);
    L.liveChar(ctx, C, cx, 652, 590, t, { period: 2.5, glow: 'rgba(255,80,80,0.55)', glowBlur: 50 });

    // 左のタイトルブロック
    const lx = 96;
    const dot = 0.55 + 0.45 * Math.sin((t / 1.25) * L.TAU);
    L.panel(ctx, lx, 132, 214, 44, 22, { fill: 'rgba(239,68,68,0.16)', stroke: 'rgba(239,68,68,0.8)', lineWidth: 2 });
    ctx.save(); ctx.fillStyle = `rgba(255,70,70,${dot})`; ctx.shadowColor = '#ff4040'; ctx.shadowBlur = 14;
    ctx.beginPath(); ctx.arc(lx + 26, 154, 8, 0, L.TAU); ctx.fill(); ctx.restore();
    L.text(ctx, 'LIVE STREAM', lx + 44, 163, { font: L.font(800, 22, 'Montserrat'), color: '#ffd6d6', spacing: 3 });

    L.text(ctx, 'STARTING', lx - 4, 296, { font: L.font(900, 112, 'Montserrat'), grad: ['#ffffff', '#d1d5db', '#fca5a5'], spacing: 2, glow: 'rgba(255,80,80,0.5)', glowBlur: 30 });
    L.text(ctx, 'SOON', lx - 4, 404, { font: L.font(900, 112, 'Montserrat'), grad: ['#fca5a5', '#ef4444'], spacing: 6, glow: 'rgba(255,60,60,0.6)', glowBlur: 30 });
    // タイトルの光が走る（5秒ごと）
    const sw = L.prog(t % 5, 0.6, 1.6);
    if (sw > 0 && sw < 1) {
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      ctx.beginPath(); ctx.rect(lx, 190, 560, 230); ctx.clip();
      const sx = L.lerp(lx - 200, lx + 760, L.E.inOutCubic(sw));
      const g = ctx.createLinearGradient(sx - 80, 0, sx + 80, 0);
      g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,255,255,0.35)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g; ctx.transform(1, 0, -0.35, 1, 0, 0); ctx.fillRect(sx - 80 + 100, 190, 160, 230);
      ctx.restore();
    }
    const dots = '.'.repeat(Math.floor(t / 0.625) % 4);
    L.text(ctx, 'まもなく配信がはじまります' + dots, lx, 466, { font: L.font(700, 30), color: '#f3f4f6', spacing: 2 });
    L.waveBars(ctx, lx, 530, 420, 46, t, { n: 36, color: ['#ef4444', '#f9a8d4', '#a78bfa'], P: 2.5, mirror: true, alpha: 0.9 });

    // 右上の時刻
    L.text(ctx, 'TONIGHT 21:00 –', w - 60, 76, { font: L.font(800, 24, 'Montserrat'), color: 'rgba(255,255,255,0.85)', align: 'right', spacing: 3 });

    // 下のティッカー（10秒で1ユニット分流れる）
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(0, h - 58, w, 58);
    ctx.fillStyle = '#ef4444'; ctx.fillRect(0, h - 58, w, 3);
    L.panel(ctx, 0, h - 55, 168, 55, 0, { fill: '#ef4444' });
    L.text(ctx, 'TODAY', 84, h - 18, { font: L.font(900, 24, 'Montserrat'), align: 'center', spacing: 3 });
    ctx.beginPath(); ctx.rect(168, h - 55, w - 168, 55); ctx.clip();
    const unit = '歌枠 & 雑談 ♪　リクエスト曲 受付中　／　初見さん大歓迎　／　コメントで一緒に盛り上がろう　／　';
    const f = { font: L.font(700, 24), color: '#fff' };
    const uw = L.measure(ctx, unit, f);
    const x0 = 190 - ((t / P) * uw) % uw;
    for (let k = 0; k < 3; k++) L.text(ctx, unit, x0 + k * uw, h - 19, f);
    ctx.restore();
    L.vignette(ctx, w, h, 0.45);
  },
};
