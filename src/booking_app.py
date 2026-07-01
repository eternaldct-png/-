"""
面談予約アプリ — 独立した Flask アプリ

5人（kazuto / あまりん / さな / しー / かぴのすけ）のうち、
kazuto と各メンバーの組み合わせ（4ペア）について:
  - 各人がログイン不要で自分の空き時間（1時間単位）を登録
  - kazuto とメンバー双方が空いている時間だけが予約ページに公開される
  - 外部ゲストがログイン不要で名前だけ入力して1時間の面談を予約できる
  - 予約は早い者勝ち（先着順で埋まったら他の人は予約できない）
  - kazuto は全ペアに共通の参加者なので、kazuto が埋まれば他の3ペアの
    同時刻も自動的に予約不可になる（同一スロットはシステム全体で一意）
  - 予約が確定すると eternal.d.c.t@gmail.com の Google カレンダーに同期

環境変数（Render などで設定）:
  FLASK_SECRET_KEY            セッション用秘密鍵
  DATABASE_URL                Supabase の接続 URI（永続化に必要。未設定時はファイル）
  GOOGLE_SERVICE_ACCOUNT_JSON Google サービスアカウントの JSON キー
  GOOGLE_CALENDAR_ID          同期先カレンダー ID（eternal.d.c.t@gmail.com と共有したカレンダー）
"""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify, session

sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

AVAILABILITY_PASSWORD = os.environ.get("AVAILABILITY_PASSWORD", "ETERNALLOVE")

ADMIN = "kazuto"
MEMBER_SLUGS = {
    "amarin": "あまりん",
    "sana": "さな",
    "shi": "しー",
    "kapinosuke": "かぴのすけ",
}
ALL_PEOPLE = [ADMIN] + list(MEMBER_SLUGS.values())
HOURS = [f"{h:02d}:00" for h in range(9, 22)]  # 09:00〜21:00開始、最終枠21:00-22:00
DAYS_AHEAD = 21  # 予約ページに表示する日数


AVAILABILITY_FILE = Path("posts/booking_availability.json")
BOOKINGS_FILE = Path("posts/booking_reservations.json")
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
                        slot TEXT NOT NULL UNIQUE,
                        guest_name TEXT NOT NULL DEFAULT '',
                        created_at TEXT DEFAULT '',
                        google_calendar_event_id TEXT
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
    """slot はシステム全体で一意（kazuto が全ペア共通のため）。
    既に予約済みなら None を返す。"""
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
    if any(r["slot"] == slot for r in rows):
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


# ── 予約ロジック ─────────────────────────────────────────────────

def slot_iso(date_str, hour_str):
    return f"{date_str}T{hour_str}:00+09:00"


def slot_end_iso(date_str, hour_str):
    h = int(hour_str[:2])
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=JST) + timedelta(hours=h + 1)
    return dt.strftime("%Y-%m-%dT%H:%M:00+09:00")


def person_available_slots(person):
    return {r["slot"] for r in load_availability() if r["person"] == person}


def booked_slots():
    return {r["slot"] for r in load_bookings()}


def pair_open_slots(member_name):
    """kazuto と member_name の両方が空けていて、まだ誰にも予約されていないスロット集合"""
    return person_available_slots(ADMIN) & person_available_slots(member_name) - booked_slots()


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
    booked = booked_slots()
    booked_by = {r["slot"]: r for r in load_bookings()}
    hours = []
    for h in HOURS:
        slot = slot_iso(date, h)
        b = booked_by.get(slot)
        hours.append({
            "hour": h,
            "available": slot in avail,
            "booked": slot in booked,
            "booked_with": b["member"] if b else "",
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
    if slot in booked_slots():
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
                "title": f"面談: {guest_name} × {booking['member']}",
                "description": f"{booking['member']} との1時間面談（ゲスト: {guest_name}）",
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
    return jsonify({"ok": True})


# ── API: 面談予約（公開） ────────────────────────────────────────

@app.route("/api/book/<slug>/slots")
def api_book_slots(slug):
    member = MEMBER_SLUGS.get(slug)
    if not member:
        return jsonify({"error": "not found"}), 404
    open_slots = pair_open_slots(member)
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
    member = MEMBER_SLUGS.get(slug)
    if not member:
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
    if slot not in pair_open_slots(member):
        return jsonify({"error": "この時間はすでに予約できません"}), 409
    booking = create_booking(member, slot, guest_name)
    if not booking:
        return jsonify({"error": "この時間はすでに予約できません"}), 409
    try:
        from google_calendar import sync_create
        google_id = sync_create({
            "title": f"面談: {guest_name} × {member}",
            "description": f"{member} との1時間面談（ゲスト: {guest_name}）",
            "event_type": "interview",
            "start_datetime": slot,
            "end_datetime": slot_end_iso(date, hour),
            "all_day": False,
        })
        if google_id:
            set_booking_google_event_id(booking["id"], google_id)
    except Exception:
        pass
    return jsonify({"ok": True})


# ── API: メンバー内部予約（パスワード保護） ──────────────────────

@app.route("/api/self-book/<slug>/slots")
def api_self_book_slots(slug):
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    member = MEMBER_SLUGS.get(slug)
    if not member:
        return jsonify({"error": "not found"}), 404
    open_slots = pair_open_slots(member)
    today = datetime.now(JST).date()
    days = []
    for i in range(DAYS_AHEAD):
        d = today + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        hours = [h for h in HOURS if slot_iso(ds, h) in open_slots]
        if hours:
            days.append({"date": ds, "hours": hours})
    return jsonify({"ok": True, "member": member, "days": days})


@app.route("/api/self-book/<slug>", methods=["POST"])
def api_self_book_create(slug):
    if not is_avail_authed():
        return jsonify({"error": "unauthorized"}), 401
    member = MEMBER_SLUGS.get(slug)
    if not member:
        return jsonify({"error": "not found"}), 404
    data = request.get_json(force=True)
    date = data.get("date", "")
    hour = data.get("hour", "")
    if not date or hour not in HOURS:
        return jsonify({"error": "invalid params"}), 400
    slot = slot_iso(date, hour)
    if slot not in pair_open_slots(member):
        return jsonify({"error": "この時間はすでに予約できません"}), 409
    booking = create_booking(member, slot, member)
    if not booking:
        return jsonify({"error": "この時間はすでに予約できません"}), 409
    try:
        from google_calendar import sync_create
        google_id = sync_create({
            "title": f"打ち合わせ: kazuto × {member}",
            "description": f"kazuto × {member} 内部打ち合わせ",
            "event_type": "interview",
            "start_datetime": slot,
            "end_datetime": slot_end_iso(date, hour),
            "all_day": False,
        })
        if google_id:
            set_booking_google_event_id(booking["id"], google_id)
    except Exception:
        pass
    return jsonify({"ok": True})


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
"""

TOAST_JS = """
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2600);
}
"""

HOME_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>面談スケジュール</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <div class="header-icon">🤝</div>
  <div class="header-info">
    <div class="header-title">面談スケジュール</div>
    <div class="header-sub">空き時間登録 &amp; 面談予約</div>
  </div>
</div>
<div class="wrap">
  <div class="card">
    <div class="card-title">📝 空き時間を登録する</div>
    <div class="card-sub">kazuto / あまりん / さな / しー / かぴのすけ 共通</div>
    <a class="btn-pri" href="/availability">空き時間を登録する</a>
  </div>
  __MEMBER_CARDS__
</div>
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
  <a class="back-btn" href="/">‹</a>
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
<script>
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
      who.textContent = `${h.booked_with}×${h.guest_name}`;
      btn.appendChild(who);
      const actions = document.createElement('div');
      actions.className = 'booking-actions';
      const editBtn = document.createElement('button');
      editBtn.className = 'act-btn'; editBtn.textContent = '編集';
      editBtn.onclick = (e) => { e.stopPropagation(); editBooking(h.booking_id, h.guest_name); };
      const delBtn = document.createElement('button');
      delBtn.className = 'act-btn danger'; delBtn.textContent = '削除';
      delBtn.onclick = (e) => { e.stopPropagation(); deleteBooking(h.booking_id, h.hour, h.booked_with); };
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
async function deleteBooking(bookingId, hour, member) {
  if (!window.confirm(`${hour} ${member}の予約を削除しますか？`)) return;
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
    }
  } catch(e) {}
}
async function checkStorage() {
  try {
    const d = await (await fetch('/api/availability/storage-status')).json();
    document.getElementById('storage-warn').style.display = d.database_connected ? 'none' : 'block';
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
<title>__MEMBER__と面談予約</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <a class="back-btn" href="/">‹</a>
  <div class="header-icon">🤝</div>
  <div class="header-info">
    <div class="header-title">__MEMBER__ と面談予約</div>
    <div class="header-sub">1時間の面談を予約できます（kazuto 同席）</div>
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
<div class="toast" id="toast"></div>
<script>
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
async function confirmBook() {
  const guest_name = document.getElementById('f-name').value.trim();
  if (!guest_name) { toast('名前を入力してください'); return; }
  if (!pickHour) return;
  try {
    const r = await fetch(`/api/book/${SLUG}`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ date: pickHour.ds, hour: pickHour.h, guest_name }),
    });
    const d = await r.json();
    if (d.ok) { closeModal(); toast('予約が完了しました'); await loadSlots(); }
    else { toast(d.error || '予約に失敗しました'); await loadSlots(); }
  } catch(e) { toast('通信エラーが発生しました'); }
}
__TOAST_JS__
loadSlots();
</script>
</body>
</html>
"""


SELF_BOOK_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>kazuto × __MEMBER__ — 内部予約</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <a class="back-btn" href="/">‹</a>
  <div class="header-icon">🗓️</div>
  <div class="header-info">
    <div class="header-title">kazuto × __MEMBER__ 予約</div>
    <div class="header-sub">内部打ち合わせスケジュール</div>
  </div>
  <button class="back-btn" onclick="doLogout()" title="ログアウト">🔒</button>
</div>
<div class="wrap">
  <div class="day-nav">
    <button class="day-btn" onclick="changeDay(-1)">‹</button>
    <span class="day-label" id="day-label"></span>
    <button class="day-btn" onclick="changeDay(1)">›</button>
  </div>
  <div class="hour-grid" id="hour-grid"></div>
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

<div class="overlay" id="bk-overlay" onclick="onBg(event)">
  <div class="sheet">
    <div class="handle"></div>
    <div class="sheet-title" id="bk-title"></div>
    <div class="btn-row">
      <button class="btn-sec" onclick="closeModal()">キャンセル</button>
      <button class="btn-pri" onclick="confirmBook()">予約する</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
const SLUG = __SLUG__;
let curDate = new Date();
let daysData = [];
let pickSlot = null;
function dateFmt(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function dayLabel(d) {
  const wd = ['日','月','火','水','木','金','土'][d.getDay()];
  return `${d.getMonth()+1}月${d.getDate()}日(${wd})`;
}
function changeDay(diff) { curDate.setDate(curDate.getDate()+diff); renderGrid(); }
async function loadSlots() {
  const r = await fetch(`/api/self-book/${SLUG}/slots`);
  if (r.status === 401) { checkAuth(); return; }
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
  pickSlot = { ds, h };
  document.getElementById('bk-title').textContent = `${ds} ${h} に予約しますか？`;
  document.getElementById('bk-overlay').classList.add('open');
}
function closeModal() { document.getElementById('bk-overlay').classList.remove('open'); pickSlot = null; }
function onBg(e) { if (e.target===document.getElementById('bk-overlay')) closeModal(); }
async function confirmBook() {
  if (!pickSlot) return;
  try {
    const r = await fetch(`/api/self-book/${SLUG}`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ date: pickSlot.ds, hour: pickSlot.h }),
    });
    const d = await r.json();
    if (d.ok) { closeModal(); toast('予約が完了しました'); await loadSlots(); }
    else { toast(d.error || '予約に失敗しました'); await loadSlots(); }
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
      loadSlots();
    }
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
      loadSlots();
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


@app.route("/")
def index():
    cards = ""
    for slug, name in MEMBER_SLUGS.items():
        cards += (
            '<div class="card">'
            f'<div class="card-title">🤝 {name} と面談を予約する</div>'
            f'<div class="card-sub">kazuto × {name} の空き時間から1時間を選んで予約</div>'
            f'<a class="btn-pri" href="/book/{slug}">予約する</a>'
            '</div>'
        )
    cards += '<div class="card"><div class="card-title" style="margin-bottom:10px;">🗓️ メンバー内部予約（PW必要）</div>'
    for slug, name in MEMBER_SLUGS.items():
        cards += (
            f'<a class="btn-sec" href="/self-book/{slug}" '
            f'style="margin-bottom:8px;">kazuto × {name}</a>'
        )
    cards += '</div>'
    html = HOME_HTML.replace("__CSS__", CSS).replace("__MEMBER_CARDS__", cards)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/availability")
def availability_page():
    options = "".join(f'<option value="{p}">{p}</option>' for p in ALL_PEOPLE)
    html = (AVAILABILITY_HTML
            .replace("__CSS__", CSS)
            .replace("__PERSON_OPTIONS__", options)
            .replace("__TOAST_JS__", TOAST_JS))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/book/<slug>")
def book_page(slug):
    member = MEMBER_SLUGS.get(slug)
    if not member:
        return "Not Found", 404
    html = (BOOK_HTML
            .replace("__CSS__", CSS)
            .replace("__MEMBER__", member)
            .replace("__SLUG__", json.dumps(slug))
            .replace("__TOAST_JS__", TOAST_JS))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/self-book/<slug>")
def self_book_page(slug):
    member = MEMBER_SLUGS.get(slug)
    if not member:
        return "Not Found", 404
    html = (SELF_BOOK_HTML
            .replace("__CSS__", CSS)
            .replace("__MEMBER__", member)
            .replace("__SLUG__", json.dumps(slug))
            .replace("__TOAST_JS__", TOAST_JS))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


_ensure_tables()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
