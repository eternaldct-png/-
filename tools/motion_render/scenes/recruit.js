// 求人・オーディション募集動画（9:16 / 12秒）メインキャラ: 2（後半に全員集合）
window.SCENE = {
  w: 720, h: 1280, dur: 12, poster: 7.6,
  draw(ctx, t) {
    const { w, h } = this, E = L.E;
    const INK = '#3b0764';
    L.linear(ctx, w, h, ['#fdba74', '#f9a8d4', '#a78bfa'], 100);
    // 回転する光線
    ctx.save(); ctx.globalAlpha = 0.22;
    L.rays(ctx, 360, 520, 20, 0, 1300, '#ffffff', t * 0.15, 0.06);
    ctx.restore();
    L.glowBlob(ctx, 360, 520, 420, 'rgba(255,255,255,0.55)');
    L.risingParticles(ctx, w, h, t, { n: 40, P: 12, color: '#ffffff', sparkle: true, alpha: 0.8, seed: 5 });
    const fadeAll = 1 - E.inCubic(L.prog(t, 11.4, 11.95));
    ctx.save(); ctx.globalAlpha = fadeAll;

    // ── ヘッダー（常時。後半は少し小さく）
    const hp = E.outBack(L.prog(t, 0.15, 0.6));
    const shrink = E.inOutCubic(L.prog(t, 1.9, 2.4));
    ctx.save(); ctx.translate(360, L.lerp(250, 150, shrink)); ctx.scale(hp * L.lerp(1, 0.68, shrink), hp * L.lerp(1, 0.68, shrink));
    L.text(ctx, 'LIVER', 0, -10, { font: L.font(900, 132, 'Montserrat'), color: '#fff', align: 'center', stroke: INK, strokeWidth: 16, shadow: 'rgba(59,7,100,0.35)', shadowBlur: 0, shadowY: 10, spacing: 4 });
    L.text(ctx, 'AUDITION', 0, 92, { font: L.font(900, 96, 'Montserrat'), grad: ['#fde047', '#fb923c'], align: 'center', stroke: INK, strokeWidth: 14, spacing: 2 });
    ctx.restore();
    const pp = E.outBackBig(L.prog(t, 0.6, 0.95)) * (1 - shrink);
    if (pp > 0) {
      ctx.save(); ctx.translate(360, 440); ctx.scale(pp, pp); ctx.rotate(-0.04);
      L.pill(ctx, 'ライバー募集中！', 0, 0, { font: L.font(900, 46), bg: INK, color: '#fff', padX: 36 });
      ctx.restore();
    }

    // ── マスコット（イントロは中央 → チェック中は左下）
    if (t < 6.2) {
      const ip = E.outBack(L.prog(t, 0.3, 0.8));
      const mv = E.inOutCubic(L.prog(t, 1.9, 2.5));
      const out = E.inBack(L.prog(t, 5.7, 6.1));
      const x = L.lerp(360, 560, mv), y = L.lerp(1040, 1290, mv) + out * 500, sz = L.lerp(540, 420, mv) * ip;
      L.groundShadow(ctx, x, y, sz * 0.7, 0.25 * (1 - mv));
      L.liveChar(ctx, 2, x, y, sz, t, { period: 0.9, shadow: 'rgba(59,7,100,0.3)' });
      L.emoji(ctx, '📣', x - sz * 0.42, y - sz * 0.72, 88 * ip, { rot: -0.3 + Math.sin(t * 8) * 0.08 * (t < 2 ? 1 : 0) });
    }

    // ── こんな人を待ってます（チェックリスト）
    if (t > 2.2 && t < 6.4) {
      const out = E.inCubic(L.prog(t, 5.8, 6.2));
      const tp = L.prog(t, 2.3, 2.6) * (1 - out);
      L.text(ctx, 'こんな人を待ってます', 360, 330, { font: L.font(900, 40), color: INK, align: 'center', alpha: tp });
      const items = ['歌うのが好き', '話すのが好き', '新しいことに挑戦したい'];
      items.forEach((s, i) => {
        const st = 2.6 + i * 0.8, p = E.outBack(L.prog(t, st, st + 0.45));
        if (p <= 0) return;
        const y = 390 + i * 128;
        ctx.save(); ctx.globalAlpha *= 1 - out; ctx.translate(360, y + 50); ctx.scale(p, p); ctx.translate(-360, -(y + 50));
        L.panel(ctx, 50, y, 620, 100, 50, { fill: '#ffffff', shadow: 'rgba(59,7,100,0.2)', shadowBlur: 20, shadowY: 8 });
        L.panel(ctx, 72, y + 18, 64, 64, 16, { fill: '#fdf4ff', stroke: '#c084fc', lineWidth: 3 });
        L.check(ctx, 104, y + 50, 40, '#db2777', L.prog(t, st + 0.3, st + 0.6), 8);
        L.text(ctx, s, 160, y + 64, { font: L.font(900, 38), color: INK });
        ctx.restore();
      });
      const ap = E.outBack(L.prog(t, 5.0, 5.35)) * (1 - out);
      if (ap > 0) {
        ctx.save(); ctx.translate(330, 820); ctx.scale(ap, ap); ctx.rotate(-0.04);
        L.text(ctx, 'ひとつでも当てはまったら…！', 0, 0, { font: L.font(900, 32), color: '#fff', align: 'center', stroke: INK, strokeWidth: 10 });
        ctx.restore();
      }
    }

    // ── 全員集合
    if (t > 6.2) {
      const out = E.inCubic(L.prog(t, 11.3, 11.8));
      const tp = L.prog(t, 6.3, 6.6);
      L.charText(ctx, '仲間と一緒に、', 360, 360, t, { font: L.font(900, 50), color: INK, align: 'center', t0: 6.3, stagger: 0.05, dur: 0.35, mode: 'rise' });
      L.charText(ctx, 'はじめよう。', 360, 450, t, { font: L.font(900, 74), color: '#fff', align: 'center', t0: 6.6, stagger: 0.06, dur: 0.4, mode: 'pop', stroke: INK, strokeWidth: 12 });
      const team = [[4, 92, 1010, 400], [1, 226, 1010, 420], [2, 360, 1020, 300], [5, 494, 1010, 420], [3, 628, 1010, 410]];
      const order = [2, 1, 3, 0, 4];
      team.forEach(([id, x, y, hh], i) => {
        const st = 6.4 + order[i] * 0.14;
        const p = L.prog(t, st, st + 0.5);
        if (p <= 0) return;
        const jump = Math.sin(L.clamp(p) * Math.PI) * 120;
        const sq = p >= 1 ? 1 - 0.05 * Math.sin(L.prog(t, st + 0.5, st + 0.7) * Math.PI) : 1;
        const hop = t > 8.6 ? Math.max(0, Math.sin((t - 8.6 - i * 0.12) * 7)) * 14 * (1 - L.prog(t, 9.4, 9.8)) : 0;
        L.groundShadow(ctx, x, y + 4, hh * 0.5, 0.25);
        L.liveChar(ctx, id, x, y - jump - hop, hh, t, { phase: i, sy: sq, sx: 2 - sq, alpha: L.clamp(p * 3) });
      });
      // 床
      ctx.fillStyle = 'rgba(255,255,255,0.5)'; ctx.fillRect(0, 1014, w, 3);

      // CTA
      const cp = E.outBack(L.prog(t, 9.0, 9.4));
      if (cp > 0) {
        L.text(ctx, 'ETERNALd.c.t ライバーオーディション', 360, 1086, { font: L.font(900, 30), color: INK, align: 'center', alpha: cp });
        const pulse = 1 + 0.04 * Math.sin((t - 9.4) * 9) * (t > 9.4 ? 1 : 0);
        ctx.save(); ctx.translate(360, 1166); ctx.scale(cp * pulse, cp * pulse);
        L.panel(ctx, -230, -46, 460, 92, 46, { fill: ['#db2777', '#7c3aed'], shadow: 'rgba(59,7,100,0.4)', shadowBlur: 24 });
        L.text(ctx, '今すぐ応募する ▶', 0, 14, { font: L.font(900, 40), color: '#fff', align: 'center' });
        ctx.restore();
        L.text(ctx, '応募はプロフィールのリンクから', 360, 1248, { font: L.font(700, 24), color: INK, align: 'center', alpha: L.prog(t, 9.6, 10.0) });
      }
    }
    ctx.restore();
  },
};
