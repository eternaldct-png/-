'use strict';
/* ================================================================
   アマテラス MV — タイムライン（共通部分 + 前半 0:00〜1:16）
   scene(a,b,fn)   : a〜b秒の間、レイヤーに描く
   bgSeg(a,b,fn)   : a〜b秒の背景シェーダーの設定
   postSeg(a,b,fn) : a〜b秒の仕上げ（揺れ・フラッシュなど）の上書き
   ================================================================ */
const C_INK = '#08060d', C_WHITE = '#fff5e4', C_GOLD = '#ffc64d', C_VERM = '#ff4420', C_ORANGE = '#ff8a1f', C_ULTRA = '#3350ff', C_DEEP = '#0a1650';
const rgba = (r, g, b, a) => `rgba(${r},${g},${b},${a})`;
const SC = [], BGS = [], POS = [];
const scene = (a, b, fn) => SC.push({ a, b, fn });
const bgSeg = (a, b, fn) => BGS.push({ a, b, fn });
const postSeg = (a, b, fn) => POS.push({ a, b, fn });
const _lc = new Map();
function LT(str, o) { const k = str + JSON.stringify(o || {}); let l = _lc.get(k); if (!l) { l = layout(str, o); _lc.set(k, l); } return l; }
const ALLTEXT = '黎明前静脈を走る衝動閉ざされた天の岩戸こじ開けろアマテラス均衡を装った静寂感情は地下で暴徒化正しさの定義に飼い慣らされた本音光を恐れたのは焼かれるからじゃない照らされた瞬間嘘が死ぬからだ運命論で濁した選択肢可能性という名の逃走経路それでも消去できない残像あなたという未解決の太陽その一瞥で理性は蒸発夜の構造が崩壊していく咲き乱れろ魂の向日葵焦燥も劣等も全部燃料にして絶対零度の孤独さえその高圧で抱きしめろこの矛盾を愛と呼びたい祝福と試練の境界線踏み越えるたび剥がれる仮面強がりの裏に潜伏していた幼い願いが今息をする支配じゃない征服でもないただ存在するという革命あなたが在るそれだけで再編される宇宙奪わない光があることを初めて知ったんだ群青の闇を撃ち抜け何度倒れても首を上げる炎触れられなくても構わない距離さえ意味に変えて希望を更新し続けろ依存と共鳴の違いも知らず求めることを罪にしてたでもあなたは証明した愛は束縛じゃなく照射だと闇があるから光がある？違う光があるから闇が定義される夜明けは外じゃない内側から起動する咲き誇れ神話を超えて向日葵の海が天を震わせる恋は衝動愛は覚醒終わらない朝を引き連れて今この世界を照らせ太陽は奪わないただ在るだけで救われる命がある天照壱弐参肆伍陸漆捌玖拾序終・「」【】名詞一二三℃';

// 小さな章ラベル（左上）
function label(c, t, t0, jp, en, col = C_WHITE, dur = 4.5) {
  const k = ez(t, t0, t0 + .7, E.outQuint), o = ez(t, t0 + dur - .6, t0 + dur, E.inCubic); if (k <= 0 || o >= 1) return;
  c.save(); c.globalAlpha = k * (1 - o) * .9; c.fillStyle = col;
  c.fillRect(96, 92, 46 * k, 2);
  c.font = fnt(F_MIN, 26, 500); c.textBaseline = 'middle'; c.textAlign = 'left'; c.fillText(jp, 158 + (1 - k) * 20, 93);
  c.font = fnt(F_LAT, 15, 400); try { c.letterSpacing = '5px'; } catch (e) { } c.fillText(en, 160 + (1 - k) * 30, 126); try { c.letterSpacing = '0px'; } catch (e) { }
  c.restore();
}
// 画面の左右に分けて描く（岩戸で文字が裂ける）
function splitDraw(c, gapPx, fn) {
  c.save(); c.beginPath(); c.rect(0, 0, CX, H); c.clip(); c.translate(-gapPx, 0); fn(); c.restore();
  c.save(); c.beginPath(); c.rect(CX, 0, CX, H); c.clip(); c.translate(gapPx, 0); fn(); c.restore();
}
// 円に沿って回る文字（傾いた輪。太陽の後ろ側は隠す）
function orbitText(c, str, cx, cy, R, tilt, ang, size, o = {}) {
  const fam = o.fam || F_LAT; const chars = [...str]; const n = chars.length;
  c.save(); c.font = fnt(fam, size, o.w || 400); c.textAlign = 'center'; c.textBaseline = 'middle';
  const a0 = c.globalAlpha;
  for (let i = 0; i < n; i++) {
    if (chars[i] === ' ') continue;
    const th = ang + i / n * TAU; const x = Math.cos(th) * R, z = Math.sin(th) * R;
    const y = z * Math.sin(tilt), depth = z * Math.cos(tilt);   // depth>0 が奥
    const sc = 1 - depth / R * .22;
    if (o.hideR && depth > 0 && Math.hypot(x, y) < o.hideR) continue;
    c.globalAlpha = a0 * (depth > 0 ? .38 : 1) * (o.alphaFn ? o.alphaFn(i, n) : 1);
    c.save(); c.translate(cx + x, cy + y); c.scale(sc * Math.abs(Math.sin(th)) * .82 + sc * .18, sc);
    c.fillText(chars[i], 0, 0); c.restore();
  }
  c.restore();
}
// 目盛りの輪
function tickRing(c, cx, cy, R, n, len, ang, w = 1.5, every = 0, len2 = 0) {
  c.beginPath();
  for (let i = 0; i < n; i++) { const th = ang + i / n * TAU; const l = (every && i % every === 0) ? len2 : len; const cs = Math.cos(th), sn = Math.sin(th); c.moveTo(cx + cs * R, cy + sn * R); c.lineTo(cx + cs * (R + l), cy + sn * (R + l)); }
  c.lineWidth = w; c.stroke();
}
// 文字を小さなマスに分けて風で散らす（燃えて消える）
function glyphSprite(str, o) {
  const L = LT(str, o); const pad = L.size * .25; const w = (L.vert ? L.size : L.len) + pad * 2, h = (L.vert ? L.len : L.size * 1.25) + pad * 2;
  return variant('gs' + str + JSON.stringify(o), w, h, (c, cv) => { c.fillStyle = o.col || C_WHITE; drawText(c, L, cv.width / 2, cv.height / 2, null); });
}
function disintegrate(c, spr, x, y, k, o = {}) {
  const cell = o.cell || 10, w = spr.width, h = spr.height; const nx = Math.ceil(w / cell), ny = Math.ceil(h / cell);
  const wx = o.wx === undefined ? 260 : o.wx, wy = o.wy === undefined ? -180 : o.wy; const a0 = c.globalAlpha;
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    const order = o.dirY ? 1 - j / ny : i / nx; const d = order * .55 + rnd(i * 31 + j, 7) * .25;
    const q = sat((k - d) / .32); if (q >= 1) continue;
    const e = q * q; const sx = i * cell, sy = j * cell;
    c.globalAlpha = a0 * (1 - q);
    const dx = e * (wx * (.4 + rnd(i, j)) + rs(i + j * 7, 3) * 60), dy = e * (wy * (.4 + rnd(j, i + 5)) + rs(i * 3 + j, 9) * 50);
    const s = 1 - q * .6;
    c.drawImage(spr, sx, sy, cell, cell, x - w / 2 + sx + dx, y - h / 2 + sy + dy, cell * s, cell * s);
  }
  c.globalAlpha = a0;
}
// 火の粉
function embers(c, t, t0, n, x0, y0, sx, sy, o = {}) {
  c.save(); c.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const life = (o.life || 2.4) * (.5 + rnd(i, 11)); const born = t0 + rnd(i, 3) * (o.spread || 1.5); const a = (t - born) / life; if (a < 0 || a > 1) continue;
    const x = x0 + rs(i, 1) * sx + (o.vx || 60) * a * life * (.3 + rnd(i, 5)) + Math.sin(t * 2 + i) * 14;
    const y = y0 + rs(i, 2) * sy + (o.vy || -150) * a * life * (.4 + rnd(i, 6));
    const r = (o.size || 3) * (.4 + rnd(i, 8)) * (1 - a * .5);
    c.globalAlpha = Math.sin(a * Math.PI) * (.5 + .5 * rnd(i, 4));
    c.fillStyle = a < .4 ? '#ffd27a' : '#ff5a22'; c.beginPath(); c.arc(x, y, r, 0, TAU); c.fill();
  }
  c.restore();
}

// ================================================================
//  0:00–0:16  黎明前 — 閉ざされた岩戸
// ================================================================
const doorGap = t => {
  if (t < B(7)) return 0;
  if (t < B(12)) { const u = (t - B(7)) / (P * 2); const n = Math.floor(u), f = u - n; return (n + E.outExpo(sat(f * 2.2))) / 10 * .07; }
  return lerp(.07, 1.5, E.outExpo(prog(t, B(12), B(12) + .9)));
};
bgSeg(0, B(18), t => {
  const open = prog(t, B(12), B(12) + .5);
  const r = track([[B(12), .2], [B(12) + .6, .3, E.outExpo], [B(18), .315, E.lin]])(t);
  return {
    uDoorOn: t < B(13) ? 1 : 0, uDoor: doorGap(t),
    uSeam: t < B(7) ? ez(t, 0, 2.2, E.outCubic) * (.45 + .25 * Math.sin(t * 1.3) + env('all', t) * .5) * (1 + 1.2 * ez(t, 6.3, B(7), E.inCubic)) : .9,
    uSun: [0, 0, r], uSunI: t < B(12) ? .95 + kick(t) * .25 : .85 + kick(t) * .06 + .6 * (1 - E.outCubic(prog(t, B(12), B(12) + 1.2))),
    uCorona: lerp(1.6, 1.15, open) + kick(t) * .5, uRays: 1.4 + kick(t), uFog: 1, uStars: 0, uSurf: lerp(1, .55, open),
    uRingR: (t - B(12)) * 1.1, uRingA: t > B(12) ? Math.exp(-(t - B(12)) * 2.2) * 1.1 : 0,
  };
});
postSeg(0, B(18), t => {
  const k = kick(t), build = prog(t, B(7), B(12));
  const blast = t > B(12) ? Math.exp(-(t - B(12)) * 3.2) : 0;
  const a = t < B(12) ? k * 5 * build : blast * 26 + k * 3;
  return {
    fade: ez(t, 0, .5, E.outCubic), shake: [sn1(t * 31) * a, sn1(t * 37, 2) * a], flash: blast * .85,
    zoom: t < B(12) ? 1 + build * .035 + k * .006 * build : 1.06 - .06 * E.outExpo(prog(t, B(12), B(12) + 1.0)) + (t - B(12)) * .0035 + k * .004,
    ca: .0012 + blast * .008 + k * .0012, bars: lerp(.11, 0, E.outExpo(prog(t, B(12), B(12) + .5))), vig: .9,
  };
});
scene(0, B(13), (c, t) => {
  const gap = doorGap(t) * H;
  // 静脈のように継ぎ目を走る光
  if (t < B(7)) {
    for (let i = 0; i < 3; i++) {
      const t0 = [2.6, 4.0, 5.3][i]; const k = prog(t, t0, t0 + 1.1); if (k <= 0 || k >= 1) continue;
      const y = lerp(-80, H + 80, E.inOutCubic(k)) * (i % 2 ? 1 : 1); const yy = i % 2 ? H - y : y;
      const g = c.createRadialGradient(CX, yy, 0, CX, yy, 150); g.addColorStop(0, rgba(255, 90, 40, .85 * Math.sin(k * Math.PI))); g.addColorStop(1, 'rgba(255,60,20,0)');
      c.save(); c.globalCompositeOperation = 'lighter'; c.scale(1, 1); c.fillStyle = g; c.translate(CX, yy); c.scale(.07, 1); c.translate(-CX, -yy); c.fillRect(CX - 150, yy - 150, 300, 300); c.restore();
    }
  }
  // 歌詞1: 黎明前 / 静脈を走る衝動（縦書き・継ぎ目の両側）
  const o1 = 6.0;
  c.fillStyle = C_WHITE;
  const La = LT('黎明前', { size: 104, vert: true, track: .16 });
  drawText(c, La, CX - 250, 420, rise(t, 1.13, { stag: .2, dur: .9, vert: true, dist: -30, out: o1, odur: .5 }));
  const Lb = LT('静脈を走る衝動', { size: 70, vert: true, track: .1 });
  drawText(c, Lb, CX + 250, 540, (g, i, n) => { const r = rise(t, 2.75, { stag: .19, dur: .7, vert: true, dist: 30, out: o1 + .1, odur: .5 })(g, i, n); const pl = Math.exp(-Math.abs((t - 2.75) / .19 - i - 2) * .9); r.col = pl > .3 ? C_VERM : C_WHITE; return r; });
  c.save(); c.globalAlpha = ez(t, 1.3, 2.2) * (1 - ez(t, o1, o1 + .5)) * .7; c.fillStyle = C_WHITE; c.font = fnt(F_LAT, 15, 400); try { c.letterSpacing = '7px'; } catch (e) { }
  c.textAlign = 'center'; c.fillText('BEFORE DAWN', CX - 250, 660); c.restore();
  // 歌詞2: 閉ざされた天の岩戸 / こじ開けろ（岩戸と一緒に裂ける）
  const out2 = B(9) + .3;
  splitDraw(c, gap, () => {
    c.fillStyle = C_WHITE;
    drawText(c, LT('閉ざされた天の岩戸', { size: 74, track: .22 }), CX, 392, rise(t, 6.33, { stag: .1, dur: .7, out: out2, odur: .5 }));
    const Lk = LT('こじ開けろ', { size: 210, fam: F_GOTH, track: .02 });
    drawText(c, Lk, CX, 590, (g, i, n) => { const k = E.outExpo(prog(t, 9.25 + i * .085, 9.25 + i * .085 + .35)); const o = ez(t, out2 + .4, out2 + 1.2, E.inCubic); return { a: k * (1 - o), s: lerp(1.9, 1, k) + kick(t) * .03, col: C_WHITE }; });
  });
  // 岩戸からこぼれる砂ぼこり
  if (t > B(7)) {
    c.save(); c.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 90; i++) {
      const born = B(7) + rnd(i, 1) * 7.4; const a = (t - born) / (1.6 + rnd(i, 2)); if (a < 0 || a > 1) continue;
      const side = i % 2 ? 1 : -1; const x = CX + side * (gap + 6 + rnd(i, 3) * 50 + a * 30 * rnd(i, 6)); const y = rnd(i, 4) * H * .9 + a * a * 420;
      c.globalAlpha = (1 - a) * .55; c.fillStyle = '#ffb060'; c.fillRect(x, y, 2 + rnd(i, 5) * 2, 2 + rnd(i, 5) * 5);
    }
    c.restore();
  }
});

// ================================================================
//  0:16–0:34  題字 — 太陽の中の「アマテラス」
// ================================================================
const TITLE0 = B(12);
function sunDials(c, t, cx, cy, R, a, col) {
  c.save(); c.globalAlpha = a; c.strokeStyle = col; c.fillStyle = col;
  c.lineWidth = 1.5; c.beginPath(); c.arc(cx, cy, R + 60, 0, TAU); c.stroke();
  tickRing(c, cx, cy, R + 72, 120, 10, t * .05, 1.5, 10, 26);
  c.globalAlpha = a * .5; c.beginPath(); c.arc(cx, cy, R + 190, -t * .08, -t * .08 + TAU * .62); c.stroke();
  c.globalAlpha = a; orbitText(c, 'AMATERASU  ·  天照  ·  THE SUN THAT DOES NOT TAKE  ·  ', cx, cy, R + 140, 0, -t * .09, 22, { fam: F_LAT });
  c.restore();
}
scene(TITLE0, B(18) + .5, (c, t) => {
  const R = 340, k0 = ez(t, TITLE0 + .1, TITLE0 + 1.2, E.outExpo);
  const out = ez(t, B(18) - .15, B(18) + .35, E.inCubic);
  // 目盛りの輪とオービット文字
  const rr = R + (1 - k0) * 260;
  sunDials(c, t, CX, CY, rr - 30, k0 * (1 - out) * .85, C_GOLD);
  // 題字（墨色・縦）
  const L = LT('アマテラス', { size: 126, vert: true, track: .0 });
  c.fillStyle = '#050308';
  drawText(c, L, CX, CY, (g, i, n) => {
    const t0 = bt(49) + i * P; const k = E.outExpo(prog(t, t0, t0 + .32));
    const hold = 1 + pulse(t, 2, 4) * .012;
    return { a: k * (1 - out), s: lerp(2.6, 1, k) * hold, dy: -out * 60 * (i - 2) };
  });
  // 左右の小さな添え字
  c.save(); c.globalAlpha = ez(t, TITLE0 + 2.2, TITLE0 + 3.2) * (1 - out); c.fillStyle = C_WHITE;
  c.font = fnt(F_LAT, 17, 400); try { c.letterSpacing = '9px'; } catch (e) { } c.textBaseline = 'middle';
  c.textAlign = 'left'; c.fillText('A M A T E R A S U', 120, CY); c.fillRect(120, CY + 26, 60, 1.5);
  c.textAlign = 'right'; c.fillText('ETERNAL d.c.t', W - 120, CY); c.fillRect(W - 180, CY + 26, 60, 1.5);
  c.restore();
});
// 0:24–0:34 間奏: 引きの画。水平線、太陽、背を向けて立つ少年
const INT0 = B(18), INT1 = B(25);
const horY = track([[INT0, 1300], [INT0 + 1.4, 742, E.outExpo], [INT1 - 2.2, 742], [INT1, 560, E.inOutCubic]]);
bgSeg(INT0, INT1, t => {
  const y = track([[INT0, 540], [INT0 + 1.5, 400, E.outExpo], [INT1 - 2.6, 372, E.lin], [INT1, 560, E.inOutCubic]])(t);
  const r = track([[INT0, .315], [INT0 + 1.5, .15, E.outExpo], [INT1 - 2.6, .158, E.lin], [INT1, .085, E.inOutCubic]])(t);
  const ecl = ez(t, INT1 - 2.6, INT1 - .6, E.inOutCubic);
  const ring = (t - INT0) % (P * 16);
  return {
    uSun: [...px2p(CX, y), r], uSunI: lerp(.86, 1.0, ez(t, INT0, INT0 + 1.2)) + kick(t) * .1 - ecl * .25, uCorona: 1.1 + kick(t) * .5, uRays: 1 - ecl * .6, uSurf: .6, uStars: ez(t, INT0, INT0 + 2) * .8,
    uHorOn: 1, uHor: px2p(0, horY(t))[1], uEclipse: ecl, uRingR: ring * .5, uRingA: Math.exp(-ring * 1.6) * .5 * (1 - ecl), uDim: 1 - ecl * .25,
  };
});
postSeg(INT0, INT1, t => ({ zoom: 1 + (t - INT0) * .006 + kick(t) * .004, shake: [sn1(t * 30) * kick(t) * 2.5, sn1(t * 33, 2) * kick(t) * 2.5], ca: .0012 + kick(t) * .001, bars: ez(t, INT0, INT0 + .8, E.outExpo) * .075 }));
scene(INT0, INT1, (c, t) => {
  const k = ez(t, INT0, INT0 + 1.5, E.outExpo), out = ez(t, INT1 - 2.4, INT1 - .9, E.inCubic);
  const sy = track([[INT0, 540], [INT0 + 1.5, 400, E.outExpo], [INT1 - 2.6, 372, E.lin], [INT1, 560, E.inOutCubic]])(t);
  sunDials(c, t, CX, sy, 150 + (1 - k) * 200, k * (1 - out) * .6, C_GOLD);
  // 少年（背中）— 下からせり上がる。太陽の光でふちが光る
  const by = lerp(1700, 1052, k) + (t - INT0) * 3;
  c.save(); c.globalAlpha = 1 - out;
  // 水面の影
  const sh = c.createLinearGradient(0, by - 30, 0, by + 200); sh.addColorStop(0, 'rgba(0,0,0,.75)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
  c.fillStyle = sh; c.beginPath(); c.ellipse(CX, by + 60, 130, 120, 0, 0, TAU); c.fill();
  drawChar(c, 'back', CX, by, 560, { live: t, grade: '#0a0a1c', gamt: .88, rim: [0, 5], rimCol: '#ffb24a', rimA: .95 });
  c.restore();
  // クレジット
  const a = ez(t, INT0 + 1.2, INT0 + 2.2) * (1 - out);
  c.save(); c.globalAlpha = a; c.fillStyle = C_WHITE;
  drawText(c, LT('アマテラス', { size: 54, vert: true, track: .3 }), 190, 470, rise(t, INT0 + 1.2, { stag: .08, vert: true, dist: -20 }));
  c.fillRect(189, 700, 2, 110 * ez(t, INT0 + 1.6, INT0 + 2.6, E.outQuint));
  c.font = fnt(F_LAT, 16, 400); try { c.letterSpacing = '8px'; } catch (e) { } c.textAlign = 'right'; c.textBaseline = 'middle';
  c.fillText('MUSIC VIDEO', W - 150, 470); c.font = fnt(F_LAT, 30, 700); c.fillText('ETERNAL d.c.t', W - 150, 512);
  c.fillRect(W - 150 - 64, 546, 64, 1.5);
  c.restore();
});

// ================================================================
//  0:34–0:55  Aメロ — 均衡の水平線
// ================================================================
const V1 = B(25), V1b = 39.57, V1c = 44.6, V1d = 49.7, PRE = 55.0;
bgSeg(V1, V1c, t => ({
  uSun: [...px2p(lerp(CX, 1330, ez(t, V1b - .2, V1b + .5, E.inOutExpo)), lerp(560, 500, ez(t, V1b - .2, V1b + .5, E.inOutExpo))), lerp(.085, .2, ez(t, V1b - .2, V1b + .5, E.inOutExpo))], uSunI: .78 + kick(t) * .1, uEclipse: 1, uCorona: .9 + kick(t) * .4, uRays: .25, uSurf: .5, uStars: .7, uHorOn: t < V1b ? 1 : 0, uHor: px2p(0, 560)[1], uDim: .75, uFog: 1.3,
}));
postSeg(V1, V1c, t => {
  const riot = prog(t, 36.6, 39.5); const cage = t > V1b ? 1 : 0;
  const h = env('hit', t) * (t > 43 ? 1 : .3);
  return { rot: cage ? 0 : sn1(t * 1.7) * .006 * riot + sn1(t * 23) * .0025 * riot * kick(t), shake: [sn1(t * 41) * (kick(t) * 2 + h * 12), sn1(t * 37, 4) * (kick(t) * 2 + h * 9)], bars: .075, ca: .0012 + h * .004, zoom: 1.01 + (t - V1) * .002 };
});
scene(V1, V1b + .3, (c, t) => {
  label(c, t, V1 + .2, '壱　均衡', 'EQUILIBRIUM');
  const out = ez(t, V1b - .25, V1b + .1, E.inCubic); const y0 = 560;
  // 水平線（均衡の目盛り）
  c.save(); c.globalAlpha = (1 - out) * ez(t, V1, V1 + .8); c.strokeStyle = C_WHITE; c.fillStyle = C_WHITE; c.lineWidth = 1.5;
  const lw = 1500 * ez(t, V1, V1 + 1.2, E.outQuint);
  c.beginPath(); c.moveTo(CX - lw / 2, y0); c.lineTo(CX + lw / 2, y0); c.stroke();
  for (let i = -15; i <= 15; i++) { const x = CX + i * 50; if (Math.abs(i * 50) > lw / 2) continue; c.fillRect(x, y0 - (i % 5 === 0 ? 12 : 5), 1.5, i % 5 === 0 ? 12 : 5); }
  c.restore();
  // 上: 均衡を装った静寂（静か・白）
  c.fillStyle = C_WHITE;
  const La = LT('均衡を装った静寂', { size: 96, track: .2 });
  drawText(c, La, CX, y0 - 190, rise(t, 34.33, { stag: .12, dur: .8, dist: 24, out: V1b - .3, odur: .3 }));
  // 下: 感情は地下で暴徒化（水面下で暴れる・朱）
  const Lb = LT('感情は地下で暴徒化', { size: 96, track: .12 });
  const riot = ez(t, 36.7, 39.4, E.inQuad);
  drawText(c, Lb, CX, y0 + 196, (g, i, n) => {
    const k = E.outExpo(prog(t, 36.75 + i * .09, 36.75 + i * .09 + .3)); if (k <= 0) return null;
    const j = (3 + riot * 20) * (.4 + kick(t)); const q = Math.floor(t * 30);
    return { a: k * (1 - out) * (.75 + .25 * rnd(q, i)), dx: rs(q + i * 13, 1) * j, dy: rs(q + i * 7, 2) * j * .7 + (1 - k) * 60, rot: rs(q + i, 3) * (.03 + riot * .16), s: 1 + rs(q + i * 3, 5) * riot * .22, col: C_VERM };
  });
});
// 正しさの定義に 飼い慣らされた 本音（檻）
scene(V1b - .1, V1c + .25, (c, t) => {
  const k = ez(t, V1b, V1b + .5, E.outExpo), brk = prog(t, 44.36, 44.36 + .5);
  const out = ez(t, V1c - .1, V1c + .2, E.inCubic);
  c.save(); c.globalAlpha = 1 - out;
  // 辞書の見出しのような組み
  c.fillStyle = C_WHITE; c.strokeStyle = C_WHITE;
  const x0 = 250;
  c.save(); c.globalAlpha *= k; c.lineWidth = 1.5; c.strokeRect(x0 - 40, 318, 640 * k, 330);
  c.font = fnt(F_LAT, 15, 400); try { c.letterSpacing = '6px'; } catch (e) { } c.textAlign = 'left'; c.fillText('DEFINITION  /  n.', x0, 300); c.restore();
  const l1 = LT('正しさの定義に', { size: 74, track: .06 }), l2 = LT('飼い慣らされた', { size: 74, track: .06 });
  drawText(c, l1, x0 + l1.len / 2, 420, rise(t, 39.57, { stag: .07, dur: .5 }));
  drawText(c, l2, x0 + l2.len / 2, 540, rise(t, 40.95, { stag: .07, dur: .5 }));
  // 本音（檻の中で暴れる）
  const hx = 1330, hy = 500; const hit = env('hit', t) * (t > 43.3 ? 1 : .25) + kick(t) * .25;
  const Lh = LT('本音', { size: 300, fam: F_GOTH });
  const kh = E.outExpo(prog(t, 42.3, 42.75));
  c.fillStyle = C_VERM;
  drawText(c, Lh, hx + sn1(t * 40) * hit * 22, hy + sn1(t * 37, 3) * hit * 12, (g, i) => ({ a: kh, s: lerp(.6, 1, kh) * (1 + hit * .09 + brk * .25), rot: rs(Math.floor(t * 30), i) * hit * .05 }));
  // 檻の格子
  const bars = 11, bw = 760, bx = hx - bw / 2;
  c.strokeStyle = C_WHITE; c.lineCap = 'butt';
  for (let i = 0; i < bars; i++) {
    const kb = E.outExpo(prog(t, 41.2 + i * .05, 41.2 + i * .05 + .5)); if (kb <= 0) continue;
    const x = bx + i / (bars - 1) * bw; const bend = Math.exp(-Math.pow((x - hx) / 260, 2)) * hit * 46 * (i % 2 ? 1 : -1);
    const fall = brk > 0 ? E.inCubic(brk) : 0; const dir = (i - (bars - 1) / 2);
    c.save(); c.globalAlpha *= kb * (1 - fall); c.lineWidth = 5;
    c.translate(x + dir * fall * 120, 0); c.rotate(dir * fall * .25);
    c.beginPath(); c.moveTo(0, 260 - (1 - kb) * 400); c.quadraticCurveTo(bend * 2, hy, 0, 260 + 480 * kb); c.stroke(); c.restore();
  }
  c.lineWidth = 5; c.save(); c.globalAlpha *= ez(t, 41.2, 41.7) * (1 - E.inCubic(brk));
  c.beginPath(); c.moveTo(bx - 30, 260); c.lineTo(bx + bw + 30, 260); c.moveTo(bx - 30, 740); c.lineTo(bx + bw + 30, 740); c.stroke(); c.restore();
  c.restore();
});
// 光を恐れたのは 焼かれるからじゃない / 照らされた瞬間 嘘が死ぬからだ
bgSeg(V1c, PRE, t => {
  const lit = ez(t, 49.83, 50.5, E.outExpo);
  return { uSun: [...px2p(lerp(-260, -120, prog(t, V1c, PRE)), 430), .34], uSunI: .8 + lit * .28 + kick(t) * .08, uEclipse: 1 - lit, uCorona: 1.1 + lit * .5, uRays: .5 + lit * 1.2, uSurf: .7, uStars: .5 * (1 - lit), uFog: 1.2, uDim: .8 + lit * .2 };
});
postSeg(V1c, PRE, t => { const f = t > 49.83 ? Math.exp(-(t - 49.83) * 3) : 0; return { bars: .075, flash: f * .7, zoom: 1.02 + (t - V1c) * .003, shake: [sn1(t * 30) * (kick(t) * 2 + f * 14), sn1(t * 33, 2) * (kick(t) * 2 + f * 10)], ca: .0012 + f * .006 }; });
scene(V1c, PRE + .2, (c, t) => {
  const lit = ez(t, 49.83, 50.4, E.outExpo), k = ez(t, V1c, V1c + 1.0, E.outExpo);
  const out = ez(t, PRE - .32, PRE - .02, E.inCubic);
  // 少年（横顔）。光の方を向いている
  c.save(); c.globalAlpha = (1 - out) * k;
  const bx = 1500 + (1 - k) * 160 - (t - V1c) * 5, by = 1500;
  drawChar(c, 'side', bx, by, 1700, { live: t, grade: '#07081a', gamt: lerp(.84, .45, lit), rim: [-12, 3], rimCol: lit > .5 ? '#ffd9a0' : '#ff9a4a', rimA: .55 + lit * .45 });
  c.restore();
  c.save(); c.globalAlpha = 1 - out; c.fillStyle = C_WHITE;
  const o1 = 49.55;
  drawText(c, LT('光を恐れたのは', { size: 84, vert: true, track: .12 }), 1010, 470, rise(t, 44.8, { stag: .09, dur: .6, vert: true, dist: 30, out: o1, odur: .3 }));
  drawText(c, LT('焼かれるからじゃない', { size: 64, vert: true, track: .1 }), 870, 560, rise(t, 46.75, { stag: .08, dur: .6, vert: true, dist: 30, out: o1 + .05, odur: .3 }));
  // 照らされた瞬間
  const L3 = LT('照らされた瞬間', { size: 70, track: .2 });
  drawText(c, L3, 800, 270, (g, i) => { const kk = E.outExpo(prog(t, 49.83 + i * .05, 49.83 + i * .05 + .4)); return { a: kk, dx: (1 - kk) * -80 }; });
  // 嘘（が死ぬからだ）: 「嘘」が光に焼かれて散る
  const dk = prog(t, 52.9, 54.5);
  const kk = E.outExpo(prog(t, 51.35, 51.75));
  if (kk > 0) {
    const spr = glyphSprite('嘘', { size: 400, fam: F_MIN });
    c.save(); c.globalAlpha *= kk;
    if (dk <= 0) c.drawImage(spr, 560 - spr.width / 2, 610 - spr.height / 2); else disintegrate(c, spr, 560, 610, dk * 1.1, { cell: 9, wx: 420, wy: -160 });
    c.restore();
    drawText(c, LT('が死ぬからだ', { size: 66, vert: true, track: .12 }), 850, 650, rise(t, 51.9, { stag: .08, dur: .5, vert: true, dist: 30 }));
    if (dk > 0) embers(c, t, 52.9, 160, 560, 610, 150, 170, { vx: 320, vy: -140, life: 1.8, spread: 1.3, size: 3.5 });
  }
  c.restore();
});

// ================================================================
//  0:55–1:07  Bメロ — 文字の回廊を突き抜ける
// ================================================================
const GATES = [
  { s: 55.07, e: 58.2, a: '運命論で', b: '濁した選択肢', x: 0, y: 0, roll: 0 },
  { s: 58.2, e: 61.27, a: '可能性という名の', b: '逃走経路', x: 260, y: -60, roll: .12 },
  { s: 61.27, e: 64.2, a: 'それでも消去できない', b: '残像', x: -240, y: 40, roll: -.1 },
  { s: 64.2, e: 67.5, a: 'あなたという', b: '未解決の太陽', x: 0, y: 0, roll: 0 },
];
const GZ = 5200; // ゲートの間隔
function corridorCam(t) {
  // 各ゲートの手前でゆっくり漂い、次の行の頭で一気に突き抜ける
  let z = -1500, x = 0, y = 0, roll = 0;
  for (let i = 0; i < GATES.length; i++) {
    const g = GATES[i]; const gz = i * GZ; const hover0 = gz - 1700, hover1 = gz - 1150;
    if (t < g.s) break;
    const prev = i === 0 ? { z: -3200, x: 0, y: 0, roll: 0 } : { z: (i - 1) * GZ - 1150, x: GATES[i - 1].x, y: GATES[i - 1].y, roll: GATES[i - 1].roll };
    const a = E.inOutExpo(prog(t, g.s - .22, g.s + .38));
    const drift = prog(t, g.s + .3, g.e);
    z = lerp(prev.z, lerp(hover0, hover1, drift), a); x = lerp(prev.x, g.x, a); y = lerp(prev.y, g.y, a); roll = lerp(prev.roll, g.roll, a);
  }
  const last = GATES[3]; if (t > last.e - .22) { const a = E.inExpo(prog(t, last.e - .3, last.e + .1)); z = lerp(z, 3 * GZ + 600, a); }
  return camera({ x, y: y + sn1(t * .9) * 12, z, roll: roll + sn1(t * .7, 3) * .012, f: 1000 });
}
bgSeg(PRE, 67.5, t => {
  const k = prog(t, PRE, 67.5); const last = ez(t, 64.2, 67.4, E.inCubic);
  return { uSun: [0, .01, .02 + k * .03 + last * .22], uSunI: .9 + kick(t) * .12 + last * .15, uCorona: 1.3, uRays: 1.2 + kick(t), uSurf: .6, uStars: 1, uFog: .9, uDim: .9 };
});
postSeg(PRE, 67.5, t => {
  let punch = 0; for (const g of GATES) punch = Math.max(punch, Math.exp(-Math.abs(t - g.s) * 7));
  const end = Math.exp(-Math.abs(t - 67.5) * 9);
  return { mb: 5, shutter: .9, shake: [sn1(t * 30) * (kick(t) * 3 + punch * 6), sn1(t * 33, 2) * (kick(t) * 3 + punch * 6)], ca: .0014 + punch * .006 + kick(t) * .001, flash: end * .9, zoom: 1 + punch * .02 };
});
const WALLW = ['逃走経路', '運命論', '可能性', '選択肢', '残像', '未解決'];
scene(PRE - .05, 67.55, (c, t) => {
  const cam = corridorCam(t);
  if (t < PRE + 4) { c.setTransform(1, 0, 0, 1, 0, 0); label(c, t, PRE + .3, '弐　逃走経路', 'ESCAPE ROUTE'); }
  // 壁・床の線と、流れていく文字
  const z0 = Math.floor((cam.z + 150) / 260) * 260;
  c.save();
  c.font = fnt(F_MIN, 100); c.textAlign = 'center'; c.textBaseline = 'middle';
  for (let side = -1; side <= 1; side += 2) for (let row = 0; row < 3; row++) {
    const wx = side * 900, wy = (row - 1) * 330;
    for (let zi = 0; zi < 26; zi++) {
      const z = z0 + zi * 260; const idx = Math.round(z / 260); const wd = WALLW[Math.abs(idx * 7 + row * 3 + (side > 0 ? 1 : 0)) % WALLW.length]; const word = [...wd];
      const ci = ((idx % (word.length + 2)) + word.length + 2) % (word.length + 2); const ch = side < 0 ? word[ci] : word[word.length - 1 - ci]; if (!ch) continue;
      const p0 = planeTransform(c, cam, wx, wy, z, [0, 0, -side * 2.1], [0, 2.1, 0]); if (!p0) continue;
      const fadeFar = sat(1 - (p0.z - 300) / 6200), near = sat((p0.z - 120) / 500);
      c.globalAlpha = fadeFar * near * (row === 1 ? .5 : .28); c.fillStyle = row === 1 ? '#4a66ff' : '#2a3fc0'; c.fillText(ch, 0, 0);
    }
  }
  c.setTransform(1, 0, 0, 1, 0, 0);
  // 奥へ収束する光の筋
  c.globalCompositeOperation = 'lighter'; c.lineWidth = 2;
  for (let i = 0; i < 8; i++) {
    const ang = i / 8 * TAU + .39; const rx = Math.cos(ang) * 1250, ry = Math.sin(ang) * 600;
    const a = proj(cam, rx, ry, cam.z + 260), b = proj(cam, rx, ry, cam.z + 9000); if (!a || !b) continue;
    const g = c.createLinearGradient(a.x, a.y, b.x, b.y); g.addColorStop(0, 'rgba(70,100,255,0)'); g.addColorStop(.5, 'rgba(90,120,255,.5)'); g.addColorStop(1, 'rgba(255,200,120,.7)');
    c.strokeStyle = g; c.globalAlpha = .6; c.beginPath(); c.moveTo(a.x, a.y); c.lineTo(b.x, b.y); c.stroke();
  }
  c.restore();
  // 歌詞のゲート（正面を向いた文字の板。カメラが突き抜ける）
  for (let i = GATES.length - 1; i >= 0; i--) {
    const g = GATES[i]; const gz = i * GZ; const d = gz - cam.z; if (d < 40 || d > 9000) continue;
    const p0 = proj(cam, g.x, g.y, gz); if (!p0) continue;
    const s = p0.s; const vis = sat((d - 40) / 300) * sat(1 - (d - 5200) / 3000);
    c.save(); c.translate(p0.x, p0.y); c.rotate(g.roll - cam.roll); c.scale(s, s); c.globalAlpha = vis;
    const La = LT(g.a, { size: 120, track: .1 }), Lb = LT(g.b, { size: i === 3 ? 250 : 270, fam: i % 2 ? F_GOTH : F_MIN, track: .03 });
    c.fillStyle = C_WHITE;
    drawText(c, La, 0, -210, (gl, j) => { const k = E.outExpo(prog(t, g.s + .1 + j * .04, g.s + .45 + j * .04)); return { a: k, dy: (1 - k) * 60 }; });
    // 残像: 3行目はずれた像を重ねる
    if (i === 2) { for (let q = 3; q >= 1; q--) { c.fillStyle = rgba(255, 70, 30, .22); drawText(c, Lb, q * 46 * (1 + kick(t)), 60, null); } }
    c.fillStyle = i === 3 ? C_GOLD : i === 1 ? C_WHITE : C_WHITE;
    const tb = g.s + (g.e - g.s) * .42;
    drawText(c, Lb, 0, 60, (gl, j) => { const k = E.outExpo(prog(t, tb + j * .05, tb + .35 + j * .05)); return { a: k, s: lerp(1.6, 1, k) }; });
    // 細い枠線
    c.globalAlpha = vis * .5; c.strokeStyle = C_WHITE; c.lineWidth = 2.5; const fw = Math.max(La.len, Lb.len) + 220;
    c.beginPath(); c.moveTo(-fw / 2, -330); c.lineTo(-fw / 2 + 90, -330); c.moveTo(-fw / 2, -330); c.lineTo(-fw / 2, -240);
    c.moveTo(fw / 2, 270); c.lineTo(fw / 2 - 90, 270); c.moveTo(fw / 2, 270); c.lineTo(fw / 2, 180); c.stroke();
    c.restore();
  }
});

// ================================================================
//  1:07–1:16  その一瞥で 理性は蒸発 / 夜の構造が崩壊していく
// ================================================================
const EYE0 = 67.5, COL0 = 71.4, CH1 = 76.33;
bgSeg(EYE0, COL0, t => ({ uSunI: 0, uFog: .4, uDim: .5 }));
postSeg(EYE0, COL0, t => { const f = Math.exp(-(t - EYE0) * 5); return { flash: f * .9, bars: 0, zoom: 1 + (t - EYE0) * .012, shake: [sn1(t * 30) * kick(t) * 2, sn1(t * 33, 2) * kick(t) * 2], grain: .07 }; });
scene(EYE0, COL0 + .05, (c, t) => {
  const k = ez(t, EYE0, EYE0 + .5, E.outExpo), out = ez(t, COL0 - .28, COL0, E.inExpo);
  const sh = 172 * k * (1 - out);
  // 細い帯の中に目もとだけが見える
  c.save(); c.beginPath(); c.rect(0, CY - sh, W, sh * 2); c.clip();
  c.fillStyle = '#050409'; c.fillRect(0, 0, W, H);
  const s = 3.0 + (t - EYE0) * .06; const im = IMG.face; const ex = 380, ey = 505;
  const ox = CX - ex * s + sn1(t * .5) * 10 - (t - EYE0) * 8, oy = CY - ey * s;
  c.drawImage(im, ox, oy, im.width * s, im.height * s);
  // 瞳に映る太陽
  c.globalCompositeOperation = 'lighter';
  for (const [px, py] of [[296, 487], [470, 519]]) {
    const gx = ox + px * s + 14, gy = oy + py * s - 10; const r = 60 + 30 * kick(t) + (t - EYE0) * 12;
    const g = c.createRadialGradient(gx, gy, 0, gx, gy, r); g.addColorStop(0, 'rgba(255,225,150,.95)'); g.addColorStop(.18, 'rgba(255,150,50,.6)'); g.addColorStop(1, 'rgba(255,80,20,0)');
    c.fillStyle = g; c.fillRect(gx - r, gy - r, r * 2, r * 2);
  }
  c.globalCompositeOperation = 'multiply'; const gr = c.createLinearGradient(0, CY - sh, 0, CY + sh); gr.addColorStop(0, '#6a4a5a'); gr.addColorStop(.5, '#ffe9d0'); gr.addColorStop(1, '#6a4a5a'); c.fillStyle = gr; c.fillRect(0, CY - sh, W, sh * 2);
  c.restore();
  c.fillStyle = C_GOLD; c.globalAlpha = .9 * (1 - out); c.fillRect(0, CY - sh - 3, W * k, 2); c.fillRect(W * (1 - k), CY + sh + 1, W * k, 2); c.globalAlpha = 1 - out;
  c.fillStyle = C_WHITE;
  drawText(c, LT('その一瞥で', { size: 88, track: .5 }), CX, 220, rise(t, 67.53, { stag: .08, dur: .5 }));
  // 理性は蒸発 — 文字が湯気になって昇る
  const L = LT('理性は蒸発', { size: 120, track: .3 });
  drawText(c, L, CX, 860, (g, i) => {
    const kk = E.outExpo(prog(t, 69.25 + i * .07, 69.25 + i * .07 + .35)); const v = E.inQuad(prog(t, 70.05 + i * .11, 70.05 + i * .11 + 1.1));
    return { a: kk * (1 - v), dy: (1 - kk) * 40 - v * 230, dx: Math.sin(t * 5 + i * 2) * v * 34, sy: 1 + v * 1.5, sx: 1 - v * .35 };
  });
  c.globalAlpha = 1;
});
// 夜の構造が崩壊していく — 「夜」のタイルの壁が崩れ、奥の太陽が現れる
const TCOLS = 16, TROWS = 9, TS = 120;
const tileT = (i, j) => { const d = Math.hypot(i - 7.5, (j - 4) * 1.2) / 9; const base = 72.2 + (1 - d) * 0 + d * 2.6 + rnd(i * 17 + j, 4) * .9; return Math.min(Math.round((base - OFF) / (P / 2)) * (P / 2) + OFF, B(56) + rnd(i, j) * .45); };
bgSeg(COL0, CH1, t => ({ uSun: [0, 0, .17 + (t - COL0) * .006], uSunI: .92 + kick(t) * .12, uCorona: 1.1, uRays: 1.5, uSurf: .9, uFog: .6 }));
postSeg(COL0, CH1, t => { const b = prog(t, COL0, CH1); return { bars: 0, zoom: 1 + b * .05, shake: [sn1(t * 30) * (kick(t) * 4 * b + 1), sn1(t * 33, 2) * (kick(t) * 4 * b + 1)], ca: .0012 + kick(t) * .002 * b }; });
scene(COL0 - .05, CH1 + .3, (c, t) => {
  const kin = ez(t, COL0 - .05, COL0 + .3);
  c.font = fnt(F_MIN, 64); c.textAlign = 'center'; c.textBaseline = 'middle';
  for (let j = 0; j < TROWS; j++) for (let i = 0; i < TCOLS; i++) {
    const t0 = tileT(i, j); const dt = t - t0; const x = i * TS + TS / 2, y = j * TS + TS / 2;
    c.save();
    if (dt > 0) {
      const s = 1 / (1 + dt * 1.6); const a = sat(1 - dt / 1.1); if (a <= 0) { c.restore(); continue; }
      c.translate(lerp(x, CX + (x - CX) * .7, sat(dt)), y + 900 * dt * dt + 60 * dt); c.rotate(rs(i, j) * dt * 3.2); c.scale(s, s * Math.cos(dt * (3 + rnd(j, i) * 5))); c.globalAlpha = a;
    } else { const pre = Math.exp(dt * 9); c.translate(x + rs(Math.floor(t * 30), i + j * 16) * pre * 5, y); }
    c.fillStyle = '#04050c'; c.fillRect(-TS / 2 - .5, -TS / 2 - .5, TS + 1, TS + 1);
    c.strokeStyle = 'rgba(60,80,200,.35)'; c.lineWidth = 1; c.strokeRect(-TS / 2 + .5, -TS / 2 + .5, TS - 1, TS - 1);
    c.globalAlpha *= kin * (.16 + .5 * Math.exp(dt * 5) * (dt < 0 ? 1 : 0) + rnd(i, j * 3) * .12); c.fillStyle = '#5a78ff'; c.fillText('夜', 0, 2);
    c.restore();
  }
  c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1;
  // 歌詞
  const out = prog(t, B(56) - .1, B(56) + .5);
  const La = LT('夜の構造が', { size: 150, track: .06 }), Lb = LT('崩壊していく', { size: 190, fam: F_GOTH, track: .02 });
  for (const pass of [0, 1]) {
  c.fillStyle = pass ? C_WHITE : C_INK; c.translate(pass ? -9 : 9, pass ? -9 : 9);
  drawText(c, La, CX, 400, (g, i) => { const k = E.outExpo(prog(t, 71.47 + i * .07, 71.47 + i * .07 + .4)); return { a: k * (1 - E.inCubic(out)), dy: (1 - k) * 50 + E.inCubic(out) * 300 * (1 + rnd(i, 1)), rot: out * rs(i, 2) * .8 }; });
  drawText(c, Lb, CX, 640, (g, i) => { const k = E.outExpo(prog(t, 73.2 + i * .08, 73.2 + i * .08 + .35)); const fo = E.inCubic(prog(t, B(56) - .2 + i * .05, B(56) + .45 + i * .05)); return { a: k * (1 - fo), s: lerp(1.5, 1, k), dy: fo * 500 * (1 + rnd(i, 5)) + (k < 1 ? 0 : Math.max(0, t - 74.6) * 16 * rnd(i, 3)), rot: fo * rs(i, 6) * 1.2 + (t > 74.6 ? rs(i, 8) * .03 * (t - 74.6) : 0) }; });
  }
});

