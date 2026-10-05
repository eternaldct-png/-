import json
import unittest

from src import web_app
import waku_tracker  # web_app と同じモジュール（src を sys.path に入れて読み込まれる）


class WakuConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = waku_tracker.load_config()
        self.tiers = {t["label"]: t for t in self.config["tiers"]}

    def test_tiers_match_the_uta_oshi_calculator(self):
        # 歌推し計算ツールの 10pt〜49K（55段階）と、50K〜100K の計算式
        self.assertEqual(len(self.config["tiers"]), 55 + 51)
        self.assertEqual(
            self.tiers["10pt"]["patterns"],
            [
                {"coins": 1, "viewing_hours": 0.25, "super_like_days": 0},
                {"coins": 10, "viewing_hours": 0.1, "super_like_days": 0},
                {"coins": 30, "viewing_hours": 0, "super_like_days": 0},
            ],
        )
        self.assertEqual(
            self.tiers["1K"]["patterns"][0],
            {"coins": 80, "viewing_hours": 1.75, "super_like_days": 4},
        )
        self.assertEqual(self.tiers["49K"]["patterns"][2]["coins"], 2200000)

    def test_50k_and_above_use_the_calculator_formula(self):
        # coins = base + (K - 49) × 500,000
        self.assertEqual(
            [p["coins"] for p in self.tiers["50K"]["patterns"]],
            [2500000, 2600000, 2700000],
        )
        self.assertEqual(self.tiers["60K"]["patterns"][0]["coins"], 2000000 + 11 * 500000)
        self.assertEqual(
            [p["viewing_hours"] for p in self.tiers["100K"]["patterns"]], [14, 6, 0]
        )
        self.assertEqual(
            [t["pt"] for t in self.config["tiers"]],
            sorted(t["pt"] for t in self.config["tiers"]),
        )

    def test_dropdown_options_and_default_target(self):
        self.assertIn(60, self.config["viewing_minutes"])
        self.assertIn(100, self.config["coin_presets"])
        self.assertIn(self.config["default_target"], self.tiers)

    def test_uta_oshi_starts_at_1k_but_lower_tiers_stay_for_each_jun(self):
        # 歌推しは月間1Kから。旬ごとの推しPt（0.3K など）の計算には下の段階も使う
        self.assertEqual(self.config["default_target"], "1K")
        self.assertEqual(self.config["targets"][0], "1K")
        self.assertEqual(len(self.config["targets"]), 49 - 1 + 1 + 51)
        self.assertIn("0.3K", self.tiers)
        self.assertNotIn("0.7K", self.config["targets"])


class WakuPageTest(unittest.TestCase):
    def setUp(self):
        self.client = web_app.app.test_client()

    def test_page_opens_without_login_and_embeds_the_conditions(self):
        response = self.client.get("/waku")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('name="password"', html)

        start = html.index("const CONFIG = ") + len("const CONFIG = ")
        config = json.loads(html[start:html.index(";\n", start)])
        self.assertEqual(len(config["tiers"]), 106)
        self.assertEqual(config["default_target"], waku_tracker.load_config()["default_target"])

    def test_records_stay_in_the_browser(self):
        html = self.client.get("/waku").get_data(as_text=True)
        self.assertIn("localStorage", html)
        for option in ('value="came"', 'value="went"', 'value="missed"'):
            self.assertIn(option, html)
        # サーバー側に記録を受け取る口はない
        self.assertEqual(self.client.post("/waku").status_code, 405)
        self.assertEqual(self.client.get("/api/waku/records").status_code, 404)


if __name__ == "__main__":
    unittest.main()
