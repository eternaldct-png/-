import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src import web_app
import sales_leads as sl  # web_app と同じモジュール（src を sys.path に入れて読み込まれる）
import sales_leads_web

ME = "1000"
LEAD_UID = "2000"


def _event(event_id, sender, text):
    return SimpleNamespace(
        id=event_id, text=text, sender_id=sender, created_at="",
        dm_conversation_id=f"{ME}-{LEAD_UID}", participant_ids=[ME, LEAD_UID],
    )


class FakeX:
    """tweepy.Client の代わり。get_direct_message_events は新しい順に返す。"""

    def __init__(self, events=None):
        self.events = list(events or [])
        self.sent = []

    def get_me(self, user_auth=True):
        return SimpleNamespace(data=SimpleNamespace(id=ME))

    def get_direct_message_events(self, **params):
        data = sorted(self.events, key=lambda e: int(e.id), reverse=True)
        return SimpleNamespace(data=data, meta={})

    def create_direct_message(self, participant_id=None, text=None, user_auth=True):
        self.sent.append((participant_id, text))
        return SimpleNamespace(data={"dm_event_id": str(9000 + len(self.sent))})


def _config(**agent):
    config = sl.load_config()
    config["agent"] = {**config["agent"], "active_hours": [0, 24], "mode": "auto", **agent}
    return config


NOON = datetime(2026, 10, 9, 12, 0, tzinfo=sl.JST)


class SalesLeadsLogicTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = sl.LeadStore(database_url="", file_path=Path(self.tmp.name) / "leads.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _lead(self, **fields):
        lead = sl.new_lead("customer", **{"x_user_id": LEAD_UID, "status": "sent", **fields})
        self.store.save(lead)
        return lead

    def _run(self, fake, config=None, reply=None, notes=None, now=NOON):
        notes = notes if notes is not None else []
        reply = reply or (lambda lead, cfg: {"reply": "ご返信ありがとうございます！", "handoff": False, "reason": ""})
        return sl.run_agent(self.store, config or _config(), client=fake, notify=notes.append, reply_fn=reply, now=now)

    def test_normalize_username(self):
        self.assertEqual(sl.normalize_username("@shop_owner"), "shop_owner")
        self.assertEqual(sl.normalize_username("https://x.com/shop_owner/status/123"), "shop_owner")
        self.assertEqual(sl.normalize_username("https://twitter.com/abc"), "abc")
        self.assertEqual(sl.normalize_username("not valid name"), "")
        self.assertEqual(sl.normalize_username("https://x.com/home"), "")

    def test_collect_drops_candidates_without_real_post_url(self):
        text = json.dumps([
            {"username": "@real_shop", "post_url": "https://x.com/real_shop/status/111", "post_text": "見積もりが大変"},
            {"username": "made_up", "post_url": "", "post_text": "URLなし"},
        ], ensure_ascii=False)
        response = SimpleNamespace(status_code=200, json=lambda: {"output": [
            {"type": "message", "content": [{"type": "output_text", "text": f"結果です\n{text}"}]}
        ]})
        with patch.dict(os.environ, {"XAI_API_KEY": "test"}):
            found = sl.collect_with_grok("見積もり", sl.load_config(), http_post=lambda *a, **k: response)
        self.assertEqual([c["username"] for c in found], ["real_shop"])

    def test_add_candidates_skips_duplicates(self):
        added, skipped = sl.add_candidates(self.store, [{"username": "a_shop"}, {"username": "@A_shop"}, {"username": "!!"}], "grok")
        self.assertEqual((added, skipped), (1, 2))

    def test_first_run_only_records_position(self):
        self._lead()
        fake = FakeX([_event("10", LEAD_UID, "昔のDM")])
        summary = self._run(fake)
        self.assertTrue(summary["initialized"])
        self.assertEqual(fake.sent, [])
        self.assertEqual(self.store.get_state()["last_event_id"], "10")

    def test_auto_reply_with_disclosure_once(self):
        lead = self._lead()
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        fake = FakeX([_event("11", LEAD_UID, "詳しく聞きたいです")])
        summary = self._run(fake)
        self.assertEqual(summary["replied"], 1)
        self.assertEqual(len(fake.sent), 1)
        self.assertIn("AIアシスタント", fake.sent[0][1])
        saved = self.store.get(lead["id"])
        self.assertEqual(saved["status"], "replied")
        self.assertEqual(saved["auto_reply_count"], 1)
        self.assertFalse(saved["needs_reply"])

        # 2回目の返信には「AIです」の一文を付けない。処理済みイベントには二度返さない
        fake.events.append(_event("12", LEAD_UID, "料金は？"))
        self._run(fake)
        self.assertEqual(len(fake.sent), 2)
        self.assertNotIn("AIアシスタント", fake.sent[1][1])
        self._run(fake)
        self.assertEqual(len(fake.sent), 2)

    def test_outgoing_manual_dm_marks_lead_sent(self):
        lead = self._lead(status="ready")
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        self._run(FakeX([_event("11", ME, "はじめまして")]))
        saved = self.store.get(lead["id"])
        self.assertEqual(saved["status"], "sent")
        self.assertEqual(saved["messages"][-1]["role"], "me")

    def test_stop_keyword_stops_and_never_replies_again(self):
        lead = self._lead()
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        notes = []
        fake = FakeX([_event("11", LEAD_UID, "営業DMは不要です")])
        self._run(fake, notes=notes)
        self.assertEqual(self.store.get(lead["id"])["status"], "stopped")
        self.assertEqual(len(fake.sent), 1)  # 「今後連絡しません」の一通だけ
        fake.events.append(_event("12", LEAD_UID, "まだ来る？"))
        self._run(fake, notes=notes)
        self.assertEqual(len(fake.sent), 1)
        self.assertTrue(any("配信停止" in n for n in notes))

    def test_handoff_keyword_and_ai_handoff(self):
        lead = self._lead()
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        notes = []
        fake = FakeX([_event("11", LEAD_UID, "契約の流れを教えて")])
        self._run(fake, notes=notes)
        self.assertEqual(self.store.get(lead["id"])["status"], "handoff")
        self.assertTrue(any("引き継ぎ" in n for n in notes))
        # 引き継ぎ後は自動返信せず、通知だけ
        fake.events.append(_event("12", LEAD_UID, "よろしくお願いします"))
        self._run(fake, notes=notes)
        self.assertEqual(len(fake.sent), 1)

        other = sl.new_lead("other", x_user_id="3000", status="sent")
        self.store.save(other)
        ai_handoff = lambda lead, cfg: {"reply": "", "handoff": True, "reason": "判断できない"}
        fake.events.append(SimpleNamespace(id="13", text="特殊な相談", sender_id="3000", created_at="",
                                           dm_conversation_id=f"{ME}-3000", participant_ids=[ME, "3000"]))
        self._run(fake, reply=ai_handoff, notes=notes)
        self.assertEqual(self.store.get(other["id"])["status"], "handoff")

    def test_max_auto_replies_hands_off(self):
        lead = self._lead(auto_reply_count=4)
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        self._run(FakeX([_event("11", LEAD_UID, "もう少し聞きたい")]))
        self.assertEqual(self.store.get(lead["id"])["status"], "handoff")

    def test_outside_hours_waits_until_business_hours(self):
        lead = self._lead()
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        fake = FakeX([_event("11", LEAD_UID, "夜分にすみません")])
        config = _config(active_hours=[9, 21])
        self._run(fake, config=config, now=datetime(2026, 10, 9, 23, 0, tzinfo=sl.JST))
        self.assertEqual(fake.sent, [])
        self.assertTrue(self.store.get(lead["id"])["needs_reply"])
        self._run(fake, config=config, now=datetime(2026, 10, 10, 9, 30, tzinfo=sl.JST))
        self.assertEqual(len(fake.sent), 1)

    def test_approve_mode_only_drafts(self):
        lead = self._lead()
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        fake = FakeX([_event("11", LEAD_UID, "気になります")])
        self._run(fake, config=_config(mode="approve"))
        self.assertEqual(fake.sent, [])
        self.assertIn("ご返信ありがとうございます", self.store.get(lead["id"])["pending_reply"])

    def test_unknown_sender_is_ignored_by_default(self):
        self.store.set_state({"me_id": ME, "last_event_id": "10"})
        fake = FakeX([SimpleNamespace(id="11", text="こんにちは", sender_id="5555", created_at="",
                                      dm_conversation_id=f"{ME}-5555", participant_ids=[ME, "5555"])])
        self._run(fake)
        self.assertEqual(fake.sent, [])
        self.assertEqual(self.store.leads(), [])

    def test_csv_neutralizes_formulas(self):
        lead = sl.new_lead("abc", memo="=HYPERLINK(\"x\")")
        csv_text = sl.to_csv([lead])
        self.assertTrue(csv_text.startswith("﻿"))
        self.assertIn("'=HYPERLINK", csv_text)


class SalesLeadsWebTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = sl.LeadStore(database_url="", file_path=Path(self.tmp.name) / "leads.json")
        self.patcher = patch.object(sales_leads_web, "get_store", return_value=self.store)
        self.patcher.start()
        self.client = web_app.app.test_client()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def _login(self):
        with self.client.session_transaction() as s:
            s["leads_admin_ok"] = True
            s["leads_admin_csrf"] = "tok"

    def test_admin_requires_login(self):
        response = self.client.get("/leads/admin")
        self.assertIn('type="password"', response.get_data(as_text=True))

    def test_admin_lists_candidates(self):
        self._login()
        self.store.save(sl.new_lead("shop_a", post_text="予約の電話が多くて大変", reason="予約対応に困っている"))
        html = self.client.get("/leads/admin").get_data(as_text=True)
        self.assertIn("@shop_a", html)
        self.assertIn("Xで送る", html)
        self.assertIn("予約の電話が多くて大変", html)
        self.assertNotIn("{hidden}", html)
        self.assertIn('name="csrf_token" value="tok"', html)

    def test_open_redirects_to_prefilled_dm_and_marks_sent(self):
        self._login()
        lead = sl.new_lead("shop_a", x_user_id="777")
        self.store.save(lead)
        response = self.client.post(f"/leads/admin/{lead['id']}/open", data={"csrf_token": "tok", "draft": "はじめまして"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("https://x.com/messages/compose?recipient_id=777&text=", response.headers["Location"])
        saved = self.store.get(lead["id"])
        self.assertEqual(saved["status"], "sent")
        self.assertEqual(saved["draft"], "はじめまして")

    def test_open_without_user_id_shows_copy_page(self):
        self._login()
        lead = sl.new_lead("shop_b")
        self.store.save(lead)
        with patch.object(sl, "x_configured", return_value=False):
            response = self.client.post(f"/leads/admin/{lead['id']}/open", data={"csrf_token": "tok", "draft": "こんにちは"})
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("https://x.com/shop_b", html)

    def test_post_without_csrf_is_rejected(self):
        self._login()
        lead = sl.new_lead("shop_c")
        self.store.save(lead)
        response = self.client.post(f"/leads/admin/{lead['id']}/delete", data={"csrf_token": "wrong"})
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(self.store.get(lead["id"]))

    def test_task_requires_token(self):
        with patch.dict(os.environ, {"LEADS_TASK_SECRET": "secret"}):
            self.assertEqual(self.client.get("/tasks/leads-agent?token=bad").status_code, 403)
        with patch.dict(os.environ, {"LEADS_TASK_SECRET": ""}):
            self.assertEqual(self.client.get("/tasks/leads-agent?token=").status_code, 403)


if __name__ == "__main__":
    unittest.main()
