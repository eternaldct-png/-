// 会議の詳細
(function () {
  "use strict";
  const { api, toast, withLoading, toLocalInput, localInputToUTC } = window.MN;
  const $ = (id) => document.getElementById(id);
  const root = $("meeting");
  const id = root.dataset.id;
  const on = (elId, ev, fn) => { const el = $(elId); if (el) el.addEventListener(ev, fn); };

  // ── 処理中は状態を見に行く ──
  const labels = { queued: "順番待ち…", transcribing: "文字起こし中…", summarizing: "AIがノートを書いています…" };
  if (labels[root.dataset.status]) {
    const poll = async () => {
      try {
        const s = await api("GET", `/api/meetings/${id}/status`);
        if (!labels[s.status]) { location.reload(); return; }
        $("progress-label").textContent = labels[s.status];
        $("progress-detail").textContent = s.status === "transcribing" && s.total_sec
          ? `（${Math.floor(s.done_sec / 60)}分 / ${Math.ceil(s.total_sec / 60)}分）` : "";
      } catch (e) { /* 一時的な失敗は次で取り直す */ }
      setTimeout(poll, 2000);
    };
    setTimeout(poll, 1500);
  }

  // ── 編集・削除 ──
  const form = $("edit-form");
  const startInput = form.elements.started_at;
  startInput.value = toLocalInput(new Date(startInput.dataset.utc));
  function toggleEdit(show) { form.hidden = !show; $("edit-btn").setAttribute("aria-expanded", String(show)); if (show) form.elements.title.focus(); }
  on("edit-btn", "click", () => toggleEdit(form.hidden));
  on("edit-cancel", "click", () => toggleEdit(false));
  on("edit-save", "click", (e) => withLoading(e.currentTarget, async () => {
    await api("PATCH", `/api/meetings/${id}`, {
      title: form.elements.title.value,
      started_at: localInputToUTC(startInput.value),
      tags: form.elements.tags.value,
      participants: form.elements.participants.value,
    });
    location.reload();
  }));
  on("delete-btn", "click", (e) => {
    if (!confirm("この会議を削除しますか？ノート・やること・文字起こし・録音ファイルがすべて消え、元に戻せません。")) return;
    withLoading(e.currentTarget, async () => { await api("DELETE", `/api/meetings/${id}`); location.href = "/"; });
  });

  on("retry-btn", "click", (e) => withLoading(e.currentTarget, async () => { await api("POST", `/api/meetings/${id}/retry`); location.reload(); }));
  on("regen-btn", "click", (e) => {
    if (!confirm("ノートを作り直しますか？今のノートは上書きされます（手で足したやること・完了の印は残ります）。")) return;
    withLoading(e.currentTarget, async () => { await api("POST", `/api/meetings/${id}/regenerate`); location.reload(); });
  });

  // ── Markdown をコピー ──
  on("copy-md", "click", (e) => withLoading(e.currentTarget, async () => {
    const res = await fetch(`/m/${id}/export.md`);
    const text = await res.text();
    await navigator.clipboard.writeText(text);
    toast("Markdown をコピーしました（Notion・Slack にそのまま貼れます）");
  }));

  // ── やることを追加 ──
  on("na-add", "click", (e) => {
    const text = $("na-text").value.trim();
    if (!text) { toast("やることを入れてください", "error"); $("na-text").focus(); return; }
    withLoading(e.currentTarget, async () => {
      await api("POST", "/api/actions", { meeting_id: id, text, owner: $("na-owner").value, due: $("na-due").value });
      location.hash = "tab-actions"; location.reload();
    });
  });
  on("na-text", "keydown", (e) => { if (e.key === "Enter" && !e.isComposing) $("na-add").click(); });

  // ── 文字起こし: 時刻で再生・検索・話者名 ──
  const player = $("player");
  document.querySelectorAll(".tline .t[data-t]").forEach((b) => b.addEventListener("click", () => {
    if (!player || b.dataset.t === "") return;
    player.currentTime = Math.max(0, parseFloat(b.dataset.t) - 1);
    player.play();
  }));
  const lines = [...document.querySelectorAll("#transcript .txt")];
  const originals = lines.map((l) => l.textContent);
  on("t-find", "input", (e) => {
    const q = e.target.value.trim();
    let hits = 0, first = null;
    lines.forEach((l, i) => {
      const t = originals[i];
      if (!q) { l.textContent = t; return; }
      const idx = t.toLowerCase().indexOf(q.toLowerCase());
      if (idx < 0) { l.textContent = t; return; }
      hits++;
      l.replaceChildren(document.createTextNode(t.slice(0, idx)), Object.assign(document.createElement("mark"), { textContent: t.slice(idx, idx + q.length) }), document.createTextNode(t.slice(idx + q.length)));
      first = first || l;
    });
    $("t-count").textContent = q ? `${hits}件` : "";
    if (first) first.scrollIntoView({ block: "center", behavior: "smooth" });
  });
  on("sp-save", "click", (e) => {
    const to = $("sp-to").value.trim();
    if (!to) { toast("新しい名前を入れてください", "error"); return; }
    withLoading(e.currentTarget, async () => {
      await api("POST", `/api/meetings/${id}/speakers`, { from: $("sp-from").value, to });
      location.hash = "tab-transcript"; location.reload();
    });
  });

  // ── この会議に質問 ──
  function addMsg(role, text) {
    const d = document.createElement("div");
    d.className = `msg msg-${role}`; d.textContent = text;
    $("chat").appendChild(d); d.scrollIntoView({ block: "nearest" });
    const empty = $("chat-empty"); if (empty) empty.remove();
    return d;
  }
  async function ask(btn) {
    const q = $("question").value.trim();
    if (!q) { toast("質問を入れてください", "error"); return; }
    addMsg("user", q);
    $("question").value = "";
    const thinking = addMsg("assistant", "考えています…");
    const data = await withLoading(btn, () => api("POST", `/api/meetings/${id}/ask`, { question: q }));
    if (data) thinking.textContent = data.answer; else { thinking.remove(); $("question").value = q; }
  }
  on("ask-btn", "click", (e) => ask(e.currentTarget));
  on("question", "keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask($("ask-btn")); });
  on("chat-clear", "click", (e) => {
    if (!confirm("この会議への質問の履歴を消しますか？")) return;
    withLoading(e.currentTarget, async () => { await api("DELETE", `/api/meetings/${id}/chat`); location.hash = "tab-ask"; location.reload(); });
  });
})();
