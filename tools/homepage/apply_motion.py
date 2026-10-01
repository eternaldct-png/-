"""ホームページ（eternaldct.net）に「動画制作」ページを追加する（Mac で1回実行するだけ）。

Mac の「ターミナル」に次の1行を貼って Enter:
  curl -fsSL https://raw.githubusercontent.com/eternaldct-png/-/refs/heads/claude/nifty-galileo-9f3t1l/tools/homepage/apply_motion.py | python3 -

やること（いまの Mac のサイトのファイルに「足す」だけ。消したり置き換えたりはしない）:
  1. motion.html（動画制作・作例集）を作る。ヘッダー・フッター・計測タグは works.html と同じものを使う
  2. css/motion.css・js/motion.js・assets/motion/（動画とポスター）を置く
  3. 全ページのメニューに「08 MOTION 動画制作」、フッターに「動画制作」を足す
  4. トップページの WORKS の下に「こんな動画、つくれます。」の枠を足す
変更する前のファイルは ETERNALライバー事務所/_backup_motion_日時/ に保存する。何度実行しても同じ結果になる。
終わったら、いつもどおり管理画面の「サイトに直接反映」でサーバーに送る。

サイトのフォルダが別の場所なら: python3 apply_motion.py <eternaldct-new-site のパス>
"""
import datetime
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

REF = "refs/heads/claude/nifty-galileo-9f3t1l"
RAW = f"https://raw.githubusercontent.com/eternaldct-png/-/{REF}/"
def _local_root():
    """このファイルがリポジトリ内にあるとき（python3 tools/homepage/apply_motion.py）は、手元のファイルを使う。
    curl ... | python3 - のとき（__file__ が無い／"<stdin>"）は None を返し、GitHub からダウンロードする"""
    name = globals().get("__file__")
    if not name or name.startswith("<"):
        return None
    for parent in Path(name).resolve().parents:
        if (parent / "tools/homepage/site/motion-main.html").is_file():
            return parent
    return None


LOCAL_ROOT = _local_root()

SITE_FRAGMENTS = "tools/homepage/site/"
MEDIA_SRC = "src/static/motion/"

TITLE = "動画制作・作例集｜ETERNALd.c.t（エターナルディクト）"
DESCRIPTION = ("ETERNALd.c.t（エターナルディクト）のモーション動画制作の作例集。配信の待機画面やギフト演出、"
               "リリックモーション、SNS縦型広告、店舗サイネージ、会社紹介まで、用途別の作例をご覧いただけます。")
OG_DESCRIPTION = "配信・音楽・SNS広告・店舗や企業のPRまで。ETERNALd.c.tが制作するモーション動画の作例集です。"
PAGE_URL = "https://eternaldct.net/motion.html"
OG_IMAGE = "https://eternaldct.net/assets/motion/ogp.jpg"

MENU_RE = re.compile(
    r'(?P<i>[ \t]*)<li><a href="works\.html"><span class="num">08</span>WORKS<span class="jp">実績</span></a></li>\n'
    r'[ \t]*<li><a href="contact\.html"><span class="num">09</span>CONTACT<span class="jp">お問い合わせ</span></a></li>'
)
MENU_NEW = (
    '{i}<li><a href="motion.html"><span class="num">08</span>MOTION<span class="jp">動画制作</span></a></li>\n'
    '{i}<li><a href="works.html"><span class="num">09</span>WORKS<span class="jp">実績</span></a></li>\n'
    '{i}<li><a href="contact.html" style="transition-delay:0.5s;"><span class="num">10</span>CONTACT'
    '<span class="jp">お問い合わせ</span></a></li>'
)
FOOTER_RE = re.compile(r'(?P<i>[ \t]*)<a href="music\.html">音楽制作</a>\n')
FOOTER_LINK = '<a href="motion.html">動画制作</a>'
STYLE_RE = re.compile(r'<link rel="stylesheet" href="css/style\.css[^"]*">')
MAINJS_RE = re.compile(r'<script src="js/main\.js[^"]*"></script>')


class ApplyError(RuntimeError):
    pass


def find_site(argv):
    if argv:
        return Path(argv[0]).expanduser()
    home = Path.home()
    # Mac のファイル名は濁点が分かれて保存されることがあるので、正規化して探す
    for child in home.iterdir():
        if unicodedata.normalize("NFC", child.name) == "ETERNALライバー事務所":
            return child / "eternaldct-new-site"
    return home / "ETERNALライバー事務所" / "eternaldct-new-site"


def fetch(rel):
    """リポジトリのファイルを取り出す（手元にあればそれを、なければ GitHub からダウンロード）"""
    if LOCAL_ROOT:
        return (LOCAL_ROOT / rel).read_bytes()
    with tempfile.NamedTemporaryFile() as tmp:
        result = subprocess.run(["curl", "-fsSL", "--retry", "3", "-o", tmp.name, RAW + rel],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise ApplyError(f"ダウンロードに失敗しました: {rel}（{result.stderr.strip()}）")
        return Path(tmp.name).read_bytes()


class Site:
    def __init__(self, root):
        self.root = root
        self.backup = None
        self.changed = []

    def _backup(self, path):
        if not path.exists():
            return
        if self.backup is None:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.backup = self.root.parent / f"_backup_motion_{stamp}"
        dst = self.backup / path.relative_to(self.root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)

    def write(self, rel, data):
        path = self.root / rel
        if isinstance(data, str):
            data = data.encode("utf-8")
        if path.exists() and path.read_bytes() == data:
            return
        self._backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.changed.append(rel)

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")


def sub_once(pattern, repl, text, what):
    new, n = re.subn(pattern, repl, text, count=1, flags=re.S)
    if n != 1:
        raise ApplyError(f"works.html の中に {what} が見つからないため、motion.html を作れませんでした")
    return new


def patch_menu_footer(html):
    if 'class="num">08</span>MOTION' not in html:
        html = MENU_RE.sub(lambda m: MENU_NEW.format(i=m.group("i")), html, count=1)
    if FOOTER_LINK not in html:
        html = FOOTER_RE.sub(lambda m: m.group(0) + f'{m.group("i")}{FOOTER_LINK}\n', html, count=1)
    return html


def build_motion_page(template, main_html, modal_html):
    """works.html をひな形にして motion.html を作る（計測タグ・ヘッダー・フッターはそのまま）"""
    html = template
    html = sub_once(r"<title>[^<]*</title>", f"<title>{TITLE}</title>", html, "<title>")
    html = sub_once(r'<meta name="description" content="[^"]*">',
                    f'<meta name="description" content="{DESCRIPTION}">', html, "description")
    html = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{PAGE_URL}">', html)
    for prop, value in (("og:title", TITLE), ("og:description", OG_DESCRIPTION), ("og:url", PAGE_URL),
                        ("og:image", OG_IMAGE)):
        html = re.sub(rf'<meta property="{prop}" content="[^"]*">', f'<meta property="{prop}" content="{value}">', html)
    html = re.sub(r'<meta name="twitter:image" content="[^"]*">', f'<meta name="twitter:image" content="{OG_IMAGE}">', html)
    # 構造化データ（パンくず）を「実績」から「動画制作」に
    block = re.search(r"<!-- AUTO-SEO:START.*?<!-- AUTO-SEO:END -->", html, re.S)
    if block:
        seo = block.group(0).replace("works.html", "motion.html").replace('"実績"', '"動画制作"')
        html = html[:block.start()] + seo + html[block.end():]
    html = sub_once(r'<body data-accent="[^"]*"', '<body data-accent="magenta"', html, "<body>")
    # ヘッダーで「WORKS」が現在のページとして光らないようにする
    html = re.sub(r'(<a href="[^"]*") class="active"', r"\1", html)
    html = sub_once(STYLE_RE.pattern, lambda m: m.group(0) + '\n<link rel="stylesheet" href="css/motion.css">',
                    html, "style.css の読み込み")
    html = sub_once(r"<main>.*?</main>\n", lambda m: main_html, html, "<main>")
    html = sub_once(r"</footer>\n", lambda m: m.group(0) + "\n" + modal_html, html, "</footer>")
    html = sub_once(MAINJS_RE.pattern, lambda m: m.group(0) + '\n<script src="js/motion.js"></script>', html,
                    "main.js の読み込み")
    return patch_menu_footer(html)


def patch_index(html, section):
    if "css/motion.css" not in html:
        html, n = STYLE_RE.subn(lambda m: m.group(0) + '\n<link rel="stylesheet" href="css/motion.css">', html, count=1)
        if n != 1:
            raise ApplyError("index.html に style.css の読み込みが見つかりません")
    if "js/motion.js" not in html:
        html, n = MAINJS_RE.subn(lambda m: m.group(0) + '\n<script src="js/motion.js"></script>', html, count=1)
        if n != 1:
            raise ApplyError("index.html に main.js の読み込みが見つかりません")
    if "<!-- MOTION WORKS preview -->" not in html:
        for anchor in ("  <!-- MARQUEE 2 -->", "  <!-- NEWS -->"):
            if anchor in html:
                html = html.replace(anchor, section + "\n" + anchor, 1)
                break
        else:
            raise ApplyError("index.html に紹介枠を入れる場所（<!-- MARQUEE 2 --> または <!-- NEWS -->）が見つかりません")
    return patch_menu_footer(html)


def apply(site_root, log=print):
    site = Site(site_root)
    if not (site_root / "index.html").is_file() or not (site_root / "works.html").is_file():
        raise ApplyError(f"サイトのフォルダが見つかりません: {site_root}")

    motion_path = site_root / "motion.html"
    if motion_path.exists() and 'id="mw-modal"' not in motion_path.read_text(encoding="utf-8"):
        raise ApplyError("motion.html がすでにあり、このスクリプトで作ったものではないため止めました")

    log("ファイルを準備しています…")
    main_html = fetch(SITE_FRAGMENTS + "motion-main.html").decode("utf-8")
    modal_html = fetch(SITE_FRAGMENTS + "motion-modal.html").decode("utf-8")
    section = fetch(SITE_FRAGMENTS + "index-section.html").decode("utf-8")

    site.write("css/motion.css", fetch(SITE_FRAGMENTS + "css/motion.css"))
    site.write("js/motion.js", fetch(SITE_FRAGMENTS + "js/motion.js"))
    site.write("assets/motion/ogp.jpg", fetch(SITE_FRAGMENTS + "assets/motion/ogp.jpg"))
    media = sorted(set(re.findall(r"assets/motion/([\w.-]+\.(?:mp4|jpg))", main_html + section)) - {"ogp.jpg"})
    log(f"動画・画像を用意しています（{len(media)} ファイル）…")
    for name in media:
        if not (site_root / "assets/motion" / name).exists():
            site.write(f"assets/motion/{name}", fetch(MEDIA_SRC + name))

    site.write("motion.html", build_motion_page(site.read("works.html"), main_html, modal_html))
    site.write("index.html", patch_index(site.read("index.html"), section))

    skipped = []
    for path in sorted(site_root.glob("*.html")):
        if path.name in ("admin.html", "motion.html", "index.html"):
            continue
        html = site.read(path.name)
        new = patch_menu_footer(html)
        if new == html and 'class="num">08</span>MOTION' not in html:
            skipped.append(path.name)  # メニューがないページ（LINE相談ページなど）
        site.write(path.name, new)
    return site, skipped


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    site_root = find_site(argv)
    print(f"サイトのフォルダ: {site_root}")
    try:
        site, skipped = apply(site_root)
    except ApplyError as e:
        print(f"\n⚠️ 止めました: {e}\n何も壊していません。このメッセージをそのまま Claude に送ってください。")
        return 1
    if not site.changed:
        print("\n✅ すでに反映済みです（変更なし）。管理画面の「サイトに直接反映」で送れば公開されます。")
        return 0
    print(f"\n✅ 完了しました（変更・追加したファイル {len(site.changed)} 個）")
    for rel in site.changed:
        print(f"   - {rel}")
    if skipped:
        print(f"   （メニューがないため変更しなかったページ: {', '.join(skipped)}）")
    if site.backup:
        print(f"変更前のファイルは {site.backup} に保存しました。")
    print("\n次に、いつもの管理画面で「サイトに直接反映」を押してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
