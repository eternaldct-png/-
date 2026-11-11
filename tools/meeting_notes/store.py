"""キキトメのデータ層（SQLite）。

自分専用・1台で使う前提。接続は呼び出しごとに開いて閉じる（Flask の各リクエストと
バックグラウンドの処理スレッドが同時に触るため、接続を共有しない）。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")

STATUSES = ("queued", "transcribing", "summarizing", "done", "failed")
BUSY = ("queued", "transcribing", "summarizing")

DEFAULT_SETTINGS = {
    "custom_context": "",
    "language": "ja",
    "whisper_model": "small",
    "model": "claude-opus-5-5",
    # 口コミの不満への対応（replica/fixes.md）
    "vocabulary": "",            # よく出る言葉・固有名詞（Whisper と AI に渡す）
    "quiet_mode": "0",           # 小さい声を拾う（無音カットをしない）
    "monthly_budget_jpy": "0",   # 月の AI 費用の上限（0 = 上限なし）
    "usd_jpy": "150",            # 費用の円換算
    "audio_retention_days": "0", # 録音を自動で消すまでの日数（0 = 消さない）
    # 端末保存・API なしで使う（AI の選び方は ai.resolve_engine）
    "ai_engine": "auto",           # auto | ollama | simple | claude（claude は明示して選んだときだけ）
    "ollama_model": "qwen2.5:7b",  # 端末内AI のモデル名
}

# あとから足した列（古い DB にも足す）
MIGRATIONS = [
    ("meetings", "consent", "INTEGER"),                      # 1 = 相手に録音を伝えた / 2 = 自分だけのメモ / NULL = 不明
    ("action_items", "evidence", "TEXT NOT NULL DEFAULT ''"),  # 根拠になった発言（文字起こしからの引用）
    ("action_items", "evidence_time", "REAL"),               # 根拠の発言の時刻（秒）
    ("action_items", "verified", "INTEGER NOT NULL DEFAULT 1"),  # 0 = 根拠が文字起こしに見つからない（要確認）
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA.read_text(encoding="utf-8"))
            for table, col, decl in MIGRATIONS:
                cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
                if col not in cols:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.db_path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ── 会議 ────────────────────────────────────────────

    @staticmethod
    def _meeting(row) -> dict | None:
        if row is None:
            return None
        m = dict(row)
        for key, empty in (("participants", []), ("tags", []), ("transcript", []), ("notes", {})):
            try:
                m[key] = json.loads(m.get(key) or "null") or empty
            except json.JSONDecodeError:
                m[key] = empty
        return m

    def create_meeting(self, *, title: str, started_at: str, source: str, participants=None,
                       tags=None, audio_path: str = "", transcript=None, language: str = "ja",
                       duration_sec: float | None = None, consent: int | None = None) -> str:
        mid = new_id()
        ts = now()
        with self.conn() as c:
            c.execute(
                "INSERT INTO meetings (id, title, started_at, duration_sec, participants, tags, source,"
                " status, audio_path, language, transcript, consent, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (mid, title.strip(), started_at, duration_sec,
                 json.dumps(clean_list(participants), ensure_ascii=False),
                 json.dumps(clean_list(tags), ensure_ascii=False),
                 source, "queued", audio_path, language,
                 json.dumps(transcript or [], ensure_ascii=False), consent, ts, ts),
            )
        return mid

    def get_meeting(self, mid: str) -> dict | None:
        with self.conn() as c:
            return self._meeting(c.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone())

    def list_meetings(self, q: str = "", tag: str = "") -> list[dict]:
        sql = "SELECT * FROM meetings"
        where, args = [], []
        for term in split_terms(q):
            like = f"%{escape_like(term)}%"
            where.append(
                "(title LIKE ? ESCAPE '\\' OR notes LIKE ? ESCAPE '\\' OR transcript LIKE ? ESCAPE '\\'"
                " OR participants LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\'"
                " OR id IN (SELECT meeting_id FROM action_items WHERE text LIKE ? ESCAPE '\\'))"
            )
            args += [like] * 6
        rows = []
        with self.conn() as c:
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY started_at DESC"
            rows = [self._meeting(r) for r in c.execute(sql, args).fetchall()]
        if tag:
            rows = [m for m in rows if tag in m["tags"]]
        return rows

    def all_tags(self) -> list[str]:
        tags = set()
        with self.conn() as c:
            for (raw,) in c.execute("SELECT tags FROM meetings"):
                try:
                    tags.update(json.loads(raw or "[]"))
                except json.JSONDecodeError:
                    pass
        return sorted(tags)

    def update_meeting(self, mid: str, **fields) -> None:
        allowed = {"title", "started_at", "participants", "tags", "status", "error", "transcript",
                   "notes", "notes_model", "duration_sec", "language", "audio_path", "consent"}
        sets, args = [], []
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"変更できない項目です: {key}")
            if key in ("participants", "tags"):
                value = json.dumps(clean_list(value), ensure_ascii=False)
            elif key in ("transcript", "notes"):
                value = json.dumps(value, ensure_ascii=False)
            elif key == "status" and value not in STATUSES:
                raise ValueError(f"不明な状態です: {value}")
            sets.append(f"{key}=?")
            args.append(value)
        if not sets:
            return
        sets.append("updated_at=?")
        args += [now(), mid]
        with self.conn() as c:
            c.execute(f"UPDATE meetings SET {', '.join(sets)} WHERE id=?", args)

    def delete_meeting(self, mid: str) -> dict | None:
        m = self.get_meeting(mid)
        if m:
            with self.conn() as c:
                c.execute("DELETE FROM meetings WHERE id=?", (mid,))
        return m

    def busy_meeting_ids(self) -> list[str]:
        with self.conn() as c:
            q = "SELECT id FROM meetings WHERE status IN (?,?,?) ORDER BY created_at"
            return [r[0] for r in c.execute(q, BUSY)]

    def set_segment_speaker(self, mid: str, index: int, speaker: str) -> bool:
        """1行だけ話者を付け替える（不満: 話者の取り違え）。人が直した行は「推定」の印を外す。"""
        m = self.get_meeting(mid)
        if not m or not (0 <= index < len(m["transcript"])):
            return False
        seg = m["transcript"][index]
        seg["speaker"] = speaker
        seg.pop("guessed", None)
        self.update_meeting(mid, transcript=m["transcript"])
        return True

    def rename_speaker(self, mid: str, old: str, new: str) -> int:
        m = self.get_meeting(mid)
        if not m:
            return 0
        n = 0
        for seg in m["transcript"]:
            if seg.get("speaker", "") == old:
                seg["speaker"] = new
                seg.pop("guessed", None)
                n += 1
        if n:
            self.update_meeting(mid, transcript=m["transcript"])
        return n

    # ── アクションアイテム ───────────────────────────────

    def replace_ai_actions(self, mid: str, items: list[dict]) -> None:
        """AI が抽出したアクションを入れ替える。手で足した行は残し、同じ文言の行は完了状態を引き継ぐ。"""
        with self.conn() as c:
            old = {r["text"]: dict(r) for r in c.execute(
                "SELECT * FROM action_items WHERE meeting_id=? AND manual=0", (mid,))}
            c.execute("DELETE FROM action_items WHERE meeting_id=? AND manual=0", (mid,))
            for pos, it in enumerate(items):
                text = str(it.get("text", "")).strip()
                if not text:
                    continue
                prev = old.get(text, {})
                c.execute(
                    "INSERT INTO action_items (id, meeting_id, text, owner, due, done, done_at, position, manual,"
                    " evidence, evidence_time, verified, created_at) VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?)",
                    (new_id(), mid, text, str(it.get("owner", "")).strip(), str(it.get("due", "")).strip(),
                     prev.get("done", 0), prev.get("done_at", ""), pos,
                     str(it.get("evidence", "")).strip(), it.get("evidence_time"),
                     1 if it.get("verified", True) else 0, now()),
                )

    def add_action(self, mid: str, text: str, owner: str = "", due: str = "") -> str:
        aid = new_id()
        with self.conn() as c:
            pos = c.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM action_items WHERE meeting_id=?",
                            (mid,)).fetchone()[0]
            c.execute(
                "INSERT INTO action_items (id, meeting_id, text, owner, due, position, manual, created_at)"
                " VALUES (?,?,?,?,?,?,1,?)",
                (aid, mid, text.strip(), owner.strip(), due.strip(), pos, now()),
            )
        return aid

    def get_action(self, aid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM action_items WHERE id=?", (aid,)).fetchone()
            return dict(r) if r else None

    def update_action(self, aid: str, **fields) -> None:
        sets, args = [], []
        for key in ("text", "owner", "due"):
            if key in fields:
                sets.append(f"{key}=?")
                args.append(str(fields[key]).strip())
        if fields.get("verified"):  # 人が確かめた
            sets.append("verified=1")
        if "done" in fields:
            done = 1 if fields["done"] else 0
            sets += ["done=?", "done_at=?"]
            args += [done, now() if done else ""]
        if not sets:
            return
        args.append(aid)
        with self.conn() as c:
            c.execute(f"UPDATE action_items SET {', '.join(sets)} WHERE id=?", args)

    def delete_action(self, aid: str) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM action_items WHERE id=?", (aid,))

    def actions_for(self, mid: str) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM action_items WHERE meeting_id=? ORDER BY position, created_at", (mid,))]

    def list_actions(self, owner: str = "", state: str = "open") -> list[dict]:
        sql = ("SELECT a.*, m.title AS meeting_title, m.started_at AS meeting_started_at"
               " FROM action_items a JOIN meetings m ON m.id = a.meeting_id")
        where, args = [], []
        if state == "open":
            where.append("a.done=0")
        elif state == "done":
            where.append("a.done=1")
        if owner == "__none__":
            where.append("a.owner=''")
        elif owner:
            where.append("a.owner=?")
            args.append(owner)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.started_at DESC, a.position"
        with self.conn() as c:
            return [dict(r) for r in c.execute(sql, args)]

    def action_owners(self) -> list[str]:
        with self.conn() as c:
            return [r[0] for r in c.execute(
                "SELECT DISTINCT owner FROM action_items WHERE owner != '' ORDER BY owner")]

    # ── 質問の履歴 ──────────────────────────────────────

    def add_chat(self, mid: str | None, role: str, content: str) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO chat_messages (id, meeting_id, role, content, created_at) VALUES (?,?,?,?,?)",
                      (new_id(), mid, role, content, now()))

    def chat_for(self, mid: str | None) -> list[dict]:
        with self.conn() as c:
            if mid is None:
                rows = c.execute("SELECT * FROM chat_messages WHERE meeting_id IS NULL ORDER BY created_at, rowid")
            else:
                rows = c.execute("SELECT * FROM chat_messages WHERE meeting_id=? ORDER BY created_at, rowid", (mid,))
            return [dict(r) for r in rows]

    def clear_chat(self, mid: str | None) -> None:
        with self.conn() as c:
            if mid is None:
                c.execute("DELETE FROM chat_messages WHERE meeting_id IS NULL")
            else:
                c.execute("DELETE FROM chat_messages WHERE meeting_id=?", (mid,))

    # ── 設定 ────────────────────────────────────────────

    def settings(self) -> dict:
        out = dict(DEFAULT_SETTINGS)
        with self.conn() as c:
            for r in c.execute("SELECT key, value FROM settings"):
                out[r["key"]] = r["value"]
        return out

    def save_settings(self, **values) -> None:
        with self.conn() as c:
            for key, value in values.items():
                if key not in DEFAULT_SETTINGS:
                    continue
                c.execute("INSERT INTO settings (key, value) VALUES (?,?)"
                          " ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    # ── AI の費用（不満: 高い・いくらかかるか分からない） ────────

    def add_usage(self, meeting_id, kind: str, model: str, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO ai_usage (id, meeting_id, kind, model, input_tokens, output_tokens, cost_usd, created_at)"
                      " VALUES (?,?,?,?,?,?,?,?)",
                      (new_id(), meeting_id, kind, model, int(input_tokens), int(output_tokens), float(cost_usd), now()))

    def usage_since(self, since_iso: str) -> float:
        with self.conn() as c:
            return float(c.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM ai_usage WHERE created_at >= ?",
                                   (since_iso,)).fetchone()[0])

    def usage_for_meeting(self, mid: str) -> float:
        with self.conn() as c:
            return float(c.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM ai_usage WHERE meeting_id=?",
                                   (mid,)).fetchone()[0])

    def usage_by_month(self, months: int = 6) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd"
                " FROM ai_usage GROUP BY month ORDER BY month DESC LIMIT ?", (months,))]

    # ── 操作の記録（不満: 記録の透明性・監査ログが無い） ──────────

    def log(self, action: str, meeting_id: str | None = None, detail: str = "") -> None:
        with self.conn() as c:
            c.execute("INSERT INTO activity (id, at, action, meeting_id, detail) VALUES (?,?,?,?,?)",
                      (new_id(), now(), action, meeting_id, detail[:500]))

    def activity(self, limit: int = 200) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM activity ORDER BY at DESC, rowid DESC LIMIT ?", (limit,))]

    # ── 録音の途中保存（不満: 録音が消えた） ────────────────────

    def create_recording(self, rid: str, path: str, ext: str, meta: dict) -> None:
        ts = now()
        with self.conn() as c:
            c.execute("INSERT INTO recordings (id, path, ext, meta, started_at, updated_at) VALUES (?,?,?,?,?,?)",
                      (rid, path, ext, json.dumps(meta, ensure_ascii=False), ts, ts))

    def get_recording(self, rid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM recordings WHERE id=?", (rid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["meta"] = json.loads(d["meta"] or "{}")
        return d

    def touch_recording(self, rid: str, nbytes: int) -> None:
        with self.conn() as c:
            c.execute("UPDATE recordings SET bytes=bytes+?, chunks=chunks+1, updated_at=? WHERE id=?", (nbytes, now(), rid))

    def set_recording_status(self, rid: str, status: str) -> None:
        with self.conn() as c:
            c.execute("UPDATE recordings SET status=?, updated_at=? WHERE id=?", (status, now(), rid))

    def open_recordings(self, older_than_iso: str) -> list[dict]:
        """録音中のまま止まった（ブラウザが落ちた・閉じた）録音。"""
        with self.conn() as c:
            rows = c.execute("SELECT * FROM recordings WHERE status='recording' AND updated_at < ? AND bytes > 0"
                             " ORDER BY started_at DESC", (older_than_iso,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d["meta"] or "{}")
            out.append(d)
        return out

    # ── 録音の自動削除（不満: データの保存期間を選べない） ─────────

    def meetings_with_old_audio(self, before_iso: str) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT id, title, audio_path FROM meetings WHERE audio_path != '' AND started_at < ? AND status IN ('done','failed')",
                (before_iso,))]

    # ── バックアップ ─────────────────────────────────────

    def export_all(self) -> dict:
        with self.conn() as c:
            return {
                "exported_at": now(),
                "meetings": [self._meeting(r) for r in c.execute("SELECT * FROM meetings ORDER BY started_at")],
                "action_items": [dict(r) for r in c.execute("SELECT * FROM action_items")],
                "chat_messages": [dict(r) for r in c.execute("SELECT * FROM chat_messages")],
                "ai_usage": [dict(r) for r in c.execute("SELECT * FROM ai_usage")],
                "activity": [dict(r) for r in c.execute("SELECT * FROM activity")],
                "settings": self.settings(),
            }


def clean_list(values) -> list[str]:
    """「a, b、c」のような文字列やリストを、空白を除いた重複なしのリストにする。"""
    if values is None:
        return []
    if isinstance(values, str):
        values = values.replace("、", ",").replace("，", ",").split(",")
    out = []
    for v in values:
        v = str(v).strip()
        if v and v not in out:
            out.append(v)
    return out


def split_terms(q: str) -> list[str]:
    return [t for t in (q or "").replace("　", " ").split() if t]


def escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
