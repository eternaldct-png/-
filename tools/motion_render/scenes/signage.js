// 店頭サイネージ・メニュー動画（9:16 / 12秒でつなぎ目なくループ）キャラ: 4 — 店名・価格はサンプル
window.SCENE = {
  w: 720, h: 1280, dur: 12, poster: 1.6,
  latte(ctx, t) {
    // ソーサー
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.ellipse(0, 120, 210, 46, 0, 0, L.TAU); ctx.fill();
    ctx.fillStyle = '#e7e5e4'; ctx.beginPath(); ctx.ellipse(0, 116, 150, 30, 0, 0, L.TAU); ctx.fill();
    // カップ
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 26; ctx.beginPath(); ctx.ellipse(150, 20, 44, 52, 0, -1.4, 1.4); ctx.stroke();
    const g = ctx.createLinearGradient(-150, 0, 150, 0); g.addColorStop(0, '#e7e5e4'); g.addColorStop(0.3, '#fff'); g.addColorStop(1, '#d6d3d1');
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(-150, -50); ctx.bezierCurveTo(-150, 90, -90, 120, 0, 120); ctx.bezierCurveTo(90, 120, 150, 90, 150, -50); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#f5f5f4'; ctx.beginPath(); ctx.ellipse(0, -50, 150, 38, 0, 0, L.TAU); ctx.fill();
    ctx.fillStyle = '#a16207'; ctx.beginPath(); ctx.ellipse(0, -48, 136, 30, 0, 0, L.TAU); ctx.fill();
    // ラテアート（ハート）
    ctx.save(); ctx.translate(0, -50); ctx.scale(1, 0.24); ctx.fillStyle = '#fef3c7'; L.heart(ctx, 0, -70, 140); ctx.fill(); ctx.restore();
    // 湯気
    ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 8; ctx.lineCap = 'round';
    for (let i = 0; i < 3; i++) {
      const k = ((t * 0.5 + i / 3) % 1);
      ctx.globalAlpha = Math.sin(k * Math.PI) * 0.8;
      ctx.beginPath();
      for (let j = 0; j <= 20; j++) { const y = -100 - j * 6 - k * 60, x = -50 + i * 50 + Math.sin(j * 0.5 + t * 3 + i) * 12; j ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  },
  icecream(ctx, t) {
    // コーン
    ctx.fillStyle = '#d97706'; ctx.beginPath(); ctx.moveTo(-100, -20); ctx.lineTo(100, -20); ctx.lineTo(0, 200); ctx.closePath(); ctx.fill();
    ctx.save(); ctx.clip(); ctx.strokeStyle = '#b45309'; ctx.lineWidth = 6;
    for (let i = -6; i < 8; i++) { ctx.beginPath(); ctx.moveTo(-120 + i * 30, -20); ctx.lineTo(-20 + i * 30, 200); ctx.stroke(); ctx.beginPath(); ctx.moveTo(120 - i * 30, -20); ctx.lineTo(20 - i * 30, 200); ctx.stroke(); }
    ctx.restore();
    // スクープ×2
    const scoop = (x, y, r, c1, c2, seed) => {
      const g = ctx.createRadialGradient(x - r * 0.3, y - r * 0.4, r * 0.1, x, y, r); g.addColorStop(0, c1); g.addColorStop(1, c2);
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, Math.PI * 0.95, Math.PI * 2.05);
      for (let i = 0; i <= 8; i++) { const a = Math.PI * 2.05 - (i / 8) * Math.PI * 1.1; ctx.lineTo(x + Math.cos(a) * r * 1.02, y + 20 + Math.sin(i * 2) * 8); }
      ctx.closePath(); ctx.fill();
      const rr = L.rng(seed); ctx.fillStyle = '#3f2a1d';
      for (let i = 0; i < 10; i++) { const a = rr() * Math.PI + Math.PI, d = rr() * r * 0.85; ctx.save(); ctx.translate(x + Math.cos(a) * d, y + Math.sin(a) * d * 0.9); ctx.rotate(rr() * 3); ctx.fillRect(-7, -4, 14, 8); ctx.restore(); }
    };
    scoop(0, -40, 110, '#d1fae5', '#6ee7b7', 3);
    scoop(0, -160, 92, '#ecfdf5', '#86efac', 9);
    // ミントの葉
    ctx.fillStyle = '#16a34a'; ctx.beginPath(); ctx.ellipse(30, -258, 30, 14, -0.5, 0, L.TAU); ctx.fill(); ctx.beginPath(); ctx.ellipse(-12, -262, 26, 12, 0.6, 0, L.TAU); ctx.fill();
    // キラキラ
    L.sparkle(ctx, -110, -200, 16, '#fff', 0.6 + 0.4 * Math.sin(t * 5));
    L.sparkle(ctx, 120, -120, 12, '#fff', 0.6 + 0.4 * Math.sin(t * 5 + 2));
  },
  parfait(ctx, t) {
    // グラス
    ctx.save();
    ctx.beginPath(); ctx.moveTo(-120, -150); ctx.lineTo(120, -150); ctx.bezierCurveTo(110, 40, 40, 80, 30, 110); ctx.lineTo(-30, 110); ctx.bezierCurveTo(-40, 80, -110, 40, -120, -150); ctx.closePath();
    ctx.clip();
    const layers = [['#fecdd3', -150], ['#fff7ed', -90], ['#fb7185', -40], ['#fef3c7', 10], ['#a16207', 60]];
    layers.forEach(([c, y], i) => { ctx.fillStyle = c; ctx.beginPath(); ctx.moveTo(-130, y); for (let x = -130; x <= 130; x += 20) ctx.lineTo(x, y + Math.sin(x * 0.05 + i) * 6); ctx.lineTo(130, 200); ctx.lineTo(-130, 200); ctx.fill(); });
    ctx.restore();
    ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(-120, -150); ctx.bezierCurveTo(-110, 40, -40, 80, -30, 110); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.fillRect(-14, 110, 28, 70); ctx.beginPath(); ctx.ellipse(0, 186, 80, 18, 0, 0, L.TAU); ctx.fill();
    // ホイップと苺
    ctx.fillStyle = '#fff'; [[-70, -165, 50], [0, -185, 60], [70, -165, 50], [-30, -215, 40], [35, -215, 40]].forEach(([x, y, r]) => { ctx.beginPath(); ctx.arc(x, y, r, 0, L.TAU); ctx.fill(); });
    const straw = (x, y, s, rot) => {
      ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.fillStyle = '#e11d48';
      ctx.beginPath(); ctx.moveTo(0, s); ctx.bezierCurveTo(-s, s * 0.2, -s * 0.8, -s * 0.7, 0, -s * 0.6); ctx.bezierCurveTo(s * 0.8, -s * 0.7, s, s * 0.2, 0, s); ctx.fill();
      ctx.fillStyle = '#fde68a'; for (let i = 0; i < 6; i++) ctx.fillRect(-s * 0.4 + (i % 3) * s * 0.35, -s * 0.2 + Math.floor(i / 3) * s * 0.4, 4, 6);
      ctx.fillStyle = '#16a34a'; ctx.beginPath(); ctx.ellipse(0, -s * 0.65, s * 0.5, s * 0.16, 0, 0, L.TAU); ctx.fill();
      ctx.restore();
    };
    straw(0, -270, 52, 0.1 + Math.sin(t * 3) * 0.05); straw(-80, -220, 40, -0.4); straw(85, -215, 40, 0.5);
    ctx.fillStyle = '#7c2d12'; ctx.fillRect(40, -330, 10, 120);
  },
  draw(ctx, t) {
    const { w, h } = this, C = 4, E = L.E, P = 12;
    const BROWN = '#3f2a1d', CREAM = '#fff7ed';
    L.linear(ctx, w, h, ['#fff7ed', '#fde7c8'], 90);
    // 背景の大きな円（ゆっくり回転）
    ctx.save(); ctx.translate(360, 560); ctx.rotate((t / P) * L.TAU);
    ctx.strokeStyle = 'rgba(63,42,29,0.08)'; ctx.lineWidth = 2; ctx.setLineDash([6, 14]);
    ctx.beginPath(); ctx.arc(0, 0, 300, 0, L.TAU); ctx.stroke(); ctx.setLineDash([]); ctx.restore();

    // ヘッダー
    ctx.fillStyle = BROWN; ctx.fillRect(0, 0, w, 150);
    L.text(ctx, 'CAFE ETERNAL', 360, 82, { font: L.font(900, 50, 'Montserrat'), color: CREAM, align: 'center', spacing: 6 });
    L.text(ctx, 'COFFEE · SWEETS · MUSIC', 360, 122, { font: L.font(700, 18, 'Montserrat'), color: '#d6b48c', align: 'center', spacing: 6 });
    L.pill(ctx, '本日のおすすめ', 360, 210, { font: L.font(900, 30), bg: '#e11d48', color: '#fff', padX: 28 });

    const items = [
      { fn: 'latte', name: 'カフェラテ', price: '520', badge: '人気No.1', tip: '朝の一杯に☕', col: '#a16207' },
      { fn: 'icecream', name: 'チョコミントアイス', price: '480', badge: 'NEW', tip: 'ひんやり爽やか！', col: '#059669' },
      { fn: 'parfait', name: 'いちごパフェ', price: '780', badge: '期間限定', tip: '季節限定です🍓', col: '#e11d48' },
    ];
    items.forEach((it, k) => {
      const lt = (((t - k * 4 + 0.3) % P) + P) % P; // 各商品のローカル時刻（ループ対応）
      if (lt > 4.0) return;
      const pin = E.outCubic(L.prog(lt, 0, 0.55)), pout = E.inCubic(L.prog(lt, 3.55, 4.0));
      const dx = (1 - pin) * 720 - pout * 720;
      // 皿・スポット
      ctx.save(); ctx.translate(dx, 0);
      L.glowBlob(ctx, 360, 560, 300, 'rgba(255,255,255,0.95)');
      ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.ellipse(360, 690, 240, 50, 0, 0, L.TAU); ctx.fill();
      ctx.save(); ctx.translate(360, 560 + Math.sin(lt * 2.4) * 6); ctx.scale(1.05, 1.05);
      this[it.fn](ctx, t);
      ctx.restore();
      // バッジ
      ctx.save(); ctx.translate(560, 330); ctx.rotate(0.18); const bs = E.outBackBig(L.prog(lt, 0.4, 0.75)); ctx.scale(bs, bs);
      ctx.fillStyle = it.col; ctx.beginPath(); ctx.arc(0, 0, 66, 0, L.TAU); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 3; ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.arc(0, 0, 56, 0, L.TAU); ctx.stroke(); ctx.setLineDash([]);
      L.text(ctx, it.badge, 0, 10, { font: L.font(900, it.badge.length > 3 ? 24 : 32), color: '#fff', align: 'center' });
      ctx.restore();
      // 名前と価格
      L.text(ctx, it.name, 360, 840, { font: L.font(900, 60), color: BROWN, align: 'center' });
      ctx.fillStyle = it.col; ctx.fillRect(360 - 40, 866, 80, 5);
      L.text(ctx, '¥' + it.price, 320, 975, { font: L.font(900, 100, 'Montserrat'), color: BROWN, align: 'center' });
      L.text(ctx, '（税込）', 320 + L.measure(ctx, '¥' + it.price, { font: L.font(900, 100, 'Montserrat') }) / 2 + 52, 972, { font: L.font(700, 22), color: '#78716c', align: 'center' });
      ctx.restore();
      // 吹き出し（キャラのセリフ）
      const bp = E.outBack(L.prog(lt, 0.7, 1.0)) * (1 - E.inBack(L.prog(lt, 3.3, 3.6)));
      if (bp > 0) {
        ctx.save(); ctx.translate(560, 1070); ctx.scale(bp, bp);
        const bw = L.measure(ctx, it.tip, { font: L.font(900, 28) }) + 44;
        L.bubble(ctx, -bw, -32, bw, 64, { fill: '#fff', r: 32, shadow: 'rgba(63,42,29,0.2)', tail: [24, 6, 'right'] });
        L.text(ctx, it.tip, -bw / 2, 10, { font: L.font(900, 28), color: BROWN, align: 'center' });
        ctx.restore();
      }
    });

    // 店員キャラ（右下・常駐）
    L.liveChar(ctx, C, 632, 1262, 345, t, { period: 3, shadow: 'rgba(63,42,29,0.25)' });
    // ティッカー（12秒で1ユニット流れる）
    ctx.fillStyle = BROWN; ctx.fillRect(0, h - 64, w, 64);
    ctx.save(); ctx.beginPath(); ctx.rect(0, h - 64, w, 64); ctx.clip();
    const unit = 'OPEN 9:00–20:00　／　テイクアウトOK　／　Wi-Fi・電源あり　／　';
    const f = { font: L.font(700, 26), color: CREAM };
    const uw = L.measure(ctx, unit, f);
    const x0 = -((t / P) * uw) % uw;
    for (let i = 0; i < 3; i++) L.text(ctx, unit, x0 + i * uw, h - 22, f);
    ctx.restore();
    // ページ送りのドット
    items.forEach((_, k) => {
      const active = Math.floor((((t + 0.3) % P) + P) % P / 4) === k;
      ctx.fillStyle = active ? '#e11d48' : 'rgba(63,42,29,0.25)';
      ctx.beginPath(); ctx.arc(330 + k * 30, 1150, active ? 8 : 6, 0, L.TAU); ctx.fill();
    });
  },
};
