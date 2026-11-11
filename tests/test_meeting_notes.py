"""tools/meeting_notes（自分専用の会議ノート）のテスト。本物の Claude / Whisper は呼ばない。"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.meeting_notes import transcribe
from tools.meeting_notes.app import create_app, keyword_hits, to_utc
from tools.meeting_notes.store import Store

H = {"X-Meeting-Notes": "1"}

NOTES = {
    "title": "AIのタイトル",
    "summary": "会場を渋谷に決めた。",
    "sections": [{"heading": "会場", "bullets": ["渋谷で決定"]}],
    "decisions": ["12月5日開催"],
    "action_items": [
        {"text": "見積もりを送る", "owner": "山田", "due": "金曜"},
        {"text": "告知文を書く", "owner": "", "due": ""},
    ],
}


class FakeClaude:
    def __init__(self, notes=None, stop_reason="end_turn", answer="渋谷です"):
        self.notes = notes or NOTES
        self.stop_reason = stop_reason
        self.answer = answer
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        usage = SimpleNamespace(input_tokens=100_000, output_tokens=10_000)  # Opus 5.5 で $0.6
        if self.stop_reason == "refusal":
            return SimpleNamespace(stop_reason="refusal", content=[], usage=usage)
        fmt = kw["output_config"].get("format")
        if fmt and "assignments" in fmt["schema"]["properties"]:
            text = json.dumps({"assignments": [{"line": 0, "speaker": "山田"}, {"line": 1, "speaker": "知らない人"}]}, ensure_ascii=False)
        elif fmt:
            text = json.dumps(self.notes, ensure_ascii=False)
        else:
            text = self.answer
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=text)], usage=usage)


def fake_transcriber(path, *, model_size="small", language="ja", progress=None, **_):
    if progress:
        progress(5.0, 10.0)
    return [{"speaker": "", "start": 0.0, "end": 3.0, "text": "会場は渋谷にしましょう"}], 10.0


class Base(unittest.TestCase):
    transcriber = staticmethod(fake_transcriber)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.claude = FakeClaude()
        self.app = create_app(self.dir, transcriber=self.transcriber, ai_client=self.claude, start_worker=False)
        self.c = self.app.test_client()
        self.store = self.app.extensions["mn_store"]
        self.worker = self.app.extensions["mn_worker"]

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def from_text(self, text="山田: 会場は渋谷にしましょう\n自分: 了解です", **extra):
        r = self.c.post("/api/meetings", data={"source": "transcript", "transcript_text": text, **extra}, headers=H)
        self.assertEqual(r.status_code, 200, r.get_json())
        mid = r.get_json()["id"]
        self.worker.drain()
        return mid

    def upload(self, name="a.wav", content=b"RIFF....WAVE"):
        from io import BytesIO
        r = self.c.post("/api/meetings", data={"source": "upload", "audio": (BytesIO(content), name)},
                        headers=H, content_type="multipart/form-data")
        return r


class TranscriptParsing(unittest.TestCase):
    def test_vtt_with_voice_tags_and_colon_speakers(self):
        vtt = ("WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\n<v 鈴木>配信は週3回</v>\n\n"
               "2\n00:00:04.500 --> 00:00:06.000\n<v 鈴木>できます</v>\n\n"
               "3\n00:01:05.500 --> 00:01:09.000\n佐藤: ありがとうございます\n")
        segs = transcribe.parse_transcript_text(vtt, "zoom.vtt")
        self.assertEqual([s["speaker"] for s in segs], ["鈴木", "佐藤"])
        self.assertEqual(segs[0]["text"], "配信は週3回できます")  # 同じ人の続きはつなぐ（日本語は空白を入れない）
        self.assertEqual(segs[0]["end"], 6.0)
        self.assertAlmostEqual(segs[1]["start"], 65.5)

    def test_srt(self):
        srt = "1\n00:00:01,000 --> 00:00:02,500\nこんにちは\n\n2\n00:00:03,000 --> 00:00:04,000\nよろしく\n"
        segs = transcribe.parse_transcript_text(srt, "a.srt")
        self.assertEqual([s["text"] for s in segs], ["こんにちは", "よろしく"])
        self.assertEqual(segs[0]["start"], 1.0)

    def test_plain_with_speakers_and_timestamps(self):
        segs = transcribe.parse_transcript_text("[01:02] 山田：来月の件\n自分: 了解\nhttps://example.com を見て")
        self.assertEqual(segs[0], {"speaker": "山田", "start": 62, "end": 62, "text": "来月の件"})
        self.assertEqual(segs[1]["speaker"], "自分")
        self.assertEqual(segs[2]["speaker"], "")  # URL のコロンを話者と間違えない

    def test_plain_paragraphs(self):
        segs = transcribe.parse_transcript_text("﻿今日は\n雑談でした\n")
        self.assertEqual([x["text"] for x in segs], ["今日は", "雑談でした"])  # 行ごとに話者を付けられるよう分ける

    def test_empty(self):
        self.assertEqual(transcribe.parse_transcript_text("  \n "), [])

    def test_fmt_clock(self):
        self.assertEqual(transcribe.fmt_clock(65), "01:05")
        self.assertEqual(transcribe.fmt_clock(3725), "1:02:05")
        self.assertEqual(transcribe.fmt_clock(None), "")


class Helpers(unittest.TestCase):
    def test_to_utc(self):
        self.assertEqual(to_utc("2026-11-11T01:00:00.000Z"), "2026-11-11T01:00:00+00:00")
        self.assertEqual(to_utc("2026-11-11T10:00:00+09:00"), "2026-11-11T01:00:00+00:00")
        self.assertEqual(to_utc("きのう"), "")
        self.assertEqual(to_utc(""), "")


class CoreFlow(Base):
    def test_transcript_to_notes_and_actions(self):
        mid = self.from_text()
        m = self.store.get_meeting(mid)
        self.assertEqual(m["status"], "done")
        self.assertEqual(m["title"], "AIのタイトル")  # 空ならAIのタイトル
        self.assertEqual(m["participants"], ["山田", "自分"])  # 話者から参加者を自動で入れる
        self.assertNotIn("action_items", m["notes"])
        acts = self.store.actions_for(mid)
        self.assertEqual([(a["text"], a["owner"]) for a in acts], [("見積もりを送る", "山田"), ("告知文を書く", "")])
        # 自分で付けたタイトルは上書きしない
        mid2 = self.from_text(title="自分のタイトル")
        self.assertEqual(self.store.get_meeting(mid2)["title"], "自分のタイトル")

    def test_custom_context_is_sent_to_ai(self):
        self.store.save_settings(custom_context="金額は税込で書く")
        self.from_text()
        self.assertIn("金額は税込で書く", self.claude.calls[-1]["system"])
        self.assertEqual(self.claude.calls[-1]["model"], "claude-opus-5-5")

    def test_audio_upload_is_transcribed(self):
        r = self.upload()
        self.assertEqual(r.status_code, 200)
        mid = r.get_json()["id"]
        self.worker.drain()
        m = self.store.get_meeting(mid)
        self.assertEqual(m["status"], "done")
        self.assertEqual(m["duration_sec"], 10.0)
        self.assertTrue((self.dir / "audio" / m["audio_path"]).exists())
        self.assertEqual(self.c.get(f"/m/{mid}/audio").status_code, 200)

    def test_unsupported_audio_format(self):
        r = self.upload(name="virus.exe")
        self.assertEqual(r.status_code, 400)
        self.assertIn("対応していません", r.get_json()["error"])

    def test_ai_refusal_marks_failed_and_retry_works(self):
        self.claude.stop_reason = "refusal"
        mid = self.from_text()
        m = self.store.get_meeting(mid)
        self.assertEqual(m["status"], "failed")
        self.assertIn("断りました", m["error"])
        self.claude.stop_reason = "end_turn"
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/retry", headers=H).status_code, 200)
        self.worker.drain()
        self.assertEqual(self.store.get_meeting(mid)["status"], "done")

    def test_regenerate_keeps_manual_actions_and_done_state(self):
        mid = self.from_text()
        acts = {a["text"]: a for a in self.store.actions_for(mid)}
        self.c.patch(f"/api/actions/{acts['見積もりを送る']['id']}", json={"done": True}, headers=H)
        self.c.post("/api/actions", json={"meeting_id": mid, "text": "手で足した", "owner": "自分"}, headers=H)
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/regenerate", headers=H).status_code, 200)
        # 処理中にもう一度押しても受け付けない
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/regenerate", headers=H).status_code, 409)
        self.worker.drain()
        after = {a["text"]: a for a in self.store.actions_for(mid)}
        self.assertEqual(set(after), {"見積もりを送る", "告知文を書く", "手で足した"})
        self.assertEqual(after["見積もりを送る"]["done"], 1)

    def test_edit_rename_speaker_delete(self):
        mid = self.from_text()
        r = self.c.patch(f"/api/meetings/{mid}", json={"title": "新", "tags": "営業、面談", "started_at": "2026-11-01T10:00:00+09:00"}, headers=H)
        self.assertEqual(r.status_code, 200)
        m = self.store.get_meeting(mid)
        self.assertEqual((m["title"], m["tags"], m["started_at"]), ("新", ["営業", "面談"], "2026-11-01T01:00:00+00:00"))
        self.assertEqual(self.c.patch(f"/api/meetings/{mid}", json={"started_at": "x"}, headers=H).status_code, 400)
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/speakers", json={"from": "山田", "to": "山田部長"}, headers=H).get_json()["changed"], 1)
        self.assertEqual(self.store.get_meeting(mid)["transcript"][0]["speaker"], "山田部長")
        self.assertEqual(self.c.delete(f"/api/meetings/{mid}", headers=H).status_code, 200)
        self.assertIsNone(self.store.get_meeting(mid))
        self.assertEqual(self.store.actions_for(mid), [])  # やることも一緒に消える
        self.assertEqual(self.c.get(f"/m/{mid}").status_code, 404)

    def test_delete_removes_audio_file(self):
        mid = self.upload().get_json()["id"]
        self.worker.drain()
        path = self.dir / "audio" / self.store.get_meeting(mid)["audio_path"]
        self.c.delete(f"/api/meetings/{mid}", headers=H)
        self.assertFalse(path.exists())

    def test_search_and_actions_filter(self):
        mid = self.from_text()
        self.claude.notes = {**NOTES, "summary": "予算の話", "sections": [], "decisions": [],
                             "action_items": [{"text": "予算表を作る", "owner": "", "due": ""}]}
        self.from_text("佐藤: 予算の話です", title="予算会議")
        self.assertIn("AIのタイトル", self.c.get("/?q=渋谷").get_data(as_text=True))
        self.assertNotIn("予算会議", self.c.get("/?q=渋谷").get_data(as_text=True))
        self.assertIn("当てはまる会議はありません", self.c.get("/?q=100%25").get_data(as_text=True))  # % は文字として扱う
        self.assertEqual([a["text"] for a in self.store.list_actions(owner="山田")], ["見積もりを送る"])
        self.assertEqual({a["text"] for a in self.store.list_actions(owner="__none__")}, {"告知文を書く", "予算表を作る"})
        aid = self.store.actions_for(mid)[0]["id"]
        self.c.patch(f"/api/actions/{aid}", json={"done": True}, headers=H)
        self.assertEqual(len(self.store.list_actions(state="done")), 1)
        self.assertEqual(self.c.patch(f"/api/actions/{aid}", json={"text": " "}, headers=H).status_code, 400)

    def test_ask_meeting_and_across(self):
        mid = self.from_text()
        r = self.c.post(f"/api/meetings/{mid}/ask", json={"question": "会場は？"}, headers=H)
        self.assertEqual(r.get_json()["answer"], "渋谷です")
        self.assertEqual([c["role"] for c in self.store.chat_for(mid)], ["user", "assistant"])
        r = self.c.post("/api/ask", json={"question": "渋谷の会場はどうなった？"}, headers=H)
        self.assertEqual(r.get_json()["sources"][0]["id"], mid)
        self.assertIn("<transcript>", self.claude.calls[-1]["messages"][0]["content"])  # 当たった会議は全文も渡す
        self.assertEqual(self.c.post("/api/ask", json={"question": ""}, headers=H).status_code, 400)

    def test_keyword_hits_splits_japanese(self):
        mid = self.from_text()
        self.assertEqual([m["id"] for m in keyword_hits(self.store, "先月の渋谷の件について教えて")], [mid])

    def test_export_markdown(self):
        mid = self.from_text()
        md = self.c.get(f"/m/{mid}/export.md").get_data(as_text=True)
        self.assertIn("# AIのタイトル", md)
        self.assertIn("- [ ] 見積もりを送る（山田）（金曜）", md)
        self.assertIn("山田: 会場は渋谷にしましょう", md)

    def test_settings_validation_and_backup(self):
        self.assertEqual(self.c.post("/api/settings", json={"whisper_model": "../../x"}, headers=H).status_code, 400)
        self.assertEqual(self.c.post("/api/settings", json={"whisper_model": "medium", "unknown": "x"}, headers=H).status_code, 200)
        self.assertEqual(self.store.settings()["whisper_model"], "medium")
        self.from_text()
        data = json.loads(self.c.get("/api/backup").get_data(as_text=True))
        self.assertEqual(len(data["meetings"]), 1)

    def test_every_page_renders(self):
        mid = self.from_text()
        for url in ["/", "/new", "/actions", "/actions?state=all", "/ask", "/settings", "/design", f"/m/{mid}"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_restart_requeues_unfinished(self):
        mid = self.store.create_meeting(title="", started_at="2026-11-11T00:00:00+00:00", source="transcript",
                                        transcript=[{"speaker": "", "start": None, "end": None, "text": "途中"}])
        self.store.update_meeting(mid, status="summarizing")
        app2 = create_app(self.dir, transcriber=fake_transcriber, ai_client=self.claude, start_worker=False)
        w = app2.extensions["mn_worker"]
        for m_id in app2.extensions["mn_store"].busy_meeting_ids():
            w.enqueue(m_id)
        w.drain()
        self.assertEqual(self.store.get_meeting(mid)["status"], "done")


class WithoutWhisper(Base):
    """faster-whisper が無くても、録音は保存され、あとでやり直せる（録り直せない会議を失わない）。"""

    @staticmethod
    def transcriber(path, **kw):
        raise transcribe.TranscriptionUnavailable("faster-whisper が必要です")

    def test_recording_is_kept_and_failed_with_reason(self):
        with patch.object(transcribe, "whisper_available", return_value=False):
            r = self.upload(name="recording.webm")
        self.assertEqual(r.status_code, 200)
        mid = r.get_json()["id"]
        self.worker.drain()
        m = self.store.get_meeting(mid)
        self.assertEqual(m["status"], "failed")
        self.assertIn("faster-whisper", m["error"])
        self.assertTrue((self.dir / "audio" / m["audio_path"]).exists())


class Guard(Base):
    def test_writes_need_custom_header(self):
        mid = self.from_text()
        self.assertEqual(self.c.delete(f"/api/meetings/{mid}").status_code, 403)
        self.assertEqual(self.c.post("/api/meetings", data={"source": "transcript", "transcript_text": "x"}).status_code, 403)
        self.assertIsNotNone(self.store.get_meeting(mid))

    def test_other_hosts_are_refused(self):
        self.assertEqual(self.c.get("/", headers={"Host": "evil.example.com"}).status_code, 403)
        self.assertEqual(self.c.get("/", headers={"Host": "127.0.0.1:5055"}).status_code, 200)

    def test_no_transcript_no_ask(self):
        mid = self.store.create_meeting(title="", started_at="2026-11-11T00:00:00+00:00", source="record")
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/ask", json={"question": "?"}, headers=H).status_code, 400)


class ReviewFixes(Base):
    """口コミの不満への対応（replica/fixes.md）。"""

    def test_fix1_cost_is_recorded_and_budget_stops_ai(self):
        mid = self.from_text()
        self.assertAlmostEqual(self.store.usage_for_meeting(mid), 0.6)
        self.assertIn("AI費用 約90円", self.c.get(f"/m/{mid}").get_data(as_text=True))  # $0.6 × 150円
        self.store.save_settings(monthly_budget_jpy="50")
        r = self.c.post(f"/api/meetings/{mid}/ask", json={"question": "?"}, headers=H)
        self.assertEqual(r.status_code, 502)
        self.assertIn("上限", r.get_json()["error"])
        n = len(self.claude.calls)
        mid2 = self.from_text()
        self.assertEqual(len(self.claude.calls), n)  # 上限を超えたら API を呼ばない
        self.assertEqual(self.store.get_meeting(mid2)["status"], "failed")
        self.assertEqual(self.c.post("/api/settings", json={"monthly_budget_jpy": "abc"}, headers=H).status_code, 400)

    def test_fix2_diagnostics_page(self):
        body = self.c.get("/settings").get_data(as_text=True)
        for name in ("Claude の APIキー", "文字起こし（faster-whisper）", "空き容量", "データベース", "失敗した会議"):
            self.assertIn(name, body)

    def test_fix2_diagnostics_without_key_and_whisper(self):
        from tools.meeting_notes.diagnose import run_checks
        with patch.dict("os.environ", {}, clear=True), patch.object(transcribe, "whisper_available", return_value=False):
            checks = {c["name"]: c for c in run_checks(self.dir, self.store, self.worker, testing=False)}
        self.assertFalse(checks["Claude の APIキー"]["ok"])
        self.assertIn(".env", checks["Claude の APIキー"]["fix"])
        self.assertFalse(checks["文字起こし（faster-whisper）"]["ok"])
        self.assertIn("pip install faster-whisper", checks["文字起こし（faster-whisper）"]["fix"])

    def test_fix3_speakers_per_line_and_ai_guess(self):
        mid = self.from_text("会場は渋谷にしましょう\n了解です", participants="山田、自分")
        r = self.c.post(f"/api/meetings/{mid}/guess-speakers", headers=H)
        self.assertEqual(r.get_json()["guessed"], 1)
        t = self.store.get_meeting(mid)["transcript"]
        self.assertEqual((t[0]["speaker"], t[0].get("guessed")), ("山田", True))
        self.assertEqual(t[1]["speaker"], "")  # 参加者にいない名前は付けない
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/segments/1", json={"speaker": "自分"}, headers=H).status_code, 200)
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/segments/0", json={"speaker": "山田"}, headers=H).status_code, 200)
        t = self.store.get_meeting(mid)["transcript"]
        self.assertEqual([x["speaker"] for x in t], ["山田", "自分"])
        self.assertNotIn("guessed", t[0])  # 人が直したら「推定」は外れる
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/segments/9", json={"speaker": "x"}, headers=H).status_code, 404)

    def test_fix3_guess_needs_two_participants(self):
        mid = self.from_text("こんにちは", participants="自分")
        self.assertEqual(self.c.post(f"/api/meetings/{mid}/guess-speakers", headers=H).status_code, 400)

    def test_fix4_consent_activity_log_and_retention(self):
        from io import BytesIO
        r = self.c.post("/api/meetings", data={"source": "record", "consent": "told", "audio": (BytesIO(b"x"), "r.webm")},
                        headers=H, content_type="multipart/form-data")
        mid = r.get_json()["id"]
        self.worker.drain()
        self.assertEqual(self.store.get_meeting(mid)["consent"], 1)
        self.assertIn("録音は相手に伝えた", self.c.get(f"/m/{mid}").get_data(as_text=True))
        actions = [a["action"] for a in self.store.activity()]
        self.assertIn("created", actions)
        self.assertIn("ai_notes", actions)  # AI に送ったことが記録に残る
        # 保存期間を過ぎた録音は消える（ノートは残る）
        path = self.dir / "audio" / self.store.get_meeting(mid)["audio_path"]
        self.store.update_meeting(mid, started_at="2020-01-01T00:00:00+00:00")
        self.assertEqual(self.c.post("/api/settings", json={"audio_retention_days": "30"}, headers=H).status_code, 200)
        self.assertFalse(path.exists())
        m = self.store.get_meeting(mid)
        self.assertEqual(m["audio_path"], "")
        self.assertEqual(m["status"], "done")
        self.assertIn("audio_purged", [a["action"] for a in self.store.activity()])
        self.assertIn("操作の記録", self.c.get("/settings").get_data(as_text=True))

    def test_fix5_chunked_recording_survives_and_recovers(self):
        rid = self.c.post("/api/recordings", json={"ext": "webm", "title": "落ちた会議", "consent": "told"}, headers=H).get_json()["id"]
        for i, part in enumerate([b"AAA", b"BBB"]):
            self.assertEqual(self.c.post(f"/api/recordings/{rid}/chunk?seq={i}", data=part, headers=H).status_code, 200)
        # 同じかけらの送り直しは無視、飛ばしは断る
        self.assertTrue(self.c.post(f"/api/recordings/{rid}/chunk?seq=1", data=b"BBB", headers=H).get_json()["duplicate"])
        self.assertEqual(self.c.post(f"/api/recordings/{rid}/chunk?seq=5", data=b"X", headers=H).status_code, 409)
        rec = self.store.get_recording(rid)
        self.assertEqual((self.dir / "audio" / rec["path"]).read_bytes(), b"AAABBB")
        # ブラウザが落ちた → 2分後に一覧に「途中で止まった録音」が出る
        with self.store.conn() as c:
            c.execute("UPDATE recordings SET updated_at='2020-01-01T00:00:00+00:00' WHERE id=?", (rid,))
        self.assertIn("途中で止まった録音があります", self.c.get("/").get_data(as_text=True))
        r = self.c.post(f"/api/recordings/{rid}/finish", json={"recovered": 1}, headers=H)
        mid = r.get_json()["id"]
        self.worker.drain()
        m = self.store.get_meeting(mid)
        self.assertEqual((m["title"], m["status"], m["consent"]), ("落ちた会議", "done", 1))
        self.assertNotIn("途中で止まった録音", self.c.get("/").get_data(as_text=True))
        self.assertEqual(self.c.post(f"/api/recordings/{rid}/chunk?seq=2", data=b"X", headers=H).status_code, 404)

    def test_fix5_empty_and_discarded_recordings(self):
        rid = self.c.post("/api/recordings", json={"ext": "webm"}, headers=H).get_json()["id"]
        self.assertEqual(self.c.post(f"/api/recordings/{rid}/finish", json={}, headers=H).status_code, 400)
        self.assertEqual(self.c.delete(f"/api/recordings/{rid}", headers=H).status_code, 200)
        self.assertFalse((self.dir / "audio" / f"rec-{rid}.webm").exists())
        self.assertEqual(self.c.post("/api/recordings", json={"ext": "exe"}, headers=H).status_code, 400)

    def test_fix6_actions_need_evidence_from_transcript(self):
        self.claude.notes = {**NOTES, "action_items": [
            {"text": "見積もりを送る", "owner": "山田", "due": "", "evidence": "会場は渋谷に しましょう"},
            {"text": "社長に報告する", "owner": "", "due": "", "evidence": "社長に報告しておきます"},
        ]}
        mid = self.from_text("[00:42] 山田: 会場は渋谷にしましょう\n自分: 了解です")
        acts = {a["text"]: a for a in self.store.actions_for(mid)}
        self.assertEqual((acts["見積もりを送る"]["verified"], acts["見積もりを送る"]["evidence_time"]), (1, 42))
        self.assertEqual(acts["社長に報告する"]["verified"], 0)  # 文字起こしに無い発言 = 要確認
        body = self.c.get(f"/m/{mid}").get_data(as_text=True)
        self.assertIn("要確認", body)
        self.assertIn("00:42から聞く", body)
        self.c.patch(f"/api/actions/{acts['社長に報告する']['id']}", json={"verified": True}, headers=H)
        self.assertEqual(self.store.get_action(acts["社長に報告する"]["id"])["verified"], 1)
        self.assertIn("evidence", json.dumps(self.claude.calls[-1]["output_config"]["format"]["schema"]))

    def test_fix6_vocabulary_and_quiet_mode_reach_whisper_and_ai(self):
        seen = {}

        def spy(path, **kw):
            seen.update(kw)
            return fake_transcriber(path, **kw)

        self.worker.transcriber = spy
        self.store.save_settings(vocabulary="カラーシング、歌推し\nchaco", quiet_mode="1")
        self.upload()
        self.worker.drain()
        self.assertEqual(seen["vocabulary"], ["カラーシング", "歌推し", "chaco"])
        self.assertTrue(seen["quiet"])
        self.assertIn("カラーシング、歌推し、chaco", self.claude.calls[-1]["system"])

    def test_fix8_new_meeting_while_another_is_processing(self):
        r1 = self.c.post("/api/meetings", data={"source": "transcript", "transcript_text": "一つ目"}, headers=H)
        r2 = self.c.post("/api/meetings", data={"source": "transcript", "transcript_text": "二つ目"}, headers=H)
        self.assertEqual((r1.status_code, r2.status_code), (200, 200))
        self.assertIn("処理中・処理待ち 2件", self.c.get("/").get_data(as_text=True))
        self.worker.drain()
        self.assertEqual({self.store.get_meeting(r.get_json()["id"])["status"] for r in (r1, r2)}, {"done"})

    def test_migration_adds_columns_to_old_database(self):
        import sqlite3
        d = Path(tempfile.mkdtemp())
        try:
            old = sqlite3.connect(d / "old.db")
            old.executescript("CREATE TABLE meetings (id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL,"
                              " duration_sec REAL, participants TEXT NOT NULL DEFAULT '[]', tags TEXT NOT NULL DEFAULT '[]',"
                              " source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', error TEXT NOT NULL DEFAULT '',"
                              " audio_path TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT 'ja', transcript TEXT NOT NULL DEFAULT '[]',"
                              " notes TEXT NOT NULL DEFAULT '{}', notes_model TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);"
                              "CREATE TABLE action_items (id TEXT PRIMARY KEY, meeting_id TEXT NOT NULL, text TEXT NOT NULL, owner TEXT NOT NULL DEFAULT '',"
                              " due TEXT NOT NULL DEFAULT '', done INTEGER NOT NULL DEFAULT 0, done_at TEXT NOT NULL DEFAULT '', position INTEGER NOT NULL DEFAULT 0,"
                              " manual INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);")
            old.close()
            s = Store(d / "old.db")
            mid = s.create_meeting(title="x", started_at="2026-01-01T00:00:00+00:00", source="record", consent=2)
            s.replace_ai_actions(mid, [{"text": "a", "evidence": "e", "verified": False}])
            self.assertEqual((s.get_meeting(mid)["consent"], s.actions_for(mid)[0]["verified"]), (2, 0))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class StoreDirect(unittest.TestCase):
    def test_like_wildcards_are_escaped(self):
        d = Path(tempfile.mkdtemp())
        try:
            s = Store(d / "x.db")
            s.create_meeting(title="100% 達成", started_at="2026-01-01T00:00:00+00:00", source="transcript")
            s.create_meeting(title="1000 達成", started_at="2026-01-02T00:00:00+00:00", source="transcript")
            self.assertEqual([m["title"] for m in s.list_meetings(q="100%")], ["100% 達成"])
            self.assertEqual(len(s.list_meetings(q="達成")), 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
