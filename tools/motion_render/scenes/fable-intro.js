// Claude Fable 5.2 紹介動画（16:9 / 20秒）キャラなし — ターミナル → タイトル → 位置づけ → 3つのポイント → エンドカード
// 書いてある内容は公開されている事実だけ（ベンチマーク等の数値は入れていない）。非公式の紹介動画。
window.SCENE = {
  w: 1280, h: 720, dur: 20, poster: 5.6,
  MONO: (weight, size) => `${weight} ${size}px "DejaVu Sans Mono", "Liberation Mono", "Noto Sans JP", monospace`,
  C: { bg0: '#0d0b0a', bg1: '#1a1411', coral: '#e8825a', amber: '#f5c06a', cream: '#f6efe6', dim: 'rgba(246,239,230,0.6)' },

  // 場面ごとのフェード＋わずかなズーム（a〜b 秒）
  stage(ctx, t, a, b, fn) {
    const al = L.env(t, a, b, 0.45, 0.4);
    if (al <= 0) return;
    const z = 1 + (1 - L.E.outCubic(L.prog(t, a, a + 0.6))) * 0.05 + L.E.inCubic(L.prog(t, b - 0.4, b)) * 0.06;
    ctx.save(); ctx.globalAlpha = al;
    ctx.translate(640, 360); ctx.scale(z, z); ctx.translate(-640, -360);
    fn(); ctx.restore();
  },

  terminal(ctx, t) {
    const { C, MONO } = this;
    const x = 190, y = 150, w = 900, h = 400;
    L.panel(ctx, x, y, w, h, 18, { fill: '#15110f', stroke: 'rgba(246,239,230,0.14)', shadow: 'rgba(0,0,0,0.6)', shadowBlur: 50 });
    L.panel(ctx, x, y, w, 46, 18, { fill: 'rgba(246,239,230,0.05)' });
    ['#ff5f57', '#febc2e', '#28c840'].forEach((c, i) => { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x + 28 + i * 24, y + 23, 7, 0, L.TAU); ctx.fill(); });
    L.text(ctx, 'terminal', x + w / 2, y + 30, { font: MONO(400, 16), color: C.dim, align: 'center' });

    const cmd = 'claude --model claude-fable-5-2';
    const n = Math.floor(L.prog(t, 0.5, 2.2) * cmd.length);
    const f = MONO(700, 30), lx = x + 44, ly = y + 118;
    L.text(ctx, '$', lx, ly, { font: f, color: C.coral });
    const typed = cmd.slice(0, n);
    L.text(ctx, typed, lx + 36, ly, { font: f, color: C.cream });
    const cw = L.measure(ctx, typed, { font: f });
    if (t < 2.5 && (n < cmd.length || Math.floor(t * 3) % 2 === 0)) { ctx.fillStyle = C.amber; ctx.fillRect(lx + 40 + cw, ly - 28, 16, 34); }

    const rows = [['model', 'claude-fable-5-2'], ['family', 'Claude 5'], ['tier', 'Mythos class'], ['status', 'ready']];
    rows.forEach(([k, v], i) => {
      const p = L.E.outCubic(L.prog(t, 2.45 + i * 0.22, 2.75 + i * 0.22));
      if (p <= 0) return;
      const ry = ly + 70 + i * 50;
      L.text(ctx, k, lx + 36 - (1 - p) * 14, ry, { font: MONO(400, 26), color: C.dim, alpha: p });
      L.text(ctx, v, lx + 200 - (1 - p) * 14, ry, { font: MONO(700, 26), color: i === 3 ? '#7ddc8a' : C.amber, alpha: p });
    });
  },

  title(ctx, t) {
    const { C } = this, E = L.E, t0 = 3.9;
    L.glowBlob(ctx, 640, 340, 460, 'rgba(232,130,90,0.3)', L.prog(t, t0, t0 + 1));
    L.ring(ctx, 640, 340, 300, E.inOutCubic(L.prog(t, t0, t0 + 1.4)), 2, 'rgba(245,192,106,0.45)');
    L.ring(ctx, 640, 340, 322, E.inOutCubic(L.prog(t, t0 + 0.2, t0 + 1.7)), 1, 'rgba(246,239,230,0.2)', Math.PI / 2);
    const cp = L.prog(t, t0 + 0.1, t0 + 0.6);
    L.text(ctx, 'CLAUDE', 640, 232, { font: L.font(700, 30, 'Montserrat'), color: C.cream, align: 'center', spacing: L.lerp(40, 18, E.outCubic(cp)), alpha: cp });
    ctx.save(); ctx.beginPath(); ctx.rect(0, 230, 1280, 170); ctx.clip();
    L.charText(ctx, 'Fable 5.2', 640, 380, t, { font: L.font(900, 150, 'Montserrat'), grad: [C.coral, C.amber], align: 'center', t0: t0 + 0.3, stagger: 0.06, dur: 0.6, mode: 'rise', rise: 170, ease: E.outQuart, spacing: 2 });
    ctx.restore();
    const lp = E.outExpo(L.prog(t, t0 + 1.1, t0 + 1.7));
    ctx.fillStyle = C.amber; ctx.fillRect(640 - 150 * lp, 420, 300 * lp, 3);
    const sp = E.outCubic(L.prog(t, t0 + 1.3, t0 + 1.8));
    L.text(ctx, 'Claude 5 ファミリーの最新モデル', 640, 478 + (1 - sp) * 16, { font: L.font(700, 34), color: C.cream, align: 'center', spacing: 3, alpha: sp });
  },

  ladder(ctx, t) {
    const { C } = this, E = L.E, t0 = 7.8;
    const hp = E.outCubic(L.prog(t, t0, t0 + 0.5));
    L.text(ctx, 'Opus の上位、', 640, 108 + (1 - hp) * 14, { font: L.font(900, 46), color: C.cream, align: 'right', alpha: hp });
    L.text(ctx, 'Mythos クラス', 648, 108 + (1 - hp) * 14, { font: L.font(900, 46), grad: [C.coral, C.amber], align: 'left', alpha: hp });
    const cols = [['Haiku', 120], ['Sonnet', 185], ['Opus', 250], ['Fable 5.2', 350]];
    const bw = 200, gap = 40, x0 = 180, base = 600;
    cols.forEach(([name, hgt], i) => {
      const top = i === 3;
      const p = E.outBack(L.prog(t, t0 + 0.4 + i * 0.22, t0 + 1.1 + i * 0.22));
      if (p <= 0) return;
      const x = x0 + i * (bw + gap), hh = hgt * p;
      if (top) L.glowBlob(ctx, x + bw / 2, base - hh / 2, 260, 'rgba(232,130,90,0.35)', L.clamp(p));
      L.panel(ctx, x, base - hh, bw, hh, 14, top ? { fill: [C.amber, C.coral], vertical: true, shadow: 'rgba(232,130,90,0.6)', shadowBlur: 40, shadowY: 0 }
        : { fill: 'rgba(246,239,230,0.1)', stroke: 'rgba(246,239,230,0.22)' });
      L.text(ctx, name, x + bw / 2, base + 44, { font: L.font(top ? 900 : 700, top ? 30 : 26, 'Montserrat'), color: top ? C.amber : C.dim, align: 'center', alpha: L.clamp(p) });
    });
    const pp = E.outBack(L.prog(t, t0 + 1.6, t0 + 2.1));
    if (pp > 0) {
      ctx.save(); ctx.translate(1000, 208); ctx.scale(pp, pp);
      L.pill(ctx, 'Mythos クラス', 0, 8, { font: L.font(900, 24), bg: C.cream, color: '#1a1411' });
      ctx.restore();
    }
    L.text(ctx, '※ モデルの位置づけのイメージ図です（性能の数値ではありません）', 640, 692, { font: L.font(500, 18), color: 'rgba(246,239,230,0.45)', align: 'center', alpha: L.prog(t, t0 + 1.2, t0 + 1.7) });
  },

  points(ctx, t) {
    const { C } = this, E = L.E, t0 = 11.9;
    const hp = E.outCubic(L.prog(t, t0, t0 + 0.5));
    L.text(ctx, 'Fable 5.2 の 3 つのポイント', 640, 130 + (1 - hp) * 14, { font: L.font(900, 44), color: C.cream, align: 'center', alpha: hp });
    const cards = [
      ['01', '最新', ['Claude 5 ファミリーの', '最新モデル']],
      ['02', '最高の知性', ['一般提供モデルの中で', '最もインテリジェント']],
      ['03', '安全対策', ['デュアルユース領域に', '追加のセーフガード']],
    ];
    const cw = 340, ch = 330, gap = 40, x0 = 90, y0 = 210;
    cards.forEach(([num, head, body], i) => {
      const p = E.outCubic(L.prog(t, t0 + 0.4 + i * 0.3, t0 + 1.0 + i * 0.3));
      if (p <= 0) return;
      const x = x0 + i * (cw + gap), y = y0 + (1 - p) * 60;
      ctx.save(); ctx.globalAlpha *= p;
      L.panel(ctx, x, y, cw, ch, 22, { fill: ['rgba(246,239,230,0.09)', 'rgba(246,239,230,0.03)'], stroke: 'rgba(245,192,106,0.35)', shadow: 'rgba(0,0,0,0.45)' });
      L.text(ctx, num, x + 34, y + 84, { font: L.font(900, 56, 'Montserrat'), grad: [C.coral, C.amber] });
      ctx.fillStyle = C.amber; ctx.fillRect(x + 34, y + 108, 48 * E.outExpo(L.prog(t, t0 + 0.8 + i * 0.3, t0 + 1.3 + i * 0.3)), 4);
      L.text(ctx, head, x + 34, y + 180, { font: L.font(900, 42), color: C.cream });
      body.forEach((line, k) => L.text(ctx, line, x + 34, y + 236 + k * 40, { font: L.font(500, 25), color: 'rgba(246,239,230,0.78)' }));
      ctx.restore();
    });
  },

  endcard(ctx, t) {
    const { C, MONO } = this, E = L.E, t0 = 16.3;
    L.glowBlob(ctx, 640, 320, 420, 'rgba(232,130,90,0.28)', L.prog(t, t0, t0 + 0.8));
    const p = E.outCubic(L.prog(t, t0, t0 + 0.6));
    L.text(ctx, 'CLAUDE', 640, 210, { font: L.font(700, 26, 'Montserrat'), color: C.cream, align: 'center', spacing: 18, alpha: p });
    L.text(ctx, 'Fable 5.2', 640, 320 + (1 - p) * 20, { font: L.font(900, 116, 'Montserrat'), grad: [C.coral, C.amber], align: 'center', alpha: p, glow: 'rgba(232,130,90,0.5)', glowBlur: 40 });
    const q = E.outBack(L.prog(t, t0 + 0.6, t0 + 1.1));
    if (q > 0) {
      const f = MONO(700, 28), s = 'claude-fable-5-2';
      const w = L.measure(ctx, s, { font: f }) + 72;
      ctx.save(); ctx.translate(640, 420); ctx.scale(q, q);
      L.panel(ctx, -w / 2, -34, w, 68, 14, { fill: '#15110f', stroke: 'rgba(245,192,106,0.6)' });
      L.text(ctx, s, 0, 10, { font: f, color: C.amber, align: 'center' });
      ctx.restore();
    }
    const r = L.prog(t, t0 + 1.1, t0 + 1.6);
    L.text(ctx, 'モデル ID', 640, 364, { font: L.font(700, 18), color: C.dim, align: 'center', alpha: r, spacing: 4 });
    L.text(ctx, 'anthropic.com/claude/fable', 640, 530, { font: L.font(700, 28, 'Montserrat'), color: C.cream, align: 'center', alpha: r, spacing: 1 });
    L.text(ctx, '制作: ETERNAL d.c.t ／ 非公式の紹介動画です', 640, 680, { font: L.font(500, 17), color: 'rgba(246,239,230,0.45)', align: 'center', alpha: r });
  },

  draw(ctx, t) {
    const { w, h, C } = this;
    L.linear(ctx, w, h, [C.bg0, C.bg1, C.bg0], 60);
    L.blobs(ctx, w, h, t, [
      { x: 0.2, y: 0.25, r: 0.32, color: 'rgba(232,130,90,0.16)' },
      { x: 0.82, y: 0.75, r: 0.36, color: 'rgba(245,192,106,0.11)', speed: -1 },
    ], 20);
    // うすいグリッド（ゆっくり流れる）
    ctx.save(); ctx.strokeStyle = 'rgba(246,239,230,0.035)'; ctx.lineWidth = 1; ctx.beginPath();
    const off = (t * 8) % 64;
    for (let x = -64 + off; x < w; x += 64) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = -64 + off; y < h; y += 64) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke(); ctx.restore();
    L.risingParticles(ctx, w, h, t, { n: 34, P: 20, color: C.amber, alpha: 0.35, sparkle: true, seed: 11 });

    this.stage(ctx, t, 0.1, 3.9, () => this.terminal(ctx, t));
    this.stage(ctx, t, 3.8, 7.8, () => this.title(ctx, t));
    this.stage(ctx, t, 7.7, 11.9, () => this.ladder(ctx, t));
    this.stage(ctx, t, 11.8, 16.3, () => this.points(ctx, t));
    this.stage(ctx, t, 16.2, 19.9, () => this.endcard(ctx, t));
    L.vignette(ctx, w, h, 0.55);
  },
};
