"""コマドリのデータ層（SQLite）。

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

# 段階（ステッパーの順番）。key はコードで使う名前、label は画面の名前
STAGES = [
    ("script", "脚本"),
    ("characters", "キャラ"),
    ("scenes", "場面"),
    ("storyboard", "絵コンテ"),
    ("art", "絵と動き"),
    ("sound", "音"),
    ("render", "書き出し"),
]
STAGE_KEYS = [k for k, _ in STAGES]
STAGE_LABELS = dict(STAGES)
STAGE_STATES = ("todo", "generating", "review", "approved", "stale", "failed")

KINDS = {"story": "ストーリー", "mv": "MV（曲に合わせる）", "quick": "クイック（説明・告知）"}
ASPECTS = ("9:16", "16:9", "1:1")
CAMERAS = {"still": "固定", "zoom_in": "寄る", "zoom_out": "引く", "pan_left": "左へパン", "pan_right": "右へパン"}

# 自前のスタイル（名前と説明文だけ。見本画像は持たない）
STYLES = {
    "anime": ("アニメ調", "くっきりした線、セル塗り、明るい色", "anime style, clean line art, cel shading, vibrant colors"),
    "pastel": ("パステル", "やわらかい色、ふんわりした光、ゆめかわ", "soft pastel colors, dreamy light, cute, gentle watercolor texture"),
    "chibi": ("ちびキャラ", "2〜3頭身、まるい形、コミカル", "chibi characters, super deformed, round shapes, comedic, flat colors"),
    "picturebook": ("絵本", "手描きの質感、あたたかい色、余白", "children's picture book illustration, hand-drawn texture, warm colors"),
    "neon": ("ネオン", "夜の街、ネオンの光、ライブ感", "neon lights, night city, vivid magenta and cyan, concert atmosphere"),
    "manga": ("モノクロ漫画", "白黒、トーン、集中線", "black and white manga, screentone, speed lines, dramatic ink"),
}

DEFAULT_SETTINGS = {
    "ai_engine": "auto",            # auto | ollama | simple | claude（claude は明示して選んだときだけ）
    "ollama_model": "qwen2.5:7b",
    "claude_model": "claude-sonnet-5-5",
    "image_engine": "placeholder",  # placeholder（仮の絵・無料） | fal（fal.ai・従量）
    "video_engine": "camera",       # camera（カメラワーク・無料） | fal（AI動画・従量）
    "fal_image_model": "fal-ai/flux/schnell",
    "fal_video_model": "fal-ai/kling-video/v2.1/standard/image-to-video",
    "fal_image_yen": "1",           # 画像1枚あたりの見積もり（円）
    "fal_video_yen_per_sec": "8",   # AI動画1秒あたりの見積もり（円）
    "monthly_budget_jpy": "1000",   # fal.ai の月の上限（見積もりベース）
    "voice_engine": "say",          # say（Mac の読み上げ・無料） | none
    "default_voice": "Kyoko",
    "subtitles": "1",
    "chars_per_second": "8",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


def default_stages() -> dict:
    return {k: "todo" for k in STAGE_KEYS}


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA.read_text(encoding="utf-8"))

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

    # ── 設定 ────────────────────────────────────────────

    def settings(self) -> dict:
        out = dict(DEFAULT_SETTINGS)
        with self.conn() as c:
            for r in c.execute("SELECT key, value FROM settings"):
                out[r["key"]] = r["value"]
        return out

    def save_settings(self, values: dict) -> dict:
        with self.conn() as c:
            for k, v in values.items():
                if k in DEFAULT_SETTINGS:
                    c.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                              (k, str(v)))
        return self.settings()

    # ── 作品 ────────────────────────────────────────────

    @staticmethod
    def _project(r) -> dict:
        d = dict(r)
        d["script"] = json.loads(d.get("script") or "{}")
        stages = default_stages()
        stages.update(json.loads(d.get("stages") or "{}"))
        d["stages"] = stages
        d["render_warnings"] = json.loads(d.get("render_warnings") or "[]")
        d["auto"] = bool(d.get("auto"))
        return d

    def create_project(self, **f) -> dict:
        pid, t = new_id(), now()
        with self.conn() as c:
            c.execute(
                "INSERT INTO projects(id, title, kind, idea, style, aspect, duration_sec, language, mood, auto, stages, created_at, updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid, f.get("title", ""), f.get("kind", "story"), f.get("idea", ""), f.get("style", "anime"),
                 f.get("aspect", "9:16"), int(f.get("duration_sec", 30)), f.get("language", "ja"), f.get("mood", ""),
                 1 if f.get("auto") else 0, json.dumps(default_stages()), t, t))
        return self.get_project(pid)

    def get_project(self, pid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
        return self._project(r) if r else None

    def list_projects(self) -> list[dict]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
            thumbs = {r["project_id"]: r["image_path"] for r in c.execute(
                "SELECT project_id, image_path FROM shots WHERE image_path != '' ORDER BY sort DESC")}
            busy = {r["project_id"] for r in c.execute("SELECT DISTINCT project_id FROM jobs WHERE status IN ('queued','running')")}
        out = []
        for r in rows:
            p = self._project(r)
            p["thumb"] = thumbs.get(p["id"], "")
            p["busy"] = p["id"] in busy
            out.append(p)
        return out

    PROJECT_FIELDS = ("title", "kind", "idea", "style", "aspect", "duration_sec", "language", "mood", "auto",
                      "bgm_path", "bgm_volume", "render_path")

    def update_project(self, pid: str, **f) -> dict | None:
        sets, vals = [], []
        for k, v in f.items():
            if k in self.PROJECT_FIELDS:
                sets.append(f"{k} = ?")
                vals.append(int(v) if k == "auto" else v)
            elif k in ("script", "stages", "render_warnings"):
                sets.append(f"{k} = ?")
                vals.append(json.dumps(v, ensure_ascii=False))
        if not sets:
            return self.get_project(pid)
        sets.append("updated_at = ?")
        vals.append(now())
        with self.conn() as c:
            c.execute(f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", (*vals, pid))
        return self.get_project(pid)

    def set_stage(self, pid: str, stage: str, state: str, *, invalidate_after: bool = False) -> dict:
        """段階の状態を変える。invalidate_after なら後ろの段階（作業済みのもの）を「古い」にする。"""
        assert stage in STAGE_KEYS and state in STAGE_STATES
        p = self.get_project(pid)
        stages = p["stages"]
        stages[stage] = state
        if invalidate_after:
            for k in STAGE_KEYS[STAGE_KEYS.index(stage) + 1:]:
                if stages.get(k) in ("approved", "review"):
                    stages[k] = "stale"
        return self.update_project(pid, stages=stages)

    def delete_project(self, pid: str) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM projects WHERE id = ?", (pid,))

    # ── キャラ ───────────────────────────────────────────

    CHAR_FIELDS = ("name", "look", "personality", "voice", "color", "image_path", "sort")

    def add_character(self, project_id: str | None, **f) -> dict:
        cid, t = new_id(), now()
        with self.conn() as c:
            if "sort" not in f:
                f["sort"] = (c.execute("SELECT COALESCE(MAX(sort), -1) + 1 FROM characters WHERE project_id IS ?",
                                       (project_id,)).fetchone()[0])
            c.execute("INSERT INTO characters(id, project_id, name, look, personality, voice, color, image_path, library_id, sort, created_at, updated_at)"
                      " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (cid, project_id, (f.get("name") or "名前なし")[:60], f.get("look", ""), f.get("personality", ""),
                       f.get("voice", ""), f.get("color", ""), f.get("image_path", ""), f.get("library_id", ""),
                       int(f["sort"]), t, t))
        return self.get_character(cid)

    def get_character(self, cid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone()
        return dict(r) if r else None

    def characters(self, project_id: str | None) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM characters WHERE project_id IS ? ORDER BY sort, created_at",
                                                (project_id,))]

    def update_character(self, cid: str, **f) -> dict | None:
        return self._update("characters", cid, self.CHAR_FIELDS, f) and self.get_character(cid)

    def delete_character(self, cid: str) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM characters WHERE id = ?", (cid,))

    def replace_characters(self, project_id: str, items: list[dict]) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM characters WHERE project_id = ?", (project_id,))
        for i, it in enumerate(items):
            self.add_character(project_id, sort=i, **{k: v for k, v in it.items() if k in self.CHAR_FIELDS and k != "sort"})

    # ── 場面 ────────────────────────────────────────────

    SCENE_FIELDS = ("name", "description", "color", "image_path", "sort")

    def scenes(self, project_id: str) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM scenes WHERE project_id = ? ORDER BY sort, created_at", (project_id,))]

    def get_scene(self, sid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM scenes WHERE id = ?", (sid,)).fetchone()
        return dict(r) if r else None

    def add_scene(self, project_id: str, **f) -> dict:
        sid, t = new_id(), now()
        with self.conn() as c:
            sort = f.get("sort")
            if sort is None:
                sort = c.execute("SELECT COALESCE(MAX(sort), -1) + 1 FROM scenes WHERE project_id = ?", (project_id,)).fetchone()[0]
            c.execute("INSERT INTO scenes(id, project_id, name, description, color, image_path, sort, created_at, updated_at)"
                      " VALUES(?,?,?,?,?,?,?,?,?)",
                      (sid, project_id, (f.get("name") or "場面")[:60], f.get("description", ""), f.get("color", ""),
                       f.get("image_path", ""), int(sort), t, t))
        return self.get_scene(sid)

    def update_scene(self, sid: str, **f) -> dict | None:
        return self._update("scenes", sid, self.SCENE_FIELDS, f) and self.get_scene(sid)

    def delete_scene(self, sid: str) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM scenes WHERE id = ?", (sid,))

    def replace_scenes(self, project_id: str, items: list[dict]) -> list[dict]:
        with self.conn() as c:
            c.execute("UPDATE shots SET scene_id = NULL WHERE project_id = ?", (project_id,))
            c.execute("DELETE FROM scenes WHERE project_id = ?", (project_id,))
        return [self.add_scene(project_id, sort=i, **{k: v for k, v in it.items() if k in self.SCENE_FIELDS and k != "sort"})
                for i, it in enumerate(items)]

    # ── カット ───────────────────────────────────────────

    SHOT_FIELDS = ("sort", "seconds", "scene_id", "characters", "camera", "action", "speaker", "dialogue", "caption",
                   "image_prompt", "image_path", "image_source", "video_path")

    @staticmethod
    def _shot(r) -> dict:
        d = dict(r)
        d["characters"] = json.loads(d.get("characters") or "[]")
        return d

    def shots(self, project_id: str) -> list[dict]:
        with self.conn() as c:
            return [self._shot(r) for r in c.execute("SELECT * FROM shots WHERE project_id = ? ORDER BY sort, created_at", (project_id,))]

    def get_shot(self, sid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM shots WHERE id = ?", (sid,)).fetchone()
        return self._shot(r) if r else None

    def _clean_shot(self, f: dict) -> dict:
        out = {}
        for k, v in f.items():
            if k not in self.SHOT_FIELDS:
                continue
            if k == "characters":
                v = json.dumps([str(x)[:60] for x in (v or [])][:8], ensure_ascii=False)
            elif k == "seconds":
                v = min(30.0, max(0.5, float(v)))
            elif k == "camera" and v not in CAMERAS:
                v = "still"
            elif k == "scene_id" and not v:
                v = None
            out[k] = v
        return out

    def add_shot(self, project_id: str, **f) -> dict:
        sid, t = new_id(), now()
        f = self._clean_shot(f)
        with self.conn() as c:
            if "sort" not in f:
                f["sort"] = c.execute("SELECT COALESCE(MAX(sort), -1) + 1 FROM shots WHERE project_id = ?", (project_id,)).fetchone()[0]
            cols = ["id", "project_id", "created_at", "updated_at", *f.keys()]
            c.execute(f"INSERT INTO shots({', '.join(cols)}) VALUES({', '.join('?' * len(cols))})",
                      (sid, project_id, t, t, *f.values()))
        return self.get_shot(sid)

    def update_shot(self, sid: str, **f) -> dict | None:
        f = self._clean_shot(f)
        return self._update("shots", sid, self.SHOT_FIELDS, f) and self.get_shot(sid)

    def delete_shot(self, sid: str) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM shots WHERE id = ?", (sid,))

    def replace_shots(self, project_id: str, items: list[dict]) -> None:
        with self.conn() as c:
            c.execute("DELETE FROM shots WHERE project_id = ?", (project_id,))
        for i, it in enumerate(items):
            it = dict(it)
            it["sort"] = i
            self.add_shot(project_id, **it)

    def reorder_shots(self, project_id: str, ids: list[str]) -> None:
        existing = {s["id"] for s in self.shots(project_id)}
        if set(ids) != existing:
            raise ValueError("カットの一覧が合いません。画面を読み込み直してください。")
        with self.conn() as c:
            for i, sid in enumerate(ids):
                c.execute("UPDATE shots SET sort = ?, updated_at = ? WHERE id = ?", (i, now(), sid))

    # ── 共通の更新 ───────────────────────────────────────

    def _update(self, table: str, oid: str, allowed: tuple, f: dict) -> bool:
        sets, vals = [], []
        for k, v in f.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                vals.append(v)
        with self.conn() as c:
            if sets:
                sets.append("updated_at = ?")
                vals.append(now())
                c.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?", (*vals, oid))
            return c.execute(f"SELECT 1 FROM {table} WHERE id = ?", (oid,)).fetchone() is not None

    def touch(self, pid: str) -> None:
        with self.conn() as c:
            c.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now(), pid))

    # ── 進行ログ ───────────────────────────────────────────

    def log(self, project_id: str, role: str, text: str) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO logs(project_id, role, text, created_at) VALUES(?,?,?,?)", (project_id, role, text[:4000], now()))

    def logs(self, project_id: str, limit: int = 200) -> list[dict]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM logs WHERE project_id = ? ORDER BY id DESC LIMIT ?", (project_id, limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ── ジョブ ───────────────────────────────────────────

    def add_job(self, project_id: str, kind: str, instruction: str = "") -> dict:
        jid, t = new_id(), now()
        with self.conn() as c:
            c.execute("INSERT INTO jobs(id, project_id, kind, instruction, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                      (jid, project_id, kind, instruction, "queued", t, t))
        return self.get_job(jid)

    def get_job(self, jid: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM jobs WHERE id = ?", (jid,)).fetchone()
        return dict(r) if r else None

    def set_job(self, jid: str, status: str, error: str = "") -> None:
        with self.conn() as c:
            c.execute("UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?", (status, error[:2000], now(), jid))

    def jobs(self, project_id: str, limit: int = 20) -> list[dict]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
                             (project_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def active_job(self, project_id: str) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM jobs WHERE project_id = ? AND status IN ('queued','running') ORDER BY created_at LIMIT 1",
                          (project_id,)).fetchone()
        return dict(r) if r else None

    def queued_jobs(self) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at, rowid")]

    def recover_interrupted(self) -> int:
        """アプリが途中で止まったときに running のまま残ったジョブを「失敗」に戻す（やり直せるように）。"""
        with self.conn() as c:
            rows = c.execute("SELECT id, project_id, kind FROM jobs WHERE status = 'running'").fetchall()
            c.execute("UPDATE jobs SET status = 'failed', error = 'アプリが途中で止まりました。もう一度押してください。', updated_at = ?"
                      " WHERE status = 'running'", (now(),))
        for r in rows:
            p = self.get_project(r["project_id"])
            if p and r["kind"] in STAGE_KEYS and p["stages"].get(r["kind"]) == "generating":
                self.set_stage(r["project_id"], r["kind"], "failed")
        return len(rows)

    # ── 費用（fal.ai の見積もり） ───────────────────────────

    def add_spend(self, yen: float, what: str) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO spend(yen, what, created_at) VALUES(?,?,?)", (float(yen), what[:200], now()))

    def spend_since(self, iso: str) -> float:
        with self.conn() as c:
            return float(c.execute("SELECT COALESCE(SUM(yen), 0) FROM spend WHERE created_at >= ?", (iso,)).fetchone()[0])
