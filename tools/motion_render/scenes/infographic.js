// サービス紹介（数字が動くインフォグラフィック）（16:9 / 12秒）キャラ: 4 — 数値はイメージ
window.SCENE = {
  w: 1280, h: 720, dur: 12, poster: 3.6,
  title(ctx, t, a, b, num, str) {
    const p = L.E.outCubic(L.prog(t, a, a + 0.5)) * (1 - L.E.inCubic(L.prog(t, b - 0.35, b)));
    if (p <= 0) return;
    ctx.save(); ctx.globalAlpha = p; ctx.translate((1 - p) * 40, 0);
    L.panel(ctx, 330, 52, 64, 64, 16, { fill: ['#0ea5e9', '#6366f1'] });
    L.text(ctx, num, 362, 96, { font: L.font(900, 30, 'Montserrat'), align: 'center' });
    L.text(ctx, str, 414, 97, { font: L.font(900, 40), color: '#0f172a' });
    ctx.restore();
  },
  draw(ctx, t) {
    const { w, h } = this, C = 4, E = L.E;
    const BLUE = '#0ea5e9', IND = '#6366f1', INK = '#0f172a', MUTED = '#64748b';
    ctx.fillStyle = '#f8fafc'; ctx.fillRect(0, 0, w, h);
    // 方眼
    ctx.strokeStyle = 'rgba(14,165,233,0.08)'; ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x + 0.5, 0); ctx.lineTo(x + 0.5, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y + 0.5); ctx.lineTo(w, y + 0.5); ctx.stroke(); }
    L.glowBlob(ctx, 180, 420, 300, 'rgba(14,165,233,0.16)');

    // 左のガイド役キャラ
    const cIn = E.outBack(L.prog(t, 0.0, 0.5));
    const cOut = E.inCubic(L.prog(t, 11.45, 11.9));
    L.groundShadow(ctx, 160, 702, 220, 0.25);
    L.liveChar(ctx, C, 160 - cOut * 300, 704 + (1 - cIn) * 600, 600, t, { shadow: 'rgba(15,23,42,0.15)', shadowBlur: 24 });
    // 吹き出し
    const tips = [[0.5, 3.9, 'まずは時間の変化！'], [4.3, 7.7, '浮いた時間は…'], [8.1, 11.3, '導入はかんたん4ステップ']];
    tips.forEach(([a, b, s]) => {
      const p = E.outBack(L.prog(t, a, a + 0.35)) * (1 - E.inBack(L.prog(t, b - 0.3, b)));
      if (p <= 0) return;
      ctx.save(); ctx.translate(170, 70); ctx.scale(p, p);
      const bw = L.measure(ctx, s, { font: L.font(700, 20) }) + 36;
      L.bubble(ctx, -bw / 2, -26, bw, 50, { fill: INK, r: 25, tail: [0, 44, 'bottom'] });
      L.text(ctx, s, 0, 6, { font: L.font(700, 20), color: '#fff', align: 'center' });
      ctx.restore();
    });

    // ── 1. 棒グラフ（0.4〜4.1）
    if (t < 4.2) {
      this.title(ctx, t, 0.4, 4.1, '01', '月の事務作業時間');
      const out = E.inCubic(L.prog(t, 3.75, 4.1));
      ctx.save(); ctx.globalAlpha = 1 - out;
      const base = 600;
      ctx.fillStyle = '#cbd5e1'; ctx.fillRect(400, base, 760 * E.outCubic(L.prog(t, 0.6, 1.1)), 3);
      const bars = [['導入前', 40, '#94a3b8', 0.9], ['導入後', 12, BLUE, 1.6]];
      bars.forEach(([lab, v, col, st], i) => {
        const p = E.outCubic(L.prog(t, st, st + 0.9));
        const x = 470 + i * 300, bh = (v / 40) * 340 * p;
        if (col === BLUE) L.panel(ctx, x, base - bh, 150, bh, 12, { fill: [IND, BLUE], vertical: true, shadow: 'rgba(14,165,233,0.35)', shadowBlur: 20 });
        else L.panel(ctx, x, base - bh, 150, bh, 12, { fill: col });
        if (p > 0) L.text(ctx, `${Math.round(v * p)}h`, x + 75, base - bh - 18, { font: L.font(900, 52, 'Montserrat'), color: col === BLUE ? BLUE : MUTED, align: 'center' });
        L.text(ctx, lab, x + 75, base + 44, { font: L.font(700, 26), color: INK, align: 'center', alpha: L.prog(t, st, st + 0.3) });
      });
      // 矢印と削減率
      const ap = L.prog(t, 2.5, 3.0);
      const pts = [];
      for (let k = 0; k <= 30; k++) { const u = k / 30; pts.push([(1 - u) ** 2 * 630 + 2 * u * (1 - u) * 760 + u * u * 830, (1 - u) ** 2 * 230 + 2 * u * (1 - u) * 200 + u * u * 392]); }
      ctx.save(); ctx.setLineDash([10, 10]); L.polyline(ctx, pts, E.outCubic(ap), IND, 5); ctx.restore();
      if (ap >= 1) { ctx.fillStyle = IND; ctx.beginPath(); ctx.moveTo(830, 420); ctx.lineTo(813, 390); ctx.lineTo(847, 390); ctx.closePath(); ctx.fill(); }
      const bp = E.outBackBig(L.prog(t, 2.8, 3.15));
      if (bp > 0) {
        ctx.save(); ctx.translate(1010, 220); ctx.scale(bp, bp); ctx.rotate(-0.08);
        ctx.fillStyle = '#f43f5e'; L.star(ctx, 0, 0, 96, 80, 18); ctx.fill();
        L.text(ctx, '−70%', 0, 18, { font: L.font(900, 50, 'Montserrat'), color: '#fff', align: 'center' });
        ctx.restore();
      }
      L.text(ctx, '※数値はイメージです', 1240, 690, { font: L.font(500, 16), color: MUTED, align: 'right', alpha: L.prog(t, 1.0, 1.4) });
      ctx.restore();
    }

    // ── 2. ドーナツグラフ（4.2〜7.8）
    if (t > 4.1 && t < 7.9) {
      this.title(ctx, t, 4.2, 7.8, '02', '浮いた時間の使い道');
      const out = E.inCubic(L.prog(t, 7.45, 7.8));
      ctx.save(); ctx.globalAlpha = 1 - out;
      const segs = [['営業・商談', 45, BLUE], ['新しい企画', 30, IND], ['休息・学び', 25, '#f59e0b']];
      const cx = 560, cy = 390, R = 170;
      let acc = -Math.PI / 2;
      const tot = E.inOutCubic(L.prog(t, 4.5, 5.8));
      ctx.lineCap = 'butt';
      segs.forEach(([lab, v, col], i) => {
        const span = (v / 100) * L.TAU;
        const vis = L.clamp((tot * L.TAU - (acc + Math.PI / 2)) / span);
        if (vis > 0) { ctx.strokeStyle = col; ctx.lineWidth = 64; ctx.beginPath(); ctx.arc(cx, cy, R, acc + 0.02, acc + span * vis - 0.02); ctx.stroke(); }
        acc += span;
        // 凡例
        const lp = E.outCubic(L.prog(t, 5.0 + i * 0.35, 5.4 + i * 0.35));
        if (lp > 0) {
          const y = 300 + i * 92, x = 830 + (1 - lp) * 60;
          ctx.save(); ctx.globalAlpha *= lp;
          L.panel(ctx, x, y - 34, 24, 24, 6, { fill: col });
          L.text(ctx, lab, x + 40, y - 13, { font: L.font(700, 26), color: INK });
          L.text(ctx, `${Math.round(v * lp)}%`, x + 330, y - 10, { font: L.font(900, 44, 'Montserrat'), color: col, align: 'right' });
          ctx.restore();
        }
      });
      L.text(ctx, '28h', cx, cy + 6, { font: L.font(900, 64, 'Montserrat'), color: INK, align: 'center', alpha: L.prog(t, 5.5, 5.9) });
      L.text(ctx, '/ 月', cx, cy + 46, { font: L.font(700, 22), color: MUTED, align: 'center', alpha: L.prog(t, 5.5, 5.9) });
      L.text(ctx, '※数値はイメージです', 1240, 690, { font: L.font(500, 16), color: MUTED, align: 'right' });
      ctx.restore();
    }

    // ── 3. 導入の流れ（7.9〜11.4）
    if (t > 7.8) {
      this.title(ctx, t, 7.9, 11.4, '03', '導入までの流れ');
      const out = E.inCubic(L.prog(t, 11.05, 11.4));
      ctx.save(); ctx.globalAlpha = 1 - out;
      const steps = [['💬', 'ヒアリング'], ['📐', '設計・提案'], ['⚙️', '導入'], ['🤝', '運用サポート']];
      const y = 380, x0 = 430, gap = 230;
      const lp = E.inOutCubic(L.prog(t, 8.3, 10.0));
      ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 6; ctx.setLineDash([2, 14]); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x0 + gap * 3, y); ctx.stroke(); ctx.setLineDash([]);
      const g = ctx.createLinearGradient(x0, 0, x0 + gap * 3, 0); g.addColorStop(0, BLUE); g.addColorStop(1, IND);
      ctx.strokeStyle = g; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x0 + gap * 3 * lp, y); ctx.stroke();
      steps.forEach(([ic, lab], i) => {
        const st = 8.3 + i * 0.55, p = E.outBack(L.prog(t, st, st + 0.4));
        if (p <= 0) return;
        const x = x0 + i * gap;
        ctx.save(); ctx.translate(x, y); ctx.scale(p, p);
        ctx.fillStyle = '#fff'; ctx.shadowColor = 'rgba(15,23,42,0.15)'; ctx.shadowBlur = 24; ctx.shadowOffsetY = 8;
        ctx.beginPath(); ctx.arc(0, 0, 72, 0, L.TAU); ctx.fill(); ctx.shadowColor = 'transparent';
        L.ring(ctx, 0, 0, 72, 1, 4, i === 3 ? IND : BLUE);
        L.emoji(ctx, ic, 0, -4, 54);
        L.pill(ctx, `STEP ${i + 1}`, 0, -96, { font: L.font(900, 18, 'Montserrat'), bg: i === 3 ? IND : BLUE, color: '#fff', padX: 14, spacing: 1 });
        L.text(ctx, lab, 0, 122, { font: L.font(900, 28), color: INK, align: 'center' });
        ctx.restore();
      });
      const cp = E.outBack(L.prog(t, 10.4, 10.8));
      if (cp > 0) {
        ctx.save(); ctx.translate(775, 620); ctx.scale(cp, cp);
        L.panel(ctx, -250, -34, 500, 68, 34, { fill: [BLUE, IND], shadow: 'rgba(99,102,241,0.35)', shadowBlur: 20 });
        L.text(ctx, 'まずはお気軽にご相談ください', 0, 11, { font: L.font(900, 28), color: '#fff', align: 'center' });
        ctx.restore();
      }
      ctx.restore();
    }
  },
};
