import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import web_app, wordpress_motion as wm


CONFIG = """
page:
  title: "テスト作例集"
  lead: "1行目\\n2行目"
  contact_url: ""
works:
  - id: "done"
    title: "完成した作例 </script><script>alert(1)</script>"
    category: "SNS・広告"
    description: "説明 [video] & 記号"
    aspect: "9:16"
    video: "/static/motion/stream-opening.mp4"
    poster: "/static/motion/stream-opening.jpg"
    duration: "15秒"
    use: "Instagramリール"
  - id: "yt"
    title: "YouTubeの作例"
    category: "音楽"
    aspect: "16:9"
    youtube: "https://youtu.be/abcdefghijk"
  - id: "wip"
    title: "制作中の枠"
    aspect: "1:1"
"""


def _quiet(*_args, **_kwargs):
    pass


class FakeClient:
    """WordPressClient の代わり（メモリ上で WordPress の状態を持つ）"""

    def __init__(self, show_on_front="page", sidebars=None):
        self.media = {}
        self.pages = {10: {"id": 10, "slug": "home", "status": "publish", "title": {"raw": "ホーム"},
                           "content": {"raw": "<!-- wp:paragraph --><p>既存</p><!-- /wp:paragraph -->"}}}
        self.settings = {"show_on_front": show_on_front, "page_on_front": 10 if show_on_front == "page" else 0}
        self.sidebars = sidebars if sidebars is not None else [{"id": "front_top", "name": "トップページ上部"}]
        self.widgets = {}
        self.uploads = 0
        self.deleted = []

    def check_login(self):
        return {"slug": "admin"}

    def list_our_media(self):
        return {item["title"]["raw"]: item for item in self.media.values()}

    def upload_media(self, path, filename):
        self.uploads += 1
        media_id = 100 + len(self.media)
        item = {"id": media_id, "title": {"raw": filename}, "source_url": f"https://example.com/up/{filename}"}
        self.media[media_id] = item
        return item

    def delete_media(self, media_id):
        self.deleted.append(media_id)
        self.media.pop(media_id)

    def find_page(self, slug):
        return next((p for p in self.pages.values() if p["slug"] == slug), None)

    def get_page(self, page_id):
        return self.pages[page_id]

    def save_page(self, page_id, data):
        if page_id is None:
            page_id = max(self.pages) + 1
            self.pages[page_id] = {"id": page_id, "slug": data["slug"], "title": {"raw": data["title"]},
                                   "status": data["status"], "content": {"raw": ""}}
        page = self.pages[page_id]
        if "content" in data:
            page["content"] = {"raw": data["content"]}
        for key in ("status", "featured_media"):
            if key in data:
                page[key] = data[key]
        page["link"] = f"https://example.com/{page['slug']}/" if page["status"] == "publish" else f"https://example.com/?page_id={page_id}"
        return page

    def get_settings(self):
        return self.settings

    def list_sidebars(self):
        return self.sidebars

    def list_widgets(self, sidebar_id=None):
        return [w for w in self.widgets.values() if sidebar_id in (None, w["sidebar"])]

    def save_widget(self, widget_id, data):
        if widget_id is None:
            widget_id = f"custom_html-{len(self.widgets) + 2}"
            self.widgets[widget_id] = {"id": widget_id, "id_base": data["id_base"], "sidebar": "wp_inactive_widgets"}
        widget = self.widgets[widget_id]
        if "sidebar" in data:
            widget["sidebar"] = data["sidebar"]
        if "instance" in data:
            widget["instance"] = data["instance"]
        return widget


class WordPressMotionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        tmp.write(CONFIG)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        patcher = patch.object(web_app, "MOTION_CONFIG_PATH", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    # ── HTML ──
    def test_page_html_is_static_escaped_and_safe_for_wordpress_filters(self):
        page_info, works = wm.load_works()
        self.assertEqual([w["id"] for w in works], ["done", "yt"])  # 制作中の枠は載せない
        html = wm.build_page_html(page_info, works, lambda url: "https://example.com" + url)

        self.assertEqual(html.count('class="edct-mw__card"'), 2)
        self.assertIn('data-edct-src="https://example.com/static/motion/stream-opening.mp4"', html)
        self.assertIn('href="https://www.youtube.com/watch?v=abcdefghijk"', html)
        self.assertNotIn("</script><script>alert(1)", html)
        self.assertIn("1行目<br>2行目", html)
        self.assertNotIn("<iframe", html)
        self.assertIsNone(re.search(r"<h[1-6]", html))  # 目次の自動挿入などに巻き込まれない
        self.assertNotIn("onrender.com", html)
        # 自動段落（空行）とショートコード（[英字）に巻き込まれない
        self.assertNotIn("\n\n", html)
        self.assertEqual(re.findall(r"\[[A-Za-z]", html), [])
        # カテゴリが2つ以上あれば絞り込みボタンを出す
        self.assertIn('data-cat="音楽" aria-pressed="false"', html)

    def test_real_config_maps_every_local_file(self):
        with patch.object(web_app, "MOTION_CONFIG_PATH", Path("persona/motion_config.yaml")):
            page_info, works = wm.load_works()
            files = wm.required_media(works)
        self.assertEqual(len(works), 15)
        self.assertEqual(len(files), 30)
        html = wm.build_page_html(page_info, works, lambda url: "https://example.com/up/" + wm.wp_filename(files[url]))
        self.assertNotIn("/static/", html)
        self.assertEqual(html.count('class="edct-mw__card"'), 15)

    def test_wp_filename_changes_when_file_changes(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "clip.MP4"
            path.write_bytes(b"one")
            first = wm.wp_filename(path)
            path.write_bytes(b"two")
            second = wm.wp_filename(path)
        self.assertTrue(first.startswith("edct-motion-clip-") and first.endswith(".mp4"))
        self.assertNotEqual(first, second)

    def test_local_media_path_rejects_traversal(self):
        self.assertIsNone(wm.local_media_path("/static/../../persona/config.yaml"))
        self.assertIsNone(wm.local_media_path("https://example.com/a.mp4"))

    # ── トップページ ──
    def test_upsert_card_block_appends_once_and_replaces(self):
        raw = "<!-- wp:paragraph --><p>既存</p><!-- /wp:paragraph -->"
        card = wm.build_top_card_html("https://example.com/motion/")
        self.assertFalse(card.startswith("<!--"))
        self.assertIn('href="https://example.com/motion/"', card)

        once = wm.upsert_card_block(raw, card)
        self.assertTrue(once.startswith(raw))
        self.assertEqual(once.count(wm.CARD_MARKER + '"'), 1)
        twice = wm.upsert_card_block(once, card.replace("example.com", "example.org"))
        self.assertEqual(twice.count("<!-- wp:html -->"), 1)
        self.assertIn("example.org/motion/", twice)
        self.assertIn("<p>既存</p>", twice)
        self.assertTrue(wm.upsert_card_block(raw, card, "start").endswith(raw))

    # ── 公開の流れ ──
    def test_publish_creates_page_and_card_then_reuses_media(self):
        client = FakeClient()
        result = wm.publish(client, add_to_top=True, log=_quiet)

        page = client.pages[result["page_id"]]
        self.assertEqual((page["slug"], page["status"]), ("motion", "publish"))
        self.assertIn(wm.PAGE_MARKER, page["content"]["raw"])
        self.assertTrue(page["content"]["raw"].startswith("<!-- wp:html -->"))
        self.assertIn("https://example.com/up/edct-motion-stream-opening-", page["content"]["raw"])
        self.assertEqual(client.media[page["featured_media"]]["title"]["raw"][:21], "edct-motion-eyecatch-")
        self.assertEqual(client.uploads, 3)  # 動画・ポスター・アイキャッチ
        self.assertIn('href="https://example.com/motion/"', client.pages[10]["content"]["raw"])

        wm.publish(client, add_to_top=True, log=_quiet)
        self.assertEqual(client.uploads, 3)
        self.assertEqual(client.pages[10]["content"]["raw"].count("<!-- wp:html -->"), 1)
        self.assertEqual(len(client.pages), 2)

    def test_publish_refuses_to_overwrite_foreign_page(self):
        client = FakeClient()
        client.pages[20] = {"id": 20, "slug": "motion", "status": "publish", "content": {"raw": "<p>別のページ</p>"}}
        with self.assertRaises(wm.WordPressError):
            wm.publish(client, log=_quiet)
        self.assertEqual(client.pages[20]["content"]["raw"], "<p>別のページ</p>")
        wm.publish(client, force=True, log=_quiet)
        self.assertIn(wm.PAGE_MARKER, client.pages[20]["content"]["raw"])

    def test_draft_page_is_not_linked_from_top(self):
        client = FakeClient()
        result = wm.publish(client, status="draft", add_to_top=True, log=_quiet)
        self.assertEqual(result["status"], "draft")
        self.assertIsNone(result["top"])
        self.assertNotIn(wm.CARD_MARKER, client.pages[10]["content"]["raw"])

    def test_update_only_does_nothing_without_page(self):
        client = FakeClient()
        result = wm.publish(client, update_only=True, log=_quiet)
        self.assertIsNone(result["page_id"])
        self.assertEqual(client.uploads, 0)

    def test_update_keeps_current_status(self):
        client = FakeClient()
        page_id = wm.publish(client, status="draft", log=_quiet)["page_id"]
        wm.publish(client, log=_quiet)
        self.assertEqual(client.pages[page_id]["status"], "draft")

    def test_front_page_as_latest_posts_uses_widget_area_once(self):
        client = FakeClient(show_on_front="posts")
        wm.publish(client, add_to_top=True, log=_quiet)
        wm.publish(client, add_to_top=True, log=_quiet)
        self.assertEqual(len(client.widgets), 1)
        widget = next(iter(client.widgets.values()))
        self.assertEqual(widget["sidebar"], "front_top")  # 作成直後に使用停止中へ移されても戻す
        self.assertIn(wm.CARD_MARKER, widget["instance"]["raw"]["content"])

    def test_missing_widget_area_is_reported(self):
        client = FakeClient(show_on_front="posts", sidebars=[{"id": "sidebar-1", "name": "共通サイドバー"}])
        with self.assertRaises(wm.WordPressError) as ctx:
            wm.publish(client, add_to_top=True, log=_quiet)
        self.assertIn("共通サイドバー", str(ctx.exception))

    def test_prune_deletes_only_stale_uploads(self):
        client = FakeClient()
        client.media[1] = {"id": 1, "title": {"raw": "edct-motion-old-00000000.mp4"}, "source_url": "x"}
        wm.publish(client, prune=True, log=_quiet)
        self.assertEqual(client.deleted, [1])


class FakeResponse:
    def __init__(self, status, data=None, text=""):
        self.status_code, self._data, self.text = status, data, text

    def json(self):
        if self._data is None:
            raise ValueError("not json")
        return self._data


class FakeSession:
    def __init__(self, handler):
        self.handler, self.headers, self.calls = handler, {}, []

    def request(self, method, url, **kwargs):
        self.calls.append(url)
        return self.handler(method, url, kwargs)


class WordPressClientTest(unittest.TestCase):
    def test_falls_back_to_rest_route_when_pretty_urls_are_missing(self):
        admin = {"slug": "admin", "capabilities": {"upload_files": True, "edit_pages": True, "publish_pages": True}}

        def handler(method, url, kwargs):
            if "/wp-json/" in url:
                return FakeResponse(404, text="<html>Not Found</html>")
            return FakeResponse(200, admin)

        session = FakeSession(handler)
        client = wm.WordPressClient("https://example.com/", "admin", "pw", session=session)
        self.assertEqual(client.check_login()["slug"], "admin")
        self.assertEqual(session.calls[-1], "https://example.com/?rest_route=/wp/v2/users/me")

    def test_error_message_has_hint(self):
        session = FakeSession(lambda *a: FakeResponse(403, {"message": "Forbidden"}))
        client = wm.WordPressClient("https://example.com", "admin", "pw", session=session)
        with self.assertRaises(wm.WordPressError) as ctx:
            client.request("GET", "settings")
        self.assertIn("国外IP", str(ctx.exception))

    def test_requires_page_capabilities(self):
        user = {"slug": "writer", "capabilities": {"upload_files": True}}
        session = FakeSession(lambda *a: FakeResponse(200, user))
        client = wm.WordPressClient("https://example.com", "writer", "pw", session=session)
        with self.assertRaises(wm.WordPressError) as ctx:
            client.check_login()
        self.assertIn("publish_pages", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
