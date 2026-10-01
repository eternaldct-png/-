// イベント・キャンペーン告知（9:16 / 10秒）キャラ: 3 — 日付・会場はサンプル表記
window.SCENE = {
  w: 720, h: 1280, dur: 10, poster: 6.4,
  spot(ctx, x, y, ang, len, width, color, alpha) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = alpha;
    ctx.translate(x, y); ctx.rotate(ang);
    const g = ctx.createLinearGradient(0, 0, 0, len);
    g.addColorStop(0, color); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(-8, 0); ctx.lineTo(8, 0); ctx.lineTo(width, len); ctx.lineTo(-width, len); ctx.closePath(); ctx.fill();
    ctx.restore();
  },
  draw(ctx, t) {
    const { w, h } = this, C = 3, E = L.E;
    const GOLD = ['#fde68a', '#f59e0b', '#fde68a'];
    L.linear(ctx, w, h, ['#0b0618', '#1c0b2e', '#0a1028'], 100);
    // スポットライト
    const sp = L.prog(t, 0, 0.8);
    this.spot(ctx, 120, -20, -0.35 + Math.sin(t * 0.9) * 0.35, 1300, 260, 'rgba(196,181,253,0.55)', 0.5 * sp);
    this.spot(ctx, 600, -20, 0.35 + Math.sin(t * 0.8 + 2) * 0.35, 1300, 260, 'rgba(251,191,36,0.45)', 0.5 * sp);
    this.spot(ctx, 360, -40, Math.sin(t * 0.6 + 1) * 0.2, 1200, 200, 'rgba(244,114,182,0.4)', 0.4 * sp);
    L.risingParticles(ctx, w, h, t, { n: 50, P: 10, color: '#fde68a', sparkle: true, alpha: 0.6, seed: 31, max: 3 });
    const fadeAll = 1 - E.inCubic(L.prog(t, 9.45, 9.95));
    ctx.save(); ctx.globalAlpha = fadeAll;

    // タイトル（金のバーが通ったところから文字が現れる）
    const wipe = E.inOutCubic(L.prog(t, 0.3, 1.1));
    L.text(ctx, 'SPECIAL EVENT', 360, 96, { font: L.font(800, 24, 'Montserrat'), color: '#e9d5ff', align: 'center', spacing: 10, alpha: L.prog(t, 0.2, 0.6) });
    ctx.save(); ctx.beginPath(); ctx.rect(0, 100, 40 + 640 * wipe, 200); ctx.clip();
    L.text(ctx, 'ETERNAL', 360, 196, { font: L.font(900, 108, 'Montserrat'), grad: GOLD, align: 'center', spacing: 4, glow: 'rgba(251,191,36,0.5)', glowBlur: 24 });
    L.text(ctx, 'LIVE PARTY', 360, 268, { font: L.font(800, 62, 'Montserrat'), color: '#fff', align: 'center', spacing: 12 });
    ctx.restore();
    if (wipe > 0 && wipe < 1) { ctx.fillStyle = '#fde68a'; ctx.shadowColor = '#fbbf24'; ctx.shadowBlur = 20; ctx.fillRect(40 + 640 * wipe - 4, 110, 8, 180); ctx.shadowBlur = 0; }

    // キャラ（スポットに照らされてせり上がる）
    const cp = E.outCubic(L.prog(t, 1.2, 2.2));
    if (cp > 0) {
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, 1010); ctx.clip();
      L.glowBlob(ctx, 520, 760, 300, 'rgba(251,191,36,0.3)', cp);
      L.liveChar(ctx, C, 520, 1010 + (1 - cp) * 640, 640, t, { glow: 'rgba(253,230,138,0.55)', glowBlur: 36 });
      ctx.restore();
      // ステージの床
      ctx.fillStyle = 'rgba(253,230,138,0.6)'; ctx.fillRect(330, 1008, 380 * cp, 3);
    }

    // 日付（数字がめくれるように）
    const dp = L.prog(t, 2.4, 2.8);
    if (dp > 0) {
      L.text(ctx, 'DATE', 44, 410, { font: L.font(800, 22, 'Montserrat'), color: '#fbbf24', spacing: 6, alpha: dp });
      L.text(ctx, '20XX', 44, 456, { font: L.font(800, 36, 'Montserrat'), color: '#e9d5ff', spacing: 3, alpha: dp });
      const digits = '12.19';
      [...digits].forEach((d, i) => {
        const st = 2.5 + i * 0.12, k = L.prog(t, st, st + 0.5);
        if (k <= 0) return;
        const r = L.rng(i + 3);
        const shown = k < 0.8 && d !== '.' ? String(Math.floor(r() * 10 + t * 30) % 10) : d;
        const xs = [44, 104, 164, 194, 254][i];
        ctx.save(); ctx.translate(xs, 560); ctx.scale(1, E.outBack(Math.min(1, k * 1.4)));
        L.text(ctx, shown, 0, 0, { font: L.font(900, 104, 'Montserrat'), color: '#fff' });
        ctx.restore();
      });
      L.pill(ctx, 'SAT', 44, 612, { align: 'left', font: L.font(900, 24, 'Montserrat'), bg: '#fbbf24', color: '#1c0b2e', alpha: L.prog(t, 3.0, 3.3), spacing: 3 });
    }
    // 時間・会場
    const info = [['OPEN / START', '17:30 / 18:00'], ['PLACE', '〇〇ライブホール']];
    info.forEach(([k, v], i) => {
      const st = 3.4 + i * 0.5, p = E.outCubic(L.prog(t, st, st + 0.5));
      if (p <= 0) return;
      const y = 700 + i * 110, x = 44 - (1 - p) * 60;
      ctx.save(); ctx.globalAlpha *= p;
      ctx.fillStyle = '#fbbf24'; ctx.fillRect(x, y - 26, 4, 78);
      L.text(ctx, k, x + 18, y, { font: L.font(800, 20, 'Montserrat'), color: '#fbbf24', spacing: 4 });
      L.text(ctx, v, x + 18, y + 44, { font: L.font(900, 34), color: '#fff' });
      ctx.restore();
    });

    // 特典カード
    const bp = E.outBack(L.prog(t, 4.6, 5.1));
    if (bp > 0) {
      ctx.save(); ctx.translate(360, 1110); ctx.scale(bp, bp);
      L.panel(ctx, -320, -70, 640, 140, 22, { fill: ['rgba(251,191,36,0.18)', 'rgba(244,114,182,0.18)'], stroke: 'rgba(253,230,138,0.8)', lineWidth: 2 });
      L.pill(ctx, '来場特典', -200, -66, { font: L.font(900, 24), bg: '#fbbf24', color: '#1c0b2e', padX: 18 });
      L.text(ctx, '全員に限定ステッカー', 0, 6, { font: L.font(900, 42), color: '#fff', align: 'center' });
      L.text(ctx, '＋ 抽選でチェキ撮影会', 0, 52, { font: L.font(700, 26), color: '#fde68a', align: 'center' });
      ctx.restore();
      L.emoji(ctx, '🎁', 600, 1050, 54, { scale: bp, rot: Math.sin(t * 3) * 0.15 });
    }

    // チケット発売中スタンプ
    const st = L.prog(t, 6.2, 6.5);
    if (st > 0) {
      const s = L.lerp(2.2, 0.8, E.outCubic(st));
      ctx.save(); ctx.translate(200, 945); ctx.rotate(-0.22); ctx.scale(s, s); ctx.globalAlpha *= st;
      ctx.strokeStyle = '#f472b6'; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 0, 92, 0, L.TAU); ctx.stroke();
      ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(0, 0, 80, 0, L.TAU); ctx.stroke();
      ctx.fillStyle = 'rgba(244,114,182,0.9)'; ctx.fillRect(-104, -26, 208, 52);
      L.text(ctx, 'TICKET', 0, -40, { font: L.font(900, 22, 'Montserrat'), color: '#f9a8d4', align: 'center', spacing: 4 });
      L.text(ctx, '発売中！', 0, 14, { font: L.font(900, 36), color: '#fff', align: 'center' });
      L.text(ctx, 'NOW ON SALE', 0, 56, { font: L.font(800, 15, 'Montserrat'), color: '#f9a8d4', align: 'center', spacing: 2 });
      ctx.restore();
      if (st >= 1 && t < 6.9) { const k = L.prog(t, 6.5, 6.9); ctx.save(); ctx.strokeStyle = `rgba(244,114,182,${1 - k})`; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(200, 945, 80 + k * 70, 0, L.TAU); ctx.stroke(); ctx.restore(); }
    }
    // 詳細はプロフィールへ
    const lp = L.prog(t, 7.4, 7.8);
    L.text(ctx, '詳しくはプロフィールのリンクから ▶', 360, 1232, { font: L.font(700, 26), color: '#e9d5ff', align: 'center', alpha: lp * (0.75 + 0.25 * Math.sin(t * 6)) });
    ctx.restore();
    L.vignette(ctx, w, h, 0.4);
  },
};
