// テロップ・字幕アニメーション（9:16 / 11秒）キャラ: 2 — 撮影素材に見立てた部屋のシーンに動くテロップをのせる
window.SCENE = {
  w: 720, h: 1280, dur: 11, poster: 3.0,
  async init() {
    // 部屋の背景（被写界深度っぽくぼかしたもの）を一度だけ描いておく
    const c = document.createElement('canvas'); c.width = 900; c.height = 1500;
    const g = c.getContext('2d');
    const wall = g.createLinearGradient(0, 0, 0, 1500); wall.addColorStop(0, '#fde7d1'); wall.addColorStop(1, '#f5cfae');
    g.fillStyle = wall; g.fillRect(0, 0, 900, 1500);
    // 窓
    const sky = g.createLinearGradient(0, 180, 0, 700); sky.addColorStop(0, '#bae6fd'); sky.addColorStop(1, '#fef3c7');
    g.fillStyle = '#fff'; g.fillRect(470, 160, 360, 560); g.fillStyle = sky; g.fillRect(490, 180, 320, 520);
    g.fillStyle = '#fff'; g.fillRect(645, 180, 10, 520); g.fillRect(490, 430, 320, 10);
    // 棚と小物
    g.fillStyle = '#c08457'; g.fillRect(60, 520, 330, 18); g.fillRect(60, 760, 330, 18);
    [['#f472b6', 90, 440, 50, 80], ['#60a5fa', 150, 460, 40, 60], ['#34d399', 210, 420, 60, 100], ['#facc15', 300, 470, 50, 50],
      ['#a78bfa', 100, 690, 70, 70], ['#fb7185', 200, 700, 40, 60], ['#f59e0b', 270, 680, 80, 80]].forEach(([col, x, y, w, h]) => { g.fillStyle = col; g.fillRect(x, y, w, h); });
    // 観葉植物
    g.fillStyle = '#16a34a'; for (let i = 0; i < 7; i++) { g.beginPath(); g.ellipse(160 + Math.cos(i) * 50, 930 - i * 22, 26, 60, i - 3, 0, L.TAU); g.fill(); }
    g.fillStyle = '#b45309'; g.fillRect(120, 960, 90, 110);
    // 床
    const fl = g.createLinearGradient(0, 1080, 0, 1500); fl.addColorStop(0, '#d6a77a'); fl.addColorStop(1, '#a8754b');
    g.fillStyle = fl; g.fillRect(0, 1080, 900, 420);
    // ランプの光
    const lg = g.createRadialGradient(760, 900, 0, 760, 900, 300); lg.addColorStop(0, 'rgba(255,236,179,0.9)'); lg.addColorStop(1, 'rgba(255,236,179,0)');
    g.fillStyle = lg; g.fillRect(400, 500, 700, 800);
    const b = document.createElement('canvas'); b.width = 900; b.height = 1500;
    const bg = b.getContext('2d'); bg.filter = 'blur(10px)'; bg.drawImage(c, 0, 0);
    this.room = b;
  },
  // テロップ：白文字＋太い黒フチ（基本）
  telop(ctx, str, x, y, size, p, o = {}) {
    if (p <= 0) return;
    ctx.save(); ctx.translate(x, y); const s = L.E.outBack(L.clamp(p)); ctx.scale(s, s); if (o.rot) ctx.rotate(o.rot);
    L.text(ctx, str, 0, 0, { font: L.font(900, size), color: o.color || '#fff', align: 'center', stroke: o.stroke || '#111', strokeWidth: o.sw || size * 0.22, stroke2: o.stroke2, strokeWidth2: o.sw2, shadow: 'rgba(0,0,0,0.35)', shadowBlur: 0, shadowY: 6 });
    ctx.restore();
  },
  draw(ctx, t, ) {
    const { w, h } = this, C = 2, E = L.E;
    // カメラ：ジャンプカットでズーム＋手ぶれ
    const cuts = [[0, 1.0, 0], [2.0, 1.28, -30], [4.1, 1.06, 10], [6.3, 1.18, 0], [8.4, 1.45, -40], [9.6, 1.0, 0]];
    let zoom = 1, ox = 0;
    cuts.forEach(([ct, z, x]) => { if (t >= ct) { zoom = z; ox = x; } });
    zoom *= 1 + 0.02 * L.prog(t % 2.1, 0, 2.1); // ゆっくり寄る
    const sh = L.shake(t, 4, 3.2, 2);
    ctx.save();
    ctx.translate(w / 2 + sh.x + ox, h * 0.62 + sh.y);
    ctx.scale(zoom, zoom);
    ctx.translate(-w / 2, -h * 0.62);
    ctx.drawImage(this.room, -90, -110, 900, 1500);
    L.groundShadow(ctx, 360, 1150, 520, 0.3);
    L.liveChar(ctx, C, 360, 1160, 740, t, { period: 1.6 });
    ctx.restore();
    // 画面上部：録画UI
    ctx.save(); ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.fillRect(0, 0, w, 84); ctx.restore();
    ctx.fillStyle = Math.floor(t * 2) % 2 ? '#ef4444' : 'rgba(239,68,68,0.4)'; ctx.beginPath(); ctx.arc(40, 46, 10, 0, L.TAU); ctx.fill();
    const sec = Math.floor(t);
    L.text(ctx, `REC 00:${String(sec).padStart(2, '0')}`, 60, 56, { font: L.font(800, 24, 'Montserrat'), color: '#fff' });
    L.pill(ctx, 'テロップ編集サンプル', w - 150, 54, { font: L.font(800, 20), bg: 'rgba(255,255,255,0.9)', color: '#111', padX: 14 });

    const Y = 1060;
    // 0〜2：今日はね…
    if (t < 2.0) this.telop(ctx, '今日はね…', 360, Y, 64, L.prog(t, 0.2, 0.5));
    // 2〜4.1：強調テロップ＋効果音
    if (t >= 2.0 && t < 4.1) {
      const p = L.prog(t, 2.05, 2.35);
      ctx.save(); ctx.globalAlpha = 0.9 * L.clamp(p * 2) * (1 - L.prog(t, 2.6, 3.0));
      L.rays(ctx, 360, 640, 40, 300, 900, 'rgba(255,255,255,0.8)', 0, 0.02);
      ctx.restore();
      this.telop(ctx, 'ドンッ', 560, 320, 110, L.prog(t, 2.0, 2.2), { color: '#fde047', stroke: '#dc2626', sw: 18, rot: 0.18 });
      this.telop(ctx, '新しいアイス', 360, Y - 90, 70, L.prog(t, 2.15, 2.45), { color: '#fde047', stroke: '#b91c1c', sw: 16, stroke2: '#fff', sw2: 4 });
      this.telop(ctx, '買ってきた！！', 360, Y + 10, 86, L.prog(t, 2.35, 2.65), { color: '#fde047', stroke: '#b91c1c', sw: 18, stroke2: '#fff', sw2: 4, rot: -0.03 });
    }
    // 4.1〜6.3：問いかけ＋視聴者リアクション
    if (t >= 4.1 && t < 6.3) {
      ctx.save(); const p = E.outBack(L.prog(t, 4.15, 4.45));
      ctx.translate(360, Y - 10); ctx.scale(p, p);
      L.panel(ctx, -300, -62, 600, 96, 16, { fill: '#10b981' });
      L.text(ctx, 'チョコミント派の人〜？', 0, 2, { font: L.font(900, 50), color: '#fff', align: 'center' });
      ctx.restore();
      const reacts = [['🙋 はーい！', 170, 320, 4.6], ['🙋‍♀️ 大好き！！', 520, 420, 4.9], ['✋ ミント最高', 200, 540, 5.2], ['🍫 チョコ多めで', 500, 640, 5.5]];
      reacts.forEach(([s, x, y, st]) => {
        const k = E.outBack(L.prog(t, st, st + 0.3)); if (k <= 0) return;
        ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
        L.pill(ctx, s, 0, 0, { font: L.font(800, 30), bg: 'rgba(255,255,255,0.95)', color: '#065f46', padX: 22, shadow: 'rgba(0,0,0,0.2)' });
        ctx.restore();
      });
    }
    // 6.3〜8.4：いただきます＋パクッ
    if (t >= 6.3 && t < 8.4) {
      this.telop(ctx, 'いただきまーす！', 360, Y, 66, L.prog(t, 6.35, 6.65), { color: '#fff', stroke: '#db2777', sw: 14 });
      this.telop(ctx, 'パクッ', 200, 360, 104, L.prog(t, 7.2, 7.4), { color: '#fff', stroke: '#111', sw: 16, rot: -0.2 });
      const r = L.rng(4);
      for (let i = 0; i < 10; i++) {
        const st = 6.6 + r() * 1.2, k = L.prog(t, st, st + 1.0), x = 120 + r() * 480;
        if (k <= 0 || k >= 1) continue;
        ctx.save(); ctx.globalAlpha = Math.sin(k * Math.PI); ctx.fillStyle = i % 2 ? '#f472b6' : '#fb7185';
        L.heart(ctx, x, 900 - k * 500, 34); ctx.fill(); ctx.restore();
      }
    }
    // 8.4〜9.6：うまっ…（アップ＋キラキラ）
    if (t >= 8.4 && t < 9.6) {
      this.telop(ctx, 'うまっ…', 360, Y - 20, 110, L.prog(t, 8.45, 8.7), { color: '#fff', stroke: '#7c3aed', sw: 20, stroke2: '#fff', sw2: 5 });
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * L.TAU + t, rr = 300 + Math.sin(t * 4 + i) * 30;
        L.sparkle(ctx, 360 + Math.cos(a) * rr, 560 + Math.sin(a) * rr * 1.1, 20, '#fde047', L.prog(t, 8.5, 8.8));
      }
    }
    // 9.6〜：締めのテロップ
    if (t >= 9.6) {
      ctx.save(); ctx.globalAlpha = 1 - E.inCubic(L.prog(t, 10.6, 10.95));
      this.telop(ctx, '最後まで見てくれて', 360, Y - 80, 50, L.prog(t, 9.65, 9.9));
      this.telop(ctx, 'ありがとう！', 360, Y + 10, 76, L.prog(t, 9.8, 10.05), { color: '#fde047', stroke: '#111', sw: 16 });
      const fp = E.outBack(L.prog(t, 10.0, 10.3));
      ctx.save(); ctx.translate(360, 1180); ctx.scale(fp, fp);
      L.panel(ctx, -150, -34, 300, 68, 34, { fill: '#ef4444' });
      L.text(ctx, '＋ フォローしてね', 0, 11, { font: L.font(900, 30), color: '#fff', align: 'center' });
      ctx.restore();
      ctx.restore();
    }
    // プログレスバー（ショート動画風）
    ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.fillRect(0, h - 6, w, 6);
    ctx.fillStyle = '#fff'; ctx.fillRect(0, h - 6, w * (t / 11), 6);
  },
};
