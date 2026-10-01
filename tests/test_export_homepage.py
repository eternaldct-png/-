import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("export_homepage", ROOT / "tools/motion_render/export_homepage.py")
export_homepage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export_homepage)

CONFIG = """
page:
  title: "テスト"
works:
  - id: "done"
    title: "完成した作例 <script>alert(1)</script>"
    category: "配信・ライバー"
    description: "1行目\\n2行目"
    aspect: "16:9"
    video: "/static/motion/stream-opening.mp4"
    poster: "/static/motion/stream-opening.jpg"
    duration: "10秒"
  - id: "yt"
    title: "YouTubeの作例"
    category: "音楽"
    aspect: "9:16"
    youtube: "https://youtu.be/abcdefghijk"
  - id: "wip"
    title: "制作中の枠"
    aspect: "1:1"
"""

PAGE = """<main>
      <!-- MOTION:FILTERS:START -->
      <!-- MOTION:FILTERS:END -->
      <!-- MOTION:CARDS:START -->
      <p>古い一覧</p>
      <!-- MOTION:CARDS:END -->
      <p class="mw-note">※サンプル表記です</p>
</main>
"""


class ExportHomepageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.site = Path(tmp.name) / "site"
        self.site.mkdir()
        (self.site / "motion.html").write_text(PAGE, encoding="utf-8")
        config = Path(tmp.name) / "motion_config.yaml"
        config.write_text(CONFIG, encoding="utf-8")
        patcher = patch.object(export_homepage.web_app, "MOTION_CONFIG_PATH", config)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_export_fills_markers_and_copies_media(self):
        result = export_homepage.export(self.site)
        page = (self.site / "motion.html").read_text(encoding="utf-8")

        self.assertEqual(result, {"works": 2, "copied": 2})  # 制作中の枠は載せない
        self.assertTrue((self.site / "assets/motion/stream-opening.mp4").is_file())
        self.assertTrue((self.site / "assets/motion/stream-opening.jpg").is_file())
        self.assertEqual(page.count('class="mw-card"'), 2)
        self.assertNotIn("古い一覧", page)
        self.assertIn('data-src="assets/motion/stream-opening.mp4"', page)
        self.assertIn('src="https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg"', page)
        self.assertIn('data-cat="音楽" aria-pressed="false"', page)
        self.assertIn("1行目<br>2行目", page)
        self.assertNotIn("<script>alert(1)", page)
        self.assertNotIn("制作中の枠", page)
        # 目印の外は変えない
        self.assertTrue(page.startswith("<main>\n      <!-- MOTION:FILTERS:START -->\n"))
        self.assertIn('      <!-- MOTION:CARDS:END -->\n      <p class="mw-note">', page)

    def test_export_is_idempotent(self):
        export_homepage.export(self.site)
        first = (self.site / "motion.html").read_text(encoding="utf-8")
        result = export_homepage.export(self.site)
        self.assertEqual((self.site / "motion.html").read_text(encoding="utf-8"), first)
        self.assertEqual(result["copied"], 0)

    def test_missing_markers_are_reported(self):
        (self.site / "motion.html").write_text("<main></main>", encoding="utf-8")
        with self.assertRaises(ValueError):
            export_homepage.export(self.site)


if __name__ == "__main__":
    unittest.main()
