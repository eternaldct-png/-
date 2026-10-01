// グッズ・商品プロモーション（4:5 / 9秒）キャラ: 2 — マスコットを各グッズにプリントしたイメージ
window.SCENE = {
  w: 720, h: 900, dur: 9, poster: 2.6,
  async init() {
    // 白フチ付きのステッカー版（全身・顔）をオフスクリーンに作っておく
    const im = L.CHARS[2].img;
    const mk = (sx, sy, sw, sh, out, pad) => {
      const c = document.createElement('canvas');
      c.width = out + pad * 2; c.height = Math.round(out * sh / sw) + pad * 2;
      const g = c.getContext('2d');
      const dw = out, dh = c.height - pad * 2;
      g.filter = 'brightness(0) invert(1)';
      for (let i = 0; i < 32; i++) { const a = (i / 32) * L.TAU; g.drawImage(im, sx, sy, sw, sh, pad + Math.cos(a) * pad * 0.8, pad + Math.sin(a) * pad * 0.8, dw, dh); }
      g.filter = 'none'; g.drawImage(im, sx, sy, sw, sh, pad, pad, dw, dh);
      return c;
    };
    this.full = mk(0, 0, im.width, im.height, 420, 18);
    const [hx, hy, hr] = L.CHARS[2].head; const r = hr * im.width;
    this.face = mk(hx * im.width - r, Math.max(0, hy * im.height - r * 1.05), r * 2, r * 1.6, 360, 16);
  },
  mug(ctx, t, x, y, s) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
    L.groundShadow(ctx, 0, 150, 300, 0.25);
    // 取っ手
    ctx.strokeStyle = '#e5e7eb'; ctx.lineWidth = 30; ctx.beginPath(); ctx.ellipse(118, 0, 62, 78, 0, -1.3, 1.3); ctx.stroke();
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 18; ctx.beginPath(); ctx.ellipse(118, 0, 62, 78, 0, -1.3, 1.3); ctx.stroke();
    // 本体（円柱の陰影）
    const g = ctx.createLinearGradient(-130, 0, 130, 0);
    g.addColorStop(0, '#d1d5db'); g.addColorStop(0.25, '#ffffff'); g.addColorStop(0.7, '#f3f4f6'); g.addColorStop(1, '#c7cbd1');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(-130, -140); ctx.lineTo(-130, 128); ctx.ellipse(0, 128, 130, 26, 0, Math.PI, 0, true); ctx.lineTo(130, -140); ctx.closePath(); ctx.fill();
    // プリント（回転しているように横に流す）
    ctx.save(); ctx.beginPath(); ctx.rect(-126, -140, 252, 290); ctx.clip();
    const ph = Math.sin(t * 1.6) * 40;
    const fw = 190, fh = fw * this.face.height / this.face.width;
    ctx.globalAlpha = 0.95; ctx.drawImage(this.face, -fw / 2 + ph, -fh / 2 - 6, fw, fh);
    ctx.restore();
    // 光沢
    ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.fillRect(-92, -130, 16, 250);
    // 口
    ctx.fillStyle = '#e5e7eb'; ctx.beginPath(); ctx.ellipse(0, -140, 130, 26, 0, 0, L.TAU); ctx.fill();
    ctx.fillStyle = '#5b3a29'; ctx.beginPath(); ctx.ellipse(0, -138, 116, 20, 0, 0, L.TAU); ctx.fill();
    ctx.restore();
  },
  tshirt(ctx, t, x, y, s) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.rotate(Math.sin(t * 2) * 0.03);
    L.groundShadow(ctx, 0, 190, 320, 0.2);
    ctx.beginPath();
    ctx.moveTo(-48, -170); ctx.quadraticCurveTo(0, -128, 48, -170);
    ctx.lineTo(120, -146); ctx.lineTo(196, -70); ctx.lineTo(148, -18); ctx.lineTo(118, -46);
    ctx.lineTo(120, 176); ctx.quadraticCurveTo(0, 186, -120, 176); ctx.lineTo(-118, -46);
    ctx.lineTo(-148, -18); ctx.lineTo(-196, -70); ctx.lineTo(-120, -146); ctx.closePath();
    const g = ctx.createLinearGradient(-200, 0, 200, 0);
    g.addColorStop(0, '#4b3326'); g.addColorStop(0.5, '#6b4a37'); g.addColorStop(1, '#4b3326');
    ctx.fillStyle = g; ctx.shadowColor = 'rgba(0,0,0,0.25)'; ctx.shadowBlur = 20; ctx.shadowOffsetY = 10; ctx.fill(); ctx.shadowColor = 'transparent';
    ctx.strokeStyle = 'rgba(0,0,0,0.25)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(-48, -170); ctx.quadraticCurveTo(0, -112, 48, -170); ctx.stroke();
    const fw = 170, fh = fw * this.face.height / this.face.width;
    ctx.drawImage(this.face, -fw / 2, -100, fw, fh);
    L.text(ctx, 'KD', 0, 120, { font: L.font(900, 34, 'Montserrat'), color: '#a7f3d0', align: 'center', spacing: 6 });
    ctx.restore();
  },
  acrylic(ctx, t, x, y, s) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
    L.groundShadow(ctx, 0, 172, 280, 0.25);
    // 台座
    ctx.fillStyle = 'rgba(255,255,255,0.55)'; ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(0, 160, 130, 26, 0, 0, L.TAU); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(0, 150, 130, 26, 0, 0, L.TAU); ctx.fill(); ctx.stroke();
    const fw = 280, fh = fw * this.full.height / this.full.width;
    ctx.drawImage(this.full, -fw / 2, 150 - fh, fw, fh);
    // 光沢が走る
    const k = ((t * 0.7) % 1.5) - 0.25;
    ctx.save(); ctx.globalAlpha = 0.45; ctx.beginPath(); ctx.rect(-fw / 2, 150 - fh, fw, fh); ctx.clip();
    const gx = -fw / 2 + k * fw;
    const g = ctx.createLinearGradient(gx - 40, 0, gx + 40, 0);
    g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,255,255,0.9)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g; ctx.transform(1, 0, -0.4, 1, 0, 0); ctx.fillRect(gx - 40 + 60, 150 - fh, 80, fh);
    ctx.restore();
    ctx.restore();
  },
  sticker(ctx, t, x, y, s) {
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.rotate(-0.12 + Math.sin(t * 2.4) * 0.05);
    const fw = 320, fh = fw * this.face.height / this.face.width;
    ctx.shadowColor = 'rgba(0,0,0,0.28)'; ctx.shadowBlur = 22; ctx.shadowOffsetY = 12;
    ctx.drawImage(this.face, -fw / 2, -fh / 2, fw, fh);
    ctx.restore();
  },
  draw(ctx, t) {
    const { w, h } = this, C = 2, E = L.E;
    const CHOCO = '#4a2c1d', MINT = '#a7f3d0';
    L.linear(ctx, w, h, ['#ecfdf5', '#d1fae5', '#a7f3d0'], 110);
    // チョコチップ模様
    const r = L.rng(12);
    for (let i = 0; i < 36; i++) {
      const x = r() * w, y = ((r() * h) + t * 18) % (h + 40) - 20, s = 5 + r() * 8;
      ctx.save(); ctx.translate(x, y); ctx.rotate(r() * 3 + t * 0.5); ctx.fillStyle = 'rgba(74,44,29,0.16)';
      ctx.beginPath(); ctx.moveTo(-s, s * 0.6); ctx.lineTo(0, -s); ctx.lineTo(s, s * 0.6); ctx.closePath(); ctx.fill(); ctx.restore();
    }
    const fadeOut = E.inCubic(L.prog(t, 8.55, 8.95));
    ctx.save(); ctx.globalAlpha = 1 - fadeOut;

    // ── イントロ：マスコットが登場して "NEW GOODS!"
    if (t < 2.2) {
      const p = E.outBack(L.prog(t, 0.1, 0.6)), out = E.inBack(L.prog(t, 1.6, 2.0));
      L.glowBlob(ctx, 360, 480, 300, 'rgba(255,255,255,0.8)', p);
      L.rays(ctx, 360, 480, 16, 40, 520 * p, 'rgba(255,255,255,0.35)', t * 0.4, 0.08);
      L.liveChar(ctx, C, 360, 860 + out * 700, 560 * p, t, { period: 0.8, shadow: 'rgba(74,44,29,0.25)' });
      const tp = E.outBack(L.prog(t, 0.45, 0.85)) * (1 - out);
      ctx.save(); ctx.translate(360, 170); ctx.scale(tp, tp); ctx.rotate(-0.06);
      L.text(ctx, 'NEW GOODS!', 0, 0, { font: L.font(900, 92, 'Montserrat'), color: '#fff', align: 'center', stroke: CHOCO, strokeWidth: 14, shadow: 'rgba(74,44,29,0.3)', shadowBlur: 0, shadowY: 8 });
      ctx.restore();
      L.confetti(ctx, t, 0.5, 360, 400, { n: 50, seed: 2, colors: ['#4a2c1d', '#ffffff', '#34d399', '#f472b6'], vmin: 300, vmax: 700 });
    }

    // ── 商品を1つずつ紹介
    const items = [
      { name: 'マグカップ', en: 'MUG', fn: 'mug', s: 1.0 },
      { name: 'Tシャツ', en: 'T-SHIRT', fn: 'tshirt', s: 1.05 },
      { name: 'アクリルスタンド', en: 'ACRYLIC STAND', fn: 'acrylic', s: 1.05 },
      { name: 'ステッカー', en: 'STICKER', fn: 'sticker', s: 1.0 },
    ];
    const T0 = 2.0, D = 1.3;
    items.forEach((it, i) => {
      const a = T0 + i * D, b = a + D;
      if (t < a - 0.1 || t > b + 0.35) return;
      const pin = E.outBack(L.prog(t, a, a + 0.45));
      const pout = E.inCubic(L.prog(t, b - 0.05, b + 0.3));
      const x = 360 + (1 - pin) * 600 - pout * 650;
      const rot = (1 - pin) * 0.5 - pout * 0.4;
      // 背後の円
      ctx.save(); ctx.globalAlpha *= 1 - pout;
      ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(360, 430, 250 * E.outBack(L.prog(t, a - 0.05, a + 0.35)), 0, L.TAU); ctx.fill();
      ctx.strokeStyle = CHOCO; ctx.lineWidth = 4; ctx.setLineDash([10, 12]);
      ctx.beginPath(); ctx.arc(360, 430, 268 * E.outBack(L.prog(t, a, a + 0.4)), t * 0.5, t * 0.5 + L.TAU); ctx.stroke(); ctx.setLineDash([]);
      ctx.restore();
      ctx.save(); ctx.translate(x, 430); ctx.rotate(rot); ctx.translate(-x, -430);
      this[it.fn](ctx, t, x, 430, it.s);
      ctx.restore();
      // 名前
      const np = E.outBack(L.prog(t, a + 0.2, a + 0.55)) * (1 - pout);
      ctx.save(); ctx.translate(360, 790); ctx.scale(np, np);
      L.text(ctx, it.en, 0, -46, { font: L.font(900, 26, 'Montserrat'), color: '#059669', align: 'center', spacing: 6 });
      L.pill(ctx, it.name, 0, 14, { font: L.font(900, 40), bg: CHOCO, color: '#fff', padX: 34 });
      ctx.restore();
      // NEW バッジ
      const bp = E.outBackBig(L.prog(t, a + 0.3, a + 0.6)) * (1 - pout);
      ctx.save(); ctx.translate(575, 215); ctx.rotate(0.25 + Math.sin(t * 4) * 0.05); ctx.scale(bp, bp);
      ctx.fillStyle = '#f472b6'; L.star(ctx, 0, 0, 66, 52, 14); ctx.fill();
      L.text(ctx, 'NEW', 0, 11, { font: L.font(900, 30, 'Montserrat'), color: '#fff', align: 'center' });
      ctx.restore();
      // 番号
      L.text(ctx, `0${i + 1}`, 60, 110, { font: L.font(900, 64, 'Montserrat'), color: 'rgba(74,44,29,0.18)', alpha: 1 - pout });
    });

    // ── ラスト：ラインナップ＋販売中
    if (t > 7.45) {
      const g = (k) => E.outBack(L.prog(t, 7.5 + k * 0.08, 7.85 + k * 0.08));
      const cells = [[200, 330, 'mug', 0.55], [520, 330, 'tshirt', 0.5], [200, 600, 'acrylic', 0.5], [520, 590, 'sticker', 0.55]];
      cells.forEach(([x, y, fn, s], k) => {
        const p = g(k); if (p <= 0) return;
        ctx.save(); ctx.globalAlpha *= L.clamp(p);
        L.panel(ctx, x - 145, y - 130, 290, 260, 28, { fill: '#ffffff', shadow: 'rgba(74,44,29,0.15)', shadowBlur: 20, shadowY: 8 });
        this[fn](ctx, t, x, y, s * p);
        ctx.restore();
      });
      const tp = E.outBack(L.prog(t, 7.6, 8.0));
      ctx.save(); ctx.translate(360, 100); ctx.scale(tp, tp);
      L.text(ctx, 'ETERNAL STORE', 0, 0, { font: L.font(900, 52, 'Montserrat'), color: CHOCO, align: 'center', spacing: 3 });
      ctx.restore();
      const cp = E.outBack(L.prog(t, 7.8, 8.2));
      ctx.save(); ctx.translate(360, 815); ctx.scale(cp, cp);
      L.panel(ctx, -200, -40, 400, 80, 40, { fill: [CHOCO, '#6b4a37'], shadow: 'rgba(74,44,29,0.35)', shadowBlur: 20 });
      L.text(ctx, '公式ストアで販売中 ▶', 0, 12, { font: L.font(900, 32), color: MINT, align: 'center' });
      ctx.restore();
    }
    // 常に右下からマスコットがのぞく（商品紹介中）
    if (t > 2.0 && t < 7.5) {
      const p = E.outBack(L.prog(t, 2.0, 2.4)) * (1 - E.inBack(L.prog(t, 7.1, 7.45)));
      const hop = Math.abs(Math.sin(((t - T0) / D) * Math.PI)) * 14;
      L.drawChar(ctx, C, 640, 900 + 120 * (1 - p) - hop * 0, 230, { rot: -0.15, shadow: 'rgba(74,44,29,0.25)' });
    }
    ctx.restore();
  },
};
