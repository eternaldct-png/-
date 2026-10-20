import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import web_app
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


if __name__ == "__main__":
    unittest.main()
