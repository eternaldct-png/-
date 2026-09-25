import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.web_app import app

import note_status as ns  # src/ は web_app の import 時に sys.path へ追加される
import push_note_drafts


def write_article(directory, filename, title, body, status="draft", note_url=""):
    (directory / filename).write_text(
        "---\n"
        f'title: "{title}"\n'
        'date: "2026-09-25"\n'
        "tags:\n"
        '  - "ライバー"\n'
        f'note_status: "{status}"\n'
        f'note_url: "{note_url}"\n'
        "membership_only: false\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


class NoteDraftsTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.articles = root / "articles"
        self.articles.mkdir()
        self.history = root / "history.json"
        self.history.write_text("[]", encoding="utf-8")
        self.patches = [
            patch.object(ns, "ARTICLES_DIR", self.articles),
            patch.object(ns, "HISTORY_PATH", self.history),
            patch.dict(os.environ, {}, clear=False),
        ]
        for p in self.patches:
            p.start()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("WEB_PASSWORD", None)
        self.client = app.test_client()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()


class NoteStatusTest(NoteDraftsTestBase):
    def test_merge_keeps_the_more_advanced_status(self):
        self.assertEqual(ns.merge_status("draft", None), "draft")
        self.assertEqual(ns.merge_status("draft", "published"), "published")
        self.assertEqual(ns.merge_status("uploaded_draft", "draft"), "uploaded_draft")
        self.assertEqual(ns.merge_status("unknown", ""), "draft")

    def test_article_saved_as_raw_json_is_unwrapped(self):
        fp = self.articles / "a.md"
        payload = json.dumps({"title": "本当のタイトル", "body": "本当の本文", "tags": ["歌"]}, ensure_ascii=False)
        fp.write_text(
            '---\ntitle: "```json\n{"title": "本当"\nnote_status: "draft"\nnote_url: ""\n---\n\n'
            f"```json\n{payload}\n```\n",
            encoding="utf-8",
        )
        a = ns.read_article(fp)
        self.assertEqual(a["title"], "本当のタイトル")
        self.assertEqual(a["body"], "本当の本文")
        self.assertEqual(a["tags"], ["歌"])
        self.assertEqual(a["note_status"], "draft")

    def test_raw_json_with_unescaped_quotes_is_still_unwrapped(self):
        fp = self.articles / "b.md"
        fp.write_text(
            '---\ntitle: "```json"\nnote_status: "draft"\nnote_url: ""\n---\n\n'
            '```json\n{"title": "うまさは"間"だった", "body": "一行目\\n\\n"間"が大事。", "tags": ["歌配信"]}\n```\n',
            encoding="utf-8",
        )
        a = ns.read_article(fp)
        self.assertEqual(a["title"], 'うまさは"間"だった')
        self.assertEqual(a["body"], '一行目\n\n"間"が大事。')
        self.assertEqual(a["tags"], ["歌配信"])

    def test_update_frontmatter_only_touches_given_keys(self):
        write_article(self.articles, "a.md", "タイトル", "本文です")
        fp = self.articles / "a.md"
        ns.update_frontmatter(fp, {"note_status": "published", "note_url": "https://note.com/x/n/abc"})
        content = fp.read_text(encoding="utf-8")
        self.assertIn('note_status: "published"', content)
        self.assertIn('note_url: "https://note.com/x/n/abc"', content)
        self.assertIn('title: "タイトル"', content)
        self.assertIn("membership_only: false", content)
        self.assertTrue(content.rstrip().endswith("本文です"))

    def test_note_url_validation(self):
        self.assertTrue(ns.is_note_url("https://note.com/eternal/n/abc"))
        self.assertTrue(ns.is_note_url("https://editor.note.com/notes/abc/edit/"))
        self.assertFalse(ns.is_note_url("http://note.com/x"))
        self.assertFalse(ns.is_note_url("https://evilnote.com/x"))
        self.assertFalse(ns.is_note_url("javascript:alert(1)"))


class NoteDraftsApiTest(NoteDraftsTestBase):
    def test_list_shows_three_distinct_statuses_and_upload_errors(self):
        write_article(self.articles, "20260901_a.md", "未作成の記事", "本文A")
        write_article(self.articles, "20260902_b.md", "下書きの記事", "本文B", "uploaded_draft", "https://note.com/notes/b/edit")
        write_article(self.articles, "20260903_c.md", "公開の記事", "本文C", "published")
        self.history.write_text(json.dumps([{
            "filepath": "posts/note/articles/20260901_a.md",
            "note_upload_error": "note へのログインに失敗",
            "note_upload_attempted_at": "2026-09-17T11:20:03+09:00",
        }], ensure_ascii=False), encoding="utf-8")

        data = self.client.get("/api/note-drafts").get_json()
        by_title = {a["title"]: a for a in data["articles"]}

        self.assertEqual(by_title["未作成の記事"]["status_label"], "note未作成")
        self.assertEqual(by_title["下書きの記事"]["status_label"], "note下書き作成済")
        self.assertEqual(by_title["公開の記事"]["status_label"], "note公開済")
        self.assertEqual(by_title["下書きの記事"]["note_url"], "https://note.com/notes/b/edit")
        self.assertEqual(by_title["未作成の記事"]["upload_error"], "note へのログインに失敗")
        self.assertEqual(by_title["未作成の記事"]["excerpt"], "本文A")
        self.assertEqual([a["title"] for a in data["articles"]][0], "公開の記事")  # 新しい順
        self.assertEqual(data["storage"], "file")
        self.assertTrue(data["can_edit"])

    def test_status_change_requires_login_when_password_is_set(self):
        write_article(self.articles, "a.md", "記事", "本文")
        os.environ["WEB_PASSWORD"] = "secret"

        body = {"filename": "a.md", "status": "published", "note_url": ""}
        self.assertEqual(self.client.post("/api/note-drafts/status", json=body).status_code, 401)
        self.assertEqual(self.client.post("/api/note-drafts/delete", json={"filename": "a.md"}).status_code, 401)
        self.assertFalse(self.client.get("/api/note-drafts").get_json()["can_edit"])

        wrong = self.client.post("/api/note-drafts/login", json={"password": "nope"})
        self.assertEqual(wrong.status_code, 401)
        japanese = self.client.post("/api/note-drafts/login", json={"password": "ぱすわーど"})
        self.assertEqual(japanese.status_code, 401)
        ok = self.client.post("/api/note-drafts/login", json={"password": "secret"})
        self.assertTrue(ok.get_json()["ok"])

        r = self.client.post("/api/note-drafts/status", json=body)
        self.assertEqual(r.get_json(), {"ok": True, "storage": "file"})
        self.assertEqual(ns.read_article(self.articles / "a.md")["note_status"], "published")

    def test_status_change_saves_url_and_can_be_reset_without_db(self):
        write_article(self.articles, "a.md", "記事", "本文")
        r = self.client.post("/api/note-drafts/status", json={
            "filename": "a.md", "status": "uploaded_draft", "note_url": "https://note.com/notes/k/edit",
        })
        self.assertTrue(r.get_json()["ok"])
        a = self.client.get("/api/note-drafts").get_json()["articles"][0]
        self.assertEqual(a["status"], "uploaded_draft")
        self.assertEqual(a["note_url"], "https://note.com/notes/k/edit")

        self.client.post("/api/note-drafts/status", json={"filename": "a.md", "status": "", "note_url": ""})
        a = self.client.get("/api/note-drafts").get_json()["articles"][0]
        self.assertEqual(a["status"], "draft")
        self.assertEqual(a["note_url"], "")

    def test_status_change_rejects_bad_input(self):
        write_article(self.articles, "a.md", "記事", "本文")
        bad_url = self.client.post("/api/note-drafts/status", json={
            "filename": "a.md", "status": "published", "note_url": "https://example.com/x",
        })
        self.assertEqual(bad_url.status_code, 400)
        bad_status = self.client.post("/api/note-drafts/status", json={"filename": "a.md", "status": "posted"})
        self.assertEqual(bad_status.status_code, 400)
        traversal = self.client.post("/api/note-drafts/status", json={"filename": "../a.md", "status": "published"})
        self.assertEqual(traversal.status_code, 404)

    def test_page_renders(self):
        html = self.client.get("/note-drafts").get_data(as_text=True)
        self.assertIn("note下書き作成済", html)
        self.assertIn("/api/note-drafts/status", html)


class FakeBrowser:
    def __init__(self, login_ok=True):
        self.login_ok = login_ok
        self.logins = 0
        self.created = []
        self.last_error = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def login(self, email, password):
        self.logins += 1
        if not self.login_ok:
            self.last_error = "note へのログインに失敗（しばらくたってからもう一度お試しください）"
        return self.login_ok

    def create_draft(self, title, body, tags=None):
        self.created.append(title)
        return {"url": f"https://editor.note.com/notes/{len(self.created)}/edit/"}


class PushNoteDraftsTest(NoteDraftsTestBase):
    def setUp(self):
        super().setUp()
        for i in range(1, 6):
            write_article(self.articles, f"2026090{i}_x.md", f"記事{i}", f"本文{i}")
        write_article(self.articles, "20260906_x.md", "公開済みの記事", "本文", "published")
        self.history.write_text(json.dumps([
            {"filepath": f"posts/note/articles/2026090{i}_x.md", "title": f"記事{i}"} for i in range(1, 7)
        ], ensure_ascii=False), encoding="utf-8")
        os.environ.update({"NOTE_EMAIL": "a@example.com", "NOTE_PASSWORD": "pw"})
        os.environ.pop("NOTE_SESSION_TOKEN", None)
        os.environ.pop("NOTE_MAX_UPLOADS", None)
        self.patches.append(patch.object(push_note_drafts, "WAIT_BETWEEN_UPLOADS", 0))
        self.patches[-1].start()

    def run_main(self, browser, argv=()):
        import note_browser_client
        with patch.object(note_browser_client, "NoteBrowserSession", lambda: browser), \
             patch.object(sys, "argv", ["push_note_drafts.py", *argv]):
            try:
                push_note_drafts.main()
                return 0
            except SystemExit as e:
                return e.code

    def test_uploads_newest_drafts_up_to_the_limit_with_a_single_login(self):
        browser = FakeBrowser()
        self.assertEqual(self.run_main(browser), 0)
        self.assertEqual(browser.logins, 1)
        self.assertEqual(browser.created, ["記事5", "記事4", "記事3"])
        self.assertEqual(ns.read_article(self.articles / "20260905_x.md")["note_status"], "uploaded_draft")
        self.assertEqual(ns.read_article(self.articles / "20260901_x.md")["note_status"], "draft")

        self.assertEqual(self.run_main(FakeBrowser(), ["--limit", "5"]), 0)
        statuses = {fp.name: ns.read_article(fp)["note_status"] for fp in self.articles.glob("*.md")}
        self.assertEqual(statuses["20260901_x.md"], "uploaded_draft")
        self.assertEqual(statuses["20260906_x.md"], "published")

    def test_stops_after_a_failed_login_and_records_the_reason(self):
        browser = FakeBrowser(login_ok=False)
        self.assertEqual(self.run_main(browser), 1)
        self.assertEqual(browser.logins, 1)
        self.assertEqual(browser.created, [])

        history = {Path(e["filepath"]).name: e for e in json.loads(self.history.read_text(encoding="utf-8"))}
        self.assertIn("しばらくたってから", history["20260905_x.md"]["note_upload_error"])
        self.assertIn("note_upload_attempted_at", history["20260905_x.md"])
        self.assertNotIn("note_upload_error", history["20260904_x.md"])  # 試していない記事は記録しない

        a = next(x for x in self.client.get("/api/note-drafts").get_json()["articles"] if x["filename"] == "20260905_x.md")
        self.assertIn("しばらくたってから", a["upload_error"])


if __name__ == "__main__":
    unittest.main()
