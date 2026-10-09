// 縦型リリックモーション「灯（ともしび）」（9:16 / 15秒・SNSショート向け）キャラ: 3 — 歌詞はオリジナル
// 夜 → 夜明けへ。縦書きの歌詞から生まれた光が地平線に落ちて朝日になる。最後は暗転して頭に戻る（ループ再生用）
// 文字は TikTok / リール の UI（上150px・下300px・右端100px）にかからない範囲に置いている
window.SCENE = {
  w: 720, h: 1280, dur: 15, poster: 9.6,
  async init() {
    await document.fonts.load('800 20px "Shippori Mincho"', '灯夜朝');
  },
  draw(ctx, t) {
    const { w, h } = this, C = 3, E = L.E;
    const BEAT = 0.6;
    const bp = Math.pow(1 - ((t % BEAT) / BEAT), 3); // 拍ごとのパルス
    const MIN = (s) => L.font(800, s, 'Shippori Mincho');
    const dawn = E.inOutSine(L.prog(t, 6.9, 10.6)); // 0: 夜 → 1: 夜明け
    const fadeIn = E.outCubic(L.prog(t, 0, 0.7));
    const fadeOut = 1 - E.inCubic(L.prog(t, 14.2, 14.95));

    // ── 空 ──
    const mix = (a, b, k) => {
      const p = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
      const [x, y] = [p(a), p(b)];
      return `rgb(${x.map((v, i) => Math.round(L.lerp(v, y[i], k))).join(',')})`;
    };
    const night = ['#04030c', '#110b2b', '#241650'];
    const day = ['#1b1550', '#8a2e6e', '#f6a05e'];
    L.linear(ctx, w, h, night.map((c, i) => mix(c, day[i], dawn)), 90);

    // カメラ: 全体がゆっくり寄っていく
    ctx.save();
    const zoom = 1 + 0.06 * (t / 15);
    ctx.translate(w / 2, h * 0.55); ctx.scale(zoom, zoom); ctx.translate(-w / 2, -h * 0.55);

    // 星（夜明けとともに消える）
    const r = L.rng(5);
    for (let i = 0; i < 120; i++) {
      const x = r() * w, y = r() * h * 0.7, s = 0.5 + r() * 1.5, ph = r() * 10;
      const tw = 0.3 + 0.7 * Math.abs(Math.sin(t * (0.7 + r()) + ph));
      ctx.globalAlpha = tw * 0.85 * (1 - dawn) * fadeIn; ctx.fillStyle = '#e0e7ff';
      ctx.beginPath(); ctx.arc(x, y, s, 0, L.TAU); ctx.fill();
    }
    ctx.globalAlpha = 1;

    // 最後はカメラが上を向く（景色とキャラが下がり、タイトルの場所が空く）
    const tilt = 170 * E.inOutCubic(L.prog(t, 10.9, 12.3));
    ctx.save(); ctx.translate(0, tilt);

    // ── 朝日（キャラと霧の後ろ） ──
    const SX = 410, sunY = L.lerp(1200, 870, E.outCubic(L.prog(t, 7.1, 11.2)));
    if (t > 7.0) {
      const sa = L.prog(t, 7.0, 7.6);
      ctx.save(); ctx.globalAlpha = sa; ctx.globalCompositeOperation = 'lighter';
      L.rays(ctx, SX, sunY, 18, 160, 1100, 'rgba(255,214,170,0.05)', t * 0.08, 0.05);
      ctx.restore();
      L.glowBlob(ctx, SX, sunY, 520 + bp * 30, 'rgba(255,170,110,0.55)', sa);
      ctx.save(); ctx.globalAlpha = sa; ctx.shadowColor = 'rgba(255,200,140,1)'; ctx.shadowBlur = 80;
      const sg = ctx.createRadialGradient(SX, sunY - 40, 10, SX, sunY, 150);
      sg.addColorStop(0, '#fffbeb'); sg.addColorStop(1, '#fdba74');
      ctx.fillStyle = sg; ctx.beginPath(); ctx.arc(SX, sunY, 150 + bp * 4, 0, L.TAU); ctx.fill(); ctx.restore();
    }

    // 地平線の霧
    const fg = ctx.createLinearGradient(0, 900, 0, h);
    const fogC = mix('#0b0820', '#3b1640', dawn);
    fg.addColorStop(0, L.clear('#000000')); fg.addColorStop(0.35, fogC); fg.addColorStop(1, fogC);
    ctx.fillStyle = fg; ctx.fillRect(-40, 900, w + 80, h);

    // 光の粒（夜は青白く少なく、朝は暖色で多く）
    L.risingParticles(ctx, w, h, t, { n: 26, P: 7.5, seed: 21, color: '#c7d2fe', alpha: 0.5 * (1 - dawn) * fadeIn, max: 2.5 });
    L.risingParticles(ctx, w, h, t, { n: 46, P: 7.5, seed: 22, color: '#ffe4c4', alpha: 0.75 * dawn, max: 3.5, sparkle: true });

    // ── キャラ（夜はシルエット、朝日で色が戻る） ──
    const rise = E.outCubic(L.prog(t, 0.2, 1.6));
    L.liveChar(ctx, C, 230, 1330 + (1 - rise) * 60, 770, t, {
      period: BEAT * 4,
      alpha: rise,
      filter: `brightness(${L.lerp(0.16, 1, dawn).toFixed(3)}) saturate(${L.lerp(0.5, 1.05, dawn).toFixed(3)})`,
      glow: dawn > 0.5 ? 'rgba(255,190,140,0.9)' : 'rgba(167,139,250,0.75)',
      glowBlur: L.lerp(30, 54, dawn),
    });
    // 手前の霧
    const ff = ctx.createLinearGradient(0, 1130, 0, h);
    ff.addColorStop(0, L.clear('#000000')); ff.addColorStop(1, mix('#05040f', '#2a0f2e', dawn));
    ctx.fillStyle = ff; ctx.fillRect(-40, 1130, w + 80, h);
    ctx.restore(); // tilt

    // ── 歌詞 ──
    // 縦書き: 1文字ずつ、ぼかしながら上から降りてくる
    const vText = (str, x, y, o) => {
      const step = o.step ?? o.size * 1.16;
      [...str].forEach((ch, i) => {
        const a0 = o.t0 + i * (o.stagger ?? 0.1);
        const p = E.outCubic(L.prog(t, a0, a0 + (o.dur ?? 0.55)));
        const q = o.out ? E.inCubic(L.prog(t, o.out + i * 0.03, o.out + i * 0.03 + 0.4)) : 0;
        const a = p * (1 - q);
        if (a <= 0.001) return;
        ctx.save();
        ctx.translate(x, y + i * step - (1 - p) * 26 - q * 30);
        ctx.filter = `blur(${((1 - p) * 10 + q * 8).toFixed(2)}px)`;
        L.text(ctx, ch, 0, 0, { font: MIN(o.size), color: o.color || '#f5f3ff', align: 'center', baseline: 'middle', alpha: a, glow: o.glow, glowBlur: o.glowBlur ?? 22 });
        ctx.restore();
      });
    };
    ctx.save(); ctx.globalAlpha = fadeOut;
    // 1. 名前のない夜に
    if (t < 4.0) vText('名前のない夜に', 560, 300, { size: 70, t0: 0.6, stagger: 0.16, out: 3.3, glow: 'rgba(167,139,250,0.7)' });
    // 2. 声をひとつ / 灯した
    if (t > 3.4 && t < 7.6) {
      vText('声をひとつ', 590, 300, { size: 58, t0: 3.6, stagger: 0.13, out: 6.9, color: '#ddd6fe' });
      vText('灯した', 470, 420, { size: 96, t0: 4.6, stagger: 0.22, out: 6.95, glow: 'rgba(253,186,116,0.85)', glowBlur: 30 });
      // 「灯」の字に火がともる
      const lit = E.outCubic(L.prog(t, 4.7, 5.3)) * (1 - L.prog(t, 5.9, 6.2));
      L.glowBlob(ctx, 470, 420, 120 + bp * 20, 'rgba(253,186,116,0.6)', lit);
    }
    // 灯から生まれた光が地平線に落ちて朝日になる
    const orbAt = (tt) => {
      const k = E.inOutCubic(L.prog(tt, 5.9, 7.1));
      const x = L.lerp(470, SX, k) + Math.sin(k * Math.PI) * -160;
      const y = L.lerp(420, 1060, E.inQuad(k));
      return [x, y, k];
    };
    if (t > 5.8 && t < 7.2) {
      for (let j = 14; j >= 0; j--) {
        const [x, y] = orbAt(t - j * 0.025);
        L.glowBlob(ctx, x, y, 34 - j * 1.6, 'rgba(255,214,170,0.9)', (1 - j / 15) * 0.8);
      }
      const [x, y] = orbAt(t);
      L.sparkle(ctx, x, y, 26 + bp * 8, '#fff7ed', 1);
    }
    // 3. 誰かの / 朝になれ
    if (t > 7.4 && t < 11.6) {
      L.charText(ctx, '誰かの', w / 2, 330, t, { font: MIN(52), color: '#fff7ed', align: 'center', t0: 7.6, stagger: 0.14, dur: 0.5, mode: 'blur', spacing: 18, out: { t: 10.9, stagger: 0.03, dur: 0.35 } });
      L.charText(ctx, '朝になれ', w / 2, 480, t, { font: MIN(124), grad: ['#fde68a', '#fff7ed', '#fbcfe8'], align: 'center', t0: 8.3, stagger: 0.2, dur: 0.6, mode: 'drop', spacing: 6, glow: 'rgba(251,146,60,0.75)', glowBlur: 34, wave: 5, out: { t: 10.95, stagger: 0.04, dur: 0.4 } });
    }
    // 4. タイトル「灯」
    if (t > 11.0) {
      const tp = E.outExpo(L.prog(t, 11.2, 12.3));
      ctx.save();
      ctx.translate(w / 2, 360); const s = 1.25 - 0.25 * tp + bp * 0.012; ctx.scale(s, s);
      ctx.filter = `blur(${((1 - tp) * 14).toFixed(2)}px)`;
      L.text(ctx, '灯', 0, 0, { font: MIN(250), grad: ['#fde68a', '#ffffff', '#fdba74'], gradV: true, gradH: 220, align: 'center', baseline: 'middle', alpha: tp, glow: 'rgba(251,146,60,0.9)', glowBlur: 50 });
      ctx.restore();
      L.ring(ctx, w / 2, 360, 175, E.inOutCubic(L.prog(t, 11.5, 12.7)), 2, 'rgba(255,237,213,0.7)', -Math.PI / 2 + t * 0.15);
      L.charText(ctx, 'TOMOSHIBI', w / 2, 600, t, { font: L.font(700, 30, 'Montserrat'), color: '#fff7ed', align: 'center', t0: 12.2, stagger: 0.05, dur: 0.5, mode: 'blur', spacing: 16 });
      const lw = 220 * E.outCubic(L.prog(t, 12.6, 13.2));
      ctx.fillStyle = 'rgba(255,237,213,0.7)'; ctx.fillRect(w / 2 - lw / 2, 628, lw, 1.5);
      L.charText(ctx, 'Original Song  /  ETERNALd.c.t', w / 2, 668, t, { font: L.font(700, 19, 'Montserrat'), color: 'rgba(255,237,213,0.9)', align: 'center', t0: 12.8, stagger: 0.015, dur: 0.4, mode: 'rise', rise: 10, spacing: 2 });
    }
    ctx.restore();
    ctx.restore(); // カメラ

    // 光が地平線に落ちた瞬間のフラッシュと横に伸びる光
    const fl = L.env(t, 7.05, 7.9, 0.08, 0.7);
    if (fl > 0) {
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      ctx.fillStyle = `rgba(255,236,214,${0.55 * fl})`; ctx.fillRect(0, 0, w, h);
      const sg = ctx.createLinearGradient(0, 0, w, 0);
      sg.addColorStop(0, 'rgba(255,200,150,0)'); sg.addColorStop(0.5, `rgba(255,250,240,${fl})`); sg.addColorStop(1, 'rgba(255,200,150,0)');
      ctx.fillStyle = sg; ctx.fillRect(0, 1056, w, 8 * fl + 2);
      ctx.restore();
    }

    // クレジット（上部のUIを避けた位置）
    ctx.globalAlpha = fadeIn * fadeOut * (1 - L.prog(t, 10.8, 11.3));
    L.text(ctx, '♪ 灯 — ETERNALd.c.t', 48, 196, { font: L.font(700, 18, 'Montserrat'), color: 'rgba(237,233,254,0.8)', spacing: 1 });
    ctx.globalAlpha = 1;
    L.vignette(ctx, w, h, 0.55);
    // 頭と終わりの暗転（ループのつなぎ目）
    const black = Math.max(1 - fadeIn, 1 - fadeOut);
    if (black > 0) { ctx.fillStyle = `rgba(4,3,12,${black})`; ctx.fillRect(0, 0, w, h); }
  },
};
