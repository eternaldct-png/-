'use strict';
/* ================================================================
   アマテラス MV — 中盤 1:16〜2:57（サビ1 / 間奏 / Aメロ2 / ブレイク / サビ2 / 間奏2）
   ================================================================ */
// 影つきの文字（どんな背景でも読める）
function drawTextS(c, L, x, y, fn, col = C_WHITE, sh = C_INK, off = 8) {
  c.fillStyle = sh; drawText(c, L, x + off, y + off, fn ? (g, i, n) => { const r = fn(g, i, n); if (r) r.col = undefined; return r; } : null);
  c.fillStyle = col; drawText(c, L, x, y, fn);
}
// ---------- 向日葵（フィボナッチ螺旋の種 + 花びら） ----------
const SEEDC = ['#b93a08', '#d9560c', '#f07a12', '#ff9d1c', '#ffb82e', '#ffcc48', '#ffdc6e', '#ffe89a'];
const SEEDI = ['#12306e', '#1c4a9c', '#2a6ac4', '#4c8fe0', '#7ab4f2', '#a6d2fa', '#cfe8ff', '#eef8ff'];
function sunflower(c, cx, cy, R, o = {}) {
  const N = o.n || 720, grow = o.grow === undefined ? 1 : o.grow, rot = o.rot || 0, sq = o.sq === undefined ? 1 : o.sq, pet = o.pet === undefined ? 1 : o.pet;
  const cold = o.cold || 0, press = o.press || 0, beat = o.beat || 0, a0 = c.globalAlpha;
  c.save(); c.translate(cx, cy); if (o.tilt) c.rotate(o.tilt); c.scale(1, sq);
  // 花びら（2層）
  if (pet > 0.01) for (let layer = 1; layer >= 0; layer--) {
    const M = 24; c.fillStyle = cold > .5 ? (layer ? '#5a9be8' : '#cfe6ff') : (layer ? '#ff8a14' : '#ffd23c');
    for (let i = 0; i < M; i++) {
      const pk = sat(pet * 1.6 - (i * 7 % M) / M * .6); if (pk <= 0) continue;
      const ang = rot * .5 + (i + layer * .5) / M * TAU; const len = R * (layer ? .74 : .58) * E.outBack(pk) * (1 + beat * .1 * (1 + rnd(i, layer))); const w = R * (layer ? .2 : .17);
      c.save(); c.rotate(ang); c.translate(R * .93, 0);
      c.beginPath(); c.moveTo(0, -w * .32); c.quadraticCurveTo(len * .45, -w, len, 0); c.quadraticCurveTo(len * .45, w, 0, w * .32); c.closePath(); c.fill(); c.restore();
    }
  }
  // 花の芯
  c.fillStyle = cold > .5 ? '#06122e' : '#2a0b03'; c.beginPath(); c.arc(0, 0, R * (1 - press * .25) * Math.min(1, grow * 1.5 + .02), 0, TAU); c.fill();
  // 種
  const n = Math.floor(N * grow), pal = cold > .5 ? SEEDI : SEEDC, base = R / Math.sqrt(N) * .66;
  for (let b = 0; b < 8; b++) {
    const i0 = Math.floor(b / 8 * N), i1 = Math.min(n, Math.floor((b + 1) / 8 * N)); if (i0 >= n) break;
    c.fillStyle = pal[b]; c.beginPath();
    for (let i = i0; i < i1; i++) {
      const pop = E.outBack(sat((grow * N - i) / 40));
      const r = R * .96 * Math.sqrt((i + .5) / N) * (1 - press * .25) * (1 + beat * .035 * Math.sin(i * .37));
      const th = i * 2.399963 + rot; const x = Math.cos(th) * r, y = Math.sin(th) * r; const s = base * (.55 + .45 * (i / N)) * pop * (1 + beat * .25);
      c.moveTo(x + s, y); c.arc(x, y, s, 0, TAU);
    }
    c.fill();
  }
  c.restore(); c.globalAlpha = a0;
}
// ---------- 「アマテラス」の大見出し（毎回ちがう組み方） ----------
function amaHit(c, t, t0, style, o = {}) {
  const step = .41, end = o.end || t0 + 2.75; const out = ez(t, end - .3, end, E.inCubic); if (t < t0 - .05 || out >= 1) return;
  const chars = [...'アマテラス'];
  if (style === 0) { // 横・特大。1字ずつ叩きつける
    const L = LT('アマテラス', { size: 320, track: .03 });
    drawTextS(c, L, CX, o.y || CY, (g, i) => { const k = E.outExpo(prog(t, t0 + i * step, t0 + i * step + .3)); return { a: k * (1 - out), s: lerp(2.8, 1, k), dy: -out * 80 }; }, o.col || C_WHITE, C_INK, 12);
  } else if (style === 1) { // 縦・墨色。向日葵の芯に重ねる
    const L = LT('アマテラス', { size: 150, vert: true, track: .02 });
    drawTextS(c, L, o.x || CX, o.y || CY, (g, i) => { const k = E.outExpo(prog(t, t0 + i * step, t0 + i * step + .3)); return { a: k * (1 - out), s: lerp(2.4, 1, k), dx: (1 - k) * (i % 2 ? 260 : -260) }; }, C_WHITE, C_INK, 7);
    c.save(); c.globalAlpha = ez(t, t0 + .3, t0 + 1) * (1 - out); c.fillStyle = C_WHITE; c.font = fnt(F_LAT, 34, 700); c.textAlign = 'center'; c.textBaseline = 'middle';
    const sp = lerp(40, 118, ez(t, t0 + .3, t0 + 2.4, E.outQuint)); const s = 'AMATERASU'; for (let i = 0; i < 9; i++) { const x = CX + (i - 4) * sp; if (Math.abs(x - CX) < 150) continue; c.fillText(s[i], x, CY); }
    c.restore();
  } else if (style === 2) { // 1字ずつ画面いっぱい → 最後に並ぶ
    const idx = Math.floor((t - t0) / step);
    if (idx >= 0 && idx < 5) {
      const f = (t - t0) / step - idx; const k = E.outExpo(sat(f * 2.5));
      const inv = idx % 2 === 1;
      if (inv) { c.fillStyle = C_GOLD; c.fillRect(0, 0, W, H); }
      c.fillStyle = inv ? C_INK : C_WHITE; const L = LT(chars[idx], { size: 860, fam: F_GOTH });
      drawText(c, L, CX + (idx - 2) * 70, CY + 20, () => ({ s: lerp(1.5, 1, k), rot: rs(idx, 3) * .06 * (1 - k) }));
      const Ls = LT('アマテラス', { size: 44, track: .5 }); c.fillStyle = inv ? C_INK : C_GOLD; drawText(c, Ls, CX, 990, (g, i) => ({ a: i <= idx ? 1 : .25 }));
    } else if (idx >= 5) {
      const L = LT('アマテラス', { size: 250, fam: F_GOTH, track: .04 }); const k = E.outExpo(prog(t, t0 + step * 5, t0 + step * 5 + .35));
      drawTextS(c, L, CX, CY, (g, i) => ({ a: 1 - out, s: lerp(1.6, 1, k), dy: -out * 60 }), C_WHITE, C_VERM, 10);
    }
  } else if (style === 3) { // 横・ゴシック。1字ずつ上下に段をつけて並べる
    const L = LT('アマテラス', { size: 290, fam: F_GOTH, track: .05 });
    c.save(); c.translate(CX, o.y || CY); c.rotate(-.045); c.translate(-CX, -(o.y || CY));
    drawTextS(c, L, CX, o.y || CY, (g, i) => { const k = E.outExpo(prog(t, t0 + i * step, t0 + i * step + .3)); return { a: k * (1 - out), s: lerp(2.6, 1, k), dy: (i % 2 ? 46 : -46) + (1 - k) * (i % 2 ? 300 : -300) - out * 60 }; }, o.col || C_WHITE, C_VERM, 12);
    c.restore();
  }
}

// ================================================================
//  1:16–1:42  サビ1 — 太陽が向日葵になる
// ================================================================
const CH1E = 102.33, IL0 = B(76), IL1 = B(81);
const fx = track([[CH1, CX], [79.0, CX], [79.55, 1400, E.inOutExpo], [82.3, 1400], [82.8, CX, E.inOutExpo], [89.75, CX], [90.25, 1450, E.inOutExpo], [93.3, 1450], [93.8, CX, E.inOutExpo], [200, CX]]);
const fR = track([[CH1, 150], [79.0, 262, E.outCubic], [79.55, 330, E.inOutExpo], [82.3, 340], [82.8, 250, E.inOutExpo], [87, 262], [89.75, 300], [93.3, 320], [93.8, 300, E.inOutExpo], [96.9, 205, E.outCubic], [200, 205]]);
const coldK = t => ez(t, 89.95, 90.2, E.outExpo) * (1 - ez(t, 93.35, 93.6, E.outExpo));
bgSeg(CH1, IL0, t => {
  const end = ez(t, 97.0, 97.6);
  const x = fx(t), r = fR(t) / H * .9;
  const ring = Math.max(0, t - 98.75), ring0 = t - CH1;
  return {
    uSun: [...px2p(x, CY), lerp(r, .13, end)], uSunI: .9 + kick(t) * .14 + end * .1, uCorona: 1.5 + kick(t) * .8, uRays: 1.3 + kick(t) * .8, uSurf: .8, uCold: coldK(t), uStars: .5, uFog: .8,
    uRingR: t > 98.75 ? ring * 1.3 : ring0 * 1.2, uRingA: t > 98.75 ? Math.exp(-ring * 2.5) * 1.2 : Math.exp(-ring0 * 2.5),
  };
});
postSeg(CH1, IL0, t => {
  const f0 = Math.exp(-Math.max(0, t - CH1) * 3.2), cold = coldK(t), k = kick(t) * (1 - cold);
  const f2 = t > 98.75 ? Math.exp(-(t - 98.75) * 4) : 0, f3 = t > 99.75 ? Math.exp(-(t - 99.75) * 3.5) : 0, f4 = Math.exp(-Math.abs(t - 93.43) * 6);
  const a = k * 5 + f0 * 20 + f2 * 22 + f3 * 8;
  return { flash: f0 * .9 + f2 * .55 + f3 * .5 + f4 * .4, shake: [sn1(t * 31) * a, sn1(t * 37, 2) * a], zoom: 1 + k * .012 + f0 * .04 + (t - CH1) * .0008, ca: .0014 + k * .0025 + f0 * .01 + f2 * .008, satu: 1 - cold * .25, grain: .05 };
});
scene(CH1 - .02, 97.7, (c, t) => {
  if (t > CH1 + .4) label(c, t, CH1 + .5, '参　向日葵', 'SUNFLOWER OF THE SOUL');
  const cold = coldK(t), grow = ez(t, CH1, 79.6, E.outCubic), fade = 1 - ez(t, 97.05, 97.6, E.inCubic);
  const press = ez(t, 93.5, 96.8, E.inOutCubic), beat = cold > .5 ? 0 : kick(t);
  const freezeT = t > 90.0 && t < 93.4 ? 90.0 : (t > 93.4 ? t - 3.4 : t);
  c.globalAlpha = fade;
  sunflower(c, fx(t), CY, fR(t), { grow, rot: freezeT * .22, pet: ez(t, 79.2, 80.4, E.outCubic), beat, cold, press });
  c.globalAlpha = 1;
  // アマテラス（1回目）
  amaHit(c, t, CH1, 0, { end: 79.2 });
  // 咲き乱れろ 魂の向日葵
  if (t > 79.1 && t < 82.75) {
    const o = 82.35;
    drawTextS(c, LT('咲き乱れろ', { size: 168, vert: true, track: .02 }), 560, CY, (g, i) => { const k = E.outExpo(prog(t, 79.27 + i * .11, 79.27 + i * .11 + .4)); const ou = ez(t, o + i * .02, o + .3 + i * .02, E.inCubic); return { a: k * (1 - ou), s: lerp(1.8, 1, k), rot: (1 - k) * rs(i, 1) * .5, dx: -ou * 200 }; }, C_WHITE, C_VERM, 8);
    c.fillStyle = C_GOLD;
    drawText(c, LT('魂の向日葵', { size: 104, vert: true, track: .14 }), 330, CY + 30, rise(t, 80.7, { stag: .1, dur: .5, vert: true, dist: -40, out: o, odur: .3 }));
  }
  // 焦燥も劣等も 全部燃料にして — 言葉を太陽にくべる
  if (t > 82.3 && t < 87.2) {
    const W2 = [['焦燥', 82.5, -560, -210], ['劣等', 83.55, 500, 190]];
    for (const [w, t0, ox, oy] of W2) {
      const k = E.outExpo(prog(t, t0, t0 + .3)); const burn = E.inCubic(prog(t, t0 + .75, t0 + 1.5)); if (k <= 0 || burn >= 1) continue;
      const ang = burn * 2.2; const rr = 1 - burn; const x = CX + (ox * Math.cos(ang) - oy * Math.sin(ang)) * rr, y = CY + (ox * Math.sin(ang) + oy * Math.cos(ang)) * rr;
      const L = LT(w, { size: 230, fam: F_GOTH });
      c.fillStyle = burn > .3 ? C_ORANGE : C_WHITE; drawText(c, L, x, y, () => ({ a: k * (1 - burn * .6), s: lerp(1.7, 1, k) * (1 - burn * .9), rot: ang * 1.5 }));
      c.fillStyle = C_WHITE; drawText(c, LT(w === '焦燥' ? 'も' : 'も', { size: 90 }), x + 285 * (1 - burn), y + 60, () => ({ a: k * (1 - burn * 3) }));
    }
    const L2 = LT('全部燃料にして', { size: 150, track: .04 });
    drawTextS(c, L2, CX, 880, (g, i) => { const k = E.outExpo(prog(t, 84.75 + i * .07, 84.75 + i * .07 + .35)); const ou = ez(t, 86.75, 87.05, E.inCubic); return { a: k * (1 - ou), dy: (1 - k) * 80, s: 1 + kick(t) * .04 }; }, C_WHITE, C_VERM, 8);
    if (t > 83.2) embers(c, t, 83.2, 140, CX, CY, 120, 120, { vx: 0, vy: -260, life: 1.6, spread: 3.6, size: 4 });
  }
  // アマテラス（2回目）: 芯に墨の縦書き
  amaHit(c, t, 87.07, 1, { end: 89.95 });
  // 絶対零度の孤独さえ — 凍る
  if (t > 89.9 && t < 93.6) {
    const o = 93.3; c.fillStyle = '#e8f6ff';
    drawText(c, LT('絶対零度の', { size: 132, track: .16 }), 540, 440, rise(t, 90.1, { stag: .07, dur: .25, dist: 0, out: o }));
    drawText(c, LT('孤独さえ', { size: 132, track: .42 }), 540, 620, rise(t, 91.6, { stag: .12, dur: .25, dist: 0, out: o }));
    c.save(); c.globalAlpha = ez(t, 90.2, 90.5) * (1 - ez(t, o, o + .2)); c.fillStyle = '#9fd0ff'; c.font = fnt(F_LAT, 24, 400); try { c.letterSpacing = '8px'; } catch (e) { } c.textAlign = 'left';
    c.fillText('− 273.15 ℃   /   0 K', 150, 760); c.fillRect(150, 300, 800 * ez(t, 90.1, 91, E.outQuint), 1.5); c.restore();
  }
  // その高圧で抱きしめろ — 上下から締めつける
  if (t > 93.3 && t < 97.6) {
    const sq = ez(t, 93.5, 96.9, E.inOutCubic), o = 97.1;
    const La = LT('その高圧で', { size: 150, track: lerp(.5, .0, sq) }), Lb = LT('抱きしめろ', { size: 190, fam: F_GOTH, track: lerp(.45, -.02, sq) });
    drawTextS(c, La, CX, lerp(170, 262, sq), rise(t, 93.43, { stag: .06, dur: .35, dist: -50, out: o }), C_WHITE, C_INK, 8);
    drawTextS(c, Lb, CX, lerp(940, 838, sq), (g, i) => { const k = E.outExpo(prog(t, 95.2 + i * .07, 95.2 + i * .07 + .3)); return { a: k * (1 - ez(t, o, o + .3)), s: lerp(1.6, 1, k), dy: (1 - k) * 60 }; }, C_GOLD, C_INK, 8);
    // 圧力の線
    c.save(); c.strokeStyle = C_WHITE; c.lineWidth = 2; c.globalAlpha = .7 * (1 - ez(t, o, o + .3)) * ez(t, 93.5, 94);
    for (let i = 0; i < 12; i++) { const a = i / 12 * TAU + .26; const r0 = lerp(620, 300, sq) + pulse(t, 2, 5) * 30, r1 = r0 + 70; c.beginPath(); c.moveTo(CX + Math.cos(a) * r1 * 1.25, CY + Math.sin(a) * r1 * .62); c.lineTo(CX + Math.cos(a) * r0 * 1.25, CY + Math.sin(a) * r0 * .62); c.stroke(); }
    c.restore();
  }
});
// この矛盾を 愛と呼びたい — 矛（冷）と盾（熱）がぶつかって「愛」になる
scene(97.05, IL0 + .3, (c, t) => {
  const hitT = 98.75, loveT = 99.75;
  const out = ez(t, IL0 - .3, IL0 + .15, E.inCubic);
  const k1 = E.outExpo(prog(t, 97.2, 97.6)), col = E.inExpo(prog(t, 98.3, hitT));
  const fuse = ez(t, hitT, hitT + .12);
  if (fuse < 1) {
    const d = lerp(lerp(700, 380, k1), 60, col);
    c.fillStyle = '#7fc4ff'; drawText(c, LT('矛', { size: 420, fam: F_MIN }), CX - d, CY, () => ({ a: k1 * (1 - fuse), s: lerp(1.5, 1, k1), rot: -.06 * (1 - col) }));
    c.fillStyle = C_ORANGE; drawText(c, LT('盾', { size: 420, fam: F_MIN }), CX + d, CY, () => ({ a: k1 * (1 - fuse), s: lerp(1.5, 1, k1), rot: .06 * (1 - col) }));
    c.fillStyle = C_WHITE; drawText(c, LT('この矛盾を', { size: 64, track: .5 }), CX, 190, rise(t, 97.2, { stag: .06, dur: .4, out: hitT - .1, odur: .2 }));
  }
  if (t > hitT) {
    const k = E.outExpo(prog(t, hitT, hitT + .5)); const kk = E.outExpo(prog(t, loveT, loveT + .5));
    const L = LT('愛', { size: 560 });
    drawTextS(c, L, CX, CY - 10, () => ({ a: k * (1 - out), s: lerp(.4, 1, k) + kick(t) * .02 + (t - hitT) * .012 }), C_WHITE, C_VERM, 12);
    c.fillStyle = C_WHITE;
    drawText(c, LT('と呼びたい', { size: 72, track: .7 }), CX, 930, rise(t, loveT + .2, { stag: .09, dur: .5, out: IL0 - .35 }));
    // 細い十字と円
    c.save(); c.globalAlpha = kk * .7 * (1 - out); c.strokeStyle = C_GOLD; c.lineWidth = 1.5; c.beginPath(); c.arc(CX, CY, 420 + kk * 30, 0, TAU); c.stroke(); tickRing(c, CX, CY, 440 + kk * 30, 72, 10, t * .1, 1.5, 6, 22); c.restore();
  }
});

// ================================================================
//  1:49–2:10  Aメロ2 — 境界線 / 仮面 / 再編される宇宙
// ================================================================
const V2 = IL1, V2b = 112.13, V2c = 114.9, V2d = 120.75, V2e = 125.3, BRK = 130.4;
bgSeg(V2, V2d, t => {
  const face = ez(t, V2b - .15, V2b + .3);
  return { uSun: [...px2p(lerp(CX, 250, face), lerp(CY, 215, face)), lerp(.5, .11, face)], uSunI: lerp(.5, .8, face) + kick(t) * .08, uEclipse: lerp(0, .0, face), uCorona: 1, uRays: .6, uSurf: .5, uStars: .6, uFog: 1.2, uDim: lerp(.0, .85, face) };
});
postSeg(V2, V2d, t => { const h = Math.exp(-Math.abs(t - 114.56) * 8); return { bars: .075, zoom: 1.01 + (t - V2) * .0025, shake: [sn1(t * 30) * (kick(t) * 2.5 + h * 12), sn1(t * 33, 2) * (kick(t) * 2.5 + h * 12)], flash: h * .35 }; });
// 祝福と試練の境界線
scene(V2 - .05, V2b + .3, (c, t) => {
  const k = ez(t, V2, V2 + .45, E.outExpo), out = ez(t, V2b - .2, V2b + .15, E.inExpo);
  const lx = CX + sn1(t * 1.3) * 6;
  c.save(); c.globalAlpha = 1 - out;
  // 左: 祝福（明るい）/ 右: 試練（暗い）
  c.fillStyle = '#f6e7c8'; c.fillRect(0, 0, lx * k + (1 - k) * 0, H);
  c.fillStyle = '#06070f'; c.fillRect(W - (W - lx) * k, 0, (W - lx) * k, H);
  label(c, t, V2 + .1, '肆　境界線', 'BORDERLINE', '#1a1420');
  c.fillStyle = C_INK; drawText(c, LT('祝福', { size: 300 }), lx - 400, CY, (g, i) => { const kk = E.outExpo(prog(t, 109.67 + i * .12, 109.67 + i * .12 + .4)); return { a: kk, dx: (1 - kk) * -120 }; });
  c.fillStyle = C_WHITE; drawText(c, LT('試練', { size: 300 }), lx + 400, CY, (g, i) => { const kk = E.outExpo(prog(t, 110.5 + i * .12, 110.5 + i * .12 + .4)); return { a: kk, dx: (1 - kk) * 120 }; });
  c.fillStyle = C_INK; drawText(c, LT('と', { size: 80 }), lx - 80, CY + 110, rise(t, 110.25, { dur: .3 }));
  // 境界線
  c.fillStyle = C_VERM; c.fillRect(lx - 3, 0, 6, H * k);
  const Lb = LT('の境界線', { size: 62, vert: true, track: .3 }); c.fillStyle = C_VERM;
  c.save(); c.fillStyle = '#06070f'; c.fillRect(lx + 20, CY - 210, 88, 420 * ez(t, 111.1, 111.5, E.outExpo)); c.restore();
  c.fillStyle = C_VERM; drawText(c, Lb, lx + 64, CY, rise(t, 111.1, { stag: .08, dur: .4, vert: true, dist: 0 }));
  c.restore();
});
// 踏み越えるたび 剥がれる仮面 / 強がりの裏に潜伏していた / 幼い願いが 今息をする
scene(V2b - .2, V2d + .25, (c, t) => {
  const k = ez(t, V2b - .15, V2b + .4, E.outExpo), out = ez(t, V2d - .2, V2d + .15, E.inCubic);
  const breath = t > 117.7 ? Math.sin((t - 117.7) * 2.1) * .5 + .5 : 0;
  const fh = 1640 * (1 + (t - V2b) * .006 + breath * .012), im = IMG.face, s = fh / im.height, fw = im.width * s;
  const fxp = 1330 + (1 - k) * 200, fy0 = 70;
  c.save(); c.globalAlpha = (1 - out) * k;
  const warm = ez(t, 116.5, 119.5);
  drawChar(c, 'face', fxp, fy0, fh, { live: t, ay: 0, grade: '#1a1030', gamt: lerp(.62, .12, warm), rim: [-9, 4], rimCol: '#ffb866', rimA: .7 });
  // 仮面: 白い面を小片に割って、拍ごとに剥がす
  const cs = 82, sil = silhouette('face', '#f3ead9'), cols = Math.ceil(im.width / cs), rows = Math.ceil(900 / cs);
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    const d = Math.hypot(i - cols * .45, j - rows * .55) / 8; let t0 = 112.6 + d * 1.6 + rnd(i, j) * .7; t0 = Math.min(bt(Math.round(beatOf(t0))), 114.56 + rnd(j, i) * .12);
    const dt = t - t0; if (dt > .9) continue;
    const sx = i * cs, sy = j * cs; const dx = fxp - fw / 2 + sx * s, dy = fy0 + sy * s, cw = cs * s;
    c.save();
    if (dt > 0) { c.globalAlpha *= 1 - dt / .9; c.translate(dx + cw / 2 - dt * (260 + rnd(i, j) * 300), dy + cw / 2 + dt * dt * 700 - dt * 120); c.rotate(-dt * (2 + rnd(j, i) * 4)); c.scale(1 - dt * .3, Math.cos(dt * 7)); c.translate(-cw / 2, -cw / 2); }
    else c.translate(dx, dy);
    c.drawImage(sil, sx, sy, cs, cs, 0, 0, cw + .6, cw + .6);
    c.restore();
  }
  c.restore();
  // 歌詞
  c.save(); c.globalAlpha = 1 - out;
  const o1 = V2c - .15;
  drawTextS(c, LT('踏み越えるたび', { size: 86, track: .1 }), 500, 390, rise(t, 112.13, { stag: .05, dur: .35, out: o1, odur: .2 }), C_WHITE, C_INK, 5);
  drawTextS(c, LT('剥がれる仮面', { size: 150, fam: F_GOTH, track: .02 }), 540, 560, (g, i) => { const kk = E.outExpo(prog(t, 113.45 + i * .06, 113.45 + i * .06 + .3)); const ou = E.inCubic(prog(t, o1 + i * .03, o1 + .3 + i * .03)); return { a: kk * (1 - ou), s: lerp(1.5, 1, kk), dy: ou * 200, rot: ou * rs(i, 3) }; }, C_WHITE, C_VERM, 7);
  c.fillStyle = C_WHITE;
  const o2 = V2d - .3;
  drawText(c, LT('強がりの裏に', { size: 78, vert: true, track: .12 }), 640, 440, rise(t, 114.9, { stag: .07, dur: .5, vert: true, dist: 30, out: 117.5, odur: .3 }));
  drawText(c, LT('潜伏していた', { size: 78, vert: true, track: .12 }), 510, 560, rise(t, 116.1, { stag: .07, dur: .5, vert: true, dist: 30, out: 117.55, odur: .3 }));
  drawTextS(c, LT('幼い願いが', { size: 112, track: .12 }), 500, 470, rise(t, 117.75, { stag: .1, dur: .7, dist: 30, out: o2, odur: .3 }), C_GOLD, C_INK, 5);
  c.fillStyle = C_WHITE;
  drawText(c, LT('今　息をする', { size: 84, track: .34 }), 500, 610, (g, i, n) => { const r = rise(t, 119.15, { stag: .12, dur: .7, dist: 20, out: o2, odur: .3 })(g, i, n); r.s = 1 + breath * .05; return r; });
  c.restore();
});
// 支配じゃない 征服でもない / ただ存在するという革命
bgSeg(V2d, V2e, t => { const ex = ez(t, 122.67, 123.2, E.outExpo); return { uSun: [0, 0, lerp(.02, .25, ex)], uSunI: ex * .8 + kick(t) * .1, uEclipse: 1, uCorona: 1.2 + kick(t) * .6, uRays: 1, uStars: .8, uFog: 1.2, uDim: .9 }; });
postSeg(V2d, V2e, t => { let s = 0; for (const x of [121.35, 122.3]) s = Math.max(s, Math.exp(-Math.abs(t - x) * 9)); const r = Math.exp(-Math.abs(t - 124.25) * 6); return { shake: [sn1(t * 30) * (s * 18 + kick(t) * 2), sn1(t * 33, 2) * (s * 10 + kick(t) * 2)], ca: .0012 + s * .008, flash: r * .4, zoom: 1 + (t - V2d) * .004 }; });
scene(V2d - .1, V2e + .2, (c, t) => {
  const out = ez(t, V2e - .2, V2e + .15, E.inCubic);
  c.save(); c.globalAlpha = 1 - out;
  const part1 = 1 - ez(t, 122.5, 122.7, E.inCubic);
  if (part1 > 0) {
    const rows = [['支配', 'じゃない', 120.8, 121.35, 380, -1], ['征服', 'でもない', 121.75, 122.3, 720, 1]];
    for (const [w, neg, t0, ts, y, dir] of rows) {
      const k = E.outExpo(prog(t, t0, t0 + .3)); if (k <= 0) continue;
      const L = LT(w, { size: 280, fam: F_GOTH, track: .06 }); const x = CX + dir * -230;
      c.globalAlpha = (1 - out) * part1;
      const sl = E.outExpo(prog(t, ts, ts + .18));
      c.fillStyle = sl > 0 ? '#5a5f78' : C_WHITE; drawText(c, L, x, y, () => ({ a: k, s: lerp(1.5, 1, k) }));
      c.fillStyle = C_WHITE; const Ln = LT(neg, { size: 84, track: .1 }); drawText(c, Ln, x + dir * (L.len / 2 + Ln.len / 2 + 70), y + 60, rise(t, t0 + .3, { stag: .04, dur: .3 }));
      if (sl > 0) { c.strokeStyle = C_VERM; c.lineWidth = 22; c.lineCap = 'butt'; c.beginPath(); const x0 = x - L.len / 2 - 60, x1 = x + L.len / 2 + 60; c.moveTo(x0, y + 40 * dir); c.lineTo(lerp(x0, x1, sl), y + 40 * dir - 80 * dir * sl); c.stroke(); }
    }
  }
  if (t > 122.55) {
    c.globalAlpha = 1 - out;
    c.fillStyle = C_WHITE; drawText(c, LT('ただ', { size: 70, track: .6 }), CX, 190, rise(t, 122.67, { stag: .1, dur: .4 }));
    const L = LT('存在', { size: 330, track: .5 }); const k = E.outExpo(prog(t, 123.05, 123.7));
    drawTextS(c, L, CX + 80, CY - 10, (g, i) => ({ a: k, dx: (i ? 1 : -1) * (1 - k) * 300, s: 1 + (t - 123) * .01 }), C_WHITE, C_INK, 8);
    c.fillStyle = C_WHITE; drawText(c, LT('するという', { size: 60, track: .5 }), CX, 772, rise(t, 123.7, { stag: .05, dur: .35 }));
    const kr = E.outExpo(prog(t, 124.25, 124.7));
    drawTextS(c, LT('革命', { size: 150, fam: F_GOTH, track: .3 }), CX, 940, (g, i) => ({ a: kr, s: lerp(2.2, 1, kr) }), C_VERM, C_INK, 6);
  }
  c.restore();
});
// あなたが在る それだけで再編される宇宙 — 散らばった言葉が軌道に整列する
const UNI = [...'支配征服祝福試練仮面願革命衝動静寂均衡感情本音嘘運命可能性残像理性夜矛盾孤独焦燥劣等境界線'];
bgSeg(V2e, BRK, t => { const st = Math.exp(-Math.max(0, t - 129.75) * 3); return { uSun: [0, .05, .075 + ez(t, V2e, V2e + .5, E.outExpo) * .02], uSunI: .95 + kick(t) * .12, uCorona: 1.2 + kick(t) * .5, uRays: 1, uSurf: .8, uStars: 1, uFog: 1 }; });
postSeg(V2e, BRK, t => { let s = 0; for (const x of [129.75, 129.92, 130.08]) if (t >= x) s = Math.max(s, Math.exp(-(t - x) * 9)); return { zoom: 1.12 - ez(t, V2e, 129.6, E.outCubic) * .12, rot: (1 - ez(t, V2e, 129.4, E.outCubic)) * .25, shake: [sn1(t * 30) * (kick(t) * 3 + s * 20), sn1(t * 33, 2) * (kick(t) * 3 + s * 20)], flash: s * .5, ca: .0012 + s * .01, mb: 3, shutter: .7 }; });
scene(V2e - .1, BRK + .1, (c, t) => {
  const k = ez(t, 126.5, 129.4, E.inOutCubic), kin = ez(t, V2e - .1, V2e + .4), out = ez(t, BRK - .12, BRK + .05, E.inExpo);
  c.save(); c.globalAlpha = (1 - out) * kin;
  c.font = fnt(F_MIN, 52); c.textAlign = 'center'; c.textBaseline = 'middle';
  const rings = [210, 290, 370, 450];
  c.strokeStyle = C_GOLD; c.lineWidth = 1.2;
  for (let r = 0; r < 4; r++) { c.globalAlpha = (1 - out) * kin * k * .5; c.beginPath(); c.ellipse(CX, CY, rings[r] * 1.75, rings[r] * .62, 0, 0, TAU); c.stroke(); }
  for (let i = 0; i < 52; i++) {
    const ring = i % 4, R = rings[ring]; const n = 13, slot = Math.floor(i / 4);
    const th = slot / n * TAU + ring * .4 + t * (.18 + ring * .05) * (ring % 2 ? -1 : 1);
    const ox = CX + Math.cos(th) * R * 1.75, oy = CY + Math.sin(th) * R * .62;
    const cxp = CX + rs(i, 1) * 900 + Math.sin(t * 1.3 + i) * 60, cyp = CY + rs(i, 2) * 500 + Math.cos(t * 1.1 + i * 2) * 60;
    const kk = E.inOutCubic(sat(k * 1.5 - rnd(i, 9) * .5));
    const x = lerp(cxp, ox, kk), y = lerp(cyp, oy, kk); const front = Math.sin(th) > 0 ? 1 : .55;
    c.save(); c.translate(x, y); c.rotate(lerp(rs(i, 4) * 2, 0, kk)); const sc = lerp(.8 + rnd(i, 5) * .9, .7 + .5 * (Math.sin(th) * .5 + .5), kk); c.scale(sc, sc);
    c.globalAlpha = (1 - out) * kin * lerp(.4, front, kk); c.fillStyle = kk > .9 ? (ring % 2 ? C_GOLD : C_WHITE) : '#8fa0ff'; c.fillText(UNI[i % UNI.length], 0, 0); c.restore();
  }
  c.restore();
  // 軌道の中心に、ただ立っている少年（正面）
  { const kb = ez(t, V2e, V2e + .6, E.outQuint); c.save(); c.globalAlpha = (1 - out) * kb; drawChar(c, 'front', CX, CY + 128 + (1 - kb) * 30, 250, { live: t, grade: '#1a0c18', gamt: .35, rim: [0, 2], rimCol: '#ffcf8a', rimA: .8 }); c.restore(); }
  c.save(); c.globalAlpha = 1 - out;
  drawTextS(c, LT('あなたが在る', { size: 118, track: .16 }), CX, 150, rise(t, 125.37, { stag: .07, dur: .4 }), C_WHITE, C_INK, 6);
  c.fillStyle = C_WHITE; drawText(c, LT('それだけで', { size: 56, track: .5 }), CX, 878, rise(t, 126.67, { stag: .06, dur: .4 }));
  drawTextS(c, LT('再編される宇宙', { size: 116, track: .1 }), CX, 980, (g, i) => { const kk = E.outExpo(prog(t, 127.7 + i * .09, 127.7 + i * .09 + .45)); return { a: kk, dx: (1 - kk) * rs(i, 1) * 300, dy: (1 - kk) * rs(i, 2) * 200, rot: (1 - kk) * rs(i, 3) }; }, C_GOLD, C_INK, 6);
  c.restore();
});

// ================================================================
//  2:10–2:20  ブレイク — 奪わない光があることを 初めて知ったんだ
// ================================================================
const CH2 = 140.37, RE = B(101);
bgSeg(BRK, CH2, t => {
  const re = ez(t, RE, CH2, E.inCubic);
  return { uSun: [...px2p(430, 330 - (t - BRK) * 4), .085 + re * .05], uSunI: .82 + re * .2 + env('all', t) * .08, uCorona: .5 + re, uRays: .15 + re * 1.2, uSurf: .3, uStars: .9, uFog: .7, uNightA: [.006, .008, .028], uNightB: [.02, .03, .1] };
});
postSeg(BRK, CH2, t => { const re = prog(t, RE, CH2); return { bars: .1 * (1 - E.inCubic(prog(t, CH2 - .6, CH2))), zoom: 1 + (t - BRK) * .005 + E.inCubic(re) * .05, shake: [sn1(t * 30) * kick(t) * 4 * re, sn1(t * 33, 2) * kick(t) * 4 * re], grain: .07, bloom: .8 }; });
scene(BRK, CH2 + .15, (c, t) => {
  const k = ez(t, BRK + .1, BRK + 1.6, E.outCubic), out = ez(t, CH2 - .3, CH2, E.inExpo);
  c.save(); c.globalAlpha = k * (1 - out);
  // 少年（横顔）— 遠くのやわらかい光を見上げる
  drawChar(c, 'side', 1420 - (t - BRK) * 4, 1010, 640, { live: t, grade: '#0c1030', gamt: .5, rim: [-5, -2], rimCol: '#ffd9a8', rimA: .8 });
  const sh = c.createLinearGradient(1200, 0, 1700, 0); sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(.3, 'rgba(0,0,0,.5)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
  c.fillStyle = sh; c.fillRect(1200, 1004, 520, 10);
  c.restore();
  // 漂う光の粒
  c.save(); c.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 70; i++) {
    const x = (rnd(i, 1) * W + (t - BRK) * (8 + rnd(i, 3) * 22) + Math.sin(t * .6 + i) * 30) % W, y = (rnd(i, 2) * H - (t - BRK) * (6 + rnd(i, 4) * 16) + H * 4) % H;
    c.globalAlpha = (.25 + .5 * (Math.sin(t * 1.5 + i * 2.1) * .5 + .5)) * (1 - out) * k; c.fillStyle = '#ffd9a0'; c.beginPath(); c.arc(x, y, 1.2 + rnd(i, 5) * 2.2, 0, TAU); c.fill();
  }
  c.restore();
  c.save(); c.globalAlpha = 1 - out; c.fillStyle = C_WHITE;
  const o = 136.0;
  drawText(c, LT('奪わない光が', { size: 76, w: 500, track: .36 }), 760, 500, rise(t, 130.75, { stag: .2, dur: 1.1, dist: 14, out: o, odur: .5 }));
  drawText(c, LT('あることを', { size: 76, w: 500, track: .36 }), 760, 630, rise(t, 133.2, { stag: .2, dur: 1.1, dist: 14, out: o + .05, odur: .5 }));
  drawText(c, LT('初めて知ったんだ', { size: 96, track: .2 }), 760, 560, (g, i) => { const kk = E.outQuint(prog(t, 136.35 + i * .2, 136.35 + i * .2 + .7)); return { a: kk, dy: (1 - kk) * 16, col: i < 3 ? C_GOLD : C_WHITE }; });
  c.restore();
});

// ================================================================
//  2:20–2:46  サビ2
// ================================================================
const CH2E = 166.0;
const S2a = 143.9, S2b = 146.97, S2c = 151.17, S2d = 154.9, S2e = 161.95;
bgSeg(CH2, S2a, t => ({ uSun: [0, 0, .2], uSunI: 1.0 + kick(t) * .12, uCorona: 1.6 + kick(t), uRays: 1.5, uStars: .5, uRingR: (t - CH2) * 1.3, uRingA: Math.exp(-(t - CH2) * 2.5) }));
postSeg(CH2, S2a, t => { const st = (t - CH2) / .41; const f = Math.exp(-(st - Math.floor(st)) * 4) * (st < 6 ? 1 : 0); const a = f * 14 + kick(t) * 4; return { flash: Math.exp(-(t - CH2) * 4) * .8 + f * .12, shake: [sn1(t * 31) * a, sn1(t * 37, 2) * a], ca: .0014 + f * .006, zoom: 1 + f * .03 }; });
scene(CH2 - .02, S2a + .1, (c, t) => { amaHit(c, t, CH2, 2, { end: S2a + .1 }); });
// 群青の闇を撃ち抜け
bgSeg(S2a, S2b, t => { const hit = ez(t, 145.5, 145.62); return { uSun: [...px2p(lerp(-500, 2300, ez(t, 145.3, 145.75, E.inOutCubic)), CY), .05], uSunI: (t > 145.3 && t < 145.9 ? 1.2 : 0) + hit * .0, uCorona: .6, uRays: 2.5, uFog: 2.2, uStars: .4, uNightA: [.004, .01, .06], uNightB: [.02, .05, .26] }; });
postSeg(S2a, S2b, t => { const h = t > 145.5 ? Math.exp(-(t - 145.5) * 4) : 0; return { flash: h * .7, shake: [sn1(t * 31) * (h * 26 + kick(t) * 3), sn1(t * 37, 2) * (h * 12 + kick(t) * 3)], ca: .0014 + h * .012, zoom: 1 + h * .03, mb: 3 }; });
scene(S2a, S2b + .1, (c, t) => {
  const hitT = 145.5, k = E.outExpo(prog(t, 144.1, 144.6)), sp = t > hitT ? E.outExpo(prog(t, hitT, hitT + .7)) : 0, out = ez(t, S2b - .2, S2b + .05, E.inCubic);
  // 巨大な「闇」を光の線が貫いて上下に割る
  const spr = glyphSprite('闇', { size: 760, fam: F_MIN, col: '#1a35d8' });
  c.save(); c.globalAlpha = k * (1 - out);
  const gy = sp * 120, sw = spr.width, shh = spr.height, x0 = CX - sw / 2, y0 = CY - shh / 2 + 10;
  c.save(); c.translate(-sp * 50, -gy); c.rotate(-sp * .035); c.drawImage(spr, 0, 0, sw, shh / 2, x0, y0, sw, shh / 2); c.restore();
  c.save(); c.translate(sp * 50, gy); c.rotate(-sp * .035); c.drawImage(spr, 0, shh / 2, sw, shh / 2, x0, y0 + shh / 2, sw, shh / 2); c.restore();
  c.restore();
  // 光の弾道
  if (t > 145.25) {
    const head = lerp(-300, W + 600, ez(t, 145.3, 145.75, E.inOutCubic)); const fade = 1 - ez(t, 146.1, 146.9);
    c.save(); c.globalCompositeOperation = 'lighter'; c.globalAlpha = fade * (1 - out);
    const g = c.createLinearGradient(0, 0, Math.max(1, head), 0); g.addColorStop(0, 'rgba(255,120,40,0)'); g.addColorStop(.7, 'rgba(255,190,90,.9)'); g.addColorStop(1, 'rgba(255,250,230,1)');
    c.fillStyle = g; c.fillRect(0, CY - 5 - 8 * (1 - sp), Math.max(0, head), 10 + 16 * (1 - sp)); c.fillStyle = 'rgba(255,170,70,.3)'; c.fillRect(0, CY - 34, Math.max(0, head), 68);
    c.restore();
    // 破片
    if (t > hitT) { c.save(); c.fillStyle = '#3a58ff'; for (let i = 0; i < 46; i++) { const a = rs(i, 1) * 1.1 + (i % 2 ? 0 : Math.PI); const d = (t - hitT) * (500 + rnd(i, 2) * 1300); const x = CX + Math.cos(a) * d + rs(i, 5) * 200, y = CY + Math.sin(a) * d * .7 + (t - hitT) * (t - hitT) * 500; c.globalAlpha = sat(1 - (t - hitT) / 1.1) * (1 - out); c.save(); c.translate(x, y); c.rotate(t * (3 + rnd(i, 3) * 8)); c.fillRect(-8, -8, 12 + rnd(i, 4) * 22, 8 + rnd(i, 6) * 18); c.restore(); } c.restore(); }
  }
  c.save(); c.globalAlpha = 1 - out; c.fillStyle = C_WHITE;
  drawText(c, LT('群青の闇を', { size: 84, track: .5 }), CX, 150, rise(t, 144.1, { stag: .07, dur: .4, out: S2b - .3 }));
  drawTextS(c, LT('撃ち抜け', { size: 280, fam: F_GOTH, track: .06 }), CX, CY + 20, (g, i) => { const kk = E.outExpo(prog(t, hitT + i * .03, hitT + .28 + i * .03)); return { a: kk, s: lerp(2.6, 1, kk), dx: (1 - kk) * -400 }; }, C_WHITE, C_VERM, 10);
  c.restore();
});
// 何度倒れても 首を上げる炎 — 向日葵が首を起こす
bgSeg(S2b, S2c, t => { const up = riseK(t); return { uSun: [...px2p(CX, 430), .18], uSunI: .35 + up * .6 + kick(t) * .1, uCorona: 1.2 + up, uRays: up * 1.4, uStars: .6, uFog: 1.1, uDim: .8 + up * .2 }; });
function riseK(t) { // 2回倒れて3回起きる
  const a = [[146.97, .08], [147.6, .5, E.outBack], [147.95, .14, E.inCubic], [148.6, .66, E.outBack], [148.95, .2, E.inCubic], [149.75, 1, E.outBack], [152, 1]];
  return track(a)(t);
}
postSeg(S2b, S2c, t => ({ zoom: 1 + (t - S2b) * .006, shake: [sn1(t * 31) * kick(t) * 3.5, sn1(t * 37, 2) * kick(t) * 3.5] }));
scene(S2b, S2c + .1, (c, t) => {
  const up = riseK(t), out = ez(t, S2c - .2, S2c + .05, E.inCubic), kin = ez(t, S2b, S2b + .3);
  c.save(); c.globalAlpha = (1 - out) * kin;
  // 茎
  const hx = CX, hy = lerp(760, 430, up), tilt = (1 - up) * 1.05;
  c.strokeStyle = '#2f7a2a'; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); c.moveTo(CX - 40, H + 40); c.quadraticCurveTo(CX - 70 + tilt * 220, lerp(H, hy, .5), hx - Math.sin(tilt) * 30, hy + 60); c.stroke();
  sunflower(c, hx, hy, 215, { rot: t * .2, sq: lerp(.22, 1, E.inOutCubic(sat(up))), beat: kick(t), n: 520, tilt: -tilt * .5, pet: 1 });
  c.restore();
  c.save(); c.globalAlpha = 1 - out;
  // 何度倒れても（倒れた文字が起き上がる）
  const L1 = LT('何度倒れても', { size: 86, track: .06 }); const lean = (1 - sat(riseK(t))) * -.42;
  c.save(); c.translate(370 + L1.len / 2, 600); c.rotate(-lean); c.translate(-(370 + L1.len / 2), -600);
  drawTextS(c, L1, 370, 560, rise(t, 146.97, { stag: .07, dur: .3 }), C_WHITE, C_INK, 6);
  c.restore();
  drawTextS(c, LT('首を上げる', { size: 86, track: .06 }), 1540, 470, rise(t, 149.0, { stag: .07, dur: .4, dist: 80 }), C_WHITE, C_INK, 6);
  drawTextS(c, LT('炎', { size: 260, fam: F_MIN }), 1540, 690, () => { const kk = E.outExpo(prog(t, 150.2, 150.6)); return { a: kk, s: lerp(.3, 1, kk) * (1 + kick(t) * .06), dy: (1 - kk) * 120 }; }, C_VERM, C_INK, 8);
  if (t > 150.2) embers(c, t, 150.2, 60, 1540, 660, 90, 90, { vx: 20, vy: -260, life: 1.2, spread: 1, size: 4 });
  c.restore();
});
// アマテラス（サビ2・後半）
bgSeg(S2c, S2d, t => ({ uSun: [...px2p(CX, CY + 20), .21], uSunI: 1.0 + kick(t) * .12, uCorona: 1.6 + kick(t), uRays: 1.5, uStars: .5, uRingR: (t - S2c) * 1.3, uRingA: Math.exp(-(t - S2c) * 2.5) }));
postSeg(S2c, S2d, t => { const f = Math.exp(-(t - S2c) * 3.5); const a = f * 18 + kick(t) * 4; return { flash: f * .8, shake: [sn1(t * 31) * a, sn1(t * 37, 2) * a], ca: .0014 + f * .008 + kick(t) * .002, zoom: 1.04 - ez(t, S2c, S2d, E.outCubic) * .04 + kick(t) * .01 }; });
scene(S2c - .02, S2d + .1, (c, t) => { const out = ez(t, S2d - .25, S2d, E.inCubic); sunDials(c, t, CX, CY + 20, 210, .7 * (1 - out) * ez(t, S2c, S2c + .5), C_GOLD); amaHit(c, t, S2c, 3, { end: S2d, y: CY + 20 }); });
// 触れられなくても構わない / 距離さえ意味に変えて — 少年と太陽、その間の距離
bgSeg(S2d, S2e, t => { const m = ez(t, 159.9, 160.6, E.outExpo); return { uSun: [...px2p(1500, 300), .075 + m * .02], uSunI: .98 + kick(t) * .1 + m * .1, uCorona: .9 + m * .8, uRays: .5 + m, uSurf: .5, uStars: 1, uFog: 1, uHorOn: 1, uHor: px2p(0, 900)[1] }; });
postSeg(S2d, S2e, t => { const m = t > 159.9 ? Math.exp(-(t - 159.9) * 4) : 0; return { bars: .06, zoom: 1.0 + (t - S2d) * .004, flash: m * .35, shake: [sn1(t * 31) * (kick(t) * 2.5 + m * 8), sn1(t * 37, 2) * (kick(t) * 2.5 + m * 8)] }; });
scene(S2d, S2e + .1, (c, t) => {
  const k = ez(t, S2d, S2d + .7, E.outExpo), out = ez(t, S2e - .25, S2e + .05, E.inCubic), m = ez(t, 159.9, 160.5, E.outExpo);
  c.save(); c.globalAlpha = (1 - out) * k;
  const bx = 400, by = 930; drawChar(c, 'side', bx + (1 - k) * -120, by, 430, { live: t, flip: true, grade: '#0a0c22', gamt: .72, rim: [-5, -3], rimCol: '#ffc880', rimA: .9 });
  // 距離の線
  const ax = bx + 70, ay = by - 330, sx2 = 1500 - 80, sy2 = 300 + 44; const ln = ez(t, 155.2, 157.2, E.inOutCubic);
  const ex = lerp(ax, sx2, ln), ey = lerp(ay, sy2, ln);
  c.strokeStyle = m > 0 ? C_GOLD : C_WHITE; c.lineWidth = lerp(1.5, 4, m); c.setLineDash(m > .5 ? [] : [10, 12]); c.beginPath(); c.moveTo(ax, ay); c.lineTo(ex, ey); c.stroke(); c.setLineDash([]);
  const len = Math.hypot(sx2 - ax, sy2 - ay), ang = Math.atan2(sy2 - ay, sx2 - ax);
  c.save(); c.translate(ax, ay); c.rotate(ang); c.fillStyle = m > 0 ? C_GOLD : C_WHITE;
  for (let i = 0; i <= 30; i++) { const d = i / 30 * len; if (d > len * ln) break; c.fillRect(d, -(i % 5 === 0 ? 16 : 7), 1.5, i % 5 === 0 ? 16 : 7); }
  // 数字（地球と太陽の距離）→ 意味
  const num = Math.floor(149600000 * ln).toLocaleString('en-US');
  c.font = fnt(F_LAT, 30, 400); c.textAlign = 'center'; c.textBaseline = 'middle'; try { c.letterSpacing = '4px'; } catch (e) { }
  c.globalAlpha = (1 - out) * k * (1 - m); c.fillText(num + ' km', len * .5, 46);
  try { c.letterSpacing = '0px'; } catch (e) { }
  c.restore();
  c.restore();
  c.save(); c.globalAlpha = 1 - out;
  c.fillStyle = C_WHITE;
  drawText(c, LT('触れられなくても', { size: 78, track: .14 }), 1250, 640, rise(t, 155.07, { stag: .06, dur: .45, out: 157.75, odur: .25 }));
  drawText(c, LT('構わない', { size: 78, track: .14 }), 1380, 760, rise(t, 156.7, { stag: .08, dur: .45, out: 157.78, odur: .25 }));
  drawText(c, LT('距離', { size: 150, track: .1 }), 1040, 690, (g, i) => { const kk = E.outExpo(prog(t, 158.13 + i * .1, 158.13 + i * .1 + .4)); return { a: kk * (1 - m), dy: (1 - kk) * 40, s: 1 - m * .3 }; });
  drawText(c, LT('さえ', { size: 70, track: .1 }), 1270, 730, rise(t, 158.75, { stag: .08, dur: .35, out: 159.85, odur: .15 }));
  drawTextS(c, LT('意味', { size: 230, fam: F_GOTH, track: .12 }), 1090, 680, (g, i) => ({ a: m, s: lerp(2, 1, m) }), C_GOLD, C_INK, 8);
  c.fillStyle = C_WHITE; drawText(c, LT('に変えて', { size: 76, track: .2 }), 1500, 730, rise(t, 160.45, { stag: .07, dur: .4 }));
  c.restore();
});
// 希望を更新し続けろ
bgSeg(S2e, CH2E, t => ({ uSun: [0, 0, .26], uSunI: .98 + pulse(t, 2, 5) * .12, uEclipse: 0, uCorona: 1.4 + pulse(t, 2, 4), uRays: 1.4, uSurf: .9, uStars: .5 }));
postSeg(S2e, CH2E, t => { const p = pulse(t, 2, 6); return { zoom: 1 + p * .018 + (t - S2e) * .004, shake: [sn1(t * 31) * p * 5, sn1(t * 37, 2) * p * 5], ca: .0014 + p * .003, flash: Math.exp(-(t - S2e) * 5) * .4 }; });
scene(S2e, CH2E + .15, (c, t) => {
  const out = ez(t, CH2E - .2, CH2E + .1, E.inCubic); const b2 = beatOf(t) / 2, n = Math.floor(b2) - Math.floor(beatOf(S2e) / 2), f = b2 - Math.floor(b2);
  c.save(); c.globalAlpha = 1 - out;
  // 更新の輪（2拍ごとに一周して描き直す）
  c.strokeStyle = C_INK; c.lineWidth = 10; c.beginPath(); c.arc(CX, CY, 330, -Math.PI / 2, -Math.PI / 2 + TAU * E.outCubic(f)); c.stroke();
  c.strokeStyle = C_WHITE; c.lineWidth = 2; c.beginPath(); c.arc(CX, CY, 352, 0, TAU); c.stroke(); tickRing(c, CX, CY, 362, 60, 10, -t * .2, 1.5, 5, 22);
  const L = LT('希望', { size: 250, track: .08 }); c.fillStyle = C_INK;
  drawText(c, L, CX, CY - 6, (g, i) => ({ s: lerp(1.25, 1, E.outExpo(sat(f * 3))) }));
  c.fillStyle = C_WHITE; c.font = fnt(F_LAT, 26, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; try { c.letterSpacing = '6px'; } catch (e) { }
  c.fillText('HOPE  ver. ' + String(Math.max(1, n + 1)).padStart(3, '0'), CX, CY + 440); try { c.letterSpacing = '0px'; } catch (e) { }
  drawTextS(c, LT('を更新し', { size: 96, track: .12 }), 330, CY, rise(t, 162.9, { stag: .07, dur: .4 }), C_WHITE, C_INK, 6);
  drawTextS(c, LT('続けろ', { size: 150, fam: F_GOTH, track: .06 }), 1590, CY, (g, i) => { const kk = E.outExpo(prog(t, 164.0 + i * .09, 164.0 + i * .09 + .3)); return { a: kk, s: lerp(1.8, 1, kk) * (1 + pulse(t, 2, 6) * .05) }; }, C_WHITE, C_VERM, 8);
  c.restore();
});
