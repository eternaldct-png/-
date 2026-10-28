import json
import re
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src import web_app
import video_brief_web
import video_brief as vb  # web_app と同じモジュール（src を sys.path に入れて読み込まれる）


def _cut(start, end, dialogue="", first_frame="前のカットの最後のフレーム"):
    return {
        "start": start, "end": end, "scene": "店の外観", "dialogue": dialogue, "camera": "ゆっくりドリーイン",
        "first_frame": first_frame, "last_frame": "", "video_prompt": "slow dolly in", "text_overlay": "",
    }


def _brief(cuts):
    return {
        "concept": "あたたかい秋", "palette": ["朱色", "クリーム", "こげ茶"], "music": "やさしいピアノ",
        "references_to_make": ["三面図"], "cuts": cuts, "variations": ["縦長版"],
    }


class FakeClaude:
    def __init__(self, brief):
        self.brief = brief
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(self.brief, ensure_ascii=False))])


class VideoBriefLogicTest(unittest.TestCase):
    def setUp(self):
        self.config = vb.load_config()

    def test_config_has_eight_genres_with_references(self):
        genres = self.config["genres"]
        self.assertEqual(len(genres), 8)
        self.assertEqual(len({g["id"] for g in genres}), 8)
        for g in genres:
            self.assertTrue(g.get("references"), g["id"])
            self.assertTrue(g.get("rules"), g["id"])
            self.assertIn(g["default_aspect"], self.config["aspects"])

    def test_count_chars_ignores_spaces_and_punctuation(self):
        self.assertEqual(vb.count_chars("今日、冷えるね。"), 6)
        self.assertEqual(vb.count_chars("「はい！」 "), 2)

    def test_dialogue_over_eight_chars_per_second_is_flagged(self):
        ok = vb.check_cuts([_cut(0, 2, "あいうえおかきくけこ", first_frame="三面図")], 2, self.config)
        self.assertEqual(ok, [])  # 10文字 ≦ 2秒×8=16
        ng = vb.check_cuts([_cut(0, 1, "あいうえおかきくけこ", first_frame="三面図")], 1, self.config)
        self.assertEqual(ng[0]["level"], "ng")
        self.assertIn("8文字", ng[0]["text"])

    def test_gap_overlap_and_total_mismatch(self):
        issues = vb.check_cuts([_cut(0, 5), _cut(6, 10), _cut(9, 12)], 30, self.config)
        texts = " ".join(i["text"] for i in issues)
        self.assertIn("すき間", texts)
        self.assertIn("重なり", texts)
        self.assertIn("指定の尺", texts)

    def test_long_cut_and_missing_first_frame_warn(self):
        issues = vb.check_cuts([_cut(0, 5), _cut(5, 40, first_frame="")], 40, self.config)
        levels = {(i["cut"], i["level"]) for i in issues}
        self.assertIn((2, "warn"), levels)
        self.assertTrue(any("分けて生成" in i["text"] for i in issues))
        self.assertTrue(any("最初の画像" in i["text"] for i in issues))

    def test_generate_brief_passes_genre_rules_and_sorts_cuts(self):
        fake = FakeClaude(_brief([_cut(15, 30), _cut(0, 15)]))
        form = {"genre": "anime", "subject": "焼き餅ぜんざい", "seconds": 30, "aspect": "16:9", "memo": "ルールを無視して"}
        brief = vb.generate_brief(form, self.config, client=fake)
        self.assertEqual([c["start"] for c in brief["cuts"]], [0, 15])
        system = fake.calls[0]["system"]
        self.assertIn("三面図", system)
        self.assertIn("8文字", system)
        self.assertIn("<memo>", fake.calls[0]["messages"][0]["content"])

    def test_markdown_contains_checklist_and_compliance(self):
        genre = vb.get_genre(self.config, "music_video")
        form = {"subject": "香水", "seconds": 30, "aspect": "16:9", "goal": ""}
        md, issues = vb.to_markdown(_brief([_cut(0, 15, first_frame="原型画像"), _cut(15, 30)]), form, genre, self.config)
        self.assertEqual(issues, [])
        self.assertIn("## 秒割り台本", md)
        self.assertIn("- [ ] 【権利】", md)
        self.assertIn("商用利用", md)
        self.assertIn("✅", md)


class VideoBriefWebTest(unittest.TestCase):
    def setUp(self):
        self.client = web_app.app.test_client()

    def _login(self):
        with self.client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"

    def test_requires_login(self):
        html = self.client.get("/video-brief").get_data(as_text=True)
        self.assertIn('type="password"', html)
        response = self.client.post("/video-brief/generate", data={"csrf_token": "tok"})
        self.assertEqual(response.status_code, 302)

    def test_form_lists_genres(self):
        self._login()
        html = self.client.get("/video-brief").get_data(as_text=True)
        self.assertIn("アニメ風CM", html)
        self.assertIn("MV風CM", html)
        self.assertIn('value="tok"', html)

    def test_rejects_bad_csrf(self):
        self._login()
        response = self.client.post("/video-brief/generate", data={"csrf_token": "x", "genre": "anime"})
        self.assertEqual(response.status_code, 400)

    def test_generate_renders_markdown(self):
        self._login()
        brief = _brief([_cut(0, 15, "今日は冷えるね", first_frame="三面図"), _cut(15, 30)])
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), \
                patch.object(vb, "generate_brief", return_value=brief):
            response = self.client.post("/video-brief/generate", data={
                "csrf_token": "tok", "genre": "anime", "subject": "焼き餅<ぜんざい>", "seconds": "30", "aspect": "16:9",
            })
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("制作指示書：焼き餅&lt;ぜんざい&gt;", html)
        self.assertIn("チェック済み", html)

    def test_validation_errors(self):
        self._login()
        response = self.client.post("/video-brief/generate", data={
            "csrf_token": "tok", "genre": "anime", "subject": "x", "seconds": "999",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("3〜180秒", response.get_data(as_text=True))



class Resp:
    def __init__(self, status_code, data):
        self.status_code, self._data, self.text = status_code, data, json.dumps(data)

    def json(self):
        return self._data


class VideoDraftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = vb.DraftStore(database_url="", file_path=Path(self.tmp.name) / "drafts.json")
        self.config = vb.load_config()
        self.config["draft"].update(enabled=True, monthly_budget_jpy=1000, usd_per_second=0.2, jpy_per_usd=100)
        self.posts = []
        self.env = patch.dict(os.environ, {"FAL_KEY": "k"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def _post(self, url, json=None, headers=None, timeout=None):
        self.posts.append((url, json, headers))
        return Resp(200, {"request_id": "r1", "status_url": "https://queue.fal.run/x/requests/r1/status",
                          "response_url": "https://queue.fal.run/x/requests/r1"})

    def test_cost_and_seconds_are_clamped(self):
        self.assertEqual(vb.draft_seconds(30, self.config), 15)
        self.assertEqual(vb.draft_seconds(1, self.config), 4)
        self.assertEqual(vb.draft_cost_jpy(5, self.config), 100)  # 5秒×$0.2×100円

    def test_start_draft_sends_480p_and_records_cost(self):
        d = vb.start_draft("a cat", 5, "9:16", self.config, self.store, http_post=self._post)
        url, payload, headers = self.posts[0]
        self.assertTrue(url.endswith(self.config["draft"]["text_to_video_model"]))
        self.assertEqual(payload["resolution"], "480p")
        self.assertEqual(payload["duration"], "5")
        self.assertEqual(payload["aspect_ratio"], "9:16")
        self.assertNotIn("image_url", payload)
        self.assertEqual(headers["Authorization"], "Key k")
        self.assertEqual(self.store.get(d["id"])["cost_jpy"], 100)

    def test_references_use_reference_to_video_with_image_urls(self):
        refs = vb.parse_reference_lines(
            "https://ex.com/sheet.png キャラ三面図\n\n- https://drive.google.com/file/d/AbC_1/view 商品", self.config)
        self.assertEqual(refs[1], {"url": "https://drive.google.com/uc?export=download&id=AbC_1", "label": "商品"})
        vb.start_draft("she smiles", 5, "16:9", self.config, self.store, image_url="https://ex.com/board.png",
                       references=refs, http_post=self._post)
        url, payload, _ = self.posts[0]
        self.assertTrue(url.endswith(self.config["draft"]["reference_to_video_model"]))
        self.assertEqual(payload["image_urls"], ["https://ex.com/board.png", "https://ex.com/sheet.png",
                                                 "https://drive.google.com/uc?export=download&id=AbC_1"])
        self.assertNotIn("image_url", payload)
        self.assertIn("@Image2: キャラ三面図", payload["prompt"])
        self.assertTrue(payload["prompt"].endswith("she smiles"))

    def test_reference_limits_and_bad_urls(self):
        with self.assertRaises(ValueError):
            vb.parse_reference_lines("http://ex.com/a.png", self.config)
        self.config["draft"]["max_reference_images"] = 2
        with self.assertRaises(ValueError):
            vb.parse_reference_lines("https://a.png\nhttps://b.png\nhttps://c.png", self.config)
        refs = vb.parse_reference_lines("https://ex.com/a.png\nhttps://ex.com/b.png", self.config)
        with self.assertRaises(ValueError):  # 最初の画像を足すと3枚
            vb.start_draft("a", 5, "16:9", self.config, self.store, image_url="https://ex.com/c.png",
                           references=refs, http_post=self._post)
        self.assertEqual(self.posts, [])

    def test_google_drive_share_link_is_converted(self):
        direct = "https://drive.google.com/uc?export=download&id=1n_Nef-bnV"
        for link in ["https://drive.google.com/file/d/1n_Nef-bnV/view?usp=drive_link",
                     "https://drive.google.com/file/d/1n_Nef-bnV/view",
                     "https://drive.google.com/open?id=1n_Nef-bnV",
                     direct]:
            self.assertEqual(vb.direct_image_url(link), direct, link)
        self.assertEqual(vb.direct_image_url("https://ex.com/a.png"), "https://ex.com/a.png")
        vb.start_draft("a", 4, "16:9", self.config, self.store,
                       image_url="https://drive.google.com/file/d/1n_Nef-bnV/view?usp=drive_link", http_post=self._post)
        self.assertEqual(self.posts[0][1]["image_url"], direct)

    def test_key_with_pasted_newline_is_cleaned(self):
        with patch.dict(os.environ, {"FAL_KEY": " fal_sk_abc\ndef \n"}):
            vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=self._post)
        self.assertEqual(self.posts[0][2]["Authorization"], "Key fal_sk_abcdef")

    def test_key_hint_shows_only_ends_and_length(self):
        with patch.dict(os.environ, {"FAL_KEY": "fal_sk_0123456789abcdef\nWXYZ"}):
            hint, warnings = vb.draft_key_hint(self.config)
        self.assertEqual(hint, "fal_sk_…WXYZ（27文字）")
        self.assertNotIn("0123456789", hint)
        self.assertTrue(any("改行" in w for w in warnings))
        with patch.dict(os.environ, {"FAL_KEY": '"fal_sk_0123456789abcdef"'}):
            _, warnings = vb.draft_key_hint(self.config)
        self.assertTrue(any("引用符" in w for w in warnings))
        with patch.dict(os.environ, {"FAL_KEY": "FAL_KEY=fal_sk_0123456789abcdef"}):
            _, warnings = vb.draft_key_hint(self.config)
        self.assertTrue(any("余計な文字" in w for w in warnings))

    def test_form_page_shows_key_hint(self):
        client = web_app.app.test_client()
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
        with patch.dict(os.environ, {"FAL_KEY": "fal_sk_0123456789abcdefWXYZ"}), \
                patch.object(video_brief_web, "get_store", return_value=self.store):
            html = client.get("/video-brief").get_data(as_text=True)
        self.assertIn("fal_sk_…WXYZ（27文字）", html)
        self.assertNotIn("0123456789", html)

    def test_connection_error_never_shows_the_key(self):
        def boom(url, json=None, headers=None, timeout=None):
            raise ValueError(f"bad header value: {headers['Authorization']!r}")
        with patch.dict(os.environ, {"FAL_KEY": "fal_sk_secret123"}):
            with self.assertRaises(RuntimeError) as cm:
                vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=boom)
        self.assertNotIn("secret", str(cm.exception))
        self.assertIn("***", str(cm.exception))

    def test_payload_matches_fal_seedance_input(self):
        vb.start_draft("a cat", 5, "2.39:1", self.config, self.store, http_post=self._post)
        _, payload, _ = self.posts[0]
        self.assertEqual(payload["aspect_ratio"], "21:9")
        self.assertEqual(payload["duration"], "5")
        self.assertIs(payload["generate_audio"], False)
        self.assertTrue({"prompt", "resolution", "duration", "aspect_ratio"} <= set(payload))

    def test_image_url_switches_to_image_to_video(self):
        vb.start_draft("a cat", 5, "16:9", self.config, self.store, image_url="https://ex.com/a.png", http_post=self._post)
        url, payload, _ = self.posts[0]
        self.assertTrue(url.endswith(self.config["draft"]["image_to_video_model"]))
        self.assertEqual(payload["image_url"], "https://ex.com/a.png")

    def test_budget_blocks_before_calling_api(self):
        for _ in range(10):
            vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=self._post)  # 100円×10 = 1000円
        with self.assertRaises(ValueError) as cm:
            vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=self._post)
        self.assertIn("上限", str(cm.exception))
        self.assertEqual(len(self.posts), 10)

    def test_failed_drafts_do_not_count_and_last_month_resets(self):
        self.store.save({"id": "a", "created_at": "2026-09-30T23:00:00+09:00", "status": "done", "cost_jpy": 900})
        self.store.save({"id": "b", "created_at": "2026-10-01T00:10:00+09:00", "status": "failed", "cost_jpy": 900})
        self.store.save({"id": "c", "created_at": "2026-10-02T10:00:00+09:00", "status": "done", "cost_jpy": 300})
        now = datetime(2026, 10, 20, tzinfo=vb.JST)
        self.assertEqual(vb.spent_this_month(self.store.all(), now), 300)

    def test_missing_key_or_disabled_is_refused(self):
        with patch.dict(os.environ, {"FAL_KEY": ""}):
            with self.assertRaises(ValueError):
                vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=self._post)
        self.config["draft"]["enabled"] = False
        with self.assertRaises(ValueError):
            vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=self._post)
        self.assertEqual(self.posts, [])

    def test_refresh_draft_records_video_url(self):
        d = vb.start_draft("a", 5, "16:9", self.config, self.store, http_post=self._post)
        answers = {d["status_url"]: Resp(200, {"status": "IN_PROGRESS"})}
        get = lambda url, headers=None, timeout=None: answers[url]
        self.assertEqual(vb.refresh_draft(d, self.config, self.store, http_get=get)["status"], "running")
        answers[d["status_url"]] = Resp(200, {"status": "COMPLETED"})
        answers[d["response_url"]] = Resp(200, {"video": {"url": "https://v.fal.media/out.mp4"}})
        d = vb.refresh_draft(d, self.config, self.store, http_get=get)
        self.assertEqual((d["status"], d["video_url"]), ("done", "https://v.fal.media/out.mp4"))
        self.assertEqual(self.store.get(d["id"])["status"], "done")

    def test_web_draft_endpoints(self):
        client = web_app.app.test_client()
        self.assertEqual(client.post("/video-brief/draft", json={}).status_code, 401)
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        self.assertEqual(client.post("/video-brief/draft", json={"csrf_token": "x"}).status_code, 400)
        r = client.post("/video-brief/draft", json={"csrf_token": "tok", "prompt": "a", "image_url": "javascript:x"})
        self.assertEqual(r.status_code, 400)
        fake = {"id": "abc", "status": "queued", "cost_jpy": 100}
        with patch.object(video_brief_web, "get_store", return_value=self.store), \
                patch.object(vb, "start_draft", return_value=fake) as start:
            r = client.post("/video-brief/draft", json={"csrf_token": "tok", "prompt": "a", "seconds": 5, "aspect": "9:16"})
        self.assertEqual(r.get_json()["id"], "abc")
        self.assertEqual(start.call_args.args[2], "9:16")

    def test_result_page_shows_draft_buttons_only_with_key(self):
        client = web_app.app.test_client()
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        brief = _brief([_cut(0, 15, first_frame="三面図"), _cut(15, 30)])
        data = {"csrf_token": "tok", "genre": "anime", "subject": "x", "seconds": "30", "aspect": "16:9"}
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), patch.object(vb, "generate_brief", return_value=brief):
            html = client.post("/video-brief/generate", data=data).get_data(as_text=True)
            self.assertIn("下書きを作る（15秒", html)
            with patch.dict(os.environ, {"FAL_KEY": ""}):
                html = client.post("/video-brief/generate", data=data).get_data(as_text=True)
            self.assertNotIn("下書きを作る（", html)



class LoadMarkdownTest(unittest.TestCase):
    def setUp(self):
        self.config = vb.load_config()
        self.genre = vb.get_genre(self.config, "anime")
        cuts = [_cut(0, 4, "ほかほか", first_frame="三面図"), _cut(4, 9), _cut(9, 15)]
        cuts[1]["video_prompt"] = "steam rises\nfrom a sweet potato"
        cuts[2]["scene"] = "お店|カウンター"
        form = {"subject": "焼きいも", "seconds": 15, "aspect": "9:16", "goal": ""}
        self.md, _ = vb.to_markdown(_brief(cuts), form, self.genre, self.config)

    def test_round_trip_keeps_cut_numbers_times_and_prompts(self):
        form, brief = vb.parse_markdown(self.md, self.config)
        self.assertEqual((form["subject"], form["seconds"], form["aspect"], form["genre"]), ("焼きいも", 15, "9:16", "anime"))
        self.assertEqual([(c["no"], c["start"], c["end"]) for c in brief["cuts"]], [(1, 0, 4), (2, 4, 9), (3, 9, 15)])
        self.assertEqual(brief["cuts"][1]["video_prompt"], "steam rises\nfrom a sweet potato")
        self.assertEqual(brief["cuts"][2]["scene"], "お店／カウンター")
        self.assertEqual(brief["cuts"][0]["first_frame"], "三面図")
        self.assertEqual(brief["cuts"][0]["image_url"], "")

    def test_image_url_written_in_markdown_is_prefilled(self):
        md = self.md.replace("- 最初の画像: 三面図", "- 最初の画像: 三面図 https://ex.com/cut1.png")
        md = md.replace("### カット2（4–9秒）", "### カット2（4–9秒）\n- 画像URL: https://ex.com/cut2.png")
        _, brief = vb.parse_markdown(md, self.config)
        self.assertEqual([c["image_url"] for c in brief["cuts"]], ["https://ex.com/cut1.png", "https://ex.com/cut2.png", ""])

    def test_reference_lines_in_markdown_are_loaded(self):
        self.assertIn("- 参照画像: （任意", self.md)
        md = self.md.replace("### カット2（4–9秒）",
                             "### カット2（4–9秒）\n- 参照画像: https://ex.com/sheet.png キャラ三面図\n- 参照画像: https://ex.com/item.png 商品")
        _, brief = vb.parse_markdown(md, self.config)
        self.assertEqual(brief["cuts"][0]["references"], [])
        self.assertEqual([r["label"] for r in brief["cuts"][1]["references"]], ["キャラ三面図", "商品"])
        client = web_app.app.test_client()
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        with patch.dict(os.environ, {"FAL_KEY": "k"}):
            html = client.post("/video-brief/load", data={"csrf_token": "tok", "markdown": md}).get_data(as_text=True)
        self.assertIn("https://ex.com/sheet.png キャラ三面図\nhttps://ex.com/item.png 商品</textarea>", html)

    def test_no_cuts_is_an_error(self):
        with self.assertRaises(ValueError):
            vb.parse_markdown("# メモ\nただの文章", self.config)

    def test_web_load_shows_same_cuts_with_draft_buttons(self):
        client = web_app.app.test_client()
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        md = self.md.replace("- 最初の画像: 三面図", "- 最初の画像: https://ex.com/a.png")
        with patch.dict(os.environ, {"FAL_KEY": "k"}):
            html = client.post("/video-brief/load", data={"csrf_token": "tok", "markdown": md}).get_data(as_text=True)
        self.assertIn("カット3本・画像URLあり1本", html)
        self.assertIn("<b>カット2</b>", html)
        self.assertIn('value="https://ex.com/a.png"', html)
        self.assertIn("下書きを作る（5秒", html)
        self.assertEqual(client.post("/video-brief/load", data={"csrf_token": "x", "markdown": md}).status_code, 400)
        r = client.post("/video-brief/load", data={"csrf_token": "tok", "markdown": "なにもない"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("カットが見つかりませんでした", r.get_data(as_text=True))

    def test_form_page_has_load_section(self):
        client = web_app.app.test_client()
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        html = client.get("/video-brief").get_data(as_text=True)
        self.assertIn('action="/video-brief/load"', html)
        self.assertNotIn("__CSRF__", html)



class CharacterSetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = vb.load_config()
        self.chars = vb.CharacterStore(database_url="", file_path=Path(self.tmp.name) / "chars.json")
        self.patcher = patch.object(video_brief_web, "get_char_store", return_value=self.chars)
        self.patcher.start()
        self.client = web_app.app.test_client()
        with self.client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def test_make_character_validates(self):
        c = vb.make_character(" しー ", "https://drive.google.com/file/d/X1/view 三面図\nhttps://ex.com/b.png 衣装", self.config)
        self.assertEqual(c["name"], "しー")
        self.assertEqual(c["images"][0]["url"], "https://drive.google.com/uc?export=download&id=X1")
        for name, text in [("", "https://ex.com/a.png"), ("a", ""), ("a", "http://ex.com/a.png")]:
            with self.assertRaises(ValueError):
                vb.make_character(name, text, self.config)

    def test_page_add_edit_delete(self):
        self.assertEqual(self.client.get("/video-brief/characters").status_code, 200)
        r = self.client.post("/video-brief/characters", data={"csrf_token": "tok", "name": "しー",
                                                              "images": "https://ex.com/a.png 三面図"})
        self.assertIn("「しー」を保存しました", r.get_data(as_text=True))
        cid = self.chars.sets()[0]["id"]
        r = self.client.post("/video-brief/characters", data={"csrf_token": "tok", "name": "しー",
                                                              "images": "https://ex.com/x.png 別"})
        self.assertIn("もう登録されています", r.get_data(as_text=True))
        html = self.client.get(f"/video-brief/characters?edit={cid}").get_data(as_text=True)
        self.assertIn("https://ex.com/a.png 三面図</textarea>", html)
        self.client.post("/video-brief/characters", data={"csrf_token": "tok", "id": cid, "name": "しー",
                                                          "images": "https://ex.com/a.png 三面図\nhttps://ex.com/c.png 衣装"})
        self.assertEqual(len(self.chars.get(cid)["images"]), 2)
        self.assertEqual(self.client.post("/video-brief/characters", data={"csrf_token": "x", "id": cid,
                                                                          "action": "delete"}).status_code, 400)
        self.client.post("/video-brief/characters", data={"csrf_token": "tok", "id": cid, "action": "delete"})
        self.assertEqual(self.chars.sets(), [])

    def test_requires_login(self):
        client = web_app.app.test_client()
        self.assertEqual(client.get("/video-brief/characters").status_code, 302)

    def test_dropdown_and_markdown_sets(self):
        self.chars.save(vb.make_character("しー", "https://ex.com/sheet.png 三面図\nhttps://ex.com/cos.png 衣装", self.config))
        genre = vb.get_genre(self.config, "anime")
        md, _ = vb.to_markdown(_brief([_cut(0, 5, first_frame="三面図"), _cut(5, 10)]),
                               {"subject": "x", "seconds": 10, "aspect": "16:9"}, genre, self.config)
        self.assertIn("- 参照セット: （任意", md)
        md = md.replace("### カット2（5–10秒）", "### カット2（5–10秒）\n- 参照セット: しー\n- 参照セット: いない人"
                        "\n- 参照画像: https://ex.com/sheet.png 重複")
        with patch.dict(os.environ, {"FAL_KEY": "k"}):
            html = self.client.post("/video-brief/load", data={"csrf_token": "tok", "markdown": md}).get_data(as_text=True)
        self.assertIn("登録されていない参照セット: いない人", html)
        self.assertIn("https://ex.com/sheet.png 三面図\nhttps://ex.com/cos.png 衣装</textarea>", html)
        self.assertIn("＋ キャラの参照画像セットを追加", html)
        self.assertIn("しー（2枚）", html)
        self.assertIn("const CHARSETS = {", html)



def _make_clip(path, size, seconds=1):
    import subprocess
    subprocess.run([vb.ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"testsrc=size={size}:rate=24:duration={seconds}", "-pix_fmt", "yuv420p", str(path)], check=True)


class FileResp:
    def __init__(self, path, status_code=200):
        self.status_code = status_code
        self.path = path

    def iter_content(self, chunk_size=1024):
        with open(self.path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk


@unittest.skipUnless(vb.ffmpeg_exe(), "ffmpeg がない環境")
class ConcatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.clips = {"https://v.fal.media/a.mp4": root / "a.mp4", "https://v.fal.media/b.mp4": root / "b.mp4"}
        _make_clip(self.clips["https://v.fal.media/a.mp4"], "320x240")
        _make_clip(self.clips["https://v.fal.media/b.mp4"], "240x320")  # 向きが違っても余白でそろえる
        self.get = lambda url, stream=True, timeout=None: FileResp(self.clips[url])
        self.dir_patch = patch.object(vb, "CONCAT_DIR", root / "out")
        self.dir_patch.start()
        self.store = vb.DraftStore(database_url="", file_path=root / "drafts.json")
        for i, (url, cut) in enumerate([("https://v.fal.media/a.mp4", "1"), ("https://v.fal.media/b.mp4", "2")]):
            self.store.save({"id": f"d{i}", "status": "done", "video_url": url, "aspect": "16:9", "seconds": 1,
                             "subject": "焼きいも", "cut": cut, "created_at": f"2026-10-20T10:0{i}:00+09:00"})
        self.store.save({"id": "q", "status": "running", "video_url": "", "created_at": "2026-10-20T11:00:00+09:00"})

    def tearDown(self):
        self.dir_patch.stop()
        self.tmp.cleanup()

    def _duration(self, path):
        import subprocess
        r = subprocess.run([vb.ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True)
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

    def test_make_concat_joins_in_order(self):
        drafts = [self.store.get("d1"), self.store.get("d0")]
        job_id, out = vb.make_concat(drafts, http_get=self.get)
        self.assertEqual(vb.concat_path(job_id), out)
        self.assertAlmostEqual(self._duration(out), 2.0, delta=0.2)
        self.assertEqual(sorted(p.name for p in out.parent.iterdir()), ["connected.mp4"])

    def test_make_concat_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            vb.make_concat([self.store.get("d0")], http_get=self.get)
        with self.assertRaises(ValueError):
            vb.make_concat([self.store.get("d0"), self.store.get("q")], http_get=self.get)
        expired = lambda url, stream=True, timeout=None: FileResp(None, status_code=403)
        with self.assertRaises(RuntimeError):
            vb.make_concat([self.store.get("d0"), self.store.get("d1")], http_get=expired)
        self.assertIsNone(vb.concat_path("../etc"))

    def test_web_drafts_page_and_concat(self):
        client = web_app.app.test_client()
        self.assertEqual(client.get("/video-brief/drafts").status_code, 302)
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        with patch.object(video_brief_web, "get_store", return_value=self.store):
            html = client.get("/video-brief/drafts").get_data(as_text=True)
            self.assertIn('name="order_d0" value="1"', html)  # 最新案件のカット番号が順番に入る
            self.assertIn('name="order_d1" value="2"', html)
            self.assertNotIn("order_q", html)
            self.assertEqual(client.post("/video-brief/drafts", data={"csrf_token": "x"}).status_code, 400)
            with patch("requests.get", self.get):
                html = client.post("/video-brief/drafts", data={"csrf_token": "tok", "order_d0": "2", "order_d1": "1"}
                                   ).get_data(as_text=True)
        self.assertIn("2本をつなぎました", html)
        job_id = re.search(r"/video-brief/concat/([0-9a-f]{32})\.mp4", html).group(1)
        r = client.get(f"/video-brief/concat/{job_id}.mp4")
        self.assertEqual((r.status_code, r.mimetype), (200, "video/mp4"))
        r.close()
        self.assertEqual(client.get("/video-brief/concat/" + "0" * 32 + ".mp4").status_code, 404)

    def test_draft_meta_is_recorded(self):
        config = vb.load_config()
        config["draft"].update(enabled=True)
        post = lambda url, json=None, headers=None, timeout=None: Resp(200, {"status_url": "https://q/s", "response_url": "https://q/r"})
        with patch.dict(os.environ, {"FAL_KEY": "k"}):
            d = vb.start_draft("a", 4, "16:9", config, self.store, http_post=post, meta={"cut": 3, "subject": "焼きいも"})
        self.assertEqual((d["cut"], d["subject"]), ("3", "焼きいも"))



class TelopTest(unittest.TestCase):
    def setUp(self):
        self.config = vb.load_config()
        c1 = _cut(0, 4, "今日、冷えるね。")
        c2 = _cut(4, 10, "ほくほくの焼きいも、ひとつください！あと温かいお茶もお願いします。")
        c3 = _cut(10, 15)
        c3["text_overlay"] = "=秋限定 焼きいも"
        self.brief = _brief([c1, c2, c3])

    def test_split_caption_keeps_each_piece_short(self):
        pieces = vb._split_caption("ほくほくの焼きいも、ひとつください！あと温かいお茶もお願いします。")
        self.assertEqual(pieces[0], "ほくほくの焼きいも、ひとつください！")
        self.assertTrue(all(vb.count_chars(p) <= 16 for p in pieces))
        self.assertEqual("".join(pieces), "ほくほくの焼きいも、ひとつください！あと温かいお茶もお願いします。")

    def test_telops_timing_and_kinds(self):
        items = vb.telops(self.brief)
        self.assertEqual(items[0], {"start": 0.0, "end": 4.0, "cut": 1, "kind": "セリフ", "text": "今日、冷えるね。"})
        cut2 = [x for x in items if x["cut"] == 2]
        self.assertEqual((cut2[0]["start"], cut2[-1]["end"]), (4.0, 10.0))
        self.assertTrue(all(a["end"] == b["start"] for a, b in zip(cut2, cut2[1:])))
        self.assertEqual(items[-1]["kind"], "画面の文字")

    def test_srt_and_csv(self):
        items = vb.telops(self.brief)
        srt = vb.to_srt(items)
        self.assertTrue(srt.startswith("1\n00:00:00,000 --> 00:00:04,000\n今日、冷えるね。\n\n"))
        self.assertNotIn("秋限定", srt)
        csv_text = vb.to_telop_csv(items)
        self.assertTrue(csv_text.startswith("\ufeff開始(秒),終了(秒),カット,種類,文言"))
        self.assertIn("'=秋限定 焼きいも", csv_text)

    def test_markdown_round_trip_keeps_dialogue_and_overlay(self):
        md, _ = vb.to_markdown(self.brief, {"subject": "x", "seconds": 15, "aspect": "16:9"},
                               vb.get_genre(self.config, "anime"), self.config)
        _, loaded = vb.parse_markdown(md, self.config)
        self.assertEqual(loaded["cuts"][0]["dialogue"], "今日、冷えるね。")
        self.assertEqual(loaded["cuts"][2]["dialogue"], "")
        self.assertEqual(loaded["cuts"][2]["text_overlay"], "=秋限定 焼きいも")
        self.assertEqual(vb.telops(loaded), vb.telops(self.brief))

    def test_result_pages_show_telop_buttons(self):
        client = web_app.app.test_client()
        with client.session_transaction() as s:
            s["video_brief_ok"] = True
            s["video_brief_csrf"] = "tok"
        data = {"csrf_token": "tok", "genre": "anime", "subject": "x", "seconds": "15", "aspect": "16:9"}
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "x"}), patch.object(vb, "generate_brief", return_value=self.brief):
            html = client.post("/video-brief/generate", data=data).get_data(as_text=True)
        self.assertIn("📝 テロップ一覧（CSV）", html)
        self.assertIn("💬 セリフ字幕（SRT）", html)
        self.assertIn("<td>今日、冷えるね。</td>", html)
        self.assertNotIn("</script>\\u003c", html)
        md, _ = vb.to_markdown(self.brief, {"subject": "x", "seconds": 15, "aspect": "16:9"},
                               vb.get_genre(self.config, "anime"), self.config)
        html = client.post("/video-brief/load", data={"csrf_token": "tok", "markdown": md}).get_data(as_text=True)
        self.assertIn("📝 テロップ一覧（CSV）", html)
        self.assertIn("<td>=秋限定 焼きいも</td>", html)


if __name__ == "__main__":
    unittest.main()
