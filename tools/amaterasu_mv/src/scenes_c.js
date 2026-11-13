'use strict';
/* ================================================================
   アマテラス MV — 間奏と後半 （間奏1 1:42 / 間奏2 2:46 / ブリッジ / ブレイクダウン / ラスサビ / 終幕）
   ================================================================ */
// ---------- 間奏1: 向日葵の太陽と少年 ----------
bgSeg(IL0, IL1, t => { const out = ez(t, IL1 - .5, IL1, E.inCubic); const ring = (t - IL0) % (P * 8); return { uSun: [...px2p(CX, 400), .17], uSunI: .9 + kick(t) * .14, uCorona: 1.5 + kick(t) * .8, uRays: 1.4, uSurf: .8, uStars: .8, uHorOn: 1, uHor: px2p(0, 770)[1], uRingR: ring * .6, uRingA: Math.exp(-ring * 2) * .6, uDim: 1 - out * .6 }; });
postSeg(IL0, IL1, t => ({ bars: .075 * ez(t, IL0, IL0 + .5, E.outExpo), zoom: 1.0 + (t - IL0) * .008 + kick(t) * .006, shake: [sn1(t * 31) * kick(t) * 3, sn1(t * 37, 2) * kick(t) * 3], ca: .0013 + kick(t) * .0015 }));
scene(IL0, IL1 + .05, (c, t) => {
  const k = ez(t, IL0, IL0 + .9, E.outExpo), out = ez(t, IL1 - .4, IL1, E.inCubic);
  // 流れる欧文（輪郭だけ）
  c.save(); c.globalAlpha = .4 * k * (1 - out); c.strokeStyle = C_GOLD; c.lineWidth = 1.6; c.font = fnt(F_LAT, 330, 700); c.textBaseline = 'middle'; c.textAlign = 'left';
  const str = 'AMATERASU   AMATERASU   AMATERASU   '; const off = -((t - IL0) * 190) % 2760;
  c.strokeText(str + str, off - 200, 420); c.restore();
  c.save(); c.globalAlpha = k * (1 - out);
  sunflower(c, CX, 400, 196 * lerp(1.6, 1, k), { rot: t * .25, beat: kick(t), n: 560 });
  sunDials(c, t, CX, 400, 260, .55 * k * (1 - out), C_GOLD);
  const by = lerp(1600, 1066, k);
  const sh = c.createLinearGradient(0, by - 30, 0, by + 200); sh.addColorStop(0, 'rgba(0,0,0,.7)'); sh.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = sh; c.beginPath(); c.ellipse(CX, by + 50, 140, 110, 0, 0, TAU); c.fill();
  drawChar(c, 'back', CX, by, 620, { grade: '#0a0a1c', gamt: .86, rim: [0, 6], rimCol: '#ffb24a', rimA: 1 });
  c.restore();
});

// ---------- 間奏2: 歌詞の螺旋をくぐる ----------
const IL2 = CH2E, BR = B(131);
const SPIRAL = [...'アマテラス咲き乱れろ魂の向日葵焦燥も劣等も全部燃料にして絶対零度の孤独さえその高圧で抱きしめろ群青の闇を撃ち抜け何度倒れても首を上げる炎触れられなくても構わない距離さえ意味に変えて希望を更新し続けろ'];
bgSeg(IL2, BR, t => { const out = ez(t, BR - 1.2, BR, E.inCubic); return { uSun: [0, 0, .07 + kick(t) * .01], uSunI: (1 + kick(t) * .15) * (1 - out * .9), uCorona: 1.6 + kick(t), uRays: 2, uStars: 1, uFog: .9, uNightA: [.004, .008, .04], uNightB: [.012, .03, .14] }; });
postSeg(IL2, BR, t => ({ mb: 4, shutter: .8, rot: Math.sin((t - IL2) * .45) * .22, zoom: 1 + kick(t) * .015, shake: [sn1(t * 31) * kick(t) * 4, sn1(t * 37, 2) * kick(t) * 4], ca: .0016 + kick(t) * .003, flash: Math.exp(-(t - IL2) * 4) * .5 }));
scene(IL2, BR + .05, (c, t) => {
  const out = ez(t, BR - 1.0, BR - .05, E.inCubic), kin = ez(t, IL2, IL2 + .6);
  const sp = track([[IL2, 0], [BR - 1.5, (BR - 1.5 - IL2) * 1150, E.lin], [BR, (BR - 1.5 - IL2) * 1150 + 500, E.outCubic]])(t);
  let surge = 0; { const b = beatOf(t) / 4; const f = b - Math.floor(b); surge = (Math.floor(b) + E.outExpo(sat(f * 1.6))) * 260; }
  const travel = sp + surge - Math.floor(beatOf(IL2) / 4) * 260;
  const f = 900, R = 640, dz = 30, dth = TAU / 26;
  c.save(); c.globalAlpha = kin * (1 - out);
  // トンネルの輪
  c.strokeStyle = '#4a66ff'; c.lineWidth = 2;
  for (let i = 0; i < 16; i++) { let z = (i * 420 - travel % 420); if (z < 60) z += 16 * 420; const r = R * 1.35 * f / z; c.globalAlpha = kin * (1 - out) * sat(1 - z / 6400) * .5 * sat((z - 60) / 300); c.beginPath(); c.arc(CX, CY, r, 0, TAU); c.stroke(); }
  // 文字の螺旋（2本）
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.font = fnt(F_MIN, 100);
  const k0 = Math.floor(travel / dz);
  for (let arm = 0; arm < 2; arm++) for (let j = 190; j >= 0; j--) {
    const kI = k0 + j; const z = kI * dz - travel + 80; if (z < 70) continue;
    const th = kI * dth * (arm ? -1 : 1) + arm * 1.3; const s = f / z; const rr = R * (arm ? .62 : 1);
    const x = CX + Math.cos(th) * rr * s, y = CY + Math.sin(th) * rr * s;
    const a = sat(1 - z / 5600) * sat((z - 70) / 160); if (a <= 0.01) continue;
    c.save(); c.translate(x, y); c.rotate(th + (arm ? -1 : 1) * Math.PI / 2); c.scale(s * (arm ? .8 : 1.5), s * (arm ? .8 : 1.5));
    c.globalAlpha = kin * (1 - out) * a * (arm ? .55 : 1);
    const ch = SPIRAL[((kI % SPIRAL.length) + SPIRAL.length) % SPIRAL.length];
    c.fillStyle = arm ? '#6f8bff' : (Math.floor(kI / 5) % 4 === 0 ? C_WHITE : C_GOLD); c.fillText(ch, 0, 0); c.restore();
  }
  c.restore();
});

// ================================================================
//  2:57–3:13  ブリッジ — 依存と共鳴 / 束縛じゃなく照射
// ================================================================
const BRb = 179.55, BRc = 182.1, BRd = 185.75, BRe = 190.0, BD = 193.5;
bgSeg(BR, BRd, t => { const pr = ez(t, BRc, BRc + 1.2, E.outCubic); return { uSun: [0, .02, .1], uSunI: pr * .85, uEclipse: 1 - ez(t, 184.2, 185.6) * .0, uCorona: .8, uRays: .3, uStars: 1, uFog: 1.5, uNightA: [.004, .008, .04], uNightB: [.014, .03, .15] }; });
postSeg(BR, BRd, t => { const st = Math.exp(-Math.abs(t - 181.05) * 10); return { bars: .075, zoom: 1.0 + (t - BR) * .003, shake: [sn1(t * 31) * st * 14, sn1(t * 37, 2) * st * 14], ca: .0012 + st * .006, grain: .065 }; });
scene(BR, BRb + .15, (c, t) => {
  label(c, t, BR + .2, '伍　証明', 'PROOF');
  const k = ez(t, BR, BR + .8, E.outQuint), out = ez(t, BRb - .15, BRb + .1, E.inCubic);
  c.save(); c.globalAlpha = (1 - out); c.strokeStyle = C_WHITE; c.lineWidth = 2.5;
  // 依存: 小さな円が大きな円にしがみつく
  const ax = 560, ay = 500, ph = t * 1.4;
  c.globalAlpha = (1 - out) * k; c.beginPath(); c.arc(ax, ay, 150, 0, TAU * k); c.stroke();
  c.fillStyle = '#8fa0ff'; c.beginPath(); c.arc(ax + Math.cos(ph) * 208, ay + Math.sin(ph) * 208, 56, 0, TAU); c.fill();
  c.setLineDash([4, 10]); c.lineWidth = 1.5; c.beginPath(); c.arc(ax, ay, 208, 0, TAU); c.stroke(); c.setLineDash([]);
  // 共鳴: 二つの円が波を出し合う
  const bx = 1360, by2 = 500; const k2 = ez(t, 177.75, 178.4, E.outQuint);
  c.globalAlpha = (1 - out) * k2;
  for (const sx of [-140, 140]) {
    c.fillStyle = C_GOLD; c.beginPath(); c.arc(bx + sx, by2, 44 + pulse(t, 2, 5) * 8, 0, TAU); c.fill();
    for (let i = 0; i < 5; i++) { const r = ((t * .9 + i / 5) % 1) * 330 + 44; c.globalAlpha = (1 - out) * k2 * (1 - (r - 44) / 330) * .8; c.strokeStyle = C_GOLD; c.lineWidth = 2; c.beginPath(); c.arc(bx + sx, by2, r, 0, TAU); c.stroke(); }
  }
  c.globalAlpha = 1 - out; c.fillStyle = C_WHITE;
  drawText(c, LT('依存', { size: 110, track: .3 }), ax + 16, 830, rise(t, 176.67, { stag: .15, dur: .6 }));
  drawText(c, LT('と', { size: 60 }), CX, 500, rise(t, 177.45, { dur: .4 }));
  c.fillStyle = C_GOLD; drawText(c, LT('共鳴', { size: 110, track: .3 }), bx + 16, 830, rise(t, 177.75, { stag: .15, dur: .6 }));
  c.fillStyle = C_WHITE; drawText(c, LT('の違いも知らず', { size: 56, w: 500, track: .5 }), CX, 960, rise(t, 178.45, { stag: .06, dur: .5 }));
  c.restore();
});
scene(BRb - .05, BRc + .15, (c, t) => {
  const out = ez(t, BRc - .15, BRc + .1, E.inCubic); c.save(); c.globalAlpha = 1 - out;
  c.fillStyle = C_WHITE; drawText(c, LT('求めることを', { size: 104, track: .22 }), 800, 480, rise(t, 179.6, { stag: .08, dur: .5 }));
  // 罪の印
  const st = E.outExpo(prog(t, 181.05, 181.25));
  if (st > 0) { c.save(); c.translate(1420, 520); c.rotate(-.1); c.scale(lerp(2.6, 1, st), lerp(2.6, 1, st)); c.globalAlpha = (1 - out) * st; c.fillStyle = C_VERM; c.fillRect(-130, -130, 260, 260); c.fillStyle = C_INK; drawText(c, LT('罪', { size: 200 }), 0, 0, null); c.restore(); }
  c.fillStyle = C_WHITE; drawText(c, LT('にしてた', { size: 70, w: 500, track: .4 }), 1400, 760, rise(t, 181.35, { stag: .07, dur: .4 }));
  c.restore();
});
scene(BRc - .05, BRd + .15, (c, t) => {
  const out = ez(t, BRd - .15, BRd + .1, E.inCubic); c.save(); c.globalAlpha = 1 - out;
  // 作図: コンパスで円を描き、放射線を引く
  const cy = CY - 22, dr = ez(t, BRc, 183.6, E.inOutCubic);
  c.strokeStyle = C_GOLD; c.lineWidth = 2; c.beginPath(); c.arc(CX, cy, 190, -Math.PI / 2, -Math.PI / 2 + TAU * dr); c.stroke();
  c.strokeStyle = C_WHITE; c.lineWidth = 1.2;
  for (let i = 0; i < 12; i++) { const kk = E.outQuint(prog(t, 183.2 + i * .12, 183.6 + i * .12)); if (kk <= 0) continue; const a = i / 12 * TAU - Math.PI / 2; c.globalAlpha = (1 - out) * .8; c.beginPath(); c.moveTo(CX + Math.cos(a) * 210, cy + Math.sin(a) * 210); c.lineTo(CX + Math.cos(a) * (210 + 190 * kk), cy + Math.sin(a) * (210 + 190 * kk)); c.stroke(); }
  c.globalAlpha = 1 - out; c.fillStyle = C_WHITE;
  drawText(c, LT('でもあなたは', { size: 72, w: 500, track: .4 }), 420, CY - 20, rise(t, 182.17, { stag: .08, dur: .5 }));
  drawTextS(c, LT('証明した', { size: 128, track: .16 }), 1500, CY - 20, (g, i) => { const kk = E.outExpo(prog(t, 183.75 + i * .12, 183.75 + i * .12 + .4)); return { a: kk, dy: (1 - kk) * 40 }; }, C_WHITE, C_INK, 6);
  c.font = fnt(F_LAT, 20, 400); c.textAlign = 'center'; try { c.letterSpacing = '8px'; } catch (e) { } c.globalAlpha = (1 - out) * ez(t, 184.6, 185.1); c.fillText('Q. E. D.', 1500, CY + 90); try { c.letterSpacing = '0px'; } catch (e) { }
  c.restore();
});
// 愛は束縛じゃなく照射だと — 縛る輪がほどけて光線になる
const RAYT = 187.79;
bgSeg(BRd, BD, t => { const r = ez(t, RAYT, RAYT + .4, E.outExpo), out = ez(t, BD - 1.2, BD - .1, E.inCubic); return { uSun: [0, 0, lerp(.1, .13, r)], uSunI: (.85 + r * .22 + kick(t) * .1) * (1 - out), uEclipse: 1 - r, uCorona: 1 + r * .8, uRays: .3 + r * 2.2, uSurf: .8, uStars: 1 - out, uFog: 1.2 * (1 - out), uRingR: (t - RAYT) * 1.2, uRingA: t > RAYT ? Math.exp(-(t - RAYT) * 2.5) : 0, uDim: 1 - out }; });
postSeg(BRd, BD, t => { const f = t > RAYT ? Math.exp(-(t - RAYT) * 3.5) : 0; const out = ez(t, BD - .5, BD - .03, E.inCubic); return { flash: f * .8, shake: [sn1(t * 31) * (f * 20 + kick(t) * 3), sn1(t * 37, 2) * (f * 20 + kick(t) * 3)], ca: .0013 + f * .009, zoom: 1 + f * .03 + (t - BRd) * .004, fade: 1 - out }; });
scene(BRd - .05, BD, (c, t) => {
  const r = E.outExpo(prog(t, RAYT, RAYT + .6)), kin = ez(t, BRd, BRd + .5), out = ez(t, BD - 1.3, BD - .3, E.inCubic);
  const tight = ez(t, BRd, RAYT, E.inCubic);
  c.save(); c.globalAlpha = kin * (1 - out); c.lineWidth = 2.5; c.lineCap = 'round';
  const NL = 28, seg = 18;
  for (let i = 0; i < NL; i++) {
    const th = i / NL * TAU + t * .05; const rad = lerp(330, 235, tight) + (i % 4) * lerp(26, 7, tight);
    c.strokeStyle = r > .5 ? C_GOLD : C_WHITE; c.globalAlpha = kin * (1 - out) * (r > 0 ? 1 : .85);
    c.beginPath();
    for (let j = 0; j <= seg; j++) {
      const u = j / seg;
      const aa = th + u * 2.4 + Math.sin(t * 3 + i) * .04 * (1 - r); const bx = Math.cos(aa) * rad * 1.25, by = Math.sin(aa) * rad * .92; // 縛る輪
      const rx = Math.cos(th) * (240 + u * 1100), ry = Math.sin(th) * (240 + u * 1100);                                                           // 光線
      const kk = E.inOutCubic(sat(r * 1.25 - u * .25)); const x = CX + lerp(bx, rx, kk), y = CY + lerp(by, ry, kk);
      j ? c.lineTo(x, y) : c.moveTo(x, y);
    }
    c.stroke();
  }
  c.restore();
  c.save(); c.globalAlpha = 1 - out;
  drawTextS(c, LT('愛は', { size: 150, track: .2 }), CX, CY - 12, (g, i) => { const kk = E.outExpo(prog(t, 185.83 + i * .12, 185.83 + i * .12 + .4)); return { a: kk * (1 - r), s: lerp(1.4, 1, kk) * lerp(1, .86, tight) }; }, C_WHITE, C_INK, 6);
  c.fillStyle = '#aab4e8'; const Lb = LT('束縛じゃなく', { size: 66, track: .2 }); drawText(c, Lb, CX, 905, rise(t, 186.7, { stag: .06, dur: .35, out: RAYT - .05, odur: .12 }));
  if (r > 0) {
    drawTextS(c, LT('照射', { size: 330, fam: F_GOTH, track: .14 }), CX + 22, CY - 6, (g, i) => { const go = ez(t, 189.95, 190.5, E.inCubic); return { a: r * (1 - go), s: lerp(.3, 1, r) * (1 + kick(t) * .03) * (1 + go * .8) }; }, C_INK, C_GOLD, -6);
    c.fillStyle = C_WHITE; drawText(c, LT('だと', { size: 80, track: .5 }), CX, 905, rise(t, 188.75, { stag: .1, dur: .4, out: 189.9 }));
  }
  c.restore();
  // 光を浴びて立つ少年
  if (t > 189.9) { const kb = ez(t, 190.0, 191.2, E.outQuint); c.save(); c.globalAlpha = kb * (1 - out); drawChar(c, 'back', CX, lerp(1500, 1075, kb), 660, { grade: '#0a0a1c', gamt: .88, rim: [0, 6], rimCol: '#ffc46a', rimA: 1 }); c.restore(); }
});

// ================================================================
//  3:13–3:33  ブレイクダウン — 闇があるから光がある？ 違う
// ================================================================
const NO = 197.37, DEF = 197.97, BUILD = B(151), CH3 = 213.27;
const CREAM = '#f7f0e2';
bgSeg(BD, BUILD, t => ({ uSunI: 0, uFog: 0, uStars: 0, uDim: 0 }));
postSeg(BD, NO, t => ({ grain: .05, vig: .5, bloom: .3, ca: .0008 }));
scene(BD, NO, (c, t) => {
  c.fillStyle = '#020203'; c.fillRect(0, 0, W, H); c.fillStyle = C_WHITE;
  const L = LT('闇があるから光がある', { size: 62, w: 500, track: .34 });
  drawText(c, L, CX - 30, CY, (g, i) => ({ a: t > 193.63 + i * .27 ? 1 : 0 }));
  const q = t > 196.45 ? 1 : 0; drawText(c, LT('？', { size: 62, w: 500 }), CX + L.len / 2 + 30, CY, () => ({ a: q }));
  // カーソル
  const n = Math.min(10, Math.floor((t - 193.63) / .27) + 1); if (t > 193.4 && Math.floor(t * 2.96) % 2 === 0 && !q) { const gx = n <= 0 ? -L.len / 2 : L.gs[n - 1].x + 50; c.fillRect(CX - 30 + gx, CY - 36, 3, 72); }
});
postSeg(NO, BUILD, t => { const h = Math.exp(-(t - NO) * 7); return { shake: [sn1(t * 31) * h * 30, sn1(t * 37, 2) * h * 30], ca: .0008 + h * .012, grain: .045, vig: .25, bloom: .2, thr: .95, zoom: 1 + h * .05 + Math.max(0, t - DEF) * .003 }; });
scene(NO, BUILD + .05, (c, t) => {
  c.fillStyle = CREAM; c.fillRect(0, 0, W, H);
  if (t < DEF) { // 違う
    const k = E.outExpo(prog(t, NO, NO + .16)); c.fillStyle = C_INK; drawText(c, LT('違う', { size: 520, fam: F_GOTH, track: .04 }), CX, CY, () => ({ s: lerp(1.7, 1, k) })); return;
  }
  const k = ez(t, DEF, DEF + .6, E.outExpo), hold = t > B(150) ? 1 : 0;
  // 少年と、光が定義する影
  const bx = 640, by = 900, bh = 600; const Ls = lerp(.3, 1.7, ez(t, DEF, 203.0, E.outCubic));
  c.save(); c.translate(bx + 6, by - 2); c.transform(1, 0, -Ls, .2, 0, 0);
  const sil = silhouette('side', '#15121c'), im = IMG.side, s = bh / im.height;
  c.globalAlpha = .82 * k; c.drawImage(sil, -im.width * s / 2, -bh, im.width * s, bh); c.restore();
  c.globalAlpha = k; drawChar(c, 'side', bx, by, bh, {}); c.globalAlpha = 1;
  c.fillStyle = C_INK; c.fillRect(120, by + 2, (W - 240) * k, 1.5);
  // 光の向き
  c.save(); c.globalAlpha = .5 * k; c.strokeStyle = '#c7902a'; c.lineWidth = 1.5; for (let i = 0; i < 5; i++) { const y0 = 250 + i * 110; const kk = ez(t, DEF + .3 + i * .1, DEF + 1 + i * .1, E.outQuint); c.beginPath(); c.moveTo(60, y0); c.lineTo(60 + 330 * kk, y0 + 330 * kk * .16); c.stroke(); } c.restore();
  // 歌詞と「定義」の枠（Aメロの枠の再登場）
  c.fillStyle = C_INK;
  drawText(c, LT('光があるから', { size: 84, track: .16 }), 1310, 300, rise(t, 197.97, { stag: .07, dur: .45 }));
  const kf = ez(t, 199.9, 200.5, E.outExpo);
  c.save(); c.globalAlpha = kf; c.strokeStyle = C_INK; c.lineWidth = 2; c.strokeRect(960, 400, 700 * kf, 330); c.font = fnt(F_LAT, 15, 400); try { c.letterSpacing = '6px'; } catch (e) { } c.fillText('DEFINITION  /  n.', 962, 384); c.restore();
  drawText(c, LT('闇', { size: 190, fam: F_GOTH }), 1100, 565, () => { const kk = E.outExpo(prog(t, 199.92, 200.3)); return { a: kk, s: lerp(1.8, 1, kk) }; });
  drawText(c, LT('が', { size: 70 }), 1245, 610, rise(t, 200.5, { dur: .3 }));
  drawText(c, LT('定義', { size: 124, track: .08 }), 1440, 520, rise(t, 201.09, { stag: .1, dur: .4 }));
  drawText(c, LT('される', { size: 70, track: .16 }), 1470, 650, rise(t, 201.9, { stag: .07, dur: .35 }));
});
// 夜明けは外じゃない 内側から起動する — 少年の輪郭が窓になり、その中へ入っていく
const BOOT = 208.87;
const holeS = t => { const a = 1 + ez(t, BUILD, BOOT, E.inOutCubic) * .22; const z = prog(t, 210.6, CH3 + .12); return a * (1 + Math.pow(z, 3.2) * 46); };
const CHESTY = 600;
bgSeg(BUILD, CH3, t => { const s = holeS(t); const boot = prog(t, BOOT, 212.3); return { uSun: [...px2p(CX, CHESTY - 10), Math.min(.2, .028 * s)], uSunI: .5 + boot * .55 + kick(t) * .1, uCorona: 1 + boot, uRays: boot * 1.5, uSurf: .8, uStars: .8, uFog: 1, uNightA: [.01, .008, .03], uNightB: [.02, .03, .12] }; });
postSeg(BUILD, CH3, t => { const b = prog(t, BOOT, CH3); return { grain: .045, vig: .25 + b * .5, bloom: .2 + b * .4, thr: lerp(.95, .7, b), shake: [sn1(t * 31) * kick(t) * 5 * b, sn1(t * 37, 2) * kick(t) * 5 * b], ca: .0008 + b * b * .004, mb: t > 211 ? 4 : 1, shutter: .9 }; });
scene(BUILD, CH3 + .15, (c, t) => {
  const s = holeS(t), im = IMG.back, bh = 640 * s, bw = im.width * bh / im.height;
  const ax = .5, ay = .4; // 胸のあたりを中心に拡大
  const x = CX - bw * ax, y = CHESTY - bh * ay;
  c.fillStyle = CREAM; c.fillRect(0, 0, W, H);
  // 影（床）
  if (s < 3) { c.save(); c.globalAlpha = .25 * (1 - prog(s, 1.2, 3)); c.fillStyle = '#3a2a20'; c.beginPath(); c.ellipse(CX, y + bh + 6, 150 * s, 16 * s, 0, 0, TAU); c.fill(); c.restore(); }
  c.globalCompositeOperation = 'destination-out'; c.drawImage(im, x, y, bw, bh); c.globalCompositeOperation = 'source-over';
  // 輪郭に金のふち
  c.save(); c.globalCompositeOperation = 'destination-over'; c.restore();
  const fo = 1 - prog(t, 210.9, 211.5);
  if (fo > 0) {
    c.save(); c.globalAlpha = fo; c.fillStyle = C_INK;
    const o1 = BOOT - .2;
    drawText(c, LT('夜明けは', { size: 100, vert: true, track: .16 }), 560, 500, rise(t, 204.05, { stag: .12, dur: .6, vert: true, dist: 24, out: o1, odur: .3 }));
    drawText(c, LT('外', { size: 150, vert: true }), 1360, 380, rise(t, 205.9, { dur: .4, vert: true, dist: 0, out: o1, odur: .3 }));
    drawText(c, LT('じゃない', { size: 76, vert: true, track: .14 }), 1360, 660, rise(t, 206.5, { stag: .09, dur: .4, vert: true, dist: 24, out: o1, odur: .3 }));
    const sl = E.outExpo(prog(t, 206.6, 206.85)) * (1 - ez(t, o1, o1 + .3)); if (sl > 0) { c.strokeStyle = C_VERM; c.lineWidth = 12; c.beginPath(); c.moveTo(1270, 440); c.lineTo(1270 + 180 * sl, 440 - 120 * sl); c.stroke(); }
    c.fillStyle = C_INK;
    drawText(c, LT('内側から', { size: 104, vert: true, track: .16 }), 560, 500, rise(t, BOOT, { stag: .1, dur: .5, vert: true, dist: 24 }));
    drawText(c, LT('起動する', { size: 104, vert: true, track: .16 }), 1360, 500, rise(t, 210.3, { stag: .1, dur: .5, vert: true, dist: 24 }));
    c.restore();
  }
  // 胸の中の起動リング
  if (t > BOOT - .3 && s < 9) {
    const b = prog(t, BOOT, 212.3), R = 40 * s; c.save(); c.globalAlpha = ez(t, BOOT - .3, BOOT + .2) * (1 - prog(s, 4, 9));
    c.strokeStyle = 'rgba(255,198,77,.35)'; c.lineWidth = 3 * s; c.beginPath(); c.arc(CX, CHESTY - 10, R, 0, TAU); c.stroke();
    c.strokeStyle = C_GOLD; c.lineWidth = 4 * s; c.beginPath(); c.arc(CX, CHESTY - 10, R, -Math.PI / 2, -Math.PI / 2 + TAU * b); c.stroke();
    c.fillStyle = C_WHITE; c.font = fnt(F_LAT, 13 * s, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(String(Math.floor(b * 100)).padStart(2, '0') + '%', CX, CHESTY - 10 + R + 22 * s);
    c.restore();
  }
});

// ================================================================
//  3:33–4:00  ラスサビ — 向日葵の海
// ================================================================
const FIN = 238.43, OUTRO = 240.3;
const dawn = t => ez(t, 229.8, 237.6, E.inOutCubic) * .62 + ez(t, 237.4, FIN + .15, E.inExpo) * .38;
const camZ = t => { const v = 760; return (t < 230.2 ? (t - CH3) * v : (230.2 - CH3) * v + (t - 230.2) * 70 + (v - 70) * .9 * (1 - Math.exp(-(t - 230.2) / .9))); };
const SUNY = 452;
bgSeg(CH3, FIN, t => { const d = dawn(t); const ring = t - CH3, ring2 = t - 224.73; return { uSun: [...px2p(CX, SUNY), .145 + d * .02], uSunI: 1.02 + kick(t) * .1, uCorona: 1.3 + kick(t) * .6, uRays: 1.6 + kick(t) * .6, uSurf: .7, uStars: .35 * (1 - d), uFog: .9, uNightA: [.3, .09, .11], uNightB: [.045, .06, .27], uBright: d, uRingR: (ring2 > 0 ? ring2 : ring) * 1.2, uRingA: Math.exp(-(ring2 > 0 ? ring2 : ring) * 2.3) }; });
postSeg(CH3, FIN, t => {
  const f = Math.exp(-(t - CH3) * 3), f2 = t > 224.73 ? Math.exp(-(t - 224.73) * 3.5) : 0, d = dawn(t);
  const quake = prog(t, 221.7, 222.2) * (1 - prog(t, 223.4, 223.9));
  let card = 0; for (const x of [227.8, 229.2, 235.03]) if (t >= x) card = Math.max(card, Math.exp(-(t - x) * 6));
  const a = kick(t) * 4 + f * 20 + f2 * 16 + quake * (7 + kick(t) * 14) + card * 12;
  return { flash: f * .9 + f2 * .6 + card * .35 + ez(t, FIN - .25, FIN, E.inExpo), shake: [sn1(t * 31) * a, sn1(t * 37, 2) * a], ca: .0014 + kick(t) * .002 + f * .008 + quake * .003, zoom: 1 + kick(t) * .008 + f * .03, mb: t < 230.6 ? 2 : 1, shutter: .5, vig: lerp(.8, .3, d), bloom: lerp(.62, .25, d), thr: lerp(.7, .92, d), grain: .05 };
});
function flowerSprite(blur) { return variant('sfspr' + (blur || 0), 640, 640, c => { if (blur) c.filter = `blur(${blur}px)`; sunflower(c, 320, 320, 150, { n: 380 }); }); }
const FIELDY = 120;
function flowerField(c, t, alpha) {
  const spr = flowerSprite(), sprB = flowerSprite(7), sprB2 = flowerSprite(16); const cz = camZ(t); const cam = camera({ x: Math.sin(t * .5) * 60, y: -390 + Math.sin(t * .8) * 14, z: cz, f: 1000, roll: Math.sin(t * .4) * .02 });
  const d = dawn(t);
  // 地面
  c.save(); c.translate(0, FIELDY);
  const g = c.createLinearGradient(0, CY - 10, 0, H); g.addColorStop(0, d > .5 ? '#c98a2a' : '#5a2a0c'); g.addColorStop(.25, d > .5 ? '#7a6a1c' : '#2a2408'); g.addColorStop(1, d > .5 ? '#3a4a12' : '#0c1606');
  c.save(); c.globalAlpha = alpha; c.fillStyle = g; c.fillRect(0, CY + 6, W, H - CY); c.restore();
  const SP = 430, rows = 26, cols = 13; const z0 = Math.floor(cz / SP);
  for (let r = rows; r >= 1; r--) {
    const zi = z0 + r;
    for (let q = -cols; q <= cols; q++) {
      const id = zi * 131 + q * 17; const wx = q * SP + rs(id, 1) * 120 + (zi % 2 ? SP / 2 : 0); if (Math.abs(wx) < 190) continue;
      const wz = zi * SP + rs(id, 2) * 110; const hgt = 150 + rnd(id, 3) * 150;
      const p = proj(cam, wx, -hgt, wz); if (!p || p.x < -300 || p.x > W + 300) continue;
      const pg = proj(cam, wx, 0, wz); const size = 205 * p.s * (.75 + rnd(id, 4) * .5);
      const far = sat((p.z - 7000) / 4000), near = sat((p.z - 60) / 260);
      c.globalAlpha = alpha * (1 - far) * near;
      c.strokeStyle = d > .5 ? '#3f7a26' : '#1f4a18'; c.lineWidth = Math.max(1, 9 * p.s); c.beginPath(); c.moveTo(pg.x, pg.y); c.lineTo(p.x, p.y); c.stroke();
      const sway = Math.sin(t * 1.8 + id) * .08 + kick(t) * .05 * rs(id, 5);
      c.save(); c.translate(p.x, p.y); c.rotate(sway); c.scale(1, .93); c.drawImage(p.z < 520 ? sprB2 : p.z < 1000 ? sprB : spr, -size, -size, size * 2, size * 2); c.restore();
      if (far > 0 || p.z > 3000) { c.globalAlpha = alpha * sat((p.z - 3000) / 6000) * .5 * (1 - far); c.fillStyle = d > .5 ? '#ffe2a8' : '#ff7a2a'; c.beginPath(); c.arc(p.x, p.y, size * .9, 0, TAU); c.fill(); }
    }
  }
  c.restore(); c.globalAlpha = 1;
}
function petals(c, t, t0, n, alpha, col = '#ffc83c') {
  c.save(); c.fillStyle = col;
  for (let i = 0; i < n; i++) {
    const sp = .5 + rnd(i, 1); const x = ((rnd(i, 2) * W * 1.4 + (t - t0) * 190 * sp) % (W * 1.4)) - W * .2, y = ((rnd(i, 3) * H + (t - t0) * 60 * sp + Math.sin(t * 1.3 + i) * 40) % (H + 80)) - 40;
    c.save(); c.translate(x, y); c.rotate(t * (1 + rnd(i, 4) * 2) + i); c.scale(1, Math.cos(t * (2 + rnd(i, 5) * 3) + i)); c.globalAlpha = alpha * (.5 + rnd(i, 6) * .5);
    const s = 9 + rnd(i, 7) * 14; c.beginPath(); c.moveTo(-s, 0); c.quadraticCurveTo(0, -s * .55, s, 0); c.quadraticCurveTo(0, s * .55, -s, 0); c.fill(); c.restore();
  }
  c.restore();
}
scene(CH3 - .02, FIN + .2, (c, t) => {
  const d = dawn(t), wo = ez(t, FIN - .2, FIN + .15);
  flowerField(c, t, (1 - wo) * ez(t, CH3 - .02, CH3 + .15));
  petals(c, t, CH3, 26, .9 * (1 - wo));
  if (t > CH3 + .5) label(c, t, CH3 + .6, '陸　向日葵の海', 'SEA OF SUNFLOWERS');
  // 少年（背中）— 花の海の中に立つ
  if (t > 230.4) { const k = ez(t, 230.5, 232.2, E.outQuint); c.save(); c.globalAlpha = k * (1 - wo); drawChar(c, 'back', CX, lerp(1500, 1100, k), 560, { grade: '#1a0e10', gamt: lerp(.6, .25, d), rim: [0, 6], rimCol: '#ffd27a', rimA: .9 }); c.restore(); }
  // アマテラス（5回目）
  amaHit(c, t, CH3, 0, { end: 216.75, y: 300 });
  // 咲き誇れ 神話を超えて
  if (t > 216.9 && t < 220.0) {
    const o = 219.7;
    drawTextS(c, LT('咲き誇れ', { size: 260, fam: F_GOTH, track: .05 }), CX, 290, (g, i) => { const k = E.outExpo(prog(t, 217.0 + i * .09, 217.0 + i * .09 + .32)); const ou = ez(t, o, o + .25, E.inCubic); return { a: k * (1 - ou), s: lerp(2.2, 1, k) * (1 + kick(t) * .03), dy: -ou * 100 }; }, C_WHITE, C_VERM, 10);
    drawTextS(c, LT('神話を超えて', { size: 96, track: .4 }), CX, 520, rise(t, 218.35, { stag: .07, dur: .4, out: o, odur: .25 }), C_WHITE, C_INK, 6);
  }
  // 向日葵の海が 天を震わせる
  if (t > 219.7 && t < 224.2) {
    const o = 223.75;
    drawTextS(c, LT('向日葵の海が', { size: 120, track: .14 }), CX, 210, rise(t, 219.83, { stag: .07, dur: .45, out: o, odur: .25 }), C_GOLD, C_INK, 6);
    const q = Math.floor(t * 30);
    drawTextS(c, LT('天を震わせる', { size: 210, track: .03 }), CX, 400, (g, i) => { const k = E.outExpo(prog(t, 221.7 + i * .07, 221.7 + i * .07 + .3)); const ou = ez(t, o, o + .25, E.inCubic); const j = (4 + kick(t) * 16) * k; return { a: k * (1 - ou), s: lerp(1.6, 1, k), dx: rs(q + i * 3, 1) * j, dy: rs(q + i * 5, 2) * j }; }, C_WHITE, C_VERM, 9);
  }
  // アマテラス（6回目）
  amaHit(c, t, 224.73, 3, { end: 227.65, y: 320 });
  // 恋は衝動 / 愛は覚醒
  for (const [a, b, t0, t1, col] of [['恋は', '衝動', 227.8, 229.2, C_WHITE], ['愛は', '覚醒', 229.2, 230.55, C_GOLD]]) {
    if (t < t0 || t > t1 + .12) continue; const k = E.outExpo(prog(t, t0, t0 + .22)), k2 = E.outExpo(prog(t, t0 + .55, t0 + .78)), ou = ez(t, t1 - .1, t1 + .1, E.inCubic);
    drawTextS(c, LT(a, { size: 190, track: .06 }), 520, 330, (g, i) => ({ a: k * (1 - ou), s: lerp(1.6, 1, k) }), col, C_INK, 8);
    drawTextS(c, LT(b, { size: 360, fam: F_GOTH, track: .04 }), 1220, 330, (g, i) => ({ a: k2 * (1 - ou), s: lerp(2.4, 1, k2) }), col, C_VERM, 12);
  }
  // 終わらない朝を引き連れて
  if (t > 230.5 && t < 235.2) {
    const o = 234.75; const tc = d > .45 ? C_INK : C_WHITE, sc = d > .45 ? '#ffe9b8' : C_INK;
    drawTextS(c, LT('終わらない朝を', { size: 118, vert: true, track: .08 }), 520, 500, rise(t, 230.6, { stag: .09, dur: .5, vert: true, dist: 30, out: o, odur: .3 }), tc, sc, 5);
    drawTextS(c, LT('引き連れて', { size: 118, vert: true, track: .08 }), 1400, 500, rise(t, 232.7, { stag: .1, dur: .5, vert: true, dist: 30, out: o, odur: .3 }), tc, sc, 5);
  }
  // 今 この世界を照らせ
  if (t > 234.95) {
    const k = E.outExpo(prog(t, 235.03, 235.3)), ou = wo;
    drawTextS(c, LT('今', { size: 400, fam: F_MIN }), 430, 400, () => ({ a: k * (1 - ou), s: lerp(2, 1, k) }), C_INK, '#ffd27a', 10);
    drawTextS(c, LT('この世界を', { size: 110, track: .16 }), 1340, 270, rise(t, 235.95, { stag: .07, dur: .4 }), C_INK, '#ffe9b8', 5);
    drawTextS(c, LT('照らせ', { size: 230, fam: F_GOTH, track: .08 }), 1340, 480, (g, i) => { const kk = E.outExpo(prog(t, 237.0 + i * .12, 237.0 + i * .12 + .3)); return { a: kk * (1 - ou), s: lerp(2, 1, kk) }; }, C_VERM, C_INK, 8);
  }
});

// ================================================================
//  3:58–4:26  終幕 — 太陽は奪わない
// ================================================================
const LOGO = 253.2, END = 266.35;
bgSeg(FIN, END, t => { const k = ez(t, LOGO - .6, LOGO + 2.5, E.inOutCubic); return { uBright: 1, uSun: [...px2p(CX, lerp(390, 470, k)), lerp(.13, .0, ez(t, LOGO - .4, LOGO + 1.6, E.inOutCubic))], uSunI: 1 }; });
postSeg(FIN, END, t => ({ flash: Math.exp(-(t - FIN) * 1.4), vig: .22, bloom: .22, thr: .95, grain: .04, ca: .0008, zoom: 1 + (t - FIN) * .0012, fade: 1 - ez(t, END - 1.7, END - .15, E.inOutCubic) }));
scene(FIN, END, (c, t) => {
  const lg = ez(t, LOGO - .9, LOGO + .3, E.inOutCubic);
  // 少年（背中）と、ただそこに在る太陽
  const k = ez(t, FIN + .2, FIN + 2.2, E.outCubic);
  c.save(); c.globalAlpha = k * (1 - lg);
  c.fillStyle = 'rgba(120,80,30,.16)'; c.beginPath(); c.ellipse(CX, 1012, 150, 15, 0, 0, TAU); c.fill();
  drawChar(c, 'back', CX, 1010 - (t - FIN) * .8, 500, {});
  c.strokeStyle = 'rgba(176,120,40,.45)'; c.lineWidth = 1.5; c.beginPath(); c.arc(CX, 390, 200 + (t - FIN) * 2, 0, TAU); c.stroke();
  c.save(); c.strokeStyle = 'rgba(176,120,40,.55)'; tickRing(c, CX, 390, 212 + (t - FIN) * 2, 90, 8, t * .03, 1.2, 9, 20); c.restore();
  c.restore();
  petals(c, t, FIN, 14, .75 * (1 - lg) * k, '#f2b21c');
  c.save(); c.globalAlpha = 1 - lg; c.fillStyle = '#1a1210';
  label(c, t, OUTRO + .3, '終　朝', 'ENDLESS MORNING', '#3a2a20', 6);
  drawText(c, LT('太陽は奪わない', { size: 92, vert: true, track: .14 }), 1420, 500, rise(t, 240.6, { stag: .2, dur: 1.0, vert: true, dist: 16 }));
  drawText(c, LT('ただ在るだけで', { size: 92, vert: true, track: .14 }), 1270, 580, rise(t, 244.73, { stag: .17, dur: 1.0, vert: true, dist: 16 }));
  drawText(c, LT('救われる命がある', { size: 92, vert: true, track: .1 }), 520, 540, (g, i, n) => { const r = rise(t, 248.57, { stag: .17, dur: 1.0, vert: true, dist: 16 })(g, i, n); r.col = i === 4 ? '#c2410c' : '#1a1210'; return r; });
  c.restore();
  // ロゴ
  if (t > LOGO) {
    const kk = ez(t, LOGO, LOGO + 1.8, E.outCubic); const im = IMG.logoA; const h = 560 * (1 + (t - LOGO) * .004), w = im.width * h / im.height;
    c.save(); c.globalAlpha = kk; c.drawImage(im, CX - w / 2, CY - h / 2 + (1 - kk) * 14, w, h); c.restore();
  }
});
