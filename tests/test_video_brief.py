import json
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

    def test_config_has_seven_genres_with_references(self):
        genres = self.config["genres"]
        self.assertEqual(len(genres), 7)
        self.assertEqual(len({g["id"] for g in genres}), 7)
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


if __name__ == "__main__":
    unittest.main()
