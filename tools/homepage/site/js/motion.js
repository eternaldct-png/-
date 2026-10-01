/* ============================================================
   MOTION WORKS — 動画制作の作例集（motion.html と トップの紹介枠）
   ・画面に入った動画だけ読み込んで無音ループ再生し、画面外では止める（通信量対策）
   ・カテゴリで絞り込み
   ・作例をタップすると拡大表示（コントロール付き）
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const modal = document.getElementById("mw-modal");
  const visible = new Set();
  const isOpen = () => !!modal && modal.classList.contains("is-open");
  const play = video => { const p = video.play(); if (p && p.catch) p.catch(() => {}); };

  /* ---------- 画面内の動画だけ再生 ---------- */
  const videoIO = ("IntersectionObserver" in window && !reduceMotion) ? new IntersectionObserver(entries => {
    entries.forEach(en => {
      const video = en.target;
      if (en.isIntersecting) {
        visible.add(video);
        if (!video.getAttribute("src")) video.src = video.dataset.src;
        if (!isOpen()) play(video);
      } else {
        visible.delete(video);
        video.pause();
      }
    });
  }, { threshold: 0.35 }) : null;

  document.querySelectorAll("video[data-src]").forEach(video => {
    video.muted = true;
    if (videoIO) videoIO.observe(video);
  });

  /* ---------- 絞り込み ---------- */
  const chips = document.querySelectorAll(".mw-chip");
  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      const cat = chip.dataset.cat || "";
      chips.forEach(c => {
        c.classList.toggle("is-active", c === chip);
        c.setAttribute("aria-pressed", c === chip ? "true" : "false");
      });
      document.querySelectorAll(".mw-card").forEach(card => {
        card.classList.toggle("is-hidden", cat !== "" && card.dataset.cat !== cat);
      });
    });
  });

  /* ---------- 拡大表示 ---------- */
  if (!modal) return;
  const media = modal.querySelector(".mw-modal-media");
  const body = modal.querySelector(".mw-modal-body");
  const closeBtn = modal.querySelector(".mw-modal-close");
  let lastFocus = null;

  const openModal = (card, trigger) => {
    lastFocus = trigger;
    const [w, h] = (card.dataset.aspect || "16:9").split(":").map(Number);
    const inner = modal.querySelector(".mw-modal-inner");
    inner.style.setProperty("--mw-ar", `${w || 16} / ${h || 9}`);
    inner.style.setProperty("--mw-r", String((w || 16) / (h || 9)));

    media.replaceChildren();
    if (card.dataset.video) {
      const video = document.createElement("video");
      video.controls = true; video.autoplay = true; video.loop = true; video.playsInline = true;
      video.setAttribute("playsinline", "");
      if (card.dataset.poster) video.poster = card.dataset.poster;
      video.src = card.dataset.video;
      media.appendChild(video);
    } else {
      const iframe = document.createElement("iframe");
      iframe.src = `https://www.youtube-nocookie.com/embed/${card.dataset.youtube}?autoplay=1&rel=0&playsinline=1`;
      iframe.title = card.querySelector("h3").textContent;
      iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      iframe.allowFullscreen = true;
      media.appendChild(iframe);
    }

    body.replaceChildren();
    const tag = card.querySelector(".mw-tag");
    if (tag) body.appendChild(tag.cloneNode(true));
    const title = document.createElement("div");
    title.className = "mw-modal-title";
    title.id = "mw-modal-title";
    title.textContent = card.querySelector("h3").textContent;
    body.appendChild(title);
    card.querySelectorAll(".mw-desc, .mw-meta").forEach(node => body.appendChild(node.cloneNode(true)));

    visible.forEach(v => v.pause());
    document.documentElement.classList.add("mw-lock");
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    closeBtn.focus();
  };

  const closeModal = () => {
    if (!isOpen()) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    media.replaceChildren();
    document.documentElement.classList.remove("mw-lock");
    visible.forEach(play);
    if (lastFocus) lastFocus.focus();
  };

  document.querySelectorAll(".mw-card .mw-media").forEach(btn => {
    btn.addEventListener("click", () => openModal(btn.closest(".mw-card"), btn));
  });
  closeBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
});
