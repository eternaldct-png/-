// ツール操作デモ（16:9 / 13秒）キャラ: 4 — 予約ページの操作を、ズーム・注釈つきで見せる画面収録風
window.SCENE = {
  w: 1280, h: 720, dur: 13, poster: 5.4,
  draw(ctx, t) {
    const { w, h } = this, C = 4, E = L.E;
    const P = '#6366f1', INK = '#0f172a', MUTED = '#64748b';
    L.linear(ctx, w, h, ['#eef2ff', '#e0f2fe', '#f5f3ff'], 120);
    L.blobs(ctx, w, h, t, [{ x: 0.8, y: 0.2, r: 0.35, color: 'rgba(99,102,241,0.12)' }, { x: 0.3, y: 0.9, r: 0.4, color: 'rgba(14,165,233,0.12)' }], 13);
    const fade = 1 - E.inCubic(L.prog(t, 12.4, 12.9));

    // ウィンドウ座標
    const WX = 330, WY = 70, WW = 900, WH = 580;
    const dates = ['10/6 月', '10/7 火', '10/8 水', '10/9 木', '10/10 金', '10/11 土'];
    const slots = ['10:00', '10:30', '11:00', '11:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30'];
    const booked = new Set([1, 4, 9]);
    const tabXY = (i) => [WX + 30 + i * 142, WY + 150];
    const slotXY = (i) => [WX + 40 + (i % 4) * 210, WY + 250 + Math.floor(i / 4) * 78];
    const SEL_DATE = 1, SEL_SLOT = 6;
    const dateOn = t > 2.35, slotOn = t > 5.05;
    const modal = E.outBack(L.prog(t, 6.6, 7.0)) * (1 - E.inCubic(L.prog(t, 9.5, 9.75)));
    const done = E.outBack(L.prog(t, 9.75, 10.2));

    // カメラ（注目箇所にズーム）
    const keys = [[0, WX + WW / 2, WY + WH / 2, 1], [1.3, WX + 330, WY + 185, 1.28], [3.5, WX + 430, WY + 330, 1.22], [6.5, WX + WW / 2, WY + WH / 2 - 10, 1.12], [9.6, WX + WW / 2, WY + WH / 2, 1]];
    let cam = keys[0].slice(1);
    for (let i = 1; i < keys.length; i++) {
      const k = E.inOutCubic(L.prog(t, keys[i][0], keys[i][0] + 0.7));
      cam = [L.lerp(cam[0], keys[i][1], k), L.lerp(cam[1], keys[i][2], k), L.lerp(cam[2], keys[i][3], k)];
    }
    ctx.save(); ctx.globalAlpha = fade;
    ctx.beginPath(); ctx.rect(300, 0, w - 300, h); ctx.clip();
    const appear = E.outBack(L.prog(t, 0.1, 0.7));
    ctx.translate(cam[0], cam[1]); ctx.scale(cam[2] * (0.85 + 0.15 * appear), cam[2] * (0.85 + 0.15 * appear)); ctx.translate(-cam[0], -cam[1]);
    ctx.globalAlpha *= L.clamp(appear * 2);

    // ── ブラウザ
    L.panel(ctx, WX, WY, WW, WH, 18, { fill: '#ffffff', shadow: 'rgba(15,23,42,0.18)', shadowBlur: 40, shadowY: 16 });
    ctx.save(); L.rr(ctx, WX, WY, WW, WH, 18); ctx.clip();
    ctx.fillStyle = '#f1f5f9'; ctx.fillRect(WX, WY, WW, 46);
    ['#f87171', '#fbbf24', '#34d399'].forEach((c, i) => { ctx.fillStyle = c; ctx.beginPath(); ctx.arc(WX + 26 + i * 22, WY + 23, 7, 0, L.TAU); ctx.fill(); });
    L.panel(ctx, WX + 110, WY + 10, 420, 26, 13, { fill: '#fff' });
    L.text(ctx, '🔒 booking-sample.app/book', WX + 126, WY + 29, { font: L.font(500, 15), color: MUTED });
    // ヘッダー
    L.drawHead(ctx, 1, WX + 60, WY + 92, 26, { bg: '#e0e7ff' });
    L.text(ctx, 'オンライン面談の予約', WX + 100, WY + 92, { font: L.font(900, 26), color: INK });
    L.text(ctx, '30分 ・ ビデオ通話 ・ 無料', WX + 100, WY + 118, { font: L.font(500, 16), color: MUTED });
    // 日付タブ
    dates.forEach((d, i) => {
      const [x, y] = tabXY(i), sel = i === SEL_DATE && dateOn;
      L.panel(ctx, x, y, 128, 64, 14, { fill: sel ? P : '#f8fafc', stroke: sel ? P : '#e2e8f0', lineWidth: 2 });
      const [md, wd] = d.split(' ');
      L.text(ctx, md, x + 64, y + 32, { font: L.font(900, 22, 'Montserrat'), color: sel ? '#fff' : INK, align: 'center' });
      L.text(ctx, wd, x + 64, y + 54, { font: L.font(700, 15), color: sel ? '#e0e7ff' : MUTED, align: 'center' });
    });
    // 時間枠
    const slotsP = dateOn ? E.outCubic(L.prog(t, 2.4, 2.8)) : 0.35;
    slots.forEach((s, i) => {
      const [x, y] = slotXY(i), b = booked.has(i), sel = i === SEL_SLOT && slotOn;
      ctx.save(); ctx.globalAlpha *= slotsP;
      L.panel(ctx, x, y, 190, 58, 12, { fill: sel ? P : b ? '#f1f5f9' : '#ffffff', stroke: sel ? P : b ? '#e2e8f0' : '#c7d2fe', lineWidth: 2 });
      L.text(ctx, s, x + 95, y + 37, { font: L.font(800, 22, 'Montserrat'), color: sel ? '#fff' : b ? '#cbd5e1' : P, align: 'center' });
      if (b) L.text(ctx, '予約済', x + 160, y + 36, { font: L.font(700, 13), color: '#94a3b8', align: 'center' });
      ctx.restore();
    });
    ctx.restore();

    // ── 入力モーダル
    if (modal > 0) {
      ctx.save(); ctx.globalAlpha *= L.clamp(modal);
      ctx.fillStyle = 'rgba(15,23,42,0.35)'; L.rr(ctx, WX, WY, WW, WH, 18); ctx.fill();
      ctx.translate(WX + WW / 2, WY + WH / 2); ctx.scale(modal, modal);
      L.panel(ctx, -240, -150, 480, 300, 20, { fill: '#fff', shadow: 'rgba(15,23,42,0.3)', shadowBlur: 30 });
      L.text(ctx, '10/7（火）14:00〜14:30', 0, -98, { font: L.font(900, 24), color: INK, align: 'center' });
      L.text(ctx, 'お名前', -200, -48, { font: L.font(700, 16), color: MUTED });
      L.panel(ctx, -200, -36, 400, 56, 10, { fill: '#f8fafc', stroke: t > 7.3 ? P : '#cbd5e1', lineWidth: 2 });
      const name = '山田 花子';
      const n = Math.floor(L.lerp(0, name.length + 0.99, L.prog(t, 7.5, 8.4)));
      const typed = name.slice(0, n);
      L.text(ctx, typed || (t < 7.3 ? '例）山田 花子' : ''), -184, 2, { font: L.font(700, 24), color: typed ? INK : '#cbd5e1' });
      if (t > 7.3 && t < 8.9 && Math.floor(t * 3) % 2 === 0) { const tw = L.measure(ctx, typed, { font: L.font(700, 24) }); ctx.fillStyle = P; ctx.fillRect(-182 + tw, -20, 2, 28); }
      const press = t > 9.05 && t < 9.25 ? 0.96 : 1;
      ctx.save(); ctx.scale(press, press);
      L.panel(ctx, -200, 56, 400, 62, 31, { fill: [P, '#8b5cf6'] });
      L.text(ctx, '予約する', 0, 96, { font: L.font(900, 24), color: '#fff', align: 'center' });
      ctx.restore();
      ctx.restore();
    }
    // ── 完了ポップアップ
    if (done > 0) {
      ctx.save(); ctx.translate(WX + WW / 2, WY + WH / 2); ctx.scale(done, done);
      L.panel(ctx, -230, -130, 460, 260, 22, { fill: '#fff', shadow: 'rgba(15,23,42,0.3)', shadowBlur: 30 });
      ctx.fillStyle = '#22c55e'; ctx.beginPath(); ctx.arc(0, -52, 44, 0, L.TAU); ctx.fill();
      L.check(ctx, 0, -50, 44, '#fff', L.prog(t, 10.0, 10.4), 9);
      L.text(ctx, '予約が確定しました', 0, 34, { font: L.font(900, 32), color: INK, align: 'center' });
      L.text(ctx, '10/7（火）14:00〜 確認メールを送信しました', 0, 76, { font: L.font(500, 17), color: MUTED, align: 'center' });
      ctx.restore();
      L.confetti(ctx, t, 10.0, WX + WW / 2, WY + WH / 2 - 60, { n: 60, seed: 4, vmin: 300, vmax: 700 });
    }

    // ── 注釈（番号つきの丸・ラベル）
    const note = (x, y, rw, rh, num, label, a, b, side = 'top', dy = null) => {
      const p = E.outBack(L.prog(t, a, a + 0.35)) * (1 - E.inCubic(L.prog(t, b - 0.25, b)));
      if (p <= 0) return;
      ctx.save(); ctx.strokeStyle = '#f43f5e'; ctx.lineWidth = 4;
      const dp = E.outCubic(L.prog(t, a, a + 0.5));
      ctx.beginPath(); ctx.ellipse(x, y, rw, rh, -0.04, -Math.PI / 2, -Math.PI / 2 + L.TAU * dp); ctx.stroke();
      const lx = dy === null ? x + rw * 0.55 : x - 110, ly = dy !== null ? y + dy : side === 'top' ? y - rh - 34 : y + rh + 40;
      ctx.translate(lx, ly); ctx.scale(p, p);
      ctx.fillStyle = '#f43f5e'; ctx.beginPath(); ctx.arc(0, 0, 22, 0, L.TAU); ctx.fill();
      L.text(ctx, num, 0, 9, { font: L.font(900, 24, 'Montserrat'), color: '#fff', align: 'center' });
      L.pill(ctx, label, 32 + L.measure(ctx, label, { font: L.font(900, 22) }) / 2 + 20, 8, { font: L.font(900, 22), bg: INK, color: '#fff', padX: 18 });
      ctx.restore();
    };
    const [tx, ty] = tabXY(SEL_DATE);
    note(tx + 64, ty + 32, 86, 48, '1', '日付を選ぶ', 1.9, 3.5);
    const [sx, sy] = slotXY(SEL_SLOT);
    note(sx + 95, sy + 29, 124, 46, '2', '空き時間を選ぶ', 4.6, 6.4, 'bottom');
    note(WX + WW / 2, WY + WH / 2 - 12, 230, 50, '3', '名前を入れて予約', 7.1, 9.4, 'top', 190);

    // ── カーソル
    const path = [[0, WX + 700, WY + 520], [1.4, WX + 700, WY + 520], [2.1, tx + 70, ty + 36], [3.9, tx + 70, ty + 36], [4.7, sx + 100, sy + 32], [6.6, sx + 100, sy + 32], [7.2, WX + WW / 2 + 40, WY + WH / 2 - 4], [8.5, WX + WW / 2 + 40, WY + WH / 2 - 4], [9.0, WX + WW / 2 + 60, WY + WH / 2 + 94], [12, WX + WW / 2 + 60, WY + WH / 2 + 94]];
    let cx = path[0][1], cy = path[0][2];
    for (let i = 1; i < path.length; i++) {
      const k = E.inOutCubic(L.prog(t, path[i - 1][0], path[i][0]));
      if (t >= path[i - 1][0]) { cx = L.lerp(path[i - 1][1], path[i][1], k); cy = L.lerp(path[i - 1][2], path[i][2], k); }
    }
    const clicks = [2.3, 5.0, 7.3, 9.1];
    let pressed = 0;
    clicks.forEach((c) => {
      const k = L.prog(t, c, c + 0.5);
      if (k > 0 && k < 1) { ctx.save(); ctx.strokeStyle = `rgba(99,102,241,${1 - k})`; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(cx, cy, 10 + k * 40, 0, L.TAU); ctx.stroke(); ctx.restore(); }
      if (t > c && t < c + 0.15) pressed = 1;
    });
    if (t < 9.7) L.cursor(ctx, cx, cy, 1.2, pressed);
    ctx.restore();

    // ── ガイド役のキャラ（左）
    ctx.save(); ctx.globalAlpha = fade;
    const cp = E.outBack(L.prog(t, 0.2, 0.7));
    L.groundShadow(ctx, 160, 704, 220, 0.2);
    L.liveChar(ctx, C, 160, 706 + (1 - cp) * 600, 560, t, { shadow: 'rgba(15,23,42,0.15)' });
    const say = [[0.6, 1.9, 'かんたん3ステップ！'], [1.9, 3.9, '① 日付をえらんで'], [4.4, 6.6, '② 空いてる時間を'], [6.9, 9.6, '③ 名前を入れたら'], [9.9, 12.3, '予約完了です✨']];
    say.forEach(([a, b, s]) => {
      const p = E.outBack(L.prog(t, a, a + 0.3)) * (1 - E.inBack(L.prog(t, b - 0.25, b)));
      if (p <= 0) return;
      ctx.save(); ctx.translate(160, 90); ctx.scale(p, p);
      const bw = L.measure(ctx, s, { font: L.font(900, 22) }) + 40;
      L.bubble(ctx, -bw / 2, -30, bw, 58, { fill: '#fff', r: 29, shadow: 'rgba(15,23,42,0.15)', tail: [0, 50, 'bottom'] });
      L.text(ctx, s, 0, 7, { font: L.font(900, 22), color: INK, align: 'center' });
      ctx.restore();
    });
    ctx.restore();
  },
};
