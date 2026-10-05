"""
枠周り記録（/waku）— 設定の読み込みと記録の保存

- 誰が（枠周りした人）、誰の枠に（配信した人）、いつ行ったかを1件ずつ記録する
- 歌推しの条件は persona/waku_config.yaml（歌推し計算ツールと同じ数値）から読み込む
- DATABASE_URL（Postgres/Supabase）が設定されていればDBの waku_visits テーブル、
  未設定なら posts/waku_visits.json に保存する
"""
import calendar
import json
import os
import re
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WAKU_CONFIG_PATH = Path("persona/waku_config.yaml")
WAKU_FILE = Path("posts/waku_visits.json")
JST = ZoneInfo("Asia/Tokyo")

STATUSES = ("went", "missed")
NAME_MAX_LENGTH = 40
MAX_VIEWING_MINUTES = 24 * 60
MAX_COINS = 100_000_000

_DEFAULT_SLOTS = ["指定なし"]
_DEFAULT_PATTERN_NAMES = ["コイン節約型", "バランス型", "コイン一括型"]


# ── 設定（プルダウンの選択肢・歌推しの条件） ─────────────────────────

def _number(value, default=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return int(number) if number.is_integer() else number


def _pattern(raw):
    raw = raw if isinstance(raw, dict) else {}
    return {
        "coins": max(0, int(_number(raw.get("coins")))),
        "viewing_hours": max(0, _number(raw.get("viewing_hours"))),
        "super_like_days": max(0, int(_number(raw.get("super_like_days")))),
    }


def _format_k(k):
    return f"{k}K"


def _high_tiers(raw):
    """50K以上の推しPtを計算式から作る（歌推し計算ツールと同じ式）。"""
    if not isinstance(raw, dict):
        return []
    try:
        from_k = int(raw.get("from_k", 50))
        to_k = int(raw.get("to_k", from_k - 1))
        base_coins = [int(v) for v in raw.get("base_coins") or []]
        coins_per_k = int(raw.get("coins_per_k", 0))
        viewing = [_number(v) for v in raw.get("viewing_hours") or []]
        super_likes = [int(_number(v)) for v in raw.get("super_like_days") or []]
    except (TypeError, ValueError):
        return []
    if not (len(base_coins) == len(viewing) == len(super_likes) == 3):
        return []

    tiers = []
    for k in range(from_k, to_k + 1):
        tiers.append({
            "label": _format_k(k),
            "pt": k * 1000,
            "patterns": [
                {
                    "coins": base_coins[i] + (k - 49) * coins_per_k,
                    "viewing_hours": viewing[i],
                    "super_like_days": super_likes[i],
                }
                for i in range(3)
            ],
        })
    return tiers


def load_config():
    """persona/waku_config.yaml を読み込み、画面で使う形に整えて返す。"""
    import yaml

    data = {}
    if WAKU_CONFIG_PATH.exists():
        with open(WAKU_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    page = data.get("page") or {}
    slots = [str(s).strip() for s in data.get("slots") or [] if str(s).strip()]
    viewing = sorted({int(_number(v)) for v in data.get("viewing_minutes") or [] if 0 < _number(v) <= MAX_VIEWING_MINUTES})
    coins = sorted({int(_number(v)) for v in data.get("coin_presets") or [] if 0 < _number(v) <= MAX_COINS})

    uta = data.get("uta_oshi") or {}
    tiers = []
    for t in uta.get("tiers") or []:
        if not isinstance(t, dict) or not t.get("label") or len(t.get("patterns") or []) != 3:
            continue
        tiers.append({
            "label": str(t["label"]),
            "pt": int(_number(t.get("pt"))),
            "patterns": [_pattern(p) for p in t["patterns"]],
        })
    known = {t["label"] for t in tiers}
    tiers += [t for t in _high_tiers(uta.get("high_tiers")) if t["label"] not in known]
    tiers.sort(key=lambda t: t["pt"])

    names = [str(n) for n in uta.get("pattern_names") or []]
    if len(names) != 3:
        names = list(_DEFAULT_PATTERN_NAMES)

    default_target = str(uta.get("default_target") or "")
    if tiers and default_target not in {t["label"] for t in tiers}:
        default_target = tiers[0]["label"]

    return {
        "title": str(page.get("title") or "枠周り記録"),
        "slots": slots or list(_DEFAULT_SLOTS),
        "viewing_minutes": viewing,
        "coin_presets": coins,
        "pattern_names": names,
        "tiers": tiers,
        "default_target": default_target,
    }


# ── 入力チェック ──────────────────────────────────────────

def jun_of(day):
    """日にちから旬を返す（1〜10日: 上旬 / 11〜20日: 中旬 / 21日〜: 下旬）。"""
    day = int(day)
    if day <= 10:
        return "上旬"
    if day <= 20:
        return "中旬"
    return "下旬"


def normalize_name(value):
    """前後の空白を取り、連続する空白（全角含む）を1つにまとめる。"""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_date(value):
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _bounded_int(value, upper):
    try:
        number = int(str(value).strip() or 0)
    except (TypeError, ValueError):
        return None
    if number < 0 or number > upper:
        return None
    return number


def build_record(data, config):
    """フォームの入力から保存用の1件を作る。問題があれば (None, エラー文) を返す。"""
    data = data if isinstance(data, dict) else {}

    visit_date = _parse_date(data.get("date"))
    if not visit_date or not 2000 <= visit_date.year <= 2100:
        return None, "日付を選んでください"

    host = normalize_name(data.get("host"))
    visitor = normalize_name(data.get("visitor"))
    if not host:
        return None, "配信した人の名前を入れてください"
    if len(host) > NAME_MAX_LENGTH or len(visitor) > NAME_MAX_LENGTH:
        return None, f"名前は{NAME_MAX_LENGTH}文字以内で入れてください"
    if visitor and visitor == host:
        return None, "配信した人と枠周りした人が同じ名前です"

    slot = str(data.get("slot") or "").strip()
    if slot not in config["slots"]:
        slot = config["slots"][0]

    status = str(data.get("status") or "").strip()
    viewing_minutes = coins = 0
    super_like = False
    if not visitor:
        # 枠周りした人が空欄 = 枠だけ登録（まだ誰も行けていない枠）
        status = ""
    elif status not in STATUSES:
        return None, "行けた／行けなかったを選んでください"
    elif status == "went":
        viewing_minutes = _bounded_int(data.get("viewing_minutes", 0), MAX_VIEWING_MINUTES)
        coins = _bounded_int(data.get("coins", 0), MAX_COINS)
        if viewing_minutes is None:
            return None, "視聴時間の値が正しくありません"
        if coins is None:
            return None, "コインは0以上の整数で入れてください"
        super_like = str(data.get("super_like", "")).strip().lower() in {"1", "true", "yes", "on"}

    return {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "date": visit_date.isoformat(),
        "slot": slot,
        "host": host,
        "visitor": visitor,
        "status": status,
        "viewing_minutes": viewing_minutes,
        "coins": coins,
        "super_like": super_like,
    }, None


def month_range(month):
    """"2026-10" → (2026-10-01, 2026-10-31)。不正な値なら None。"""
    m = re.fullmatch(r"(\d{4})-(\d{2})", str(month or "").strip())
    if not m:
        return None
    year, mon = int(m.group(1)), int(m.group(2))
    if not (2000 <= year <= 2100 and 1 <= mon <= 12):
        return None
    return date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])


def with_jun(record):
    record = dict(record)
    record["jun"] = jun_of(int(record["date"][8:10]))
    return record


# ── 保存先：DB（DATABASE_URL）またはファイル ───────────────────────

_table_ready = False


def storage_mode():
    return "db" if os.environ.get("DATABASE_URL", "") else "file"


def _db_conn():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(url, sslmode="require")
    except Exception as e:
        print(f"[waku] DB connection failed: {e}", file=sys.stderr)
        return None


def _ensure_table(conn):
    global _table_ready
    if _table_ready:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS waku_visits (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT '',
                    visit_date DATE NOT NULL,
                    slot TEXT NOT NULL DEFAULT '',
                    host TEXT NOT NULL,
                    visitor TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    viewing_minutes INTEGER NOT NULL DEFAULT 0,
                    coins BIGINT NOT NULL DEFAULT 0,
                    super_like BOOLEAN NOT NULL DEFAULT FALSE,
                    seq BIGSERIAL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS waku_visits_date_idx ON waku_visits (visit_date)")
    _table_ready = True


def _db_row(row):
    return {
        "id": row[0],
        "created_at": row[1],
        "date": row[2].isoformat(),
        "slot": row[3],
        "host": row[4],
        "visitor": row[5],
        "status": row[6],
        "viewing_minutes": int(row[7]),
        "coins": int(row[8]),
        "super_like": bool(row[9]),
    }


def _load_file():
    try:
        if WAKU_FILE.exists():
            with open(WAKU_FILE, "r", encoding="utf-8") as f:
                rows = json.load(f)
            return rows if isinstance(rows, list) else []
    except Exception as e:
        print(f"[waku] file load failed: {e}", file=sys.stderr)
    return []


def _write_file(rows):
    """ファイル全体を原子的に置き換える（書き込み中断でJSONを壊さない）。"""
    WAKU_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = WAKU_FILE.with_suffix(WAKU_FILE.suffix + ".tmp")
    try:
        with open(temporary_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        temporary_file.replace(WAKU_FILE)
    except Exception:
        temporary_file.unlink(missing_ok=True)
        raise


def load_month(month):
    """指定した月の記録と、名前・月の一覧をまとめて返す。

    DATABASE_URL が設定済みでDBに接続できないときは、ファイルの古い記録を
    見せて誤解させないよう RuntimeError を送出する。
    """
    span = month_range(month)
    if not span:
        raise ValueError("month must be YYYY-MM")
    start, end = span
    if storage_mode() == "file":
        rows = _load_file()
        records = [r for r in rows if start.isoformat() <= str(r.get("date", "")) <= end.isoformat()]
        names = {r.get("host", "") for r in rows} | {r.get("visitor", "") for r in rows}
        months = {str(r.get("date", ""))[:7] for r in rows}
    else:
        conn = _db_conn()
        if not conn:
            raise RuntimeError("データベースに接続できません")
        try:
            _ensure_table(conn)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, created_at, visit_date, slot, host, visitor, status, "
                        "viewing_minutes, coins, super_like FROM waku_visits "
                        "WHERE visit_date BETWEEN %s AND %s ORDER BY visit_date, seq",
                        (start, end),
                    )
                    records = [_db_row(r) for r in cur.fetchall()]
                    cur.execute("SELECT host FROM waku_visits UNION SELECT visitor FROM waku_visits")
                    names = {r[0] for r in cur.fetchall()}
                    cur.execute("SELECT DISTINCT to_char(visit_date, 'YYYY-MM') FROM waku_visits")
                    months = {r[0] for r in cur.fetchall()}
        finally:
            conn.close()

    records.sort(key=lambda r: (r["date"], r.get("created_at", "")))
    return {
        "records": [with_jun(r) for r in records],
        "names": sorted(n for n in names if n),
        "months": sorted((m for m in months if m), reverse=True),
        "storage": storage_mode(),
    }


def save_record(record):
    """1件保存する。保存できなければ例外を送出する。"""
    if storage_mode() == "file":
        rows = _load_file()
        rows.append(record)
        _write_file(rows)
        return

    import time

    global _table_ready
    last_error = None
    for attempt in range(3):
        if attempt:
            time.sleep(0.4 * attempt)
        conn = _db_conn()
        if not conn:
            last_error = "connection failed"
            continue
        try:
            _ensure_table(conn)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO waku_visits (id, created_at, visit_date, slot, host, visitor, "
                        "status, viewing_minutes, coins, super_like) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            record["id"], record["created_at"], record["date"], record["slot"],
                            record["host"], record["visitor"], record["status"],
                            record["viewing_minutes"], record["coins"], record["super_like"],
                        ),
                    )
            return
        except Exception as e:
            last_error = e
            _table_ready = False
        finally:
            conn.close()
    raise RuntimeError(f"DB save failed: {last_error}")


def delete_record(record_id):
    """1件削除する。見つからなければ False、保存先に届かなければ例外を送出する。"""
    record_id = str(record_id or "").strip()
    if not record_id:
        return False

    if storage_mode() == "file":
        rows = _load_file()
        kept = [r for r in rows if r.get("id") != record_id]
        if len(kept) == len(rows):
            return False
        _write_file(kept)
        return True

    conn = _db_conn()
    if not conn:
        raise RuntimeError("データベースに接続できません")
    try:
        _ensure_table(conn)
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM waku_visits WHERE id = %s", (record_id,))
                return cur.rowcount > 0
    finally:
        conn.close()
