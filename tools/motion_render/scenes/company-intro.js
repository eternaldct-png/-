// 会社紹介ダイジェスト（16:9 / 13秒）メインキャラ: 1（事業紹介で他のメンバーも登場）
window.SCENE = {
  w: 1280, h: 720, dur: 13, poster: 5.0,
  draw(ctx, t) {
    const { w, h } = this, E = L.E;
    const secs = [
      { id: 3, icon: '🎤', en: 'LIVER MANAGEMENT', title: 'ライバー事務所', desc: '配信者・ライバーのマネジメントと育成', col: '#ec4899' },
      { id: 5, icon: '🎵', en: 'MUSIC PRODUCTION', title: '音楽制作', desc: 'オリジナル曲・歌ってみた・MV制作', col: '#8b5cf6' },
      { id: 4, icon: '🤖', en: 'AI SOLUTION', title: 'AI業務効率化', desc: '中小企業のAI導入・自動化をサポート', col: '#06b6d4' },
      { id: 2, icon: '🛍️', en: 'GOODS', title: 'グッズ制作・販売', desc: 'オリジナルグッズの企画から販売まで', col: '#f59e0b' },
    ];
    const S0 = 2.3, SD = 1.85;
    const si = Math.floor((t - S0) / SD);
    const accent = t >= S0 && si < 4 ? secs[si].col : '#d946ef';

    L.linear(ctx, w, h, ['#0d0b14', '#1a1027', '#0d0b14'], 120);
    L.blobs(ctx, w, h, t, [
      { x: 0.25, y: 0.4, r: 0.45, color: 'rgba(124,58,237,0.35)' },
      { x: 0.8, y: 0.6, r: 0.45, color: 'rgba(236,72,153,0.25)' },
    ], 13);
    // 斜めのライン
    ctx.save(); ctx.globalAlpha = 0.06; ctx.strokeStyle = '#fff'; ctx.lineWidth = 1;
    for (let i = -10; i < 30; i++) { const x = i * 80 + (t * 20) % 80; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x - 400, h); ctx.stroke(); }
    ctx.restore();

    // ── イントロ（0〜2.3）
    if (t < 2.5) {
      const out = E.inCubic(L.prog(t, 2.0, 2.4));
      const cp = E.outCubic(L.prog(t, 0.1, 0.8));
      L.glowBlob(ctx, 330, 400, 320, 'rgba(217,70,239,0.35)', cp * (1 - out));
      L.liveChar(ctx, 1, 330 - out * 300, 760 + (1 - cp) * 200, 720, t, { alpha: 1 - out, glow: 'rgba(240,171,252,0.5)', glowBlur: 40 });
      ctx.save(); ctx.globalAlpha = 1 - out;
      L.text(ctx, 'ABOUT US', 660, 220, { font: L.font(800, 24, 'Montserrat'), color: '#f0abfc', spacing: 10, alpha: L.prog(t, 0.3, 0.7) });
      L.charText(ctx, '「好き」を、', 656, 320, t, { font: L.font(900, 72), color: '#fff', t0: 0.5, stagger: 0.06, dur: 0.4, mode: 'rise' });
      L.charText(ctx, 'ずっと続く仕事に。', 656, 412, t, { font: L.font(900, 72), grad: ['#f0abfc', '#f9a8d4', '#fde68a'], t0: 0.85, stagger: 0.06, dur: 0.4, mode: 'rise' });
      const lw = 420 * E.outCubic(L.prog(t, 1.3, 1.9));
      ctx.fillStyle = '#d946ef'; ctx.fillRect(660, 450, lw, 4);
      L.text(ctx, 'ETERNALd.c.t', 660, 500, { font: L.font(800, 30, 'Montserrat'), color: '#fff', spacing: 4, alpha: L.prog(t, 1.5, 1.9) });
      ctx.restore();
    }

    // ── 事業紹介（2.3〜9.7）
    secs.forEach((s, i) => {
      const a = S0 + i * SD, b = a + SD;
      if (t < a - 0.05 || t > b + 0.3) return;
      const pin = E.outCubic(L.prog(t, a, a + 0.5)), pout = E.inCubic(L.prog(t, b - 0.1, b + 0.25));
      // 色のパネルがワイプ
      ctx.save();
      const wx = L.lerp(-200, 520, E.outQuart(L.prog(t, a - 0.05, a + 0.45))) - pout * 900;
      ctx.beginPath(); ctx.moveTo(wx - 300, 0); ctx.lineTo(wx + 100, 0); ctx.lineTo(wx - 100, h); ctx.lineTo(wx - 500, h); ctx.closePath();
      const g = ctx.createLinearGradient(0, 0, 600, h); g.addColorStop(0, s.col); g.addColorStop(1, 'rgba(13,11,20,0.2)');
      ctx.globalAlpha = 0.85; ctx.fillStyle = g; ctx.fill();
      ctx.restore();
      // キャラ
      L.glowBlob(ctx, 300, 420, 300, 'rgba(255,255,255,0.12)', pin * (1 - pout));
      L.liveChar(ctx, s.id, 300 - pout * 120 + (1 - pin) * -200, s.id === 2 ? 700 : 740, s.id === 2 ? 470 : 680, t, { alpha: pin * (1 - pout), glow: 'rgba(255,255,255,0.35)', glowBlur: 30 });
      // 文字
      ctx.save(); ctx.globalAlpha = 1 - pout; ctx.translate((1 - pin) * 80 - pout * 60, 0);
      L.text(ctx, `0${i + 1}`, 600, 250, { font: L.font(900, 120, 'Montserrat'), color: 'rgba(255,255,255,0.1)' });
      L.emoji(ctx, s.icon, 640, 330, 64, { scale: E.outBack(L.prog(t, a + 0.15, a + 0.5)) });
      L.text(ctx, s.en, 700, 316, { font: L.font(800, 22, 'Montserrat'), color: s.col, spacing: 6 });
      L.text(ctx, s.title, 600, 420, { font: L.font(900, 70), color: '#fff' });
      L.text(ctx, s.desc, 604, 476, { font: L.font(700, 28), color: 'rgba(255,255,255,0.8)', alpha: L.prog(t, a + 0.3, a + 0.6) });
      ctx.restore();
    });
    // 進行バー
    if (t > S0 - 0.1 && t < S0 + SD * 4 + 0.2) {
      const pa = L.prog(t, S0 - 0.1, S0 + 0.2) * (1 - L.prog(t, S0 + SD * 4 - 0.1, S0 + SD * 4 + 0.2));
      secs.forEach((s, i) => {
        const x = 600 + i * 150, fill = L.clamp((t - (S0 + i * SD)) / SD);
        ctx.globalAlpha = pa;
        ctx.fillStyle = 'rgba(255,255,255,0.18)'; ctx.fillRect(x, 580, 130, 4);
        ctx.fillStyle = s.col; ctx.fillRect(x, 580, 130 * fill, 4);
        L.text(ctx, s.title, x, 612, { font: L.font(700, 16), color: fill > 0 ? '#fff' : 'rgba(255,255,255,0.4)' });
        ctx.globalAlpha = 1;
      });
    }

    // ── アウトロ：全員集合（9.7〜13）
    if (t > 9.5) {
      const out = E.inCubic(L.prog(t, 12.45, 12.95));
      ctx.save(); ctx.globalAlpha = 1 - out;
      L.glowBlob(ctx, 640, 560, 520, 'rgba(217,70,239,0.3)', L.prog(t, 9.6, 10.2));
      const team = [[4, 290, 730, 400], [3, 465, 730, 420], [1, 640, 742, 440], [5, 815, 730, 425], [2, 990, 730, 300]];
      team.forEach(([id, x, y, hh], i) => {
        const st = 9.7 + Math.abs(i - 2) * 0.12, p = E.outBack(L.prog(t, st, st + 0.5));
        if (p <= 0) return;
        L.groundShadow(ctx, x, y, hh * 0.5, 0.4);
        L.liveChar(ctx, id, x, y + (1 - p) * 300, hh, t, { phase: i * 0.7, glow: 'rgba(240,171,252,0.35)', glowBlur: 24 });
      });
      const tp = E.outCubic(L.prog(t, 10.2, 10.8));
      L.text(ctx, 'ETERNALd.c.t', 640, 126, { font: L.font(900, 76, 'Montserrat'), grad: ['#f0abfc', '#ffffff', '#f9a8d4'], align: 'center', spacing: 6, alpha: tp, glow: 'rgba(217,70,239,0.6)', glowBlur: 26 });
      L.text(ctx, '配信 ・ 音楽 ・ AI ・ グッズ で、「好き」をずっと。', 640, 186, { font: L.font(700, 28), color: '#fff', align: 'center', alpha: L.prog(t, 10.6, 11.0) });
      const up = E.outBack(L.prog(t, 11.0, 11.4));
      ctx.save(); ctx.translate(640, 246); ctx.scale(up, up);
      L.pill(ctx, 'eternaldct.net', 0, 0, { font: L.font(800, 26, 'Montserrat'), bg: 'rgba(255,255,255,0.12)', border: 'rgba(255,255,255,0.4)', borderWidth: 2, color: '#fff', padX: 26, spacing: 2 });
      ctx.restore();
      ctx.restore();
    }
    L.vignette(ctx, w, h, 0.45);
  },
};
