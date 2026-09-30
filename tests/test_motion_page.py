import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import web_app
from src.web_app import app


CONFIG = """
page:
  title: "テスト作例集"
  lead: "説明文"
  contact_url: "javascript:alert(1)"
works:
  - id: "done"
    title: "完成した作例"
    category: "SNS・広告"
    aspect: 9:16
    video: "/static/motion/done.mp4"
  - id: "yt"
    title: "YouTubeの作例 </script><script>alert(1)</script>"
    aspect: "1:1"
    youtube: "https://youtube.com/shorts/abcdefghijk?feature=share"
  - id: "wip"
    title: "制作中の枠"
    aspect: "21:9"
    video: "javascript:alert(1)"
"""


def _page_data(html):
    match = re.search(r"const DATA = (.*?);\n", html)
    return json.loads(match.group(1))


class MotionPageTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        tmp.write(CONFIG)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        patcher = patch.object(web_app, "MOTION_CONFIG_PATH", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_public_page_hides_placeholders_and_normalizes_media(self):
        response = self.client.get("/motion")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<title>テスト作例集 | ETERNALd.c.t</title>", html)
        self.assertNotIn("</script><script>alert(1)", html)

        data = _page_data(html)
        self.assertFalse(data["preview"])
        self.assertEqual(data["page"]["contact_url"], "")
        works = {w["id"]: w for w in data["works"]}
        self.assertEqual(set(works), {"done", "yt"})
        self.assertEqual(works["done"]["aspect"], "9:16")  # クォートなしの 9:16 も復元される
        self.assertEqual(works["yt"]["youtube"], "abcdefghijk")

    def test_preview_shows_placeholder_slots(self):
        data = _page_data(self.client.get("/motion?preview=1").get_data(as_text=True))
        self.assertTrue(data["preview"])
        wip = next(w for w in data["works"] if w["id"] == "wip")
        self.assertTrue(wip["placeholder"])
        self.assertEqual(wip["video"], "")
        self.assertEqual(wip["aspect"], "16:9")

    def test_repository_config_loads(self):
        with patch.object(web_app, "MOTION_CONFIG_PATH", Path("persona/motion_config.yaml")):
            page, works = web_app._load_motion_config()
        self.assertTrue(page["title"])
        self.assertGreaterEqual(len(works), 10)
        self.assertEqual(len({w["id"] for w in works}), len(works))


if __name__ == "__main__":
    unittest.main()
