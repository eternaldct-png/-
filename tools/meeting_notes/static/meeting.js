// 会議の詳細
(function () {
  "use strict";
  const { api, toast, withLoading, toLocalInput, localInputToUTC } = window.MN;
  const $ = (id) => document.getElementById(id);
  const root = $("meeting");
  const id = root.dataset.id;
  const on = (elId, ev, fn) => { const el = $(elId); if (el) el.addEventListener(ev, fn); };

  // ── 処理中は状態を見に行く ──
  const labels = { queued: "順番待ち…", transcribing: "文字起こし中…", summarizing: "要点とやることを書き留めています…" };
  if (labels[root.dataset.status]) {
    const poll = async () => {
      try {
        const s = await api("GET", `/api/meetings/${id}/status`);
        if (!labels[s.status]) { notifyDone(s.status); setTimeout(() => location.reload(), 300); return; }
        $("progress-label").textContent = labels[s.status];
        $("progress-detail").textContent = s.status === "transcribing" && s.total_sec
          ? `（${Math.floor(s.done_sec / 60)}分 / ${Math.ceil(s.total_sec / 60)}分）` : "";
      } catch (e) { /* 一時的な失敗は次で取り直す */ }
      setTimeout(poll, 2000);
    };
    setTimeout(poll, 1500);
  }

  // 終わったら・失敗したらデスクトップ通知（不満: 失敗に会議の後で気づく）
  function notifyDone(status) {
    if (!("Notification" in window) || Notification.permission !== "granted" || !document.hidden) return;
    const title = document.getElementById("title-view").textContent.trim();
    new Notification(status === "failed" ? "⚠ キキトメ: 書き留められませんでした（録音は残っています）" : "✅ キキトメ: 書き留めました", { body: title });
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
  document.querySelectorAll(".tline .t[data-t], .t-jump[data-t]").forEach((b) => b.addEventListener("click", () => {
    if (!player || b.dataset.t === "") { if (!player) toast("録音が無いので再生できません", "error"); return; }
    player.currentTime = Math.max(0, parseFloat(b.dataset.t) - 1);
    player.play();
  }));

  // ── 1行ずつ話者を直す（不満: 話者の取り違え） ──
  document.querySelectorAll(".who-btn").forEach((b) => b.addEventListener("click", () => {
    if (b.parentElement.querySelector("input")) return;
    const input = Object.assign(document.createElement("input"), { type: "text", value: b.dataset.speaker, maxLength: 40 });
    input.setAttribute("list", "people-all");
    input.setAttribute("aria-label", "話者の名前（Enter で保存、Esc でやめる）");
    input.style.maxWidth = "14em";
    b.hidden = true;
    b.after(input);
    input.focus(); input.select();
    let done = false;
    const close = () => { done = true; input.remove(); b.hidden = false; b.focus(); };
    const save = async () => {
      if (done) return;
      const v = input.value.trim();
      if (v === b.dataset.speaker) { close(); return; }
      done = true;
      try {
        await api("POST", `/api/meetings/${id}/segments/${b.dataset.i}`, { speaker: v });
        b.dataset.speaker = v; b.textContent = v || "＋ 話者を付ける"; b.classList.toggle("empty", !v);
        const g = b.parentElement.querySelector(".badge-guess"); if (g) g.remove();
        input.remove(); b.hidden = false; b.focus();
        toast("話者を直しました");
      } catch (e) { done = false; toast(e.message, "error"); }
    };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); save(); }
      if (e.key === "Escape") close();
    });
    input.addEventListener("blur", () => { if (!done) save(); });
  }));
  on("guess-btn", "click", (e) => {
    if (!confirm("参加者の名前から、話者が空の行に話者を推定して付けます（文字起こしを Claude に送ります）。よろしいですか？")) return;
    withLoading(e.currentTarget, async () => {
      const r = await api("POST", `/api/meetings/${id}/guess-speakers`);
      toast(`${r.guessed}行に推定の話者を付けました`);
      location.hash = "tab-transcript"; setTimeout(() => location.reload(), 600);
    });
  });
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
