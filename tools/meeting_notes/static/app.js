// 全画面で使う小さな道具。
(function () {
  "use strict";

  // 書き換える API は必ずこのヘッダーを付ける（サーバー側で他サイトからの送信を断るため）
  async function api(method, url, body) {
    const opts = { method, headers: { "X-Meeting-Notes": "1" } };
    if (body instanceof FormData) {
      opts.body = body;
    } else if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      throw new Error("アプリにつながりません。ターミナルでアプリが動いているか確認してください。");
    }
    let data = {};
    try { data = await res.json(); } catch (e) { /* JSON 以外 */ }
    if (!res.ok) throw new Error(data.error || `エラーが起きました（${res.status}）`);
    return data;
  }

  function toast(message, kind) {
    const box = document.getElementById("toast");
    const item = document.createElement("div");
    item.className = "t-item" + (kind === "error" ? " t-error" : "");
    item.setAttribute("role", kind === "error" ? "alert" : "status");
    const span = document.createElement("span");
    span.textContent = message;
    item.appendChild(span);
    if (kind === "error") {
      const close = document.createElement("button");
      close.type = "button";
      close.textContent = "閉じる";
      close.onclick = () => item.remove();
      item.appendChild(close);
    } else {
      setTimeout(() => item.remove(), 3000);
    }
    box.replaceChildren(item);
  }

  async function withLoading(btn, fn) {
    if (btn) { btn.classList.add("is-loading"); btn.setAttribute("aria-busy", "true"); btn.disabled = true; }
    try { return await fn(); }
    catch (e) { toast(e.message, "error"); return undefined; }
    finally { if (btn) { btn.classList.remove("is-loading"); btn.removeAttribute("aria-busy"); btn.disabled = false; } }
  }

  // UTC の日時を、このPCの時刻で表示する
  const fmt = new Intl.DateTimeFormat("ja-JP", { year: "numeric", month: "numeric", day: "numeric", weekday: "short", hour: "2-digit", minute: "2-digit" });
  function localizeTimes(root) {
    (root || document).querySelectorAll("time[data-utc]").forEach((el) => {
      const d = new Date(el.dataset.utc);
      if (!isNaN(d)) { el.textContent = fmt.format(d); el.dateTime = d.toISOString(); }
    });
  }

  // <input type=datetime-local> 用: Date → "YYYY-MM-DDTHH:MM"（ローカル）
  function toLocalInput(d) {
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }
  // datetime-local の値（ローカル）→ UTC の ISO 文字列
  function localInputToUTC(v) {
    if (!v) return "";
    const d = new Date(v);
    return isNaN(d) ? "" : d.toISOString();
  }

  // role=tablist のタブ（←→キー対応）
  function setupTabs(root) {
    (root || document).querySelectorAll("[role=tablist]").forEach((list) => {
      const tabs = [...list.querySelectorAll("[role=tab]")];
      function select(tab, focus) {
        tabs.forEach((t) => {
          const on = t === tab;
          t.setAttribute("aria-selected", on ? "true" : "false");
          t.tabIndex = on ? 0 : -1;
          const panel = document.getElementById(t.getAttribute("aria-controls"));
          if (panel) panel.hidden = !on;
        });
        if (focus) tab.focus();
        if (list.dataset.remember) { try { localStorage.setItem(list.dataset.remember, tab.id); } catch (e) {} }
        list.dispatchEvent(new CustomEvent("tabchange", { detail: tab.id }));
      }
      tabs.forEach((t, i) => {
        t.addEventListener("click", () => select(t));
        t.addEventListener("keydown", (e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
            select(n, true);
          }
        });
      });
      let start = tabs.find((t) => t.getAttribute("aria-selected") === "true") || tabs[0];
      if (location.hash) {
        const h = tabs.find((t) => "#" + t.id === location.hash);
        if (h) start = h;
      }
      if (start) select(start);
    });
  }

  document.addEventListener("DOMContentLoaded", () => { localizeTimes(); setupTabs(); });
  window.MN = { api, toast, withLoading, localizeTimes, toLocalInput, localInputToUTC, setupTabs };
})();
