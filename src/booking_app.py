"""
予約アプリ — 独立した Flask アプリ（設定ファイルで外販可能）

スタッフ（persona/booking_config.yaml の members）それぞれについて:
  - 各人がログイン不要で自分の空き時間（1時間単位）を登録
  - その人自身が空けている時間（すでに予約済みの時間は除く）が予約ページに公開される
  - 外部ゲストがログイン不要で名前だけ入力して1時間の予約ができる
  - 予約は早い者勝ち（先着順で埋まったら他の人は予約できない）
  - 予約の枠は人ごとに独立している（同じ時間でも別の人になら予約可能）
  - 予約が確定すると Google カレンダーに同期
  - LINE 連携済みのスタッフには予約確定・キャンセルの LINE 通知と、
    開始前の LINE リマインドが届く

サイト名・スタッフ一覧・営業時間・予約の呼び名（面談/レッスン/施術など）は
persona/booking_config.yaml で変更できる — コード変更なしで別事業者向けの
予約ツールとしてデプロイできる。

環境変数（Render などで設定）:
  FLASK_SECRET_KEY            セッション用秘密鍵
  DATABASE_URL                Supabase の接続 URI（永続化に必要。未設定時はファイル）
  GOOGLE_SERVICE_ACCOUNT_JSON Google サービスアカウントの JSON キー
  GOOGLE_CALENDAR_ID          同期先カレンダー ID
  LINE_CHANNEL_ACCESS_TOKEN   LINE Messaging API のチャネルアクセストークン（通知に必要）
  LINE_CHANNEL_SECRET         LINE チャネルシークレット（Webhook 署名検証に必要）
  REMINDER_SECRET             /tasks/send-reminders の認証トークン
                              （未設定時は AVAILABILITY_PASSWORD を使用）
"""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify, session

sys.path.insert(0, str(Path(__file__).parent))

import line_messaging

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

AVAILABILITY_PASSWORD = os.environ.get("AVAILABILITY_PASSWORD", "ETERNALLOVE")


# ── 設定ファイル読み込み ─────────────────────────────────────────

BOOKING_CONFIG_FILE = Path(__file__).parent.parent / "persona" / "booking_config.yaml"

_DEFAULT_CONFIG = {
    "site": {
        "title": "面談スケジュール",
        "subtitle": "空き時間登録 & 面談予約",
        "icon": "🤝",
        "event_label": "面談",
    },
    "booking": {"start_hour": 9, "end_hour": 22, "days_ahead": 21},
    "members": [
        {"slug": "kazuto", "name": "kazuto"},
        {"slug": "amarin", "name": "あまりん"},
        {"slug": "sana", "name": "さな"},
        {"slug": "shi", "name": "しー"},
        {"slug": "kapinosuke", "name": "かぴのすけ"},
    ],
    "line": {"reminder_hours_before": 24},
}


def _load_config():
    cfg = {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in _DEFAULT_CONFIG.items()}
    try:
        import yaml
        with open(BOOKING_CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        for section in ("site", "booking", "line"):
            if isinstance(loaded.get(section), dict):
                cfg[section].update(loaded[section])
        members = loaded.get("members")
        if isinstance(members, list) and members:
            cfg["members"] = [
                {"slug": str(m["slug"]), "name": str(m["name"])}
                for m in members if m.get("slug") and m.get("name")
            ]
    except Exception as e:
        print(f"[booking_app] config load failed, using defaults: {e}", file=sys.stderr)
    return cfg


CONFIG = _load_config()
SITE_TITLE = CONFIG["site"]["title"]
SITE_SUBTITLE = CONFIG["site"]["subtitle"]
SITE_ICON = CONFIG["site"]["icon"]
EVENT_LABEL = CONFIG["site"]["event_label"]
MEMBERS = CONFIG["members"]
SLUG_TO_NAME = {m["slug"]: m["name"] for m in MEMBERS}
NAME_TO_SLUG = {m["name"]: m["slug"] for m in MEMBERS}
ALL_PEOPLE = [m["name"] for m in MEMBERS]
# start_hour〜(end_hour-1) 時開始の1時間枠（最終枠は end_hour に終わる）
HOURS = [f"{h:02d}:00" for h in range(int(CONFIG["booking"]["start_hour"]),
                                      int(CONFIG["booking"]["end_hour"]))]
DAYS_AHEAD = int(CONFIG["booking"]["days_ahead"])
REMINDER_HOURS_BEFORE = int(CONFIG["line"]["reminder_hours_before"])

# LINE 連携で「全予約の通知」を受け取る特別な宛先名
LINE_ADMIN_KEY = "admin"


AVAILABILITY_FILE = Path("posts/booking_availability.json")
BOOKINGS_FILE = Path("posts/booking_reservations.json")
LINE_LINKS_FILE = Path("posts/booking_line_links.json")
JST = timezone(timedelta(hours=9))


# ── DB 接続 ───────────────────────────────────────────────────────

def _db_conn():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(url, sslmode="require")
    except Exception as e:
        print(f"[booking_app] DB connection failed: {e}", file=sys.stderr)
        return None


def _ensure_tables():
    conn = _db_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS booking_availability (
                        id TEXT PRIMARY KEY,
                        person TEXT NOT NULL,
                        slot TEXT NOT NULL,
                        created_at TEXT DEFAULT '',
                        UNIQUE(person, slot)
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS interview_bookings (
                        id TEXT PRIMARY KEY,
                        member TEXT NOT NULL,
                        slot TEXT NOT NULL,
                        guest_name TEXT NOT NULL DEFAULT '',
                        created_at TEXT DEFAULT '',
                        google_calendar_event_id TEXT,
                        UNIQUE(member, slot)
                    )
                """)
                # 旧バージョン（slot が全体で一意）からの移行: 人ごとの一意制約に切り替える
                cur.execute("""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'interview_bookings_slot_key'
                        ) THEN
                            ALTER TABLE interview_bookings DROP CONSTRAINT interview_bookings_slot_key;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'interview_bookings_member_slot_key'
                        ) THEN
                            ALTER TABLE interview_bookings
                                ADD CONSTRAINT interview_bookings_member_slot_key UNIQUE (member, slot);
                        END IF;
                    END $$;
                """)
                cur.execute("""
                    ALTER TABLE interview_bookings
                        ADD COLUMN IF NOT EXISTS reminder_sent_at TEXT
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS booking_line_links (
                        id TEXT PRIMARY KEY,
                        person TEXT NOT NULL,
                        line_user_id TEXT NOT NULL,
                        created_at TEXT DEFAULT '',
                        UNIQUE(person, line_user_id)
                    )
                """)
    except Exception:
        pass
    finally:
        conn.close()


# ── データ管理: 空き時間 ─────────────────────────────────────────

def load_availability():
    conn = _db_conn()
    if conn:
        try:
            import psycopg2.extras
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM booking_availability")
                    return [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
        finally:
            conn.close()
    if AVAILABILITY_FILE.exists():
        with open(AVAILABILITY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _availability_file_save(rows):
    AVAILABILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AVAILABILITY_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def add_availability(person, slot):
    conn = _db_conn()
    row = {
        "id": str(uuid.uuid4()), "person": person, "slot": slot,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO booking_availability (id,person,slot,created_at) "
                        "VALUES (%s,%s,%s,%s) ON CONFLICT (person,slot) DO NOTHING",
                        (row["id"], person, slot, row["created_at"]),
                    )
            return True
        except Exception:
            pass
        finally:
            conn.close()
    rows = load_availability()
    if not any(r["person"] == person and r["slot"] == slot for r in rows):
        rows.append(row)
        _availability_file_save(rows)
    return True


def remove_availability(person, slot):
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM booking_availability WHERE person=%s AND slot=%s",
                        (person, slot),
                    )
            return True
        except Exception:
            pass
        finally:
            conn.close()
    rows = [r for r in load_availability() if not (r["person"] == person and r["slot"] == slot)]
    _availability_file_save(rows)
    return True


# ── データ管理: 予約 ─────────────────────────────────────────────

def load_bookings():
    conn = _db_conn()
    if conn:
        try:
            import psycopg2.extras
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM interview_bookings")
                    return [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
        finally:
            conn.close()
    if BOOKINGS_FILE.exists():
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _bookings_file_save(rows):
    BOOKINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def create_booking(member, slot, guest_name):
    """slot は member ごとに一意。すでに member 自身が同じ枠で予約済みなら None を返す。"""
    booking = {
        "id": str(uuid.uuid4()), "member": member, "slot": slot,
        "guest_name": guest_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "google_calendar_event_id": None,
    }
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO interview_bookings "
                        "(id,member,slot,guest_name,created_at) VALUES (%s,%s,%s,%s,%s)",
                        (booking["id"], member, slot, guest_name, booking["created_at"]),
                    )
            return booking
        except Exception:
            return None
        finally:
            conn.close()
    rows = load_bookings()
    if any(r["slot"] == slot and r["member"] == member for r in rows):
        return None
    rows.append(booking)
    _bookings_file_save(rows)
    return booking


def set_booking_google_event_id(booking_id, google_event_id):
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE interview_bookings SET google_calendar_event_id=%s WHERE id=%s",
                        (google_event_id, booking_id),
                    )
            return
        except Exception:
            pass
        finally:
            conn.close()
    rows = load_bookings()
    for r in rows:
        if r["id"] == booking_id:
            r["google_calendar_event_id"] = google_event_id
            break
    _bookings_file_save(rows)


def get_booking(booking_id):
    return next((r for r in load_bookings() if r["id"] == booking_id), None)


def update_booking_guest_name(booking_id, guest_name):
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE interview_bookings SET guest_name=%s WHERE id=%s",
                        (guest_name, booking_id),
                    )
            return True
        except Exception:
            return False
        finally:
            conn.close()
    rows = load_bookings()
    found = False
    for r in rows:
        if r["id"] == booking_id:
            r["guest_name"] = guest_name
            found = True
            break
    if found:
        _bookings_file_save(rows)
    return found


def delete_booking(booking_id):
    """削除した予約を返す（Googleカレンダー同期解除に使う）。なければ None。"""
    conn = _db_conn()
    if conn:
        try:
            import psycopg2.extras
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM interview_bookings WHERE id=%s", (booking_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    cur.execute("DELETE FROM interview_bookings WHERE id=%s", (booking_id,))
            return dict(row)
        except Exception:
            return None
        finally:
            conn.close()
    rows = load_bookings()
    target = next((r for r in rows if r["id"] == booking_id), None)
    if not target:
        return None
    rows = [r for r in rows if r["id"] != booking_id]
    _bookings_file_save(rows)
    return target


def mark_reminder_sent(booking_id):
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE interview_bookings SET reminder_sent_at=%s WHERE id=%s",
                        (now_iso, booking_id),
                    )
            return
        except Exception:
            pass
        finally:
            conn.close()
    rows = load_bookings()
    for r in rows:
        if r["id"] == booking_id:
            r["reminder_sent_at"] = now_iso
            break
    _bookings_file_save(rows)


# ── データ管理: LINE 連携 ────────────────────────────────────────

def load_line_links():
    conn = _db_conn()
    if conn:
        try:
            import psycopg2.extras
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM booking_line_links")
                    return [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
        finally:
            conn.close()
    if LINE_LINKS_FILE.exists():
        with open(LINE_LINKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _line_links_file_save(rows):
    LINE_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LINE_LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def add_line_link(person, line_user_id):
    row = {
        "id": str(uuid.uuid4()), "person": person, "line_user_id": line_user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO booking_line_links (id,person,line_user_id,created_at) "
                        "VALUES (%s,%s,%s,%s) ON CONFLICT (person,line_user_id) DO NOTHING",
                        (row["id"], person, line_user_id, row["created_at"]),
                    )
            return True
        except Exception:
            return False
        finally:
            conn.close()
    rows = load_line_links()
    if not any(r["person"] == person and r["line_user_id"] == line_user_id for r in rows):
        rows.append(row)
        _line_links_file_save(rows)
    return True


def remove_line_links_for_user(line_user_id):
    """そのLINEユーザーの連携をすべて解除し、解除した宛先名のリストを返す"""
    rows = load_line_links()
    removed = sorted({r["person"] for r in rows if r["line_user_id"] == line_user_id})
    if not removed:
        return []
    conn = _db_conn()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM booking_line_links WHERE line_user_id=%s",
                        (line_user_id,),
                    )
            return removed
        except Exception:
            return []
        finally:
            conn.close()
    _line_links_file_save([r for r in rows if r["line_user_id"] != line_user_id])
    return removed


def line_user_ids_for(person):
    """person 本人に連携された LINE ユーザー + 全体通知（admin）の LINE ユーザー"""
    ids = []
    for r in load_line_links():
        if r["person"] in (person, LINE_ADMIN_KEY) and r["line_user_id"] not in ids:
            ids.append(r["line_user_id"])
    return ids


# ── LINE 通知 ────────────────────────────────────────────────────

def _slot_jp(slot):
    """'2026-07-20T15:00:00+09:00' → '7月20日(月) 15:00'"""
    try:
        dt = datetime.fromisoformat(slot)
        wd = ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]
        return f"{dt.month}月{dt.day}日({wd}) {dt.strftime('%H:%M')}"
    except Exception:
        return slot


def notify_line(person, text):
    """person（と全体通知の連携者）にLINE通知。送れた人数を返す。"""
    if not line_messaging.is_configured():
        return 0
    sent = 0
    for uid in line_user_ids_for(person):
        if line_messaging.push_text(uid, text):
            sent += 1
    return sent


def notify_booking_created(booking):
    notify_line(booking["member"], (
        f"📅 新しい{EVENT_LABEL}予約が入りました\n"
        f"担当: {booking['member']}\n"
        f"日時: {_slot_jp(booking['slot'])}〜（1時間）\n"
        f"ゲスト: {booking['guest_name']} 様"
    ))


def notify_booking_cancelled(booking):
    notify_line(booking["member"], (
        f"❌ {EVENT_LABEL}予約がキャンセルされました\n"
        f"担当: {booking['member']}\n"
        f"日時: {_slot_jp(booking['slot'])}〜\n"
        f"ゲスト: {booking['guest_name']} 様"
    ))


def send_due_reminders():
    """開始が REMINDER_HOURS_BEFORE 時間以内に迫った未リマインドの予約に
    LINE リマインドを送る。送った予約IDのリストを返す。"""
    if not line_messaging.is_configured():
        return []
    now = datetime.now(JST)
    window_end = now + timedelta(hours=REMINDER_HOURS_BEFORE)
    sent = []
    for b in load_bookings():
        if b.get("reminder_sent_at"):
            continue
        try:
            start = datetime.fromisoformat(b["slot"])
        except Exception:
            continue
        if now < start <= window_end:
            n = notify_line(b["member"], (
                f"⏰ リマインド: まもなく{EVENT_LABEL}があります\n"
                f"担当: {b['member']}\n"
                f"日時: {_slot_jp(b['slot'])}〜（1時間）\n"
                f"ゲスト: {b['guest_name']} 様"
            ))
            if n > 0:
                mark_reminder_sent(b["id"])
                sent.append(b["id"])
    return sent


# ── 予約ロジック ─────────────────────────────────────────────────

def slot_iso(date_str, hour_str):
    return f"{date_str}T{hour_str}:00+09:00"


def slot_end_iso(date_str, hour_str):
    h = int(hour_str[:2])
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=JST) + timedelta(hours=h + 1)
    return dt.strftime("%Y-%m-%dT%H:%M:00+09:00")


def person_available_slots(person):
    return {r["slot"] for r in load_availability() if r["person"] == person}


def member_booked_slots(person):
    return {r["slot"] for r in load_bookings() if r["member"] == person}


def open_slots_for(person):
    """person 自身が空けている時間から、person 自身の予約済みスロットを除いた集合"""
    return person_available_slots(person) - member_booked_slots(person)


# ── 認証（空き時間登録ページ） ───────────────────────────────────

def is_avail_authed():
    return bool(session.get("avail_ok"))


@app.route("/api/availability/me")
def api_availability_me():
    return jsonify({"authed": is_avail_authed()})


@app.route("/api/availability/login", methods=["POST"])
def api_availability_login():
    data = request.get_json(force=True)
    if data.get("password") == AVAILABILITY_PASSWORD:
        session["avail_ok"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "パスワードが違います"}), 401


@app.route("/api/availability/logout", methods=["POST"])
def api_availability_logout():
    session.pop("avail_ok", None)
    return jsonify({"ok": True})


@app.route("/api/availability/storage-status")
def api_storage_status():
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    url_set = bool(os.environ.get("DATABASE_URL", ""))
    conn = _db_conn()
    connected = conn is not None
    if conn:
        conn.close()
    return jsonify({
        "database_url_set": url_set,
        "database_connected": connected,
    })


# ── API: 空き時間登録 ────────────────────────────────────────────

@app.route("/api/availability")
def api_availability_get():
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    person = request.args.get("person", "")
    date = request.args.get("date", "")
    if person not in ALL_PEOPLE or not date:
        return jsonify({"error": "invalid params"}), 400
    avail = person_available_slots(person)
    person_bookings = [r for r in load_bookings() if r["member"] == person]
    booked_by = {r["slot"]: r for r in person_bookings}
    hours = []
    for h in HOURS:
        slot = slot_iso(date, h)
        b = booked_by.get(slot)
        hours.append({
            "hour": h,
            "available": slot in avail,
            "booked": b is not None,
            "guest_name": b["guest_name"] if b else "",
            "booking_id": b["id"] if b else "",
        })
    return jsonify({"ok": True, "hours": hours})


@app.route("/api/availability/toggle", methods=["POST"])
def api_availability_toggle():
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    person = data.get("person", "")
    date = data.get("date", "")
    hour = data.get("hour", "")
    if person not in ALL_PEOPLE or not date or hour not in HOURS:
        return jsonify({"error": "invalid params"}), 400
    slot = slot_iso(date, hour)
    if slot in member_booked_slots(person):
        return jsonify({"error": "予約済みのため変更できません"}), 409
    currently = slot in person_available_slots(person)
    if currently:
        remove_availability(person, slot)
        return jsonify({"ok": True, "available": False})
    add_availability(person, slot)
    return jsonify({"ok": True, "available": True})


@app.route("/api/booking/<booking_id>/edit", methods=["POST"])
def api_booking_edit(booking_id):
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    guest_name = str(data.get("guest_name", "")).strip()
    if not guest_name:
        return jsonify({"error": "名前を入力してください"}), 400
    if not update_booking_guest_name(booking_id, guest_name):
        return jsonify({"error": "予約が見つかりません"}), 404
    booking = get_booking(booking_id)
    if booking and booking.get("google_calendar_event_id"):
        try:
            from google_calendar import sync_update
            slot = booking["slot"]
            date, hour = slot[:10], slot[11:16]
            sync_update(booking["google_calendar_event_id"], {
                "title": f"{EVENT_LABEL}: {guest_name} × {booking['member']}",
                "description": f"{booking['member']} との1時間{EVENT_LABEL}（ゲスト: {guest_name}）",
                "event_type": "interview",
                "start_datetime": slot,
                "end_datetime": slot_end_iso(date, hour),
                "all_day": False,
            })
        except Exception:
            pass
    return jsonify({"ok": True})


@app.route("/api/booking/<booking_id>/delete", methods=["POST"])
def api_booking_delete(booking_id):
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    booking = delete_booking(booking_id)
    if not booking:
        return jsonify({"error": "予約が見つかりません"}), 404
    if booking.get("google_calendar_event_id"):
        try:
            from google_calendar import sync_delete
            sync_delete(booking["google_calendar_event_id"])
        except Exception:
            pass
    try:
        notify_booking_cancelled(booking)
    except Exception:
        pass
    return jsonify({"ok": True})


# ── API: 面談予約（公開） ────────────────────────────────────────

def _resolve_slug(slug):
    """slug -> (person_display_name, open_slots_set) または None"""
    person = SLUG_TO_NAME.get(slug)
    if not person:
        return None, None
    return person, open_slots_for(person)


@app.route("/api/book/<slug>/slots")
def api_book_slots(slug):
    member, open_slots = _resolve_slug(slug)
    if member is None:
        return jsonify({"error": "not found"}), 404
    today = datetime.now(JST).date()
    days = []
    for i in range(DAYS_AHEAD):
        d = today + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        hours = [h for h in HOURS if slot_iso(ds, h) in open_slots]
        if hours:
            days.append({"date": ds, "hours": hours})
    return jsonify({"ok": True, "member": member, "days": days})


@app.route("/api/book/<slug>", methods=["POST"])
def api_book_create(slug):
    member, open_slots = _resolve_slug(slug)
    if member is None:
        return jsonify({"error": "not found"}), 404
    data = request.get_json(force=True)
    date = data.get("date", "")
    hour = data.get("hour", "")
    guest_name = str(data.get("guest_name", "")).strip()
    if not date or hour not in HOURS:
        return jsonify({"error": "invalid params"}), 400
    if not guest_name:
        return jsonify({"error": "名前を入力してください"}), 400
    slot = slot_iso(date, hour)
    if slot not in open_slots:
        return jsonify({"error": "この時間はすでに予約できません"}), 409
    booking = create_booking(member, slot, guest_name)
    if not booking:
        return jsonify({"error": "この時間はすでに予約できません"}), 409
    try:
        from google_calendar import sync_create
        google_id = sync_create({
            "title": f"{EVENT_LABEL}: {guest_name} × {member}",
            "description": f"{member} との1時間{EVENT_LABEL}（ゲスト: {guest_name}）",
            "event_type": "interview",
            "start_datetime": slot,
            "end_datetime": slot_end_iso(date, hour),
            "all_day": False,
        })
        if google_id:
            set_booking_google_event_id(booking["id"], google_id)
    except Exception:
        pass
    try:
        notify_booking_created(booking)
    except Exception:
        pass
    return jsonify({"ok": True})




# ── API: LINE 連携 ───────────────────────────────────────────────

def _line_usage_text():
    names = " / ".join(ALL_PEOPLE)
    return (
        f"友だち追加ありがとうございます🙌\n"
        f"このアカウントでは{EVENT_LABEL}予約の通知とリマインドを受け取れます。\n\n"
        f"▼ 通知を受け取るには、名前を送ってください\n"
        f"例:「連携 {ALL_PEOPLE[0]}」\n"
        f"（対象: {names}）\n\n"
        f"▼ 全員分の予約通知を受け取る場合\n"
        f"「連携 admin」\n\n"
        f"▼ 通知をやめる場合\n"
        f"「解除」"
    )


def _match_link_target(arg):
    """連携コマンドの引数を宛先名に解決する。名前・slug・admin を受け付ける。"""
    arg = arg.strip()
    if arg.lower() in (LINE_ADMIN_KEY, "管理者", "全体", "全員"):
        return LINE_ADMIN_KEY
    if arg in ALL_PEOPLE:
        return arg
    if arg in SLUG_TO_NAME:
        return SLUG_TO_NAME[arg]
    return None


def _handle_line_text(user_id, reply_token, text):
    text = text.strip()
    if text in ("解除", "連携解除"):
        removed = remove_line_links_for_user(user_id)
        if removed:
            line_messaging.reply_text(reply_token, "通知の連携を解除しました。")
        else:
            line_messaging.reply_text(reply_token, "連携中の通知はありません。")
        return
    if text.startswith("連携"):
        arg = text[len("連携"):].strip()
        if not arg:
            line_messaging.reply_text(reply_token, _line_usage_text())
            return
        target = _match_link_target(arg)
        if not target:
            line_messaging.reply_text(
                reply_token,
                f"「{arg}」が見つかりませんでした。\n対象: {' / '.join(ALL_PEOPLE)} / admin",
            )
            return
        add_line_link(target, user_id)
        label = "全員分の予約" if target == LINE_ADMIN_KEY else f"{target} の予約"
        line_messaging.reply_text(
            reply_token,
            f"✅ 連携しました！\n{label}の確定・キャンセル通知と、"
            f"{EVENT_LABEL}の{REMINDER_HOURS_BEFORE}時間前リマインドをお送りします。",
        )
        return
    line_messaging.reply_text(reply_token, _line_usage_text())


@app.route("/line/webhook", methods=["POST"])
def line_webhook():
    body = request.get_data()
    signature = request.headers.get("X-Line-Signature", "")
    if not line_messaging.verify_signature(body, signature):
        return "bad signature", 400
    try:
        events = json.loads(body).get("events", [])
    except Exception:
        return "bad request", 400
    for ev in events:
        ev_type = ev.get("type", "")
        reply_token = ev.get("replyToken", "")
        user_id = (ev.get("source") or {}).get("userId", "")
        if ev_type == "follow":
            line_messaging.reply_text(reply_token, _line_usage_text())
        elif ev_type == "unfollow":
            if user_id:
                remove_line_links_for_user(user_id)
        elif ev_type == "message":
            msg = ev.get("message") or {}
            if msg.get("type") == "text" and user_id:
                print(f"[booking_app] LINE message received: {msg.get('text', '')!r} "
                      f"from {user_id[:8]}...", file=sys.stderr, flush=True)
                try:
                    _handle_line_text(user_id, reply_token, msg.get("text", ""))
                except Exception as e:
                    print(f"[booking_app] handle_line_text error: {e}", file=sys.stderr, flush=True)
    return "ok", 200


@app.route("/tasks/send-reminders", methods=["GET", "POST"])
def tasks_send_reminders():
    """cron（cron-job.org / Render Cron など）から定期的に叩くリマインド送信"""
    token = request.args.get("token", "") or request.headers.get("X-Reminder-Token", "")
    expected = os.environ.get("REMINDER_SECRET", "") or AVAILABILITY_PASSWORD
    if not token or token != expected:
        return jsonify({"error": "unauthorized"}), 401
    if not line_messaging.is_configured():
        return jsonify({"ok": True, "sent": 0, "note": "LINE未設定"})
    sent = send_due_reminders()
    return jsonify({"ok": True, "sent": len(sent)})


@app.route("/api/line/status")
def api_line_status():
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    links = load_line_links()
    linked_counts = {}
    for r in links:
        linked_counts[r["person"]] = linked_counts.get(r["person"], 0) + 1
    return jsonify({
        "ok": True,
        "configured": line_messaging.is_configured(),
        "people": [
            {"name": p, "linked": linked_counts.get(p, 0)} for p in ALL_PEOPLE
        ],
        "admin_linked": linked_counts.get(LINE_ADMIN_KEY, 0),
        "reminder_hours_before": REMINDER_HOURS_BEFORE,
    })


# ── フロントエンド ────────────────────────────────────────────────

CSS = """
:root {
  --bg: #0a0a1a; --surface: #13132a; --surface2: #1c1c38; --surface3: #252548;
  --accent: #6d28d9; --accent2: #7c3aed; --accent-light: #a78bfa;
  --text: #e2e8f0; --muted: #7a859a; --border: #252548;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --ok: #22c55e; --busy: #ef4444;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; }
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  min-height: 100vh; padding-bottom: calc(40px + var(--safe-bottom));
}
.header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 16px 18px 14px; display: flex; align-items: center; gap: 12px;
  position: sticky; top: 0; z-index: 100;
}
.header-icon {
  width: 40px; height: 40px; background: linear-gradient(135deg, var(--accent2), #4c1d95);
  border-radius: 12px; display: flex; align-items: center; justify-content: center;
  font-size: 22px; flex-shrink: 0;
}
.header-info { flex: 1; min-width: 0; }
.header-title { font-size: 17px; font-weight: 700; }
.header-sub { font-size: 11px; color: var(--muted); margin-top: 1px; }
.wrap { max-width: 560px; margin: 0 auto; padding: 18px 16px; }
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
  padding: 16px; margin-bottom: 12px;
}
.card-title { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
.card-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.btn-pri {
  display: block; width: 100%; padding: 13px; background: var(--accent2); border: none;
  border-radius: 12px; color: white; font-size: 14px; font-weight: 700;
  cursor: pointer; text-align: center; text-decoration: none;
}
.btn-pri:active { opacity: 0.8; }
.btn-sec {
  display: block; width: 100%; padding: 13px; background: var(--surface2);
  border: 1.5px solid var(--border); border-radius: 12px; color: var(--text);
  font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; text-decoration: none;
}
select.fi, input.fi {
  width: 100%; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--text); font-size: 14px;
  padding: 10px 12px; outline: none; font-family: inherit; margin-bottom: 12px;
}
.day-nav {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.day-btn {
  background: var(--surface); border: 1.5px solid var(--border); color: var(--text);
  width: 38px; height: 38px; border-radius: 10px; font-size: 18px; cursor: pointer;
}
.back-btn {
  background: var(--surface2); border: 1.5px solid var(--border); color: var(--text);
  width: 36px; height: 36px; border-radius: 10px; font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; text-decoration: none; flex-shrink: 0;
}
.day-label { font-size: 15px; font-weight: 700; }
.hour-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.hour-btn {
  padding: 12px 4px; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--muted); font-size: 13px; font-weight: 600; cursor: pointer;
  text-align: center;
}
.hour-btn.on { border-color: var(--ok); color: var(--ok); background: rgba(34,197,94,0.12); }
.hour-btn.busy { border-color: var(--busy); color: var(--busy); background: rgba(239,68,68,0.1); cursor: not-allowed; }
.hour-btn .who { display: block; font-size: 10px; font-weight: 500; margin-top: 2px; opacity: 0.85; }
.booking-actions { display: flex; gap: 4px; margin-top: 5px; justify-content: center; }
.act-btn {
  font-size: 10px; padding: 3px 6px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--surface3); color: var(--text); cursor: pointer; font-family: inherit;
}
.act-btn.danger { border-color: var(--busy); color: var(--busy); }
.empty-msg { color: var(--muted); font-size: 13px; text-align: center; padding: 24px 0; }
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.75);
  z-index: 300; display: none; align-items: flex-end; justify-content: center;
}
.overlay.open { display: flex; }
.sheet {
  background: var(--surface); border-radius: 22px 22px 0 0; width: 100%; max-width: 560px;
  padding: 18px 18px calc(18px + var(--safe-bottom));
}
.handle { width: 38px; height: 4px; background: var(--border); border-radius: 2px; margin: 0 auto 16px; }
.sheet-title { font-size: 17px; font-weight: 700; margin-bottom: 14px; }
.btn-row { display: flex; gap: 10px; margin-top: 6px; }
.toast {
  position: fixed; bottom: calc(24px + var(--safe-bottom)); left: 50%;
  transform: translateX(-50%) translateY(14px);
  background: var(--surface3); border: 1px solid var(--border); color: var(--text);
  padding: 10px 18px; border-radius: 22px; font-size: 13px;
  opacity: 0; transition: all 0.28s; white-space: nowrap; z-index: 500; pointer-events: none;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.nav-loading {
  position: fixed; inset: 0; background: var(--bg);
  z-index: 999; display: none; align-items: center; justify-content: center;
  flex-direction: column; gap: 14px;
}
.nav-loading.show { display: flex; }
.spinner {
  width: 34px; height: 34px; border: 3px solid var(--border);
  border-top-color: var(--accent2); border-radius: 50%;
  animation: nav-spin 0.7s linear infinite;
}
@keyframes nav-spin { to { transform: rotate(360deg); } }
.nav-loading-text { font-size: 13px; color: var(--muted); }
"""

TOAST_JS = """
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2600);
}
"""

NAV_JS = """
function showNavLoading() {
  const el = document.getElementById('nav-loading');
  if (el) el.classList.add('show');
}
function hideNavLoading() {
  const el = document.getElementById('nav-loading');
  if (el) el.classList.remove('show');
}
function goTo(url) {
  showNavLoading();
  fetch(url).catch(() => {}).finally(() => { location.href = url; });
  return false;
}
window.addEventListener('pageshow', hideNavLoading);
"""

HOME_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <div class="header-icon">__ICON__</div>
  <div class="header-info">
    <div class="header-title">__TITLE__</div>
    <div class="header-sub">__SUBTITLE__</div>
  </div>
</div>
<div class="wrap">
  <div class="card">
    <div class="card-title">📝 空き時間を登録する</div>
    <div class="card-sub">__PEOPLE_LIST__ 共通</div>
    <a class="btn-pri" href="/availability" onclick="return goTo('/availability')">空き時間を登録する</a>
  </div>
  __MEMBER_CARDS__
</div>
<div class="nav-loading" id="nav-loading">
  <div class="spinner"></div>
  <div class="nav-loading-text">しばらくお待ちください…</div>
</div>
<script>
__NAV_JS__
</script>
</body>
</html>
"""

AVAILABILITY_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>空き時間登録</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <a class="back-btn" href="/" onclick="return goTo('/')">‹</a>
  <div class="header-icon">📝</div>
  <div class="header-info">
    <div class="header-title">空き時間登録</div>
    <div class="header-sub">タップで空き時間をON/OFF</div>
  </div>
  <button class="back-btn" onclick="doLogout()" title="ログアウト">🔒</button>
</div>
<div class="wrap">
  <div id="storage-warn" style="display:none; background:rgba(239,68,68,0.12); border:1px solid var(--busy); color:var(--busy); border-radius:10px; padding:10px 12px; font-size:12px; margin-bottom:12px;">
    ⚠️ データベース未接続のため、登録した空き時間や予約はサーバー再起動時に消える可能性があります。Renderの環境変数 DATABASE_URL を確認してください。
  </div>
  <select class="fi" id="f-person" onchange="onPersonChange()">__PERSON_OPTIONS__</select>
  <div class="day-nav">
    <button class="day-btn" onclick="changeDay(-1)">‹</button>
    <span class="day-label" id="day-label"></span>
    <button class="day-btn" onclick="changeDay(1)">›</button>
  </div>
  <div class="hour-grid" id="hour-grid"></div>
  <div class="card" id="line-card" style="display:none; margin-top:16px;">
    <div class="card-title">💬 LINE通知</div>
    <div class="card-sub" id="line-desc"></div>
    <div id="line-people" style="font-size:12px; line-height:1.9;"></div>
  </div>
</div>

<div class="overlay open" id="pw-overlay">
  <div class="sheet">
    <div class="handle"></div>
    <div class="sheet-title">パスワードを入力してください</div>
    <input type="password" class="fi" id="f-pw" placeholder="パスワード" onkeydown="if(event.key==='Enter')submitPw()">
    <div class="btn-row">
      <button class="btn-pri" style="width:100%" onclick="submitPw()">入る</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<div class="nav-loading" id="nav-loading">
  <div class="spinner"></div>
  <div class="nav-loading-text">しばらくお待ちください…</div>
</div>
<script>
__NAV_JS__
let curDate = new Date();
function dateFmt(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function dayLabel(d) {
  const wd = ['日','月','火','水','木','金','土'][d.getDay()];
  return `${d.getMonth()+1}月${d.getDate()}日(${wd})`;
}
function changeDay(diff) { curDate.setDate(curDate.getDate()+diff); render(); }
function onPersonChange() { render(); }
async function render() {
  document.getElementById('day-label').textContent = dayLabel(curDate);
  const person = document.getElementById('f-person').value;
  const ds = dateFmt(curDate);
  const r = await fetch(`/api/availability?person=${encodeURIComponent(person)}&date=${ds}`);
  const d = await r.json();
  const grid = document.getElementById('hour-grid');
  grid.innerHTML = '';
  grid.style.opacity = '1';
  grid.style.pointerEvents = 'auto';
  if (!d.ok) return;
  d.hours.forEach(h => {
    const btn = document.createElement('div');
    btn.className = 'hour-btn' + (h.booked ? ' busy' : h.available ? ' on' : '');
    if (h.booked) {
      btn.textContent = h.hour;
      const who = document.createElement('span');
      who.className = 'who';
      who.textContent = h.guest_name;
      btn.appendChild(who);
      const actions = document.createElement('div');
      actions.className = 'booking-actions';
      const editBtn = document.createElement('button');
      editBtn.className = 'act-btn'; editBtn.textContent = '編集';
      editBtn.onclick = (e) => { e.stopPropagation(); editBooking(h.booking_id, h.guest_name); };
      const delBtn = document.createElement('button');
      delBtn.className = 'act-btn danger'; delBtn.textContent = '削除';
      delBtn.onclick = (e) => { e.stopPropagation(); deleteBooking(h.booking_id, h.hour, h.guest_name); };
      actions.appendChild(editBtn); actions.appendChild(delBtn);
      btn.appendChild(actions);
    } else {
      btn.textContent = h.hour;
      btn.onclick = () => toggle(person, ds, h.hour);
    }
    grid.appendChild(btn);
  });
}
let toggling = false;
async function toggle(person, date, hour) {
  if (toggling) return;
  toggling = true;
  const grid = document.getElementById('hour-grid');
  grid.style.opacity = '0.5';
  grid.style.pointerEvents = 'none';
  toast('更新中…');
  try {
    const r = await fetch('/api/availability/toggle', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ person, date, hour }),
    });
    const d = await r.json();
    if (d.ok) { await render(); }
    else { toast(d.error || '更新に失敗しました'); await render(); }
  } catch(e) {
    toast('通信エラーが発生しました（サーバー起動中の可能性があります。少し待って再度お試しください）');
    grid.style.opacity = '1';
    grid.style.pointerEvents = 'auto';
  } finally {
    toggling = false;
  }
}
async function editBooking(bookingId, currentName) {
  const guest_name = window.prompt('ゲスト名を編集', currentName);
  if (guest_name === null) return;
  const trimmed = guest_name.trim();
  if (!trimmed) { toast('名前を入力してください'); return; }
  try {
    const r = await fetch(`/api/booking/${bookingId}/edit`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ guest_name: trimmed }),
    });
    const d = await r.json();
    if (d.ok) { toast('更新しました'); render(); }
    else { toast(d.error || '更新に失敗しました'); }
  } catch(e) { toast('通信エラーが発生しました'); }
}
async function deleteBooking(bookingId, hour, guestName) {
  if (!window.confirm(`${hour} ${guestName}様の予約を削除しますか？`)) return;
  try {
    const r = await fetch(`/api/booking/${bookingId}/delete`, { method: 'POST' });
    const d = await r.json();
    if (d.ok) { toast('削除しました'); render(); }
    else { toast(d.error || '削除に失敗しました'); }
  } catch(e) { toast('通信エラーが発生しました'); }
}
async function doLogout() {
  await fetch('/api/availability/logout', { method: 'POST' });
  location.reload();
}
async function checkAuth() {
  try {
    const d = await (await fetch('/api/availability/me')).json();
    if (d.authed) {
      document.getElementById('pw-overlay').classList.remove('open');
      render();
      checkStorage();
      checkLine();
    }
  } catch(e) {}
}
async function checkStorage() {
  try {
    const d = await (await fetch('/api/availability/storage-status')).json();
    document.getElementById('storage-warn').style.display = d.database_connected ? 'none' : 'block';
  } catch(e) {}
}
async function checkLine() {
  try {
    const d = await (await fetch('/api/line/status')).json();
    if (!d.ok) return;
    const card = document.getElementById('line-card');
    const desc = document.getElementById('line-desc');
    const people = document.getElementById('line-people');
    card.style.display = 'block';
    if (!d.configured) {
      desc.textContent = 'LINE通知は未設定です。LINE公式アカウントを作成し、環境変数 LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET を設定すると、予約の確定・キャンセル通知とリマインドがLINEに届きます。';
      people.innerHTML = '';
      return;
    }
    desc.textContent = `公式アカウントを友だち追加して、トークで「連携 名前」と送ると、その人の予約通知と${d.reminder_hours_before}時間前リマインドが届きます。（全員分は「連携 admin」）`;
    let html = d.people.map(p => `${p.linked > 0 ? '✅' : '⚪️'} ${p.name} ${p.linked > 0 ? '連携済み' : '未連携'}`).join('<br>');
    if (d.admin_linked > 0) html += `<br>👑 全体通知の受信者: ${d.admin_linked}人`;
    people.innerHTML = html;
  } catch(e) {}
}
async function submitPw() {
  const password = document.getElementById('f-pw').value;
  try {
    const r = await fetch('/api/availability/login', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ password }),
    });
    const d = await r.json();
    if (d.ok) {
      document.getElementById('pw-overlay').classList.remove('open');
      render();
      checkStorage();
      checkLine();
    } else {
      toast(d.error || 'パスワードが違います');
      document.getElementById('f-pw').value = '';
    }
  } catch(e) { toast('通信エラーが発生しました'); }
}
__TOAST_JS__
checkAuth();
</script>
</body>
</html>
"""

BOOK_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>__MEMBER__と__EVENT__予約</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <a class="back-btn" href="/" onclick="return goTo('/')">‹</a>
  <div class="header-icon">__ICON__</div>
  <div class="header-info">
    <div class="header-title">__MEMBER__ と__EVENT__予約</div>
    <div class="header-sub">__HEADER_SUB__</div>
  </div>
</div>
<div class="wrap">
  <div class="day-nav">
    <button class="day-btn" onclick="changeDay(-1)">‹</button>
    <span class="day-label" id="day-label"></span>
    <button class="day-btn" onclick="changeDay(1)">›</button>
  </div>
  <div class="hour-grid" id="hour-grid"></div>
</div>

<div class="overlay" id="bk-overlay" onclick="onBg(event)">
  <div class="sheet">
    <div class="handle"></div>
    <div class="sheet-title" id="bk-title"></div>
    <input type="text" class="fi" id="f-name" placeholder="お名前">
    <div class="btn-row">
      <button class="btn-sec" onclick="closeModal()">キャンセル</button>
      <button class="btn-pri" onclick="confirmBook()">予約する</button>
    </div>
  </div>
</div>
<div class="overlay" id="done-overlay" onclick="onDoneBg(event)">
  <div class="sheet" style="text-align:center;">
    <div class="handle"></div>
    <div style="font-size:40px; margin-bottom:8px;">✅</div>
    <div class="sheet-title" style="margin-bottom:6px;">予約が完了しました</div>
    <div class="card-sub" id="done-detail" style="margin-bottom:16px;"></div>
    <button class="btn-pri" onclick="closeDone()">閉じる</button>
  </div>
</div>
<div class="toast" id="toast"></div>
<div class="nav-loading" id="nav-loading">
  <div class="spinner"></div>
  <div class="nav-loading-text">しばらくお待ちください…</div>
</div>
<script>
__NAV_JS__
const SLUG = __SLUG__;
let curDate = new Date();
let daysData = [];
let pickHour = null;
function dateFmt(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function dayLabel(d) {
  const wd = ['日','月','火','水','木','金','土'][d.getDay()];
  return `${d.getMonth()+1}月${d.getDate()}日(${wd})`;
}
function changeDay(diff) { curDate.setDate(curDate.getDate()+diff); renderGrid(); }
async function loadSlots() {
  document.getElementById('hour-grid').innerHTML = '<div class="empty-msg">読み込み中…</div>';
  const r = await fetch(`/api/book/${SLUG}/slots`);
  const d = await r.json();
  if (d.ok) daysData = d.days;
  renderGrid();
}
function renderGrid() {
  document.getElementById('day-label').textContent = dayLabel(curDate);
  const ds = dateFmt(curDate);
  const grid = document.getElementById('hour-grid');
  grid.innerHTML = '';
  const day = daysData.find(x => x.date === ds);
  if (!day || day.hours.length === 0) {
    const msg = document.createElement('div');
    msg.className = 'empty-msg'; msg.textContent = 'この日に空いている時間はありません';
    grid.appendChild(msg);
    return;
  }
  day.hours.forEach(h => {
    const btn = document.createElement('div');
    btn.className = 'hour-btn on';
    btn.textContent = h;
    btn.onclick = () => openModal(ds, h);
    grid.appendChild(btn);
  });
}
function openModal(ds, h) {
  pickHour = { ds, h };
  document.getElementById('bk-title').textContent = `${ds} ${h} に予約`;
  document.getElementById('f-name').value = '';
  document.getElementById('bk-overlay').classList.add('open');
  setTimeout(() => document.getElementById('f-name').focus(), 80);
}
function closeModal() { document.getElementById('bk-overlay').classList.remove('open'); pickHour = null; }
function onBg(e) { if (e.target===document.getElementById('bk-overlay')) closeModal(); }
function showDone(ds, h) {
  document.getElementById('done-detail').textContent = `${ds} ${h}〜`;
  document.getElementById('done-overlay').classList.add('open');
}
function closeDone() { document.getElementById('done-overlay').classList.remove('open'); }
function onDoneBg(e) { if (e.target===document.getElementById('done-overlay')) closeDone(); }
async function confirmBook() {
  const guest_name = document.getElementById('f-name').value.trim();
  if (!guest_name) { toast('名前を入力してください'); return; }
  if (!pickHour) return;
  const { ds, h } = pickHour;
  try {
    const r = await fetch(`/api/book/${SLUG}`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ date: ds, hour: h, guest_name }),
    });
    const d = await r.json();
    if (d.ok) { closeModal(); showDone(ds, h); await loadSlots(); }
    else { toast(d.error || '予約できませんでした'); await loadSlots(); }
  } catch(e) { toast('通信エラーが発生しました。予約できませんでした'); }
}
__TOAST_JS__
loadSlots();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    cards = ""
    for m in MEMBERS:
        slug, name = m["slug"], m["name"]
        cards += (
            '<div class="card">'
            f'<div class="card-title">{SITE_ICON} {name} と{EVENT_LABEL}を予約する</div>'
            f'<div class="card-sub">{name} の空き時間から1時間を選んで予約</div>'
            f'<a class="btn-pri" href="/book/{slug}" onclick="return goTo(\'/book/{slug}\')">予約する</a>'
            '</div>'
        )
    html = (HOME_HTML
            .replace("__CSS__", CSS)
            .replace("__TITLE__", SITE_TITLE)
            .replace("__SUBTITLE__", SITE_SUBTITLE)
            .replace("__ICON__", SITE_ICON)
            .replace("__PEOPLE_LIST__", " / ".join(ALL_PEOPLE))
            .replace("__MEMBER_CARDS__", cards)
            .replace("__NAV_JS__", NAV_JS))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/availability")
def availability_page():
    options = "".join(f'<option value="{p}">{p}</option>' for p in ALL_PEOPLE)
    html = (AVAILABILITY_HTML
            .replace("__CSS__", CSS)
            .replace("__PERSON_OPTIONS__", options)
            .replace("__TOAST_JS__", TOAST_JS)
            .replace("__NAV_JS__", NAV_JS))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/book/<slug>")
def book_page(slug):
    member, _ = _resolve_slug(slug)
    if member is None:
        return "Not Found", 404
    header_sub = f"1時間の{EVENT_LABEL}を予約できます"
    html = (BOOK_HTML
            .replace("__CSS__", CSS)
            .replace("__MEMBER__", member)
            .replace("__EVENT__", EVENT_LABEL)
            .replace("__ICON__", SITE_ICON)
            .replace("__SLUG__", json.dumps(slug))
            .replace("__HEADER_SUB__", header_sub)
            .replace("__TOAST_JS__", TOAST_JS)
            .replace("__NAV_JS__", NAV_JS))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


_ensure_tables()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
