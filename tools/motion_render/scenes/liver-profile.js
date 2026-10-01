// ライバー紹介プロフィール動画（9:16 / 12秒）キャラ: 5
window.SCENE = {
  w: 720, h: 1280, dur: 12, poster: 6.2,
  draw(ctx, t) {
    const { w, h } = this, C = 5, E = L.E;
    const RED = '#e11d48', INK = '#111827';
    const outAll = E.inCubic(L.prog(t, 11.25, 11.85));

    // 背景（オフホワイト＋ドット）
    ctx.fillStyle = '#f4f4f5'; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(17,24,39,0.07)';
    for (let y = 30; y < h; y += 34) for (let x = 20 + ((y / 34) % 2) * 17; x < w; x += 34) { ctx.beginPath(); ctx.arc(x, y, 2, 0, L.TAU); ctx.fill(); }

    ctx.save(); ctx.globalAlpha = 1 - outAll;
    // 斜めの赤い帯
    const band = E.outQuart(L.prog(t, 0.1, 0.9));
    ctx.save(); ctx.translate(w / 2, 560); ctx.rotate(-0.32);
    ctx.fillStyle = RED; ctx.fillRect(-900 + (1 - band) * -1400, -150, 1800, 300);
    ctx.fillStyle = INK; ctx.fillRect(-900 + (1 - E.outQuart(L.prog(t, 0.25, 1.05))) * 1600, 170, 1800, 22);
    ctx.restore();

    // 縦の「PROFILE」アウトライン文字（ゆっくり流れる）
    ctx.save(); ctx.translate(108, 880 - L.anim(t, 0.2, 12, 0, 30, E.linear)); ctx.rotate(-Math.PI / 2);
    L.text(ctx, 'PROFILE', 0, 0, { font: L.font(900, 84, 'Montserrat'), color: 'rgba(0,0,0,0)', stroke: 'rgba(17,24,39,0.85)', strokeWidth: 2.5, spacing: 8, alpha: L.prog(t, 0.4, 1.0) });
    ctx.restore();

    // 上部バー
    const tb = L.prog(t, 0.3, 0.8);
    L.text(ctx, 'ETERNALd.c.t', 40, 78, { font: L.font(800, 24, 'Montserrat'), color: INK, spacing: 2, alpha: tb });
    L.text(ctx, 'LIVER No.07', w - 40, 78, { font: L.font(800, 24, 'Montserrat'), color: RED, spacing: 2, align: 'right', alpha: tb });
    ctx.fillStyle = INK; ctx.fillRect(40, 96, (w - 80) * E.outCubic(tb), 3);

    // キャラ（上から落ちてきて着地）
    const d = L.prog(t, 0.6, 1.25);
    const land = L.prog(t, 1.25, 1.6);
    const cy = d < 1 ? L.lerp(-60, 860, E.inQuad(d)) : 860;
    const sq = land > 0 && land < 1 ? 1 - 0.07 * Math.sin(land * Math.PI) : 1;
    L.groundShadow(ctx, 525, 862, 300 * L.clamp(d), 0.35);
    if (d > 0) L.liveChar(ctx, C, 525, cy, 640, t, { sy: sq, sx: 2 - sq, shadow: 'rgba(0,0,0,0.25)', shadowBlur: 30, shadowY: 10 });

    // 名前
    L.charText(ctx, 'LIVER', 40, 222, t, { font: L.font(900, 100, 'Montserrat'), color: INK, t0: 1.4, stagger: 0.06, dur: 0.5, mode: 'rise', rise: 50 });
    L.charText(ctx, 'NAME', 40, 318, t, { font: L.font(900, 100, 'Montserrat'), color: RED, t0: 1.6, stagger: 0.06, dur: 0.5, mode: 'rise', rise: 50 });
    const sub = L.prog(t, 2.1, 2.5);
    L.text(ctx, 'ライバー名', 44, 364, { font: L.font(700, 28), color: INK, alpha: sub, spacing: 4 });
    L.pill(ctx, '歌 × 雑談', 44, 410, { align: 'left', font: L.font(800, 22), bg: INK, color: '#fff', alpha: L.prog(t, 2.3, 2.7), padX: 18 });

    // 吹き出し
    const bp = E.outBack(L.prog(t, 6.3, 6.7)) * (1 - E.inBack(L.prog(t, 9.0, 9.3)));
    if (bp > 0) {
      ctx.save(); ctx.translate(560, 190); ctx.scale(bp, bp); ctx.translate(-560, -190);
      L.bubble(ctx, 400, 130, 290, 82, { fill: INK, r: 41, tail: [520, 236, 'bottom'] });
      L.text(ctx, '見つけてくれて', 545, 166, { font: L.font(700, 22), align: 'center' });
      L.text(ctx, 'ありがとう！', 545, 196, { font: L.font(900, 24), align: 'center', color: '#fda4af' });
      ctx.restore();
    }

    // 情報カード
    const rows = [
      ['🎤', '配信ジャンル', '歌・雑談'],
      ['🕘', '配信時間', '毎日 21:00〜'],
      ['💬', '好きなもの', 'ゲーム・カラオケ'],
      ['🔥', '目標', '1stワンマンライブ'],
    ];
    const rowsOut = E.inCubic(L.prog(t, 9.0, 9.5));
    rows.forEach(([ic, k, v], i) => {
      const st = 3.1 + i * 0.55;
      const p = E.outQuart(L.prog(t, st, st + 0.6));
      if (p <= 0) return;
      const y = 900 + i * 82;
      const x = 40 + (1 - p) * 700 - rowsOut * (i % 2 ? 700 : -700);
      L.panel(ctx, x, y, 640, 68, 14, { fill: '#ffffff', shadow: 'rgba(17,24,39,0.12)', shadowBlur: 18, shadowY: 6 });
      ctx.fillStyle = RED; ctx.fillRect(x, y, 8, 68);
      L.emoji(ctx, ic, x + 46, y + 35, 30);
      L.text(ctx, k, x + 80, y + 44, { font: L.font(700, 22), color: '#6b7280' });
      L.text(ctx, v, x + 620, y + 46, { font: L.font(900, 28), color: INK, align: 'right' });
    });

    // フォロー誘導
    const cta = E.outBack(L.prog(t, 9.4, 9.9));
    if (cta > 0) {
      ctx.save(); ctx.translate(360, 1040); ctx.scale(cta, cta); ctx.translate(-360, -1040);
      L.text(ctx, '毎日21時から配信中！', 360, 960, { font: L.font(900, 40), color: INK, align: 'center' });
      const pulse = 1 + 0.04 * Math.sin((t - 9.9) * 8) * (t > 9.9 ? 1 : 0);
      ctx.save(); ctx.translate(360, 1060); ctx.scale(pulse, pulse);
      L.panel(ctx, -230, -48, 460, 96, 48, { fill: [RED, '#f43f5e'], shadow: 'rgba(225,29,72,0.45)', shadowBlur: 30 });
      L.text(ctx, 'FOLLOW ME ▶', 0, 14, { font: L.font(900, 40, 'Montserrat'), align: 'center', spacing: 3 });
      ctx.restore();
      L.text(ctx, '@liver_name', 360, 1160, { font: L.font(700, 28, 'Montserrat'), color: '#6b7280', align: 'center' });
      ctx.restore();
    }
    ctx.restore();

    // 下部ライン
    ctx.fillStyle = INK; ctx.fillRect(0, h - 14, w * E.outCubic(L.prog(t, 0.3, 1.0)) * (1 - outAll), 14);
  },
};
