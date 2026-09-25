"""
note 記事の「note上の状態」を管理するモジュール

状態は3段階:
  draft          … リポジトリに記事ファイルがあるだけ（note にはまだ無い）
  uploaded_draft … note に下書きを作成済み
  published      … note で公開済み

記事ファイルの frontmatter（note_status / note_url）が基本の状態で、
src/push_note_drafts.py が note に下書きを作ると uploaded_draft に書き換わる。

/note-drafts で手動で変えた状態は DATABASE_URL（Postgres/Supabase）の
note_article_status テーブルに保存する（Render の無料プランはファイルが
再デプロイ・スリープ復帰で消えるため）。DATABASE_URL 未設定時は
記事ファイルの frontmatter を直接書き換える。

表示する状態は「ファイルの状態」と「手動で付けた状態」のうち進んでいる方。
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import yaml

ARTICLES_DIR = Path("posts/note/articles")
HISTORY_PATH = Path("posts/note/history.json")
JST = ZoneInfo("Asia/Tokyo")

STATUS_ORDER = ["draft", "uploaded_draft", "published"]
STATUS_LABELS = {
    "draft": "note未作成",
    "uploaded_draft": "note下書き作成済",
    "published": "note公開済",
}


def normalize_status(value) -> str:
    value = str(value or "").strip()
    if value in STATUS_ORDER:
        return value
    if value == "uploaded":
        return "uploaded_draft"
    return "draft"


def merge_status(file_status, manual_status) -> str:
    """ファイルの状態と手動の状態のうち、進んでいる方を返す"""
    file_status = normalize_status(file_status)
    if not manual_status:
        return file_status
    manual_status = normalize_status(manual_status)
    return max(file_status, manual_status, key=STATUS_ORDER.index)


def is_note_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "note.com" or host.endswith(".note.com"))


def article_path(filename: str) -> Path | None:
    """ファイル名を検証して記事のパスを返す（不正・存在しない場合は None）"""
    filename = str(filename or "")
    if not filename or "/" in filename or "\\" in filename or not filename.endswith(".md"):
        return None
    fp = ARTICLES_DIR / filename
    return fp if fp.is_file() else None


# ── 記事ファイルの読み書き ────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        meta = yaml.safe_load(parts[1])
        return (meta if isinstance(meta, dict) else {}), parts[2].strip()
    except yaml.YAMLError:
        return _parse_frontmatter_loosely(parts[1]), parts[2].strip()


def _parse_frontmatter_loosely(text: str) -> dict:
    """YAMLとして壊れた frontmatter から、状態に関わる行だけを拾う"""
    meta = {}
    for key in ("title", "date", "note_status", "note_url"):
        m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', text, re.MULTILINE)
        if m:
            meta[key] = m.group(1)
    return meta


def _unwrap_json_article(body: str) -> dict | None:
    """生成時にJSONのまま保存されてしまった本文（```json {...} ```）から title/body を取り出す"""
    text = body.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 文字列の中に " がエスケープされずに入っていて JSON として読めないことがある
        data = _extract_json_fields_loosely(text)
    if not isinstance(data, dict) or not data.get("body"):
        return None
    return data


def _extract_json_fields_loosely(text: str) -> dict | None:
    def decode(raw: str) -> str:
        escaped = re.sub(r'(?<!\\)"', r'\\"', raw)
        try:
            return json.loads(f'"{escaped}"')
        except json.JSONDecodeError:
            return raw.replace("\\n", "\n").replace('\\"', '"')

    title = re.search(r'"title"\s*:\s*"(.*?)"\s*,\s*"body"', text, re.DOTALL)
    body = re.search(r'"body"\s*:\s*"(.*?)"\s*(?:,\s*"tags"|}\s*$)', text, re.DOTALL)
    if not body:
        return None
    tags = re.search(r'"tags"\s*:\s*(\[.*?\])', text, re.DOTALL)
    try:
        tag_list = json.loads(tags.group(1)) if tags else []
    except json.JSONDecodeError:
        tag_list = []
    return {
        "title": decode(title.group(1)) if title else "",
        "body": decode(body.group(1)),
        "tags": tag_list,
    }


def read_article(fp: Path) -> dict:
    """記事ファイルを読み、title / date / tags / body / note_status / note_url を返す"""
    meta, body = parse_frontmatter(fp.read_text(encoding="utf-8"))
    title = str(meta.get("title") or fp.stem)
    tags = meta.get("tags") or []

    unwrapped = _unwrap_json_article(body)
    if unwrapped:
        title = str(unwrapped.get("title") or title)
        body = str(unwrapped["body"]).strip()
        tags = unwrapped.get("tags") or tags

    return {
        "filename": fp.name,
        "title": title,
        "date": str(meta.get("date") or "")[:10],
        "tags": [str(t) for t in tags] if isinstance(tags, list) else [],
        "body": body,
        "note_status": normalize_status(meta.get("note_status")),
        "note_url": str(meta.get("note_url") or ""),
    }


def update_frontmatter(fp: Path, updates: dict) -> None:
    """frontmatter の指定キーの行だけを書き換える（他の行・本文はそのまま）"""
    content = fp.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return
    parts = content.split("---", 2)
    if len(parts) < 3:
        return
    front = parts[1]
    for key, value in updates.items():
        line = f"{key}: {json.dumps(str(value), ensure_ascii=False)}"
        pattern = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
        if pattern.search(front):
            front = pattern.sub(lambda _: line, front, count=1)
        else:
            front = front.rstrip("\n") + "\n" + line + "\n"
    fp.write_text(f"---{front}---{parts[2]}", encoding="utf-8")


# ── 自動アップロードの結果（history.json）────────────────────────

def load_upload_results() -> dict:
    """ファイル名 → {note_upload_error, note_upload_attempted_at} を返す"""
    if not HISTORY_PATH.exists():
        return {}
    try:
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    results = {}
    for entry in history if isinstance(history, list) else []:
        name = Path(entry.get("filepath", "")).name
        if name:
            results[name] = {
                "error": entry.get("note_upload_error", ""),
                "attempted_at": entry.get("note_upload_attempted_at", ""),
            }
    return results


# ── 手動で付けた状態（DB）─────────────────────────────────────────

_table_ready = False


def db_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL", ""))


def _db_conn():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(url, sslmode="require")
    except Exception as e:
        print(f"[note_status] DB connection failed: {e}", file=sys.stderr)
        return None


def _ensure_table(conn) -> None:
    global _table_ready
    if _table_ready:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS note_article_status (
                    filename TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    note_url TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
    _table_ready = True


def load_manual_statuses() -> tuple[dict, bool]:
    """
    手動で付けた状態を返す: ({ファイル名: {status, note_url, updated_at}}, DBを読めたか)
    DATABASE_URL 未設定時は ({}, True)（ファイルの状態がそのまま正）。
    """
    if not db_configured():
        return {}, True
    conn = _db_conn()
    if not conn:
        return {}, False
    try:
        _ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT filename, status, note_url, updated_at FROM note_article_status")
            rows = cur.fetchall()
        return {
            r[0]: {"status": normalize_status(r[1]), "note_url": r[2], "updated_at": r[3]}
            for r in rows
        }, True
    except Exception as e:
        print(f"[note_status] load failed: {e}", file=sys.stderr)
        return {}, False
    finally:
        conn.close()


def set_manual_status(fp: Path, status: str | None, note_url: str = "") -> str:
    """
    記事の状態を手動で設定する。status=None は手動設定の取り消し。
    保存先（"db" / "file"）を返す。保存できなければ例外を送出する。
    """
    if status is not None and status not in STATUS_ORDER:
        raise ValueError(f"unknown status: {status}")

    if not db_configured():
        current = read_article(fp)
        update_frontmatter(fp, {
            "note_status": status or "draft",
            "note_url": note_url or (current["note_url"] if status else ""),
        })
        return "file"

    conn = _db_conn()
    if not conn:
        raise RuntimeError("データベースに接続できませんでした")
    try:
        _ensure_table(conn)
        with conn:
            with conn.cursor() as cur:
                if status is None:
                    cur.execute("DELETE FROM note_article_status WHERE filename = %s", (fp.name,))
                else:
                    cur.execute(
                        """
                        INSERT INTO note_article_status (filename, status, note_url, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (filename) DO UPDATE
                        SET status = EXCLUDED.status,
                            note_url = EXCLUDED.note_url,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (fp.name, status, note_url, datetime.now(JST).isoformat(timespec="seconds")),
                    )
        return "db"
    finally:
        conn.close()
