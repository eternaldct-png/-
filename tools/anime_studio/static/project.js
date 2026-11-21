// コマドリ: 制作ワークスペース（S03〜S10）。サーバーの状態（/api/projects/<id>）をそのまま描く。
(() => {
  const PID = window.PID;
  const STAGES = window.STAGE_LIST; // [[key, label], ...]
  const LABEL = Object.fromEntries(STAGES);
  const KEYS = STAGES.map(s => s[0]);
  const STATE = { todo: '未着手', generating: '作成中', review: '確認待ち', approved: '✓ 承認済み', stale: '古い', failed: '失敗' };
  const ROLE = { director: '🎬 監督', writer: '✍️ 脚本', character: '🧑‍🎨 キャラ', scene: '🏞 場面', storyboard: '🎞 絵コンテ',
    animator: '🖌 作画', sound: '🎵 音', editor: '🎚 編集', me: 'あなた', system: '⚠️ お知らせ' };
  const esc = K.esc;
  let P = null, cur = null, pollTimer = null, lastActive = null, userPicked = false;

  const qs = new URLSearchParams(location.search);
  if (KEYS.includes(qs.get('stage'))) { cur = qs.get('stage'); userPicked = true; }

  async function load() {
    try { P = await K.api('GET', `/api/projects/${PID}`); }
    catch (e) { K.toast(e.message, true); return; }
    const active = P.active_job ? P.active_job.kind : null;
    if (!cur) cur = firstOpen();
    // おまかせ・承認のあと、作っている段階へついていく
    if (active && active !== lastActive && (!userPicked || P.auto)) cur = active;
    lastActive = active;
    render();
    clearTimeout(pollTimer);
    if (active || Object.values(P.stages).includes('generating')) pollTimer = setTimeout(load, active ? 2000 : 1000);
  }
  function firstOpen() {
    return KEYS.find(k => P.stages[k] !== 'approved') || 'render';
  }
  function go(stage) {
    cur = stage; userPicked = true;
    history.replaceState(null, '', `?stage=${stage}`);
    render();
    document.getElementById('panel').focus?.();
  }

  // ── 全体 ──────────────────────────────────────────
  function render() {
    document.getElementById('ptitle').textContent = P.title || '（題名なし）';
    document.title = `${P.title || '作品'} — コマドリ`;
    document.getElementById('pmeta').textContent = `${P.aspect}・目標${P.duration_sec}秒・${P.auto ? 'おまかせ' : '1段ずつ確認'}`;
    document.getElementById('engine-label').textContent = `文章AI: ${P.engine}`;
    renderStepper();
    renderLog();
    renderPanel();
  }

  function renderStepper() {
    document.getElementById('stepper').innerHTML = STAGES.map(([k, label], i) => {
      const st = P.stages[k];
      return `<li><a href="?stage=${k}" data-stage="${k}" ${k === cur ? 'aria-current="step"' : ''}>
        <span class="num">${i + 1}</span>${label}<span class="st ${st}">${STATE[st]}</span></a></li>`;
    }).join('');
    document.querySelectorAll('#stepper a').forEach(a => a.addEventListener('click', e => { e.preventDefault(); go(a.dataset.stage); }));
  }

  function renderLog() {
    const log = document.getElementById('log');
    const atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
    let html = P.logs.map(l => `<div class="msg ${l.role === 'me' ? 'me' : l.role === 'system' ? 'system' : ''}">
      <span class="who">${ROLE[l.role] || esc(l.role)}</span>${esc(l.text)}</div>`).join('');
    if (P.active_job) html += `<div class="msg"><span class="who">${ROLE.director}</span>${LABEL[P.active_job.kind] || ''}を作っています…${P.progress ? '（' + esc(P.progress) + '）' : ''}</div>`;
    if (!P.logs.length && !P.active_job) html = '<p class="small muted">指示を書くと、今の段階を作り直します。</p>';
    log.innerHTML = html;
    if (atBottom || P.active_job) log.scrollTop = log.scrollHeight;
  }

  // ── 段階パネル ─────────────────────────────────────
  function stageBar(stage, opts = {}) {
    const st = P.stages[stage];
    const generating = P.active_job && P.active_job.kind === stage;
    const anyBusy = !!P.active_job;
    const idx = KEYS.indexOf(stage);
    let buttons = '';
    if (stage === 'render') {
      buttons = `<button class="btn primary" data-act="generate" ${anyBusy ? 'disabled' : ''}>${P.render_url ? 'もう一度書き出す' : '書き出す'}</button>`;
    } else {
      const genLabel = st === 'todo' ? '作る' : (st === 'failed' ? 'やり直す' : '作り直す');
      buttons = `<button class="btn" data-act="generate" ${anyBusy ? 'disabled' : ''}>${genLabel}</button>`;
      if (['review', 'stale', 'approved'].includes(st)) {
        buttons += `<button class="btn primary" data-act="approve" ${anyBusy ? 'disabled' : ''}>${st === 'approved' ? 'もう一度承認して次を作る' : 'OK・次へ'} →</button>`;
      }
    }
    let banner = '';
    if (generating) banner = `<div class="banner info" role="status">作っています…${P.progress ? '（' + esc(P.progress) + '）' : ''} 終わるまで編集はお待ちください。</div>`;
    else if (st === 'failed') {
      const job = P.jobs.find(j => j.kind === stage && j.status === 'failed');
      banner = `<div class="banner danger" role="alert">失敗しました: ${esc(job ? job.error : '')}<br>直してから「やり直す」を押してください。</div>`;
    } else if (st === 'stale' && stage === 'render') banner = `<div class="banner warning">前の段階が変わりました。「もう一度書き出す」で今の内容にそろえられます。</div>`;
    else if (st === 'stale') banner = `<div class="banner warning">前の段階が変わりました。「作り直す」で合わせるか、このままでよければ「OK・次へ」を押してください。</div>`;
    else if (st === 'todo' && idx > 0 && P.stages[KEYS[idx - 1]] !== 'approved' && !anyBusy) {
      banner = `<div class="banner info">前の段階「${LABEL[KEYS[idx - 1]]}」の確認がまだです。先に進めることもできます。</div>`;
    }
    return `<div class="stagebar"><div class="row"><h2 tabindex="-1" id="stage-h">${idx + 1}. ${LABEL[stage]}</h2><span class="badge ${st}">${STATE[st]}</span>${opts.extra || ''}</div>
      <div class="row">${buttons}</div></div>${banner}`;
  }

  function renderPanel() {
    const panel = document.getElementById('panel');
    // 入力中は描き直さない（打っている文字が消えないように）
    if (panel.contains(document.activeElement) && document.activeElement.matches('input, textarea, select') && P.active_job && P.active_job.kind !== cur) return;
    const fn = { script: pScript, characters: pCharacters, scenes: pScenes, storyboard: pStoryboard, art: pArt, sound: pSound, render: pRender }[cur];
    const locked = P.active_job && P.active_job.kind === cur;
    panel.innerHTML = stageBar(cur) + `<div ${locked ? 'inert' : ''}>${fn()}</div>`;
    bindPanel(panel);
  }

  const fileInput = (kind, id, label = '画像を入れる', accept = 'image/png,image/jpeg,image/webp') =>
    `<label class="drop" data-drop="${kind}:${id}"><input type="file" accept="${accept}" data-upload="${kind}:${id}">📁 ${label}</label>`;

  // 1. 脚本
  function pScript() {
    const s = P.script || {};
    if (!s.scenes || !s.scenes.length) return `<div class="card empty"><p>まだ脚本がありません。「作る」を押すか、左の欄に指示を書いてください。</p>
      <details><summary class="small">元のアイデア</summary><p class="small" style="white-space: pre-wrap">${esc(P.idea)}</p></details></div>`;
    const scenes = s.scenes.map((sc, i) => `<div class="scriptscene" data-scene="${i}">
      <div class="two"><label class="field"><span>場面${i + 1}の場所</span><input type="text" data-k="place" value="${esc(sc.place)}" maxlength="60"></label>
      <label class="field"><span>何が起きるか</span><input type="text" data-k="summary" value="${esc(sc.summary)}" maxlength="400"></label></div>
      ${sc.lines.map(l => lineRow(l)).join('')}
      <div class="row"><button class="btn sm ghost" data-act="add-line" type="button">＋ セリフを足す</button>
      <button class="btn sm ghost" data-act="del-scene" type="button">この場面を消す</button></div></div>`).join('');
    return `<form id="script-form" class="card">
      <label class="field"><span>題名</span><input type="text" id="s-title" value="${esc(s.title)}" maxlength="80"></label>
      <label class="field"><span>ひとことで（ログライン）</span><input type="text" id="s-logline" value="${esc(s.logline)}" maxlength="300"></label>
      ${scenes}
      <div class="between"><button class="btn sm" data-act="add-scene" type="button">＋ 場面を足す</button>
      <button class="btn ink" type="submit">脚本を保存</button></div></form>`;
  }
  function lineRow(l) {
    return `<div class="line"><input type="text" aria-label="話す人" data-k="speaker" value="${esc(l.speaker)}" maxlength="30">
      <textarea aria-label="セリフ" data-k="text" rows="1" maxlength="400">${esc(l.text)}</textarea>
      <button class="btn sm ghost" data-act="del-line" type="button" aria-label="この行を消す">×</button></div>`;
  }
  function collectScript() {
    const f = document.getElementById('script-form');
    return {
      title: f.querySelector('#s-title').value, logline: f.querySelector('#s-logline').value,
      scenes: [...f.querySelectorAll('.scriptscene')].map(sc => ({
        place: sc.querySelector('[data-k=place]').value, summary: sc.querySelector('[data-k=summary]').value,
        lines: [...sc.querySelectorAll('.line')].map(l => ({ speaker: l.querySelector('[data-k=speaker]').value, text: l.querySelector('[data-k=text]').value })),
      })),
    };
  }

  // 2. キャラ
  function avatar(o, wide) {
    const bg = o.color || 'var(--ink)';
    return `<div class="avatar ${wide ? 'wide' : ''}" style="background:${esc(bg)}">${o.image_url ? `<img src="${o.image_url}" alt="${esc(o.name)}の画像">` : esc((o.name || '?')[0])}</div>`;
  }
  function pCharacters() {
    const list = P.characters.map(c => `<div class="card item" data-char="${c.id}">${avatar(c)}<div>
      <div class="two"><label class="field"><span>名前</span><input type="text" data-f="name" value="${esc(c.name)}" maxlength="60"></label>
      <label class="field"><span>声（Mac の読み上げ・空なら設定の声）</span><input type="text" data-f="voice" value="${esc(c.voice)}" placeholder="Kyoko など" maxlength="40"></label></div>
      <label class="field"><span>見た目</span><textarea data-f="look" maxlength="600" placeholder="髪型・髪色・服・小物など">${esc(c.look)}</textarea></label>
      <label class="field"><span>性格</span><input type="text" data-f="personality" value="${esc(c.personality)}" maxlength="400"></label>
      <div class="row">${fileInput('character', c.id, c.image_url ? '画像を差し替える' : '画像を入れる（透過PNGがおすすめ）')}
        <button class="btn sm ghost" data-act="lib-save" data-id="${c.id}" type="button">キャラ帳に保存</button>
        <button class="btn sm ghost" data-act="del-char" data-id="${c.id}" type="button">消す</button></div></div></div>`).join('');
    return `<p class="small muted">キャラの画像を入れると、絵の段階でそのまま使います（LINEスタンプメーカーで背景を抜いたPNGなど）。</p>
      <div class="items">${list || '<div class="card empty">キャラがいません。</div>'}</div>
      <div class="row" style="margin-top: var(--sp-3)"><button class="btn sm" data-act="add-char" type="button">＋ キャラを足す</button>
      <span id="lib-add"></span></div>`;
  }

  // 3. 場面
  function pScenes() {
    const list = P.scenes.map(sc => `<div class="card item wide" data-scene-id="${sc.id}">${avatar(sc, true)}<div>
      <label class="field"><span>場面の名前</span><input type="text" data-f="name" value="${esc(sc.name)}" maxlength="60"></label>
      <label class="field"><span>背景の説明</span><textarea data-f="description" maxlength="600">${esc(sc.description)}</textarea></label>
      <div class="row">${fileInput('scene', sc.id, sc.image_url ? '背景を差し替える' : '背景の画像を入れる')}
        <button class="btn sm ghost" data-act="del-scene-row" data-id="${sc.id}" type="button">消す</button></div></div></div>`).join('');
    return `<p class="small muted">背景の画像を入れると、その場面のカットの背景になります。無ければ場面の色で仮の背景を描きます。</p>
      <div class="items">${list || '<div class="card empty">場面がありません。</div>'}</div>
      <div class="row" style="margin-top: var(--sp-3)"><button class="btn sm" data-act="add-scene-row" type="button">＋ 場面を足す</button></div>`;
  }

  // 4. 絵コンテ
  const arClass = () => ({ '9:16': 'ar-916', '16:9': 'ar-169', '1:1': 'ar-11' }[P.aspect]);
  function frame(sh) {
    const inner = sh.video_url ? `<video src="${sh.video_url}" muted loop playsinline autoplay></video>`
      : sh.image_url ? `<img src="${sh.image_url}" alt="カットの絵">` : '絵はまだありません';
    return `<div class="frame ${arClass()}">${inner}</div>`;
  }
  function pStoryboard() {
    const warns = P.warnings.length ? `<div class="banner warning"><b>確認してください</b><ul>${P.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul></div>` : '';
    const sceneOpts = (sel) => `<option value="">（なし）</option>` + P.scenes.map(s => `<option value="${s.id}" ${s.id === sel ? 'selected' : ''}>${esc(s.name)}</option>`).join('');
    const camOpts = (sel) => Object.entries(window.CAMERAS).map(([k, v]) => `<option value="${k}" ${k === sel ? 'selected' : ''}>${v}</option>`).join('');
    const cards = P.shots.map((sh, i) => {
      const n = (sh.dialogue || '').length;
      return `<div class="card shot" data-shot="${sh.id}">
      <div class="between"><h3>カット ${i + 1}</h3><div class="row">
        <button class="btn sm ghost" data-act="up" ${i === 0 ? 'disabled' : ''} aria-label="カット${i + 1}を前へ">↑</button>
        <button class="btn sm ghost" data-act="down" ${i === P.shots.length - 1 ? 'disabled' : ''} aria-label="カット${i + 1}を後ろへ">↓</button>
        <button class="btn sm ghost" data-act="add-after" aria-label="カット${i + 1}の後ろに足す">＋</button>
        <button class="btn sm ghost" data-act="del-shot" aria-label="カット${i + 1}を消す">×</button></div></div>
      <div class="two"><label class="field"><span>秒</span><input type="number" data-f="seconds" min="0.5" max="30" step="0.1" value="${sh.seconds}"></label>
      <label class="field"><span>カメラ</span><select data-f="camera">${camOpts(sh.camera)}</select></label></div>
      <label class="field"><span>場面</span><select data-f="scene_id">${sceneOpts(sh.scene_id)}</select></label>
      <fieldset class="checks" style="border:0;padding:0;margin:0 0 var(--sp-2)"><legend class="small" style="font-weight:700">出るキャラ</legend>
        ${P.characters.map(c => `<label><input type="checkbox" data-char-name="${esc(c.name)}" ${sh.characters.includes(c.name) ? 'checked' : ''}> ${esc(c.name)}</label>`).join('') || '<span class="xs muted">キャラなし</span>'}</fieldset>
      <label class="field"><span>何が起きるか</span><input type="text" data-f="action" value="${esc(sh.action)}" maxlength="400"></label>
      <div class="two"><label class="field"><span>話す人</span><input type="text" data-f="speaker" value="${esc(sh.speaker)}" maxlength="30"></label>
      <label class="field"><span>画面の文字</span><input type="text" data-f="caption" value="${esc(sh.caption)}" maxlength="80"></label></div>
      <label class="field"><span>セリフ</span><textarea data-f="dialogue" rows="2" maxlength="400">${esc(sh.dialogue)}</textarea>
        <div class="counter ${n > sh.max_chars ? 'over' : ''}">${n} / ${sh.max_chars}文字</div></label>
      <details><summary class="small">絵の指示（英語・AI画像生成用）</summary><textarea data-f="image_prompt" maxlength="1000">${esc(sh.image_prompt)}</textarea></details>
    </div>`;
    }).join('');
    return `${warns}<p class="small muted">合計 <b>${P.total_seconds}秒</b>（目標 ${P.duration_sec}秒）・${P.shots.length}カット。変えたところはすぐ保存されます。</p>
      <div class="shots">${cards || '<div class="card empty">カットがありません。</div>'}</div>
      <div class="row" style="margin-top: var(--sp-3)"><button class="btn sm" data-act="add-shot" type="button">＋ カットを足す</button></div>`;
  }

  // 5. 絵と動き
  function pArt() {
    const cards = P.shots.map((sh, i) => `<div class="card shot" data-shot="${sh.id}">
      <div class="between"><h3>カット ${i + 1}</h3><span class="xs muted">${sh.seconds}秒・${window.CAMERAS[sh.camera]}</span></div>
      ${frame(sh)}
      <p class="small">${esc(sh.dialogue || sh.action)}</p>
      <div class="row">${fileInput('shot', sh.id, '自分の絵にする')}
      ${sh.image_source === 'upload' ? `<button class="btn sm ghost" data-act="clear-img" type="button">自分の絵をやめる</button><span class="badge approved">自分の絵</span>` : ''}
      ${sh.image_source === 'placeholder' ? '<span class="badge">仮の絵</span>' : ''}${sh.image_source === 'fal' ? '<span class="badge">AI生成</span>' : ''}</div></div>`).join('');
    return `<div class="banner info">絵の作り方・動きの付け方は「設定」で変えられます（既定は無料の「仮の絵＋カメラの動き」）。キャラ・場面に画像を入れてから「作り直す」と、その画像で合成します。
      自分で描いた絵・ChatGPT などで作った絵は「自分の絵にする」で差し替えられ、作り直しても残ります。</div>
      <div class="shots">${cards || '<div class="card empty">カットがありません。絵コンテを先に作ってください。</div>'}</div>`;
  }

  // 6. 音
  function pSound() {
    return `<div class="card">
      <h3>BGM・曲</h3>
      ${P.bgm_url ? `<p class="small">いまのBGM: ${esc(P.bgm_name)}</p><audio controls src="${P.bgm_url}" style="width:100%"></audio>` : '<p class="small muted">BGMはまだありません。著作権に問題のない曲（自作・フリー音源・Suno で作った曲など）を入れてください。</p>'}
      <div class="row" style="margin: var(--sp-3) 0">${fileInput('bgm', PID, P.bgm_url ? '曲を差し替える' : '曲を入れる', 'audio/*')}
        ${P.bgm_url ? '<button class="btn sm" data-act="fit-bgm" type="button">カットの秒数を曲の長さに合わせる（MV）</button>' : ''}</div>
      <label class="field"><span>BGMの音量: <output id="vol-out">${Math.round(P.bgm_volume * 100)}%</output></span>
        <input type="range" id="bgm-vol" min="0" max="1" step="0.05" value="${P.bgm_volume}" style="width:100%"></label>
    </div>
    <div class="card" style="margin-top: var(--sp-3)">
      <h3>セリフの声</h3>
      <p class="small">${P.say_available ? `Mac の読み上げで声を付けます（いま ${P.voice_count} カット分）。キャラごとの声は「キャラ」の段階で変えられます。`
        : 'このPCでは読み上げ（say）が使えないので、声なし・字幕だけで書き出します。'}</p>
    </div>`;
  }

  // 7. 書き出し
  function pRender() {
    const w = (P.render_warnings || []).length ? `<div class="banner warning"><ul>${P.render_warnings.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
    const stale = KEYS.slice(0, -1).filter(k => ['stale', 'todo', 'failed', 'generating'].includes(P.stages[k]));
    const pre = stale.length && !P.active_job && P.stages.render !== 'stale' ? `<div class="banner warning">まだ終わっていない・古い段階があります: ${stale.map(k => LABEL[k]).join('・')}</div>` : '';
    if (!P.render_url) return pre + `<div class="card empty"><p>まだ書き出していません。「書き出す」を押すと、全部のカットを1本の動画にします。</p></div>`;
    return pre + w + `<div class="player"><video controls playsinline src="${P.render_url}"></video></div>
      <div class="row end" style="margin-top: var(--sp-3)"><a class="btn primary" href="${P.render_url}&download=1">⬇ ダウンロード（mp4）</a></div>`;
  }

  // ── 操作 ──────────────────────────────────────────
  async function act(fn, btn) {
    K.busy(btn, true);
    try { await fn(); await load(); }
    catch (e) { K.toast(e.message, true); }
    finally { K.busy(btn, false); }
  }
  async function quietSave(url, data) {
    try {
      await K.api('PATCH', url, data);
      const fresh = await K.api('GET', `/api/projects/${PID}`);
      P = fresh; renderStepper();
      K.toast('保存しました');
    } catch (e) { K.toast(e.message, true); }
  }

  function bindPanel(panel) {
    panel.querySelector('[data-act=generate]')?.addEventListener('click', e => act(() => K.api('POST', `/api/projects/${PID}/stages/${cur}/generate`, {}), e.currentTarget));
    panel.querySelector('[data-act=approve]')?.addEventListener('click', e => act(async () => {
      await K.api('POST', `/api/projects/${PID}/stages/${cur}/approve`);
      const i = KEYS.indexOf(cur); cur = KEYS[Math.min(i + 1, KEYS.length - 1)]; userPicked = false;
      history.replaceState(null, '', `?stage=${cur}`);
    }, e.currentTarget));

    // アップロード（クリックでもドラッグでも）
    panel.querySelectorAll('[data-upload]').forEach(inp => inp.addEventListener('change', () => inp.files[0] && upload(inp.dataset.upload, inp.files[0], inp.closest('label'))));
    panel.querySelectorAll('[data-drop]').forEach(lb => {
      lb.addEventListener('dragover', e => { e.preventDefault(); lb.classList.add('over'); });
      lb.addEventListener('dragleave', () => lb.classList.remove('over'));
      lb.addEventListener('drop', e => { e.preventDefault(); lb.classList.remove('over'); const f = e.dataTransfer.files[0]; if (f) upload(lb.dataset.drop, f, lb); });
    });

    // 脚本
    const sf = panel.querySelector('#script-form');
    if (sf) {
      sf.addEventListener('submit', e => { e.preventDefault(); act(() => K.api('PATCH', `/api/projects/${PID}`, { script: collectScript() }), sf.querySelector('[type=submit]')); });
      sf.addEventListener('click', e => {
        const b = e.target.closest('[data-act]'); if (!b) return;
        if (b.dataset.act === 'add-line') { b.closest('.scriptscene').querySelector('.row').insertAdjacentHTML('beforebegin', lineRow({ speaker: 'ナレーション', text: '' })); }
        if (b.dataset.act === 'del-line') b.closest('.line').remove();
        if (b.dataset.act === 'del-scene') b.closest('.scriptscene').remove();
        if (b.dataset.act === 'add-scene') {
          const n = sf.querySelectorAll('.scriptscene').length;
          b.closest('.between').insertAdjacentHTML('beforebegin', `<div class="scriptscene"><div class="two"><label class="field"><span>場面${n + 1}の場所</span><input type="text" data-k="place" maxlength="60"></label>
            <label class="field"><span>何が起きるか</span><input type="text" data-k="summary" maxlength="400"></label></div>${lineRow({ speaker: 'ナレーション', text: '' })}
            <div class="row"><button class="btn sm ghost" data-act="add-line" type="button">＋ セリフを足す</button><button class="btn sm ghost" data-act="del-scene" type="button">この場面を消す</button></div></div>`);
        }
      });
    }

    // キャラ
    panel.querySelectorAll('[data-char]').forEach(card => {
      card.querySelectorAll('[data-f]').forEach(inp => inp.addEventListener('change', () => quietSave(`/api/characters/${card.dataset.char}`, { [inp.dataset.f]: inp.value })));
    });
    panel.querySelectorAll('[data-act=del-char]').forEach(b => b.addEventListener('click', async () => {
      if (await K.confirm('このキャラを消しますか？', '消す')) act(() => K.api('DELETE', `/api/characters/${b.dataset.id}`), b);
    }));
    panel.querySelectorAll('[data-act=lib-save]').forEach(b => b.addEventListener('click', () => act(async () => { await K.api('PATCH', `/api/characters/${b.dataset.id}`, { save_to_library: true }); K.toast('キャラ帳に保存しました'); }, b)));
    panel.querySelector('[data-act=add-char]')?.addEventListener('click', e => act(() => K.api('POST', `/api/projects/${PID}/characters`, {}), e.currentTarget));
    const libSpot = panel.querySelector('#lib-add');
    if (libSpot) K.api('GET', '/api/library').then(lib => {
      if (!lib.length) return;
      libSpot.innerHTML = `<label class="row small">キャラ帳から: <select id="lib-sel"><option value="">選ぶ</option>${lib.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label>`;
      libSpot.querySelector('select').addEventListener('change', ev => ev.target.value && act(() => K.api('POST', `/api/projects/${PID}/characters`, { from_id: ev.target.value })));
    }).catch(() => {});

    // 場面
    panel.querySelectorAll('[data-scene-id]').forEach(card => {
      card.querySelectorAll('[data-f]').forEach(inp => inp.addEventListener('change', () => quietSave(`/api/scenes/${card.dataset.sceneId}`, { [inp.dataset.f]: inp.value })));
    });
    panel.querySelectorAll('[data-act=del-scene-row]').forEach(b => b.addEventListener('click', async () => {
      if (await K.confirm('この場面を消しますか？（カットの場面は「なし」になります）', '消す')) act(() => K.api('DELETE', `/api/scenes/${b.dataset.id}`), b);
    }));
    panel.querySelector('[data-act=add-scene-row]')?.addEventListener('click', e => act(() => K.api('POST', `/api/projects/${PID}/scenes`, {}), e.currentTarget));

    // カット
    panel.querySelectorAll('[data-shot]').forEach(card => {
      const id = card.dataset.shot;
      card.querySelectorAll('[data-f]').forEach(inp => inp.addEventListener('change', async () => {
        await quietSave(`/api/shots/${id}`, { [inp.dataset.f]: inp.value });
        if (['seconds', 'dialogue'].includes(inp.dataset.f)) renderPanel(); // 文字数・合計を更新
      }));
      const boxes = card.querySelectorAll('[data-char-name]');
      boxes.forEach(cb => cb.addEventListener('change', () => quietSave(`/api/shots/${id}`, { characters: [...boxes].filter(x => x.checked).map(x => x.dataset.charName) })));
      card.querySelectorAll('[data-act]').forEach(b => b.addEventListener('click', async () => {
        const ids = P.shots.map(s => s.id), i = ids.indexOf(id);
        if (b.dataset.act === 'up' || b.dataset.act === 'down') {
          const j = b.dataset.act === 'up' ? i - 1 : i + 1;
          [ids[i], ids[j]] = [ids[j], ids[i]];
          act(() => K.api('POST', `/api/projects/${PID}/shots/reorder`, { ids }), b);
        }
        if (b.dataset.act === 'add-after') act(() => K.api('POST', `/api/projects/${PID}/shots`, { after: id, seconds: 3 }), b);
        if (b.dataset.act === 'del-shot' && await K.confirm(`カット${i + 1}を消しますか？`, '消す')) act(() => K.api('DELETE', `/api/shots/${id}`), b);
        if (b.dataset.act === 'clear-img') act(() => K.api('POST', `/api/shots/${id}/clear-image`), b);
      }));
    });
    panel.querySelector('[data-act=add-shot]')?.addEventListener('click', e => act(() => K.api('POST', `/api/projects/${PID}/shots`, { seconds: 3 }), e.currentTarget));

    // 音
    const vol = panel.querySelector('#bgm-vol');
    if (vol) {
      vol.addEventListener('input', () => { panel.querySelector('#vol-out').textContent = Math.round(vol.value * 100) + '%'; });
      vol.addEventListener('change', () => quietSave(`/api/projects/${PID}`, { bgm_volume: vol.value }));
    }
    panel.querySelector('[data-act=fit-bgm]')?.addEventListener('click', e => act(() => K.api('POST', `/api/projects/${PID}/fit-to-bgm`), e.currentTarget));
  }

  async function upload(target, file, label) {
    const [kind, id] = target.split(':');
    const fd = new FormData();
    fd.append('file', file);
    label?.setAttribute('aria-busy', 'true');
    try { await K.api('POST', `/api/upload/${kind}/${id}`, fd, true); K.toast('入れました'); await load(); }
    catch (e) { K.toast(e.message, true); }
    finally { label?.removeAttribute('aria-busy'); }
  }

  // 指示（チャット）
  document.getElementById('chat-form').addEventListener('submit', async e => {
    e.preventDefault();
    const ta = document.getElementById('instruction'), btn = e.target.querySelector('[type=submit]');
    const text = ta.value.trim();
    if (!text) { K.toast('指示を書いてください。', true); ta.focus(); return; }
    if (cur === 'render') { K.toast('書き出しには指示を出せません。前の段階を選んでください。', true); return; }
    await act(async () => { await K.api('POST', `/api/projects/${PID}/stages/${cur}/generate`, { instruction: text }); ta.value = ''; }, btn);
  });
  document.getElementById('instruction').addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) document.getElementById('chat-form').requestSubmit();
  });
  document.getElementById('del-project').addEventListener('click', async e => {
    if (!await K.confirm('この作品を消しますか？絵・音・書き出した動画もすべて消えます。', '消す')) return;
    try { await K.api('DELETE', `/api/projects/${PID}`); location.href = '/'; }
    catch (err) { K.toast(err.message, true); }
  });

  load();
})();
