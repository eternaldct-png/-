import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("apply_motion", ROOT / "tools/homepage/apply_motion.py")
apply_motion = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apply_motion)

MENU = """    <ul class="menu-list">
      <li><a href="music.html"><span class="num">07</span>MUSIC<span class="jp">音楽制作</span></a></li>
      <li><a href="works.html"><span class="num">08</span>WORKS<span class="jp">実績</span></a></li>
      <li><a href="contact.html"><span class="num">09</span>CONTACT<span class="jp">お問い合わせ</span></a></li>
    </ul>
"""
FOOTER = """<footer class="site-footer">
        <a href="livers.html">ライバー紹介</a>
        <a href="music.html">音楽制作</a>
      </div>
</footer>
"""


def page(title, main, accent="cyan", extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<title>{title}</title>
<meta name="description" content="説明">
<link rel="canonical" href="https://eternaldct.net/works.html">
<meta property="og:url" content="https://eternaldct.net/works.html">
<link rel="stylesheet" href="css/style.css?v=883be056">
<!-- AUTO-SEO:START -->
<script type="application/ld+json">{{"url": "https://eternaldct.net/works.html", "name": "実績"}}</script>
<!-- AUTO-SEO:END -->{extra_head}
</head>
<body data-accent="{accent}">
<nav class="gnav"><a href="works.html" class="active">WORKS</a></nav>
{MENU}<main>
{main}
</main>
{FOOTER}
<script src="js/main.js?v=bde1039e"></script>
</body>
</html>
"""


class ApplyMotionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.site = Path(tmp.name) / "ETERNALライバー事務所" / "eternaldct-new-site"
        self.site.mkdir(parents=True)
        index_main = "  <!-- WORKS preview -->\n  <section>実績</section>\n\n  <!-- MARQUEE 2 -->\n  <div>marquee</div>"
        (self.site / "index.html").write_text(page("トップ", index_main), encoding="utf-8")
        (self.site / "works.html").write_text(page("実績", "<section>実績一覧</section>"), encoding="utf-8")
        (self.site / "privacy.html").write_text(page("プライバシー", "<p>本文</p>"), encoding="utf-8")
        (self.site / "line-consult.html").write_text("<html><body>LINE相談</body></html>", encoding="utf-8")
        (self.site / "admin.html").write_text(page("管理", "<p>管理</p>"), encoding="utf-8")

    def read(self, name):
        return (self.site / name).read_text(encoding="utf-8")

    def test_apply_adds_page_menu_footer_and_top_section(self):
        site, skipped = apply_motion.apply(self.site, log=lambda *a: None)

        motion = self.read("motion.html")
        self.assertIn("<title>動画制作・作例集", motion)
        self.assertIn('<link rel="canonical" href="https://eternaldct.net/motion.html">', motion)
        self.assertIn('"url": "https://eternaldct.net/motion.html", "name": "動画制作"', motion)
        self.assertIn('<body data-accent="magenta"', motion)
        self.assertNotIn('class="active"', motion)
        self.assertEqual(motion.count('class="mw-card"'), 15)
        self.assertNotIn("実績一覧", motion)
        self.assertIn('<script src="js/main.js?v=bde1039e"></script>\n<script src="js/motion.js"></script>', motion)
        self.assertIn('id="mw-modal"', motion)

        index = self.read("index.html")
        self.assertIn('<link rel="stylesheet" href="css/style.css?v=883be056">\n<link rel="stylesheet" href="css/motion.css">', index)
        self.assertLess(index.index("<!-- WORKS preview -->"), index.index("<!-- MOTION WORKS preview -->"))
        self.assertLess(index.index("<!-- MOTION WORKS preview -->"), index.index("<!-- MARQUEE 2 -->"))

        for name in ("index.html", "works.html", "privacy.html", "motion.html"):
            html = self.read(name)
            self.assertIn('<span class="num">08</span>MOTION', html, name)
            self.assertIn('<span class="num">10</span>CONTACT', html, name)
            self.assertEqual(html.count('<a href="motion.html">動画制作</a>'), 1, name)
        self.assertNotIn("motion.html", self.read("admin.html"))
        self.assertEqual(skipped, ["line-consult.html"])
        self.assertTrue((self.site / "assets/motion/stream-opening.mp4").is_file())
        self.assertTrue((self.site / "css/motion.css").is_file())
        # 変更前のファイルを残す
        self.assertIn("08</span>WORKS", (site.backup / "works.html").read_text(encoding="utf-8"))

    def test_apply_is_idempotent(self):
        apply_motion.apply(self.site, log=lambda *a: None)
        before = {p.name: p.read_bytes() for p in self.site.glob("*.html")}
        site, _ = apply_motion.apply(self.site, log=lambda *a: None)
        self.assertEqual(site.changed, [])
        self.assertEqual({p.name: p.read_bytes() for p in self.site.glob("*.html")}, before)

    def test_refuses_to_overwrite_foreign_motion_page(self):
        (self.site / "motion.html").write_text("<p>別のページ</p>", encoding="utf-8")
        with self.assertRaises(apply_motion.ApplyError):
            apply_motion.apply(self.site, log=lambda *a: None)
        self.assertEqual(self.read("motion.html"), "<p>別のページ</p>")
        self.assertNotIn("MOTION", self.read("index.html"))

    def test_find_site_handles_decomposed_folder_name(self):
        import unicodedata
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as home:
            nfd = unicodedata.normalize("NFD", "ETERNALライバー事務所")
            (Path(home) / nfd).mkdir()
            with patch.object(Path, "home", return_value=Path(home)):
                found = apply_motion.find_site([])
            self.assertEqual(found, Path(home) / nfd / "eternaldct-new-site")


if __name__ == "__main__":
    unittest.main()
