"""ホームページ（eternaldct.net・WordPress）に、モーション動画の作例集を固定ページとして反映する。

Render の /motion を iframe で埋め込むのではなく、作例集の HTML / CSS / JS を
WordPress の固定ページ本文（カスタムHTMLブロック）に直接書き込む。
動画とポスター画像は WordPress のメディアライブラリにアップロードして使うので、
公開後は Render が止まっていてもページは表示される。

作例の中身は /motion と同じ persona/motion_config.yaml から作る（制作中の枠は載せない）。

使い方（リポジトリのルートで実行）:
  # ページのHTMLだけ作って確認する（WordPressには接続しない）
  python src/wordpress_motion.py build --out /tmp/motion_page.html

  # WordPress に反映する（動画のアップロード → 固定ページ作成/更新 → トップに入口を追加）
  WP_USER=... WP_APP_PASSWORD=... python src/wordpress_motion.py publish --add-to-top

環境変数:
  WP_URL           サイトのURL（省略時 https://eternaldct.net）
  WP_USER          WordPress のユーザー名（管理者）
  WP_APP_PASSWORD  そのユーザーの「アプリケーションパスワード」（ログインパスワードではない）
"""
import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import sys
from pathlib import Path

try:
    from src import web_app
except ImportError:  # python src/wordpress_motion.py で直接実行したとき
    import web_app

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "src"
DOCS_DIR = ROOT / "docs" / "wordpress_motion"
TOP_CARD_PATH = DOCS_DIR / "top_card.html"
EYECATCH_PATH = DOCS_DIR / "eyecatch.jpg"

DEFAULT_WP_URL = "https://eternaldct.net"
DEFAULT_SLUG = "motion"
DEFAULT_TITLE = "動画制作"
MEDIA_PREFIX = "edct-motion-"
# このスクリプトが書き込んだブロックの目印（既存ページを誤って上書きしないために使う）
PAGE_MARKER = 'id="edct-mw"'
CARD_MARKER = "edct-mcard"
TOP_CARD_DEFAULT_HREF = "https://eternaldct.net/motion/"
FRONT_WIDGET_AREAS = ("トップページ上部", "トップページ下部")

BLOCK_RE = re.compile(r"<!-- wp:html -->(?:(?!<!-- /wp:html -->).)*?<!-- /wp:html -->", re.S)


# ── ページHTMLの組み立て ─────────────────────────────────────

def load_works():
    """公開する作例（制作中の枠を除く）とページ設定を読み込む"""
    page_info, works = web_app._load_motion_config()
    return page_info, [w for w in works if not w["placeholder"]]


def local_media_path(url):
    """/static/... のURLをリポジトリ内のファイルパスに変換する（外部URLなら None）"""
    if not url.startswith("/static/"):
        return None
    path = (STATIC_DIR / url.lstrip("/")).resolve()
    if STATIC_DIR.resolve() not in path.parents:
        return None
    return path


def wp_filename(path):
    """アップロード時のファイル名。中身のハッシュを付けて、動画を作り直したら別ファイルとして上がるようにする"""
    digest = hashlib.sha1(Path(path).read_bytes()).hexdigest()[:8]
    return f"{MEDIA_PREFIX}{Path(path).stem}-{digest}{Path(path).suffix.lower()}"


def required_media(works):
    """アップロードが必要なローカルファイル（/static/... のURL → Path）"""
    files = {}
    for w in works:
        for key in ("video", "poster"):
            path = local_media_path(w[key]) if w[key] else None
            if path is None:
                continue
            if not path.is_file():
                raise FileNotFoundError(f"{w['id']} の {key} が見つかりません: {path}")
            files[w[key]] = path
    return files


def _e(value):
    # [ ] も文字参照にして、説明文の「[video]」などが WordPress のショートコードとして動かないようにする
    return html.escape(str(value), quote=True).replace("[", "&#91;").replace("]", "&#93;")


def _text(value):
    """改行を <br> にしたテキスト（空行を作らないようにする）"""
    return "<br>".join(_e(line) for line in str(value).split("\n"))


def _meta_html(work):
    items = [(label, value) for label, value in (("尺", work["duration"]), ("用途", work["use"])) if value]
    if not items:
        return ""
    spans = "".join(f"<span><b>{_e(label)}</b>{_e(value)}</span>" for label, value in items)
    return f'<div class="edct-mw__meta">{spans}</div>'


def _card_html(work, media_url):
    video = media_url(work["video"]) if work["video"] else ""
    poster = media_url(work["poster"]) if work["poster"] else ""
    youtube = work["youtube"]
    ratio = "edct-mw__ar-" + work["aspect"].replace(":", "x")
    label = f"「{work['title']}」を再生"

    if video:
        href = video
        inner = (
            '<video class="edct-mw__video" muted loop playsinline preload="none"'
            + (f' poster="{_e(poster)}"' if poster else "")
            + f' data-edct-src="{_e(video)}"></video>'
        )
    else:
        href = f"https://www.youtube.com/watch?v={youtube}"
        thumb = poster or f"https://i.ytimg.com/vi/{youtube}/hqdefault.jpg"
        inner = f'<img class="edct-mw__thumb" src="{_e(thumb)}" alt="" loading="lazy" decoding="async">'

    body = []
    if work["category"]:
        body.append(f'<span class="edct-mw__tag">{_e(work["category"])}</span>')
    body.append(f'<div class="edct-mw__title" role="heading" aria-level="3">{_e(work["title"])}</div>')
    if work["description"]:
        body.append(f'<p class="edct-mw__desc">{_text(work["description"])}</p>')
    meta = _meta_html(work)
    if meta:
        body.append(meta)

    return (
        f'<article class="edct-mw__card" data-cat="{_e(work["category"])}" data-aspect="{_e(work["aspect"])}"'
        f' data-video="{_e(video)}" data-poster="{_e(poster)}" data-youtube="{_e(youtube)}">\n'
        f'<a class="edct-mw__media {ratio}" href="{_e(href)}" target="_blank" rel="noopener" aria-label="{_e(label)}">'
        f'{inner}<span class="edct-mw__play" aria-hidden="true"></span></a>\n'
        f'<div class="edct-mw__body">{"".join(body)}</div>\n'
        "</article>"
    )


PAGE_CSS = """
#edct-mw, #edct-mw-modal {
  --edct-bg: #0d0b14; --edct-surface: #17141f; --edct-surface2: #221e2c;
  --edct-grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --edct-accent: #e879f9; --edct-text: #f4f2f8; --edct-muted: #a8a3b6; --edct-border: #2c2738;
}
#edct-mw, #edct-mw *, #edct-mw-modal, #edct-mw-modal * { box-sizing: border-box; }
#edct-mw {
  position: relative; overflow: hidden; margin: 0 0 2em; padding: 0; border-radius: 18px;
  background: var(--edct-bg); color: var(--edct-text); line-height: 1.6; text-align: left;
}
#edct-mw p, #edct-mw-modal p {
  margin: 0; padding: 0; border: 0; border-radius: 0; background: none; box-shadow: none;
  color: inherit; font-family: inherit; letter-spacing: normal; text-align: inherit; text-shadow: none;
}
#edct-mw a, #edct-mw-modal a { text-decoration: none; box-shadow: none; }
#edct-mw .edct-mw__hero {
  position: relative; overflow: hidden; text-align: center;
  padding: 56px 16px 40px; border-bottom: 1px solid var(--edct-border);
}
#edct-mw .edct-mw__hero::before {
  content: ""; position: absolute; inset: -40%; z-index: 0; opacity: 0.35; pointer-events: none;
  background: radial-gradient(circle at 30% 40%, #7c3aed 0, transparent 38%),
              radial-gradient(circle at 70% 60%, #ec4899 0, transparent 34%);
  animation: edct-mw-drift 14s ease-in-out infinite alternate;
}
@keyframes edct-mw-drift { from { transform: translate(-4%, -3%) rotate(0deg); } to { transform: translate(4%, 3%) rotate(8deg); } }
#edct-mw .edct-mw__hero > * { position: relative; z-index: 1; }
#edct-mw .edct-mw__badge {
  display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: 0.24em; line-height: 1.6;
  color: #fff; background: var(--edct-grad); padding: 5px 16px; border-radius: 999px; margin-bottom: 16px;
}
#edct-mw .edct-mw__heading { display: block; font-size: clamp(24px, 5vw, 38px); font-weight: 900; line-height: 1.35; color: #fff; }
#edct-mw .edct-mw__lead { font-size: 14px; color: var(--edct-muted); margin: 14px auto 0; max-width: 560px; line-height: 1.9; }
#edct-mw .edct-mw__cta {
  display: inline-block; margin-top: 24px; padding: 14px 28px; border-radius: 999px;
  background: var(--edct-grad); color: #fff !important; font-weight: 800; font-size: 15px; line-height: 1.4;
  box-shadow: 0 8px 26px rgba(217, 70, 239, 0.35); transition: transform 0.15s, opacity 0.15s;
}
#edct-mw .edct-mw__cta:hover { transform: translateY(-1px); }
#edct-mw .edct-mw__filters {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;
  padding: 24px 16px 4px; max-width: 1120px; margin: 0 auto;
}
#edct-mw .edct-mw__chip {
  margin: 0; border: 1px solid var(--edct-border); background: var(--edct-surface); color: var(--edct-muted);
  padding: 8px 16px; border-radius: 999px; font: inherit; font-size: 13px; font-weight: 700; line-height: 1.4;
  cursor: pointer; box-shadow: none; text-transform: none;
}
#edct-mw .edct-mw__chip.is-active { background: var(--edct-grad); color: #fff; border-color: transparent; }
#edct-mw .edct-mw__grid { max-width: 1120px; margin: 0 auto; padding: 18px 16px 8px; column-width: 300px; column-gap: 18px; }
#edct-mw .edct-mw__card {
  break-inside: avoid; -webkit-column-break-inside: avoid; margin: 0 0 18px; padding: 0;
  background: var(--edct-surface); border: 1px solid var(--edct-border); border-radius: 18px; overflow: hidden;
}
#edct-mw .edct-mw__card.is-hidden { display: none; }
#edct-mw .edct-mw__media {
  position: relative; display: block; width: 100%; margin: 0; padding: 0; border: 0; cursor: pointer;
  background: var(--edct-surface2); color: #fff; overflow: hidden;
}
#edct-mw .edct-mw__media video, #edct-mw .edct-mw__media img {
  position: absolute; inset: 0; width: 100%; height: 100%; max-width: none; margin: 0;
  object-fit: cover; display: block; border-radius: 0;
}
#edct-mw .edct-mw__ar-16x9 { aspect-ratio: 16 / 9; }
#edct-mw .edct-mw__ar-9x16 { aspect-ratio: 9 / 16; }
#edct-mw .edct-mw__ar-1x1 { aspect-ratio: 1 / 1; }
#edct-mw .edct-mw__ar-4x5 { aspect-ratio: 4 / 5; }
#edct-mw .edct-mw__play {
  position: absolute; right: 12px; bottom: 12px; width: 40px; height: 40px; border-radius: 50%;
  background: rgba(13, 11, 20, 0.72); transition: transform 0.15s, background 0.15s;
}
#edct-mw .edct-mw__play::after {
  content: ""; position: absolute; left: 50%; top: 50%; margin: -7px 0 0 -4px;
  border-style: solid; border-width: 7px 0 7px 12px; border-color: transparent transparent transparent #fff;
}
#edct-mw .edct-mw__media:hover .edct-mw__play, #edct-mw .edct-mw__media:focus-visible .edct-mw__play { transform: scale(1.1); background: #d946ef; }
#edct-mw .edct-mw__media:focus-visible { outline: 3px solid var(--edct-accent); outline-offset: -3px; }
#edct-mw .edct-mw__body, #edct-mw-modal .edct-mw-modal__body { padding: 16px 18px 18px; }
#edct-mw .edct-mw__tag, #edct-mw-modal .edct-mw__tag {
  display: inline-block; font-size: 11px; font-weight: 800; line-height: 1.6; color: var(--edct-accent);
  border: 1px solid rgba(232, 121, 249, 0.4); padding: 2px 10px; border-radius: 999px; margin-bottom: 10px;
}
#edct-mw .edct-mw__title { display: block; font-size: 16px; font-weight: 800; line-height: 1.5; color: var(--edct-text); }
#edct-mw .edct-mw__desc, #edct-mw-modal .edct-mw__desc { font-size: 13px; color: var(--edct-muted); line-height: 1.8; margin-top: 6px; }
#edct-mw .edct-mw__meta, #edct-mw-modal .edct-mw__meta {
  display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 12px; font-size: 12px; line-height: 1.6; color: var(--edct-muted);
}
#edct-mw .edct-mw__meta b, #edct-mw-modal .edct-mw__meta b { color: var(--edct-text); font-weight: 700; margin-right: 4px; }
#edct-mw .edct-mw__bottom { text-align: center; padding: 40px 16px 44px; }
#edct-mw .edct-mw__bottom-title { display: block; font-size: 20px; font-weight: 900; line-height: 1.5; color: #fff; }
#edct-mw .edct-mw__bottom-text { font-size: 13px; color: var(--edct-muted); margin-top: 8px; line-height: 1.8; }
#edct-mw .edct-mw__note { text-align: center; font-size: 12px; color: var(--edct-muted); padding: 8px 16px 28px; }
#edct-mw-modal {
  position: fixed; inset: 0; z-index: 100000; display: none; align-items: center; justify-content: center;
  padding: 16px; background: rgba(5, 4, 9, 0.9); color: var(--edct-text); line-height: 1.6; text-align: left;
}
#edct-mw-modal.is-open { display: flex; }
#edct-mw-modal .edct-mw-modal__inner {
  position: relative; width: 100%; max-height: 100%; overflow-y: auto;
  max-width: max(360px, min(960px, calc(68vh * var(--edct-r, 1.7778))));
  background: var(--edct-surface); border: 1px solid var(--edct-border); border-radius: 18px;
}
#edct-mw-modal .edct-mw-modal__media { margin: 0 auto; background: #000; width: min(100%, calc(68vh * var(--edct-r, 1.7778))); aspect-ratio: var(--edct-ar, 16 / 9); }
#edct-mw-modal .edct-mw-modal__media video, #edct-mw-modal .edct-mw-modal__media iframe {
  width: 100%; height: 100%; max-width: none; margin: 0; border: 0; display: block; background: #000;
}
#edct-mw-modal .edct-mw-modal__title { display: block; font-size: 18px; font-weight: 800; line-height: 1.5; color: var(--edct-text); }
#edct-mw-modal .edct-mw-modal__close {
  position: absolute; top: 10px; right: 10px; z-index: 2; width: 38px; height: 38px; margin: 0; padding: 0;
  border: 0; border-radius: 50%; background: rgba(13, 11, 20, 0.8); color: #fff;
  font: inherit; font-size: 22px; line-height: 38px; text-align: center; cursor: pointer; box-shadow: none;
}
html.edct-mw-lock, html.edct-mw-lock body { overflow: hidden; }
@media (max-width: 599px) {
  #edct-mw { border-radius: 12px; }
  #edct-mw .edct-mw__hero { padding: 44px 16px 32px; }
}
@media (prefers-reduced-motion: reduce) {
  #edct-mw .edct-mw__hero::before { animation: none; }
}
"""

PAGE_JS = """
(function () {
  "use strict";
  var root = document.getElementById("edct-mw");
  var modal = document.getElementById("edct-mw-modal");
  if (!root || !modal || root.getAttribute("data-ready") === "1") return;
  root.setAttribute("data-ready", "1");
  // テーマ側の transform などの影響を受けないよう、拡大表示は body 直下に移す
  document.body.appendChild(modal);

  var media = modal.querySelector(".edct-mw-modal__media");
  var closeBtn = modal.querySelector(".edct-mw-modal__close");
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var visible = new Set();
  var lastFocus = null;

  function isOpen() { return modal.classList.contains("is-open"); }
  function play(video) { var p = video.play(); if (p && p.catch) p.catch(function () {}); }

  // 画面内に入った動画だけ読み込んで無音ループ再生し、画面外に出たら止める（通信量とバッテリー対策）
  var observer = ("IntersectionObserver" in window && !reduceMotion) ? new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      var video = entry.target;
      if (entry.isIntersecting) {
        visible.add(video);
        if (!video.getAttribute("src")) video.src = video.getAttribute("data-edct-src");
        if (!isOpen()) play(video);
      } else {
        visible.delete(video);
        video.pause();
      }
    });
  }, { threshold: 0.35 }) : null;

  root.querySelectorAll(".edct-mw__video").forEach(function (video) {
    video.muted = true;
    if (observer) observer.observe(video);
  });

  var chips = root.querySelectorAll(".edct-mw__chip");
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var cat = chip.getAttribute("data-cat");
      chips.forEach(function (c) {
        c.classList.toggle("is-active", c === chip);
        c.setAttribute("aria-pressed", c === chip ? "true" : "false");
      });
      root.querySelectorAll(".edct-mw__card").forEach(function (card) {
        card.classList.toggle("is-hidden", cat !== "" && card.getAttribute("data-cat") !== cat);
      });
    });
  });

  function openModal(card, trigger) {
    lastFocus = trigger;
    var parts = (card.getAttribute("data-aspect") || "16:9").split(":");
    var w = Number(parts.shift()) || 16;
    var h = Number(parts.shift()) || 9;
    var inner = modal.querySelector(".edct-mw-modal__inner");
    inner.style.setProperty("--edct-ar", w + " / " + h);
    inner.style.setProperty("--edct-r", String(w / h));

    media.textContent = "";
    var src = card.getAttribute("data-video");
    var poster = card.getAttribute("data-poster");
    if (src) {
      var video = document.createElement("video");
      video.controls = true; video.autoplay = true; video.loop = true; video.playsInline = true;
      video.setAttribute("playsinline", "");
      if (poster) video.poster = poster;
      video.src = src;
      media.appendChild(video);
    } else {
      var iframe = document.createElement("iframe");
      iframe.src = "https://www.youtube-nocookie.com/embed/" + card.getAttribute("data-youtube") + "?autoplay=1&rel=0&playsinline=1";
      iframe.title = card.querySelector(".edct-mw__title").textContent;
      iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      iframe.allowFullscreen = true;
      media.appendChild(iframe);
    }

    var body = modal.querySelector(".edct-mw-modal__body");
    body.textContent = "";
    var tag = card.querySelector(".edct-mw__tag");
    if (tag) body.appendChild(tag.cloneNode(true));
    var title = document.createElement("div");
    title.className = "edct-mw-modal__title";
    title.id = "edct-mw-modal-title";
    title.textContent = card.querySelector(".edct-mw__title").textContent;
    body.appendChild(title);
    ["edct-mw__desc", "edct-mw__meta"].forEach(function (cls) {
      var node = card.querySelector("." + cls);
      if (node) body.appendChild(node.cloneNode(true));
    });

    visible.forEach(function (v) { v.pause(); });
    document.documentElement.classList.add("edct-mw-lock");
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    closeBtn.focus();
  }

  function closeModal() {
    if (!isOpen()) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    media.textContent = "";
    document.documentElement.classList.remove("edct-mw-lock");
    visible.forEach(play);
    if (lastFocus) lastFocus.focus();
  }

  root.querySelectorAll(".edct-mw__media").forEach(function (link) {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      openModal(link.closest(".edct-mw__card"), link);
    });
  });
  closeBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });
})();
"""


def build_page_html(page_info, works, media_url=lambda url: url):
    """固定ページ本文に入れる HTML（style + 作例集 + script）を作る。

    WordPress の本文フィルタ（自動段落・ショートコード）の影響を受けないよう、
    空行を作らず、「[英字」の並び（ショートコードと誤認される）も出さない。
    見出しは h2/h3 タグを使わず role="heading" にする（SWELL などの「目次の自動挿入」「見出し前の広告」が
    作例集の中に差し込まれないようにするため）。
    """
    cats = list(dict.fromkeys(w["category"] for w in works if w["category"]))
    contact_url = page_info.get("contact_url") or ""
    contact_label = page_info.get("contact_label") or "制作について相談する"

    parts = ['<div class="edct-mw" id="edct-mw">']
    hero = [
        '<div class="edct-mw__hero">',
        '<span class="edct-mw__badge">MOTION WORKS</span>',
        f'<div class="edct-mw__heading" role="heading" aria-level="2">{_e(page_info["title"])}</div>',
    ]
    if page_info.get("lead"):
        hero.append(f'<p class="edct-mw__lead">{_text(page_info["lead"])}</p>')
    if contact_url:
        hero.append(f'<a class="edct-mw__cta" href="{_e(contact_url)}" target="_blank" rel="noopener">{_e(contact_label)}</a>')
    hero.append("</div>")
    parts.extend(hero)

    if len(cats) >= 2:
        chips = ['<div class="edct-mw__filters" role="group" aria-label="カテゴリで絞り込み">',
                 '<button type="button" class="edct-mw__chip is-active" data-cat="" aria-pressed="true">すべて</button>']
        chips += [f'<button type="button" class="edct-mw__chip" data-cat="{_e(c)}" aria-pressed="false">{_e(c)}</button>' for c in cats]
        chips.append("</div>")
        parts.extend(chips)

    parts.append('<div class="edct-mw__grid">')
    parts.extend(_card_html(w, media_url) for w in works)
    parts.append("</div>")

    if contact_url:
        parts += [
            '<div class="edct-mw__bottom">',
            '<span class="edct-mw__bottom-title">「こんな動画がほしい」を、かたちに。</span>',
            '<p class="edct-mw__bottom-text">用途・尺・ご予算がざっくりでも大丈夫です。お気軽にご相談ください。</p>',
            f'<a class="edct-mw__cta" href="{_e(contact_url)}" target="_blank" rel="noopener">{_e(contact_label)}</a>',
            "</div>",
        ]
    else:
        parts.append('<p class="edct-mw__note">作例をタップすると、音ありの拡大表示で再生できます。</p>')

    parts += [
        '<div class="edct-mw-modal" id="edct-mw-modal" role="dialog" aria-modal="true" aria-labelledby="edct-mw-modal-title" aria-hidden="true">',
        '<div class="edct-mw-modal__inner">',
        '<button type="button" class="edct-mw-modal__close" aria-label="閉じる">&times;</button>',
        '<div class="edct-mw-modal__media"></div>',
        '<div class="edct-mw-modal__body"></div>',
        "</div>",
        "</div>",
        "</div>",
    ]
    body = "\n".join(parts)
    css = "\n".join(line for line in PAGE_CSS.strip().splitlines() if line.strip())
    js = "\n".join(line for line in PAGE_JS.strip().splitlines() if line.strip())
    return f"<style>\n{css}\n</style>\n{body}\n<script>\n{js}\n</script>"


def wrap_html_block(content):
    """カスタムHTMLブロックとして本文に入れる形にする"""
    return f"<!-- wp:html -->\n{content}\n<!-- /wp:html -->"


def build_top_card_html(page_link):
    """トップページ用のカード（docs/wordpress_motion/top_card.html）のリンク先を差し替えて返す"""
    card = TOP_CARD_PATH.read_text(encoding="utf-8")
    card = re.sub(r"^\s*<!--.*?-->\s*", "", card, count=1, flags=re.S)  # 先頭の説明コメントを外す
    return card.replace(f'href="{TOP_CARD_DEFAULT_HREF}"', f'href="{_e(page_link)}"').strip()


def upsert_card_block(raw, card_html, position="end"):
    """トップページ本文にカードのブロックを入れる。すでにあれば差し替える（重複させない）"""
    block = wrap_html_block(card_html)
    for match in BLOCK_RE.finditer(raw):
        if CARD_MARKER in match.group(0):
            return raw[:match.start()] + block + raw[match.end():]
    if not raw.strip():
        return block
    return f"{block}\n\n{raw}" if position == "start" else f"{raw.rstrip()}\n\n{block}\n"


# ── WordPress REST API ─────────────────────────────────────

class WordPressError(RuntimeError):
    pass


_HINTS = {
    401: "ユーザー名かアプリケーションパスワードが違うか、サーバーが認証ヘッダーを落としています"
         "（レンタルサーバーによっては .htaccess の設定が必要）。",
    403: "そのユーザーに権限がないか、サーバーの『国外IPアクセス制限』『REST API制限』で拒否されています"
         "（エックスサーバー等の WordPress セキュリティ設定を確認）。",
    404: "REST API が見つかりません。REST API を無効にするプラグインや、パーマリンク設定を確認してください。",
}


class WordPressClient:
    def __init__(self, base_url, user, app_password, session=None, timeout=120):
        import requests

        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.auth = (user, app_password)
        self.session.headers.setdefault("User-Agent", "ETERNALdct-motion-publisher/1.0")
        self.timeout = timeout
        self.pretty = True  # /wp-json/ が使えないサイトでは ?rest_route= に切り替える

    def _url(self, path):
        if self.pretty:
            return f"{self.base_url}/wp-json/wp/v2/{path}"
        return f"{self.base_url}/?rest_route=/wp/v2/{path}"

    def request(self, method, path, **kwargs):
        # ?rest_route= 形式でも、requests が params を「&」でつないでくれる
        resp = self.session.request(method, self._url(path), timeout=self.timeout, **kwargs)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("message", "")
            except ValueError:
                detail = resp.text[:200]
            hint = _HINTS.get(resp.status_code, "")
            raise WordPressError(f"{method} {path} → HTTP {resp.status_code}: {detail} {hint}".strip())
        try:
            return resp.json()
        except ValueError:
            raise WordPressError(f"{method} {path} → JSON ではない応答が返りました（REST API が使えない可能性）: {resp.text[:200]}")

    def check_login(self):
        """認証と権限を確認し、ユーザー情報を返す"""
        try:
            me = self.request("GET", "users/me", params={"context": "edit"})
        except WordPressError as e:
            if "HTTP 404" not in str(e) and "JSON ではない" not in str(e):
                raise
            self.pretty = False
            me = self.request("GET", "users/me", params={"context": "edit"})
        caps = me.get("capabilities") or {}
        missing = [c for c in ("upload_files", "edit_pages", "publish_pages") if not caps.get(c)]
        if missing:
            raise WordPressError(f"ユーザー {me.get('slug')} に必要な権限がありません: {', '.join(missing)}（管理者ユーザーを使ってください）")
        return me

    # メディア
    def list_our_media(self):
        """このスクリプトがアップロードしたメディア（タイトルが edct-motion- で始まるもの）を title → item で返す"""
        found, page = {}, 1
        while True:
            try:
                items = self.request("GET", "media", params={
                    "search": MEDIA_PREFIX.rstrip("-"), "per_page": 100, "page": page, "context": "edit",
                })
            except WordPressError:
                if page == 1:
                    raise
                return found  # ちょうど100件の倍数のとき、次のページは「範囲外」エラーになる
            for item in items:
                title = (item.get("title") or {}).get("raw", "")
                if title.startswith(MEDIA_PREFIX):
                    found[title] = item
            if len(items) < 100:
                return found
            page += 1

    def upload_media(self, path, filename):
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return self.request(
            "POST", "media",
            params={"title": filename},
            data=Path(path).read_bytes(),
            headers={"Content-Type": mime, "Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def delete_media(self, media_id):
        return self.request("DELETE", f"media/{media_id}", params={"force": "true"})

    # 固定ページ
    def find_page(self, slug):
        pages = self.request("GET", "pages", params={
            "slug": slug, "status": "publish,future,draft,pending,private", "context": "edit",
        })
        return pages[0] if pages else None

    def get_page(self, page_id):
        return self.request("GET", f"pages/{page_id}", params={"context": "edit"})

    def save_page(self, page_id, data):
        return self.request("POST", f"pages/{page_id}" if page_id else "pages", json=data)

    # トップページ
    def get_settings(self):
        return self.request("GET", "settings")

    def list_sidebars(self):
        return self.request("GET", "sidebars", params={"context": "edit"})

    def list_widgets(self, sidebar_id=None):
        params = {"context": "edit"}
        if sidebar_id:
            params["sidebar"] = sidebar_id
        return self.request("GET", "widgets", params=params)

    def save_widget(self, widget_id, data):
        return self.request("POST", f"widgets/{widget_id}" if widget_id else "widgets", json=data)


def sync_media(client, files, log=print, prune=False):
    """ローカルの動画・画像をメディアライブラリに上げ（同じ中身のものは再利用）、{ローカルパス: URL} を返す"""
    existing = client.list_our_media()
    urls = {}
    wanted = set()
    for path in files:
        name = wp_filename(path)
        wanted.add(name)
        item = existing.get(name)
        if item:
            log(f"  - 既存を使用: {name}")
        else:
            log(f"  - アップロード: {name}")
            item = client.upload_media(path, name)
            existing[name] = item
        urls[str(path)] = {"url": item["source_url"], "id": item["id"]}
    if prune:
        for name, item in existing.items():
            if name not in wanted:
                log(f"  - 古いファイルを削除: {name}")
                client.delete_media(item["id"])
    return urls


def add_card_to_front(client, card_html, position="end", log=print):
    """トップページにカードを入れる。トップが固定ページなら本文に、最新の投稿ならウィジェットに追加する"""
    settings = client.get_settings()
    if settings.get("show_on_front") == "page" and settings.get("page_on_front"):
        front = client.get_page(settings["page_on_front"])
        raw = (front.get("content") or {}).get("raw", "")
        updated = upsert_card_block(raw, card_html, position)
        if updated == raw:
            log("  - トップページはすでに最新です")
        else:
            client.save_page(front["id"], {"content": updated})
            log(f"  - トップページ（固定ページ「{(front.get('title') or {}).get('raw', '')}」）にカードを追加/更新しました")
        return {"type": "page", "id": front["id"]}

    sidebars = client.list_sidebars()
    target = None
    for name in FRONT_WIDGET_AREAS:
        target = next((s for s in sidebars if name in (s.get("name") or "")), None)
        if target:
            break
    if not target:
        names = "、".join(s.get("name", "") for s in sidebars) or "なし"
        raise WordPressError(f"トップページ用のウィジェットエリアが見つかりません（あるエリア: {names}）。"
                             "トップの固定ページにカードを手で貼ってください（docs/wordpress_motion/top_card.html）。")
    instance = {"raw": {"title": "", "content": card_html}}
    # 以前のカードが別のエリア（使用停止中のウィジェットなど）に移っていても、作り直さずに戻して使う
    for widget in client.list_widgets():
        content = ((widget.get("instance") or {}).get("raw") or {}).get("content", "")
        if widget.get("id_base") == "custom_html" and CARD_MARKER in content:
            client.save_widget(widget["id"], {"sidebar": target["id"], "instance": instance})
            log(f"  - ウィジェットエリア「{target['name']}」のカードを更新しました")
            return {"type": "widget", "id": widget["id"]}
    created = client.save_widget(None, {"id_base": "custom_html", "sidebar": target["id"], "instance": instance})
    # WordPress は作成直後のレスポンス処理でウィジェットを「使用停止中」に移してしまうことがあるため、
    # もう一度エリアを指定して確定させる
    client.save_widget(created["id"], {"sidebar": target["id"]})
    log(f"  - ウィジェットエリア「{target['name']}」にカードを追加しました")
    return {"type": "widget", "id": created["id"]}


def publish(client, *, slug=DEFAULT_SLUG, title=DEFAULT_TITLE, status=None, add_to_top=False,
            top_position="end", prune=False, force=False, update_only=False, log=print):
    me = client.check_login()
    log(f"WordPress にログインしました（ユーザー: {me.get('slug')}）")

    page_info, works = load_works()
    if not works:
        raise WordPressError("公開できる作例がありません（persona/motion_config.yaml を確認してください）")
    files = required_media(works)

    page = client.find_page(slug)
    if not page and update_only:
        log(f"スラッグ「{slug}」の固定ページがまだないため、何もしませんでした（初回は手動で実行してください）")
        return {"page_id": None, "link": None, "status": None, "top": None}
    if page and PAGE_MARKER not in (page.get("content") or {}).get("raw", "") and not force:
        raise WordPressError(f"スラッグ「{slug}」の固定ページがすでにあり、このスクリプトで作ったものではありません。"
                             "上書きしてよければ --force を付けて実行してください。")

    log(f"動画・画像をメディアライブラリに反映します（{len(files)} ファイル + アイキャッチ）")
    uploads = sync_media(client, list(files.values()) + [EYECATCH_PATH], log=log, prune=prune)
    url_map = {url: uploads[str(path)]["url"] for url, path in files.items()}
    content = wrap_html_block(build_page_html(page_info, works, lambda url: url_map.get(url, url)))

    data = {"content": content, "featured_media": uploads[str(EYECATCH_PATH)]["id"]}
    if page:
        if status:
            data["status"] = status
        page = client.save_page(page["id"], data)
        log(f"固定ページを更新しました: {page.get('link')}（状態: {page.get('status')}）")
    else:
        data.update({"title": title, "slug": slug, "status": status or "publish"})
        page = client.save_page(None, data)
        log(f"固定ページを作成しました: {page.get('link')}（状態: {page.get('status')}）")

    result = {"page_id": page["id"], "link": page.get("link"), "status": page.get("status"), "top": None}
    if add_to_top:
        if page.get("status") != "publish":
            log("※ ページが公開状態ではないため、トップページへの追加はスキップしました（リンク切れ防止）")
        else:
            log("トップページに入口のカードを追加します")
            result["top"] = add_card_to_front(client, build_top_card_html(page["link"]), top_position, log=log)
    return result


# ── CLI ─────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="作例集をホームページ（WordPress）の固定ページとして反映する")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="ページのHTMLを作ってファイルに書き出す（WordPressには接続しない）")
    b.add_argument("--out", required=True, help="書き出し先")
    b.add_argument("--media-base", default="", help="動画・画像のURLの先頭（省略時は /static/motion/... のまま）")

    p = sub.add_parser("publish", help="WordPress に反映する")
    p.add_argument("--slug", default=DEFAULT_SLUG)
    p.add_argument("--title", default=DEFAULT_TITLE, help="新しく作るときのページタイトル")
    p.add_argument("--status", choices=["publish", "draft"], default=None,
                   help="ページの状態（省略時: 新規は公開、更新は今の状態のまま）")
    p.add_argument("--add-to-top", action="store_true", help="トップページに入口のカードを追加する")
    p.add_argument("--top-position", choices=["end", "start"], default="end",
                   help="トップが固定ページのとき、カードを本文の最後/最初のどちらに入れるか")
    p.add_argument("--prune", action="store_true", help="このスクリプトが以前上げた、今は使っていない動画・画像を削除する")
    p.add_argument("--force", action="store_true", help="同じスラッグの既存ページを上書きする")
    p.add_argument("--update-only", action="store_true", help="ページがすでにあるときだけ更新する（自動同期用）")

    args = parser.parse_args(argv)

    if args.command == "build":
        page_info, works = load_works()
        files = required_media(works)
        if args.media_base:
            base = args.media_base.rstrip("/") + "/"
            media_url = lambda url: base + wp_filename(files[url]) if url in files else url  # noqa: E731
        else:
            media_url = lambda url: url  # noqa: E731
        Path(args.out).write_text(build_page_html(page_info, works, media_url), encoding="utf-8")
        print(f"{args.out} に書き出しました（作例 {len(works)} 本）")
        return 0

    user = os.environ.get("WP_USER", "").strip()
    password = os.environ.get("WP_APP_PASSWORD", "").strip()
    if not user or not password:
        print("WP_USER と WP_APP_PASSWORD を設定してください（WordPress のアプリケーションパスワード）", file=sys.stderr)
        return 2
    client = WordPressClient(os.environ.get("WP_URL", "").strip() or DEFAULT_WP_URL, user, password)
    try:
        result = publish(client, slug=args.slug, title=args.title, status=args.status, add_to_top=args.add_to_top,
                         top_position=args.top_position, prune=args.prune, force=args.force,
                         update_only=args.update_only)
    except (WordPressError, FileNotFoundError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
