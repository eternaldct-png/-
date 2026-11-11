// やることの完了・削除（会議の詳細と「やること」一覧で共通）
(function () {
  "use strict";
  const { api, toast } = window.MN;
  function updateCount() {
    const el = document.getElementById("open-count");
    if (el) el.textContent = document.querySelectorAll(".action-row:not(.done)").length;
  }
  document.addEventListener("change", async (e) => {
    const box = e.target.closest('[data-action="toggle"]');
    if (!box) return;
    const row = box.closest(".action-row");
    const done = box.checked;
    row.classList.toggle("done", done);
    updateCount();
    try {
      await api("PATCH", `/api/actions/${row.dataset.id}`, { done });
      if (row.closest("[data-hide-done]") && done) setTimeout(() => row.remove(), 600);
    } catch (err) {
      box.checked = !done; row.classList.toggle("done", !done); updateCount();
      toast(err.message, "error");
    }
  });
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest('[data-action="delete"]');
    if (!btn) return;
    const row = btn.closest(".action-row");
    if (!confirm("このやることを削除しますか？")) return;
    try {
      await api("DELETE", `/api/actions/${row.dataset.id}`);
      row.remove(); updateCount(); toast("削除しました");
    } catch (err) { toast(err.message, "error"); }
  });
})();
