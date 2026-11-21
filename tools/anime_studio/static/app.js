// コマドリ共通: API 呼び出し・トースト・確認ダイアログ
window.K = (() => {
  const HEADER = { 'X-Komadori': '1' };
  async function api(method, url, body, isForm) {
    const opt = { method, headers: { ...HEADER } };
    if (body !== undefined) {
      if (isForm) opt.body = body;
      else { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    }
    let r;
    try { r = await fetch(url, opt); }
    catch (e) { throw new Error('アプリにつながりません。コマドリが起動しているか確認してください。'); }
    let data = null;
    try { data = await r.json(); } catch (e) { /* 空 */ }
    if (!r.ok) throw new Error((data && data.error) || `エラーが起きました（${r.status}）`);
    return data;
  }
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  let timer;
  function toast(msg, isError) {
    const root = document.getElementById('toast-root');
    root.innerHTML = `<div class="toast ${isError ? 'error' : ''}" role="${isError ? 'alert' : 'status'}"><span>${esc(msg)}</span><button type="button" aria-label="閉じる">×</button></div>`;
    root.querySelector('button').onclick = () => { root.innerHTML = ''; };
    clearTimeout(timer);
    if (!isError) timer = setTimeout(() => { root.innerHTML = ''; }, 3000);
  }
  function confirmDlg(text, yes = 'はい') {
    const d = document.getElementById('confirm');
    document.getElementById('confirm-text').textContent = text;
    document.getElementById('confirm-yes').textContent = yes;
    d.returnValue = '';
    d.showModal();
    return new Promise(res => d.addEventListener('close', () => res(d.returnValue === 'yes'), { once: true }));
  }
  function busy(btn, on) {
    if (!btn) return;
    btn.setAttribute('aria-busy', on ? 'true' : 'false');
    btn.disabled = !!on;
  }
  return { api, esc, toast, confirm: confirmDlg, busy };
})();
