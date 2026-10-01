"""作例集（persona/motion_config.yaml）を、ホームページ eternaldct.net の motion.html に反映する。

ホームページは静的サイト（eternaldct-png/ETERNAL- リポジトリの eternaldct-new-site/）。
このスクリプトは次の2つだけを行う:
  1. src/static/motion/ の動画・ポスター画像を <サイト>/assets/motion/ にコピーする
  2. <サイト>/motion.html の MOTION:FILTERS / MOTION:CARDS の目印の間を、作例の一覧で書き換える
ページの見た目（ヘッダー・フッター・説明文など）は motion.html を直接編集する。

使い方（このリポジトリのルートで）:
  python tools/motion_render/export_homepage.py ../ETERNALライバー事務所/eternaldct-new-site
その後、サイトの管理画面からいつもどおりサーバーに反映する。
"""
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import web_app  # noqa: E402

MEDIA_DIR = "assets/motion"
MARKERS = ("FILTERS", "CARDS")


def _e(value):
    return html.escape(str(value), quote=True)


def _text(value):
    return "<br>".join(_e(line) for line in str(value).split("\n"))


def site_media_url(url):
    """/static/motion/xxx.mp4 → assets/motion/xxx.mp4（外部URLはそのまま）"""
    if url.startswith("/static/motion/"):
        return f"{MEDIA_DIR}/{Path(url).name}"
    return url


def filters_html(works, indent="      "):
    cats = list(dict.fromkeys(w["category"] for w in works if w["category"]))
    if len(cats) < 2:
        return ""
    chips = [f'{indent}  <button type="button" class="mw-chip is-active" data-cat="" aria-pressed="true">すべて</button>']
    chips += [f'{indent}  <button type="button" class="mw-chip" data-cat="{_e(c)}" aria-pressed="false">{_e(c)}</button>'
              for c in cats]
    return "\n".join([f'{indent}<div class="mw-filters reveal" role="group" aria-label="カテゴリで絞り込み">', *chips, f"{indent}</div>"])


def card_html(work, indent="        "):
    video = site_media_url(work["video"]) if work["video"] else ""
    poster = site_media_url(work["poster"]) if work["poster"] else ""
    ratio = "mw-ar-" + work["aspect"].replace(":", "x")
    if video:
        inner = ('<video muted loop playsinline preload="none"'
                 + (f' poster="{_e(poster)}"' if poster else "")
                 + f' data-src="{_e(video)}"></video>')
    else:
        thumb = poster or f"https://i.ytimg.com/vi/{work['youtube']}/hqdefault.jpg"
        inner = f'<img src="{_e(thumb)}" alt="" loading="lazy" decoding="async">'

    body = []
    if work["category"]:
        body.append(f'<span class="mw-tag">{_e(work["category"])}</span>')
    body.append(f'<h3>{_e(work["title"])}</h3>')
    if work["description"]:
        body.append(f'<p class="mw-desc">{_text(work["description"])}</p>')
    meta = [(label, value) for label, value in (("尺", work["duration"]), ("用途", work["use"])) if value]
    if meta:
        body.append('<div class="mw-meta">' + "".join(f"<span><b>{_e(k)}</b>{_e(v)}</span>" for k, v in meta) + "</div>")

    return "\n".join([
        f'{indent}<article class="mw-card" data-cat="{_e(work["category"])}" data-aspect="{_e(work["aspect"])}"'
        f' data-video="{_e(video)}" data-poster="{_e(poster)}" data-youtube="{_e(work["youtube"])}">',
        f'{indent}  <button type="button" class="mw-media {ratio}" aria-label="「{_e(work["title"])}」を大きく再生">'
        f'{inner}<span class="mw-play" aria-hidden="true"></span></button>',
        f'{indent}  <div class="mw-body">{"".join(body)}</div>',
        f"{indent}</article>",
    ])


def cards_html(works, indent="      "):
    cards = "\n".join(card_html(w, indent + "  ") for w in works)
    return f'{indent}<div class="mw-grid reveal">\n{cards}\n{indent}</div>'


def replace_between(page, name, content):
    pattern = re.compile(rf"(<!-- MOTION:{name}:START -->\n)(.*?)([ \t]*<!-- MOTION:{name}:END -->)", re.S)
    if not pattern.search(page):
        raise ValueError(f"motion.html に <!-- MOTION:{name}:START --> / END の目印が見つかりません")
    body = f"{content}\n" if content else ""
    return pattern.sub(lambda m: m.group(1) + body + m.group(3), page, count=1)


def export(site_dir):
    site_dir = Path(site_dir)
    page_path = site_dir / "motion.html"
    if not page_path.is_file():
        raise FileNotFoundError(f"{page_path} がありません（サイトのフォルダを指定してください）")

    _, works = web_app._load_motion_config()
    works = [w for w in works if not w["placeholder"]]

    media_dir = site_dir / MEDIA_DIR
    media_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for w in works:
        for key in ("video", "poster"):
            if w[key].startswith("/static/motion/"):
                src = ROOT / "src" / w[key].lstrip("/")
                dst = media_dir / src.name
                if not dst.exists() or dst.read_bytes() != src.read_bytes():
                    shutil.copy2(src, dst)
                    copied += 1

    page = page_path.read_text(encoding="utf-8")
    page = replace_between(page, "FILTERS", filters_html(works))
    page = replace_between(page, "CARDS", cards_html(works))
    page_path.write_text(page, encoding="utf-8")
    return {"works": len(works), "copied": copied}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    result = export(argv[0])
    print(f"motion.html を更新しました（作例 {result['works']} 本 / コピーしたファイル {result['copied']} 個）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
