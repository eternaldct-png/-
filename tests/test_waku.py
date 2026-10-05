import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(self.config["slots"][0], "指定なし")
        self.assertIn(60, self.config["viewing_minutes"])
        self.assertIn(100, self.config["coin_presets"])
        self.assertIn(self.config["default_target"], self.tiers)


class WakuRecordTest(unittest.TestCase):
    def setUp(self):
        self.config = waku_tracker.load_config()

    def build(self, **overrides):
        data = {
            "date": "2026-10-05", "slot": "夜枠", "host": "あまりん", "visitor": "さな",
            "status": "went", "viewing_minutes": "30", "coins": "100", "super_like": True,
        }
        data.update(overrides)
        return waku_tracker.build_record(data, self.config)

    def test_jun_boundaries(self):
        self.assertEqual(
            [waku_tracker.jun_of(d) for d in (1, 10, 11, 20, 21, 31)],
            ["上旬", "上旬", "中旬", "中旬", "下旬", "下旬"],
        )

    def test_went_record_keeps_amounts_and_normalizes_names(self):
        record, error = self.build(host="  あまりん ", visitor="さな　 ちゃん")
        self.assertIsNone(error)
        self.assertEqual(record["host"], "あまりん")
        self.assertEqual(record["visitor"], "さな ちゃん")
        self.assertEqual(
            (record["viewing_minutes"], record["coins"], record["super_like"]),
            (30, 100, True),
        )
        self.assertEqual(waku_tracker.with_jun(record)["jun"], "上旬")

    def test_missed_record_drops_amounts(self):
        record, error = self.build(status="missed")
        self.assertIsNone(error)
        self.assertEqual(
            (record["status"], record["viewing_minutes"], record["coins"], record["super_like"]),
            ("missed", 0, 0, False),
        )

    def test_blank_visitor_registers_only_the_frame(self):
        record, error = self.build(visitor="", status="went")
        self.assertIsNone(error)
        self.assertEqual((record["visitor"], record["status"], record["coins"]), ("", "", 0))

    def test_unknown_slot_falls_back_to_first_option(self):
        record, _ = self.build(slot="存在しない枠")
        self.assertEqual(record["slot"], "指定なし")

    def test_invalid_input_is_rejected(self):
        cases = [
            ({"date": "2026-02-30"}, "日付"),
            ({"date": "1999-12-31"}, "日付"),
            ({"host": ""}, "配信した人"),
            ({"visitor": "あまりん"}, "同じ名前"),
            ({"status": "maybe"}, "行けた"),
            ({"coins": "-5"}, "コイン"),
            ({"coins": "abc"}, "コイン"),
            ({"viewing_minutes": "99999"}, "視聴時間"),
            ({"host": "あ" * 41}, "40文字"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                record, error = self.build(**overrides)
                self.assertIsNone(record)
                self.assertIn(message, error)

    def test_month_range(self):
        self.assertEqual(
            [d.isoformat() for d in waku_tracker.month_range("2026-02")],
            ["2026-02-01", "2026-02-28"],
        )
        self.assertIsNone(waku_tracker.month_range("2026-13"))
        self.assertIsNone(waku_tracker.month_range("../etc"))


class WakuApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        file_patch = patch.object(waku_tracker, "WAKU_FILE", Path(self.tmp.name) / "waku.json")
        file_patch.start()
        self.addCleanup(file_patch.stop)
        env_patch = patch.dict(os.environ, {"WAKU_PASSWORD": "liver-pass", "WEB_PASSWORD": "admin-pass"})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        os.environ.pop("DATABASE_URL", None)

        self.client = web_app.app.test_client()
        with self.client.session_transaction() as session:
            session["waku_ok"] = True
            session["waku_csrf"] = "token"

    def create(self, **overrides):
        body = {
            "csrf_token": "token", "date": "2026-10-05", "slot": "夜枠", "host": "あまりん",
            "visitor": "さな", "status": "went", "viewing_minutes": "45", "coins": "20",
            "super_like": True,
        }
        body.update(overrides)
        return self.client.post("/api/waku/records", json=body)

    def test_login_is_required(self):
        client = web_app.app.test_client()
        page = client.get("/waku")
        self.assertEqual(page.status_code, 200)
        self.assertIn('name="password"', page.get_data(as_text=True))
        self.assertNotIn("CONFIG", page.get_data(as_text=True))
        self.assertEqual(client.get("/api/waku/records?month=2026-10").status_code, 401)
        self.assertEqual(client.post("/api/waku/records", json={}).status_code, 401)

    def test_waku_password_logs_in_and_admin_password_does_not(self):
        client = web_app.app.test_client()
        self.assertEqual(client.post("/waku", data={"password": "admin-pass"}).status_code, 401)
        response = client.post("/waku", data={"password": "liver-pass"})
        self.assertEqual(response.status_code, 302)
        page = client.get("/waku").get_data(as_text=True)
        self.assertIn("const CONFIG =", page)
        self.assertIn('"default_target"', page)

    def test_web_password_is_used_when_waku_password_is_unset(self):
        os.environ.pop("WAKU_PASSWORD")
        client = web_app.app.test_client()
        self.assertEqual(client.post("/waku", data={"password": "admin-pass"}).status_code, 302)

    def test_create_list_and_delete(self):
        response = self.create()
        self.assertEqual(response.status_code, 200)
        record = response.get_json()["record"]
        self.assertEqual((record["jun"], record["coins"]), ("上旬", 20))

        self.create(date="2026-10-15", visitor="しー", status="missed")
        self.create(date="2026-11-01", visitor="")

        data = self.client.get("/api/waku/records?month=2026-10").get_json()
        self.assertEqual(data["storage"], "file")
        self.assertEqual(
            [(r["date"], r["visitor"], r["status"], r["jun"]) for r in data["records"]],
            [("2026-10-05", "さな", "went", "上旬"), ("2026-10-15", "しー", "missed", "中旬")],
        )
        self.assertEqual(data["names"], sorted(["あまりん", "さな", "しー"]))
        self.assertEqual(data["months"], ["2026-11", "2026-10"])

        deleted = self.client.post(
            f"/api/waku/records/{record['id']}/delete", json={"csrf_token": "token"}
        )
        self.assertEqual(deleted.status_code, 200)
        again = self.client.post(
            f"/api/waku/records/{record['id']}/delete", json={"csrf_token": "token"}
        )
        self.assertEqual(again.status_code, 404)
        remaining = self.client.get("/api/waku/records?month=2026-10").get_json()["records"]
        self.assertEqual([r["visitor"] for r in remaining], ["しー"])

    def test_writes_require_csrf_token(self):
        self.assertEqual(self.create(csrf_token="wrong").status_code, 403)
        self.assertEqual(
            self.client.post("/api/waku/records/x/delete", json={}).status_code, 403
        )
        self.assertFalse(waku_tracker.WAKU_FILE.exists())

    def test_validation_errors_are_returned(self):
        response = self.create(host="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("配信した人", response.get_json()["error"])
        self.assertEqual(
            self.client.get("/api/waku/records?month=2026-1").status_code, 400
        )

    def test_unreachable_database_is_an_error_not_a_silent_file_fallback(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://example.invalid/db"}):
            with patch.object(waku_tracker, "_db_conn", return_value=None):
                with patch("time.sleep"):
                    self.assertEqual(self.create().status_code, 500)
                self.assertEqual(
                    self.client.get("/api/waku/records?month=2026-10").status_code, 500
                )
        self.assertFalse(waku_tracker.WAKU_FILE.exists())

    def test_page_embeds_config_without_breaking_script(self):
        page = self.client.get("/waku").get_data(as_text=True)
        start = page.index("const CONFIG = ") + len("const CONFIG = ")
        config = json.loads(page[start:page.index(";\n", start)])
        self.assertEqual(config["csrf_token"], "token")
        self.assertEqual(len(config["tiers"]), 106)
        self.assertEqual(config["storage"], "file")


if __name__ == "__main__":
    unittest.main()
