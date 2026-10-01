// SNS縦型広告（9:16 / 10秒）キャラ: 3 — 自社のAI業務効率化サポートを想定したサンプル
window.SCENE = {
  w: 720, h: 1280, dur: 10, poster: 5.2,
  draw(ctx, t) {
    const { w, h } = this, C = 3, E = L.E;
    const Y = '#facc15', INK = '#0f172a';

    // ── 0〜2.4秒：フック（黄色背景に大きな問いかけ）
    const toB = E.inOutQuart(L.prog(t, 2.3, 2.8)); // 黄色→紺へワイプ
    ctx.fillStyle = Y; ctx.fillRect(0, 0, w, h);
    if (t < 2.85) {
      const shake = L.shake(t, t > 0.35 && t < 0.6 ? 6 : 0, 40);
      ctx.save(); ctx.translate(shake.x, shake.y);
      // 散らかった書類（ゆれる）
      const papers = [['請求書', 150, 200, -0.2], ['日程調整', 520, 170, 0.15], ['SNS投稿', 360, 330, -0.05], ['議事録', 140, 1000, 0.18],
        ['在庫表', 560, 960, -0.14], ['見積書', 360, 1130, 0.06], ['メール返信', 590, 1150, 0.22], ['シフト表', 120, 1180, -0.1]];
      papers.forEach(([p, x, y, rot], i) => {
        const a = L.E.outBack(L.prog(t, 0.05 + i * 0.07, 0.35 + i * 0.07));
        ctx.save(); ctx.translate(x, y + Math.sin(t * 6 + i) * 4); ctx.rotate(rot + Math.sin(t * 3 + i) * 0.04); ctx.scale(a, a);
        L.panel(ctx, -95, -62, 190, 124, 6, { fill: '#fff', shadow: 'rgba(0,0,0,0.18)', shadowBlur: 12, shadowY: 6 });
        ctx.fillStyle = '#cbd5e1'; for (let k = 0; k < 3; k++) ctx.fillRect(-70, -6 + k * 18, 140 - k * 28, 7);
        L.text(ctx, p, 0, -24, { font: L.font(900, 24), color: INK, align: 'center' });
        ctx.restore();
      });
      // 問いかけ
      const q = E.outBackBig(L.prog(t, 0.3, 0.7));
      ctx.save(); ctx.translate(360, 640); ctx.scale(q, q); ctx.rotate(-0.05);
      L.panel(ctx, -320, -150, 640, 300, 26, { fill: INK, shadow: 'rgba(0,0,0,0.3)', shadowBlur: 30 });
      L.text(ctx, 'まだ', 0, -62, { font: L.font(900, 52), color: '#fff', align: 'center' });
      L.text(ctx, '手作業で', 0, 22, { font: L.font(900, 84), color: Y, align: 'center' });
      L.text(ctx, '消耗してる？', 0, 112, { font: L.font(900, 70), color: '#fff', align: 'center' });
      ctx.restore();
      L.emoji(ctx, '😵‍💫', 590, 470, 96, { scale: E.outBack(L.prog(t, 0.8, 1.1)), rot: Math.sin(t * 5) * 0.15 });
      ctx.restore();
    }
    // 紺ワイプ（斜め）
    if (toB > 0) {
      ctx.save(); ctx.beginPath();
      const k = toB * (w + h);
      ctx.moveTo(-200, h + 200); ctx.lineTo(-200 + k * 1.2, h + 200); ctx.lineTo(-200 + k * 1.2 - h - 400, -200); ctx.lineTo(-200, -200);
      ctx.closePath(); ctx.clip();
      L.linear(ctx, w, h, ['#0f172a', '#1e1b4b', '#312e81'], 100);
      L.blobs(ctx, w, h, t, [{ x: 0.7, y: 0.3, r: 0.4, color: 'rgba(250,204,21,0.18)' }, { x: 0.2, y: 0.8, r: 0.5, color: 'rgba(129,140,248,0.3)' }], 10);
      ctx.restore();
    }

    // ── 2.8〜7.4秒：解決（キャラ＋AIにおまかせ）
    if (t > 2.6) {
      const ci = E.outBack(L.prog(t, 2.75, 3.3));
      const cOut = E.inBack(L.prog(t, 9.4, 9.8));
      L.glowBlob(ctx, 180, 900, 300, 'rgba(250,204,21,0.25)', ci);
      L.liveChar(ctx, C, L.lerp(-250, 170, ci) - cOut * 450, 1300, 800, t, { glow: 'rgba(250,204,21,0.45)', glowBlur: 36 });
      const hp = L.prog(t, 3.0, 3.4);
      L.text(ctx, 'その作業、', 60, 150, { font: L.font(900, 44), color: '#fff', alpha: hp });
      L.charText(ctx, 'AIにおまかせ。', 52, 250, t, { font: L.font(900, 84), color: Y, t0: 3.25, stagger: 0.05, dur: 0.4, mode: 'pop' });
      const items = [['請求書の作成', '📄'], ['SNS投稿の下書き', '📱'], ['日程調整・予約', '📅'], ['議事録のまとめ', '📝']];
      items.forEach(([s, ic], i) => {
        const st = 4.0 + i * 0.6;
        const p = E.outQuart(L.prog(t, st, st + 0.45));
        if (p <= 0) return;
        const y = 320 + i * 96;
        const x = 290 + (1 - p) * 500;
        L.panel(ctx, x, y, 390, 78, 39, { fill: 'rgba(255,255,255,0.1)', stroke: 'rgba(255,255,255,0.25)', lineWidth: 2 });
        L.emoji(ctx, ic, x + 40, y + 40, 32);
        L.text(ctx, s, x + 76, y + 49, { font: L.font(700, 27), color: '#fff' });
        // AI処理済みのチェック
        const cp = L.prog(t, st + 0.35, st + 0.65);
        ctx.fillStyle = Y; ctx.beginPath(); ctx.arc(x + 350, y + 39, 22 * E.outBack(cp), 0, L.TAU); ctx.fill();
        L.check(ctx, x + 350, y + 40, 22, INK, L.prog(t, st + 0.5, st + 0.8), 5);
      });
      // 時間が浮く表現
      const tp = E.outBack(L.prog(t, 6.6, 7.0));
      if (tp > 0) {
        ctx.save(); ctx.translate(485, 760); ctx.scale(tp, tp); ctx.rotate(-0.04);
        L.panel(ctx, -195, -60, 390, 120, 22, { fill: Y, shadow: 'rgba(0,0,0,0.3)', shadowBlur: 24 });
        L.text(ctx, '空いた時間で', 0, -12, { font: L.font(700, 28), color: INK, align: 'center' });
        L.text(ctx, '本業に集中！', 0, 38, { font: L.font(900, 42), color: INK, align: 'center' });
        ctx.restore();
      }
    }

    // ── 7.6〜10秒：CTA
    const cta = E.outBack(L.prog(t, 7.6, 8.1));
    if (cta > 0) {
      const out = E.inCubic(L.prog(t, 9.5, 9.95));
      ctx.save(); ctx.globalAlpha = 1 - out;
      ctx.translate(485, 980); ctx.scale(cta, cta);
      L.text(ctx, 'AI業務効率化サポート', 0, -40, { font: L.font(900, 34), color: '#fff', align: 'center' });
      const pulse = 1 + 0.04 * Math.sin((t - 8.1) * 9) * (t > 8.1 ? 1 : 0);
      ctx.scale(pulse, pulse);
      L.panel(ctx, -190, 0, 380, 92, 46, { fill: [Y, '#fb923c'], shadow: 'rgba(250,204,21,0.5)', shadowBlur: 30 });
      L.text(ctx, '無料で相談する ▶', 0, 60, { font: L.font(900, 36), color: INK, align: 'center' });
      ctx.restore();
      L.text(ctx, 'ETERNALd.c.t', 485, 1140, { font: L.font(800, 26, 'Montserrat'), color: 'rgba(255,255,255,0.7)', align: 'center', spacing: 3, alpha: cta * (1 - out) });
      // 指さしタップ
      const tap = (t - 8.4) % 1.0;
      if (t > 8.4 && t < 9.5) {
        ctx.save(); ctx.globalAlpha = 0.9;
        ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 4;
        ctx.beginPath(); ctx.arc(600, 1050, 20 + tap * 50, 0, L.TAU); ctx.globalAlpha = 1 - tap; ctx.stroke();
        ctx.restore();
        L.emoji(ctx, '👆', 620, 1100 + Math.sin(tap * Math.PI) * -14, 64);
      }
    }
    // 最後は黄色に戻してループ
    const back = E.inOutQuart(L.prog(t, 9.6, 10));
    if (back > 0) { ctx.fillStyle = Y; ctx.fillRect(0, h * (1 - back), w, h * back); }
    // 上部のプログレス（SNS広告らしさ）
    ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.fillRect(20, 18, w - 40, 4);
    ctx.fillStyle = '#fff'; ctx.fillRect(20, 18, (w - 40) * (t / 10), 4);
    L.text(ctx, '広告', w - 24, 52, { font: L.font(700, 18), color: t < 2.6 || back > 0.5 ? INK : '#fff', align: 'right', alpha: 0.7 });
  },
};
