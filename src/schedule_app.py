"""
スケジュールカレンダーアプリ — 独立した Flask アプリ

機能:
  - 月次カレンダー表示（配信/ライブ・グッズ/販売・汎用メモ）
  - 予定の追加・編集・削除（パスワード認証必須）
  - Google カレンダーへの一方向同期（サービスアカウント経由）

環境変数（Render などで設定）:
  SCHEDULE_PASSWORD        ログインパスワード（必須）
  FLASK_SECRET_KEY         セッション用秘密鍵
  GOOGLE_SERVICE_ACCOUNT_JSON  Google サービスアカウントの JSON キー
  GOOGLE_CALENDAR_ID       同期先カレンダー ID（省略時: primary）
"""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, request, jsonify, session, redirect

sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

EVENTS_FILE = Path("posts/schedule_events.json")


# ── データ管理 ────────────────────────────────────────────────────

def load_events():
    if EVENTS_FILE.exists():
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_events(events):
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


# ── 認証 ─────────────────────────────────────────────────────────

def is_authed():
    return bool(session.get("schedule_ok"))


@app.route("/api/me")
def api_me():
    return jsonify({"authed": is_authed()})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    pw = os.environ.get("SCHEDULE_PASSWORD", "")
    if pw and data.get("password") == pw:
        session["schedule_ok"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "パスワードが違います"}), 401


@app.route("/logout")
def logout():
    session.pop("schedule_ok", None)
    return redirect("/")


# ── イベント CRUD API ─────────────────────────────────────────────

@app.route("/api/events", methods=["GET"])
def api_list():
    return jsonify({"ok": True, "events": load_events()})


@app.route("/api/events", methods=["POST"])
def api_create():
    if not is_authed():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    event = {
        "id": str(uuid.uuid4()),
        "title": str(data.get("title", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "event_type": data.get("event_type", "general"),
        "platform": data.get("platform", ""),
        "start_datetime": data.get("start_datetime", ""),
        "end_datetime": data.get("end_datetime", ""),
        "all_day": bool(data.get("all_day", False)),
        "google_calendar_event_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from google_calendar import sync_create
        event["google_calendar_event_id"] = sync_create(event)
    except Exception:
        pass
    events = load_events()
    events.append(event)
    save_events(events)
    return jsonify({"ok": True, "event": event})


@app.route("/api/events/<event_id>", methods=["PUT"])
def api_update(event_id):
    if not is_authed():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    events = load_events()
    for i, ev in enumerate(events):
        if ev["id"] == event_id:
            events[i].update({
                "title": str(data.get("title", ev["title"])).strip(),
                "description": str(data.get("description", ev.get("description", ""))).strip(),
                "event_type": data.get("event_type", ev["event_type"]),
                "platform": data.get("platform", ev.get("platform", "")),
                "start_datetime": data.get("start_datetime", ev["start_datetime"]),
                "end_datetime": data.get("end_datetime", ev.get("end_datetime", "")),
                "all_day": bool(data.get("all_day", ev.get("all_day", False))),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            try:
                from google_calendar import sync_update
                sync_update(ev.get("google_calendar_event_id"), events[i])
            except Exception:
                pass
            save_events(events)
            return jsonify({"ok": True, "event": events[i]})
    return jsonify({"error": "not found"}), 404


@app.route("/api/events/<event_id>", methods=["DELETE"])
def api_delete(event_id):
    if not is_authed():
        return jsonify({"error": "unauthorized"}), 401
    events = load_events()
    for i, ev in enumerate(events):
        if ev["id"] == event_id:
            try:
                from google_calendar import sync_delete
                sync_delete(ev.get("google_calendar_event_id"))
            except Exception:
                pass
            events.pop(i)
            save_events(events)
            return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404


# ── フロントエンド ────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0a0a1a">
<title>スケジュール</title>
<style>
:root {
  --bg: #0a0a1a;
  --surface: #13132a;
  --surface2: #1c1c38;
  --surface3: #252548;
  --accent: #6d28d9;
  --accent2: #7c3aed;
  --accent-light: #a78bfa;
  --text: #e2e8f0;
  --muted: #7a859a;
  --border: #252548;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --live: #ef4444;
  --goods: #f59e0b;
  --general: #818cf8;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  min-height: 100vh;
  padding-bottom: calc(86px + var(--safe-bottom));
}

/* Header */
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 18px 14px;
  display: flex; align-items: center; gap: 12px;
  position: sticky; top: 0; z-index: 100;
}
.header-icon {
  width: 40px; height: 40px;
  background: linear-gradient(135deg, var(--accent2), #4c1d95);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; flex-shrink: 0;
}
.header-info { flex: 1; min-width: 0; }
.header-title { font-size: 17px; font-weight: 700; }
.header-sub { font-size: 11px; color: var(--muted); margin-top: 1px; }
.auth-btn {
  background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; padding: 7px 12px;
  color: var(--muted); font-size: 12px; font-weight: 600;
  cursor: pointer; flex-shrink: 0; transition: all 0.15s;
  white-space: nowrap;
}
.auth-btn.authed { color: var(--accent-light); border-color: var(--accent2); }

/* Month nav */
.month-nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px; max-width: 560px; margin: 0 auto;
}
.month-btn {
  background: var(--surface); border: 1.5px solid var(--border);
  color: var(--text); width: 38px; height: 38px; border-radius: 10px;
  font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}
.month-btn:active { background: var(--surface2); }
.month-label { font-size: 18px; font-weight: 700; letter-spacing: -0.02em; }

/* Legend */
.legend {
  display: flex; gap: 14px; flex-wrap: wrap;
  padding: 2px 16px 12px; max-width: 560px; margin: 0 auto;
}
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--muted); }
.legend-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }

/* Calendar */
.cal-wrap { max-width: 560px; margin: 0 auto; padding: 0 12px; }
.cal-head {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; margin-bottom: 4px;
}
.cal-head > div {
  text-align: center; font-size: 11px; font-weight: 600;
  color: var(--muted); padding: 4px 0;
}
.cal-head > .sat { color: #60a5fa; }
.cal-head > .sun { color: #f87171; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }
.cal-cell {
  min-height: 66px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 5px 4px 3px; cursor: pointer; overflow: hidden;
  transition: background 0.12s;
}
.cal-cell:active { background: var(--surface2); }
.cal-cell.other-month { opacity: 0.28; }
.day-num {
  font-size: 12px; font-weight: 600;
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; margin-bottom: 3px;
}
.cal-cell.today .day-num { background: var(--accent2); color: white; }
.cal-cell.sat .day-num { color: #60a5fa; }
.cal-cell.sun .day-num { color: #f87171; }
.cal-cell.today.sat .day-num,
.cal-cell.today.sun .day-num { color: white; }
.ev-chip {
  display: block; font-size: 9.5px; font-weight: 600;
  border-radius: 3px; padding: 1px 4px; margin-bottom: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  cursor: pointer; color: white;
}
.ev-chip.live    { background: var(--live); }
.ev-chip.goods   { background: var(--goods); color: #1a0a00; }
.ev-chip.general { background: var(--general); }
.ev-more { font-size: 9px; color: var(--muted); padding-left: 2px; }

/* FAB */
.fab {
  position: fixed; bottom: calc(24px + var(--safe-bottom)); right: 20px;
  width: 56px; height: 56px; background: var(--accent2); border: none;
  border-radius: 50%; color: white; font-size: 28px; cursor: pointer;
  box-shadow: 0 4px 24px rgba(124,58,237,0.55);
  display: none; align-items: center; justify-content: center;
  z-index: 200; transition: transform 0.15s;
}
.fab:active { transform: scale(0.91); }
.fab.visible { display: flex; }

/* Modal (bottom sheet) */
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.75);
  z-index: 300; display: none; align-items: flex-end; justify-content: center;
}
.overlay.open { display: flex; }
.sheet {
  background: var(--surface); border-radius: 22px 22px 0 0;
  width: 100%; max-width: 560px; max-height: 93vh; overflow-y: auto;
  padding: 16px 18px calc(16px + var(--safe-bottom));
}
.handle {
  width: 38px; height: 4px; background: var(--border);
  border-radius: 2px; margin: 0 auto 16px;
}
.sheet-title { font-size: 18px; font-weight: 700; margin-bottom: 18px; }
.fg { margin-bottom: 13px; }
.fl {
  display: block; font-size: 10px; font-weight: 700;
  color: var(--muted); letter-spacing: 0.07em; text-transform: uppercase;
  margin-bottom: 5px;
}
.fi {
  width: 100%; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--text); font-size: 14px;
  padding: 10px 12px; outline: none; font-family: inherit;
}
.fi:focus { border-color: var(--accent2); }
textarea.fi { min-height: 68px; resize: vertical; }
select.fi { appearance: none; }

.type-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.ty-btn {
  padding: 10px 4px; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--muted); font-size: 12px; font-weight: 600;
  cursor: pointer; display: flex; flex-direction: column;
  align-items: center; gap: 3px; transition: all 0.13s;
}
.ty-btn .ico { font-size: 18px; }
.ty-btn.sel-live    { border-color: var(--live);    color: var(--live);    background: rgba(239,68,68,0.1); }
.ty-btn.sel-goods   { border-color: var(--goods);   color: #d97706; background: rgba(245,158,11,0.1); }
.ty-btn.sel-general { border-color: var(--general); color: var(--general); background: rgba(129,140,248,0.1); }

.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.tog-row {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; padding: 10px 12px;
}
.tog-lbl { font-size: 13px; }
.tog { position: relative; width: 44px; height: 26px; }
.tog input { opacity: 0; width: 0; height: 0; }
.tog-sl {
  position: absolute; inset: 0; background: var(--border);
  border-radius: 13px; cursor: pointer; transition: background 0.2s;
}
.tog-sl::before {
  content: ""; position: absolute; width: 20px; height: 20px;
  border-radius: 50%; background: white; top: 3px; left: 3px;
  transition: transform 0.2s;
}
.tog input:checked + .tog-sl { background: var(--accent2); }
.tog input:checked + .tog-sl::before { transform: translateX(18px); }

.btn-row { display: flex; gap: 10px; margin-top: 18px; }
.btn-pri {
  flex: 1; padding: 14px; background: var(--accent2); border: none;
  border-radius: 12px; color: white; font-size: 15px; font-weight: 700;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-pri:active { opacity: 0.8; }
.btn-sec {
  padding: 14px 18px; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 12px; color: var(--muted); font-size: 15px; font-weight: 600; cursor: pointer;
}
.btn-danger {
  padding: 14px 16px; background: rgba(239,68,68,0.1);
  border: 1.5px solid var(--live); border-radius: 12px;
  color: var(--live); font-size: 15px; font-weight: 600; cursor: pointer;
}

.gcal-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(66,133,244,0.12); border: 1px solid rgba(66,133,244,0.35);
  color: #60a5fa; border-radius: 8px; font-size: 12px;
  padding: 5px 10px; margin-bottom: 6px;
}

/* Toast */
.toast {
  position: fixed; bottom: calc(92px + var(--safe-bottom)); left: 50%;
  transform: translateX(-50%) translateY(14px);
  background: var(--surface3); border: 1px solid var(--border); color: var(--text);
  padding: 10px 18px; border-radius: 22px; font-size: 13px;
  opacity: 0; transition: all 0.28s; white-space: nowrap; z-index: 500; pointer-events: none;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>

<div class="header">
  <div class="header-icon">📅</div>
  <div class="header-info">
    <div class="header-title">スケジュール</div>
    <div class="header-sub">予定管理 &amp; Google カレンダー同期</div>
  </div>
  <button class="auth-btn" id="auth-btn" onclick="onAuthBtn()">🔒 ログイン</button>
</div>

<div class="month-nav">
  <button class="month-btn" onclick="changeMonth(-1)">‹</button>
  <span class="month-label" id="month-label"></span>
  <button class="month-btn" onclick="changeMonth(1)">›</button>
</div>

<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:var(--live)"></div>配信/ライブ</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--goods)"></div>グッズ/販売</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--general)"></div>汎用メモ</div>
</div>

<div class="cal-wrap">
  <div class="cal-head">
    <div>月</div><div>火</div><div>水</div><div>木</div><div>金</div>
    <div class="sat">土</div><div class="sun">日</div>
  </div>
  <div class="cal-grid" id="cal-grid"></div>
</div>

<button class="fab" id="fab" onclick="requireAuth(()=>openModal(null))">＋</button>

<!-- 予定モーダル -->
<div class="overlay" id="ev-overlay" onclick="onEvBg(event)">
  <div class="sheet">
    <div class="handle"></div>
    <div class="sheet-title" id="ev-title">予定を追加</div>

    <div class="fg">
      <label class="fl">タイトル</label>
      <input type="text" class="fi" id="f-title" placeholder="予定のタイトル">
    </div>

    <div class="fg">
      <label class="fl">種類</label>
      <div class="type-row">
        <button class="ty-btn" id="btn-live"    onclick="setType('live')"><span class="ico">🔴</span>配信/ライブ</button>
        <button class="ty-btn" id="btn-goods"   onclick="setType('goods')"><span class="ico">🛍️</span>グッズ/販売</button>
        <button class="ty-btn" id="btn-general" onclick="setType('general')"><span class="ico">📝</span>汎用メモ</button>
      </div>
    </div>

    <div class="fg" id="pf-group" style="display:none">
      <label class="fl">プラットフォーム</label>
      <select class="fi" id="f-pf">
        <option value="">選択してください</option>
        <option value="YouTube">YouTube</option>
        <option value="TikTok">TikTok</option>
        <option value="X">X (Twitter)</option>
        <option value="Instagram">Instagram</option>
        <option value="その他">その他</option>
      </select>
    </div>

    <div class="fg">
      <div class="tog-row">
        <span class="tog-lbl">終日</span>
        <label class="tog">
          <input type="checkbox" id="f-allday" onchange="onAlldayChange()">
          <span class="tog-sl"></span>
        </label>
      </div>
    </div>

    <div id="dt-block">
      <div class="fg">
        <div class="row2">
          <div><label class="fl">開始日</label><input type="date" class="fi" id="f-sd"></div>
          <div><label class="fl">開始時刻</label><input type="time" class="fi" id="f-st" value="20:00"></div>
        </div>
      </div>
      <div class="fg">
        <div class="row2">
          <div><label class="fl">終了日</label><input type="date" class="fi" id="f-ed"></div>
          <div><label class="fl">終了時刻</label><input type="time" class="fi" id="f-et" value="22:00"></div>
        </div>
      </div>
    </div>

    <div id="ad-block" style="display:none">
      <div class="fg">
        <div class="row2">
          <div><label class="fl">開始日</label><input type="date" class="fi" id="f-sd-ad"></div>
          <div><label class="fl">終了日</label><input type="date" class="fi" id="f-ed-ad"></div>
        </div>
      </div>
    </div>

    <div class="fg">
      <label class="fl">メモ</label>
      <textarea class="fi" id="f-desc" placeholder="詳細・メモ（任意）"></textarea>
    </div>

    <div id="gcal-info"></div>

    <div class="btn-row" id="br-new">
      <button class="btn-sec"  onclick="closeEvModal()">キャンセル</button>
      <button class="btn-pri"  onclick="saveEvent()">保存</button>
    </div>
    <div class="btn-row" id="br-edit" style="display:none">
      <button class="btn-danger" onclick="deleteEvent()">削除</button>
      <button class="btn-pri"    onclick="saveEvent()">保存</button>
    </div>
  </div>
</div>

<!-- ログインモーダル -->
<div class="overlay" id="ln-overlay" onclick="onLnBg(event)">
  <div class="sheet">
    <div class="handle"></div>
    <div class="sheet-title">ログイン</div>
    <div class="fg">
      <label class="fl">パスワード</label>
      <input type="password" class="fi" id="ln-pw" placeholder="パスワードを入力"
        onkeydown="if(event.key==='Enter')doLogin()">
    </div>
    <div id="ln-err" style="color:var(--live);font-size:13px;margin-bottom:8px;display:none"></div>
    <div class="btn-row">
      <button class="btn-sec" onclick="closeLnModal()">キャンセル</button>
      <button class="btn-pri" onclick="doLogin()">ログイン</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let Y, M, events = [], editId = null, selType = 'general';
let authed = false, pendingFn = null;

(function(){
  const n = new Date(); Y = n.getFullYear(); M = n.getMonth();
  checkAuth().then(loadEvents);
})();

/* ── 認証 ──────────────────────────────────────────────────────── */
async function checkAuth() {
  try { const d = await (await fetch('/api/me')).json(); authed = !!d.authed; }
  catch(e) { authed = false; }
  refreshAuthUI();
}

function refreshAuthUI() {
  const btn = document.getElementById('auth-btn');
  const fab = document.getElementById('fab');
  if (authed) {
    btn.textContent = '🔓 ログアウト'; btn.classList.add('authed');
    fab.classList.add('visible');
  } else {
    btn.textContent = '🔒 ログイン'; btn.classList.remove('authed');
    fab.classList.remove('visible');
  }
}

function onAuthBtn() {
  if (authed) {
    fetch('/logout').then(() => { authed = false; refreshAuthUI(); toast('ログアウトしました'); });
  } else { openLnModal(); }
}

function requireAuth(fn) {
  if (authed) fn(); else { pendingFn = fn; openLnModal(); }
}

function openLnModal() {
  document.getElementById('ln-pw').value = '';
  document.getElementById('ln-err').style.display = 'none';
  document.getElementById('ln-overlay').classList.add('open');
  setTimeout(() => document.getElementById('ln-pw').focus(), 80);
}
function closeLnModal() { document.getElementById('ln-overlay').classList.remove('open'); }
function onLnBg(e) { if (e.target===document.getElementById('ln-overlay')) closeLnModal(); }

async function doLogin() {
  const pw = document.getElementById('ln-pw').value;
  const errEl = document.getElementById('ln-err');
  try {
    const r = await fetch('/login', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ password: pw }),
    });
    if (r.ok) {
      authed = true; refreshAuthUI(); closeLnModal(); toast('ログインしました');
      if (pendingFn) { const f = pendingFn; pendingFn = null; f(); }
    } else {
      errEl.textContent = 'パスワードが違います'; errEl.style.display = 'block';
      document.getElementById('ln-pw').value = '';
      document.getElementById('ln-pw').focus();
    }
  } catch(e) {
    errEl.textContent = '通信エラーが発生しました'; errEl.style.display = 'block';
  }
}

/* ── カレンダー ─────────────────────────────────────────────────── */
async function loadEvents() {
  try { const d = await (await fetch('/api/events')).json(); if (d.ok) events = d.events || []; }
  catch(e) {}
  renderCal();
}

function changeMonth(d) {
  M += d;
  if (M < 0)  { M = 11; Y--; }
  if (M > 11) { M = 0;  Y++; }
  renderCal();
}

function dateFmt(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function renderCal() {
  document.getElementById('month-label').textContent = `${Y}年${M+1}月`;
  const grid = document.getElementById('cal-grid');
  grid.innerHTML = '';

  const first = new Date(Y, M, 1);
  let dow = first.getDay(); dow = dow===0 ? 6 : dow-1;
  const dim = new Date(Y, M+1, 0).getDate();
  const dip = new Date(Y, M,   0).getDate();
  const today = dateFmt(new Date());

  const cells = [];
  for (let i=dow-1; i>=0; i--) cells.push({d:dip-i, m:M-1, y:Y, other:true});
  for (let d=1; d<=dim; d++)   cells.push({d, m:M, y:Y, other:false});
  const rem = (7 - cells.length%7) % 7;
  for (let d=1; d<=rem; d++)   cells.push({d, m:M+1, y:Y, other:true});

  cells.forEach(cell => {
    const dt = new Date(cell.y, cell.m, cell.d);
    const ds = dateFmt(dt);
    const wd = dt.getDay();
    const el = document.createElement('div');
    el.className = 'cal-cell'
      + (cell.other ? ' other-month' : '')
      + (ds===today ? ' today' : '')
      + (wd===6 ? ' sat' : wd===0 ? ' sun' : '');

    const dn = document.createElement('div');
    dn.className = 'day-num'; dn.textContent = cell.d;
    el.appendChild(dn);

    const dayEvs = events.filter(ev => (ev.start_datetime||'').slice(0,10)===ds);
    dayEvs.slice(0,3).forEach(ev => {
      const chip = document.createElement('div');
      chip.className = `ev-chip ${ev.event_type||'general'}`;
      chip.textContent = ev.title || '(無題)';
      chip.onclick = e => { e.stopPropagation(); requireAuth(()=>openEditModal(ev)); };
      el.appendChild(chip);
    });
    if (dayEvs.length > 3) {
      const more = document.createElement('div');
      more.className = 'ev-more'; more.textContent = `+${dayEvs.length-3}件`;
      el.appendChild(more);
    }
    el.onclick = () => requireAuth(()=>openModal(ds));
    grid.appendChild(el);
  });
}

/* ── 予定モーダル ───────────────────────────────────────────────── */
function setType(t) {
  selType = t;
  ['live','goods','general'].forEach(x => {
    document.getElementById(`btn-${x}`).className = 'ty-btn' + (x===t ? ` sel-${x}` : '');
  });
  document.getElementById('pf-group').style.display = t==='live' ? 'block' : 'none';
}

function onAlldayChange() {
  const v = document.getElementById('f-allday').checked;
  document.getElementById('dt-block').style.display = v ? 'none' : 'block';
  document.getElementById('ad-block').style.display = v ? 'block' : 'none';
}

function openModal(preDate) {
  editId = null;
  document.getElementById('ev-title').textContent = '予定を追加';
  document.getElementById('br-new').style.display  = '';
  document.getElementById('br-edit').style.display = 'none';
  document.getElementById('gcal-info').innerHTML   = '';
  document.getElementById('f-title').value = '';
  document.getElementById('f-desc').value  = '';
  document.getElementById('f-pf').value    = '';
  document.getElementById('f-allday').checked = false;
  onAlldayChange();
  const ds = preDate || dateFmt(new Date());
  ['f-sd','f-ed','f-sd-ad','f-ed-ad'].forEach(id => document.getElementById(id).value = ds);
  document.getElementById('f-st').value = '20:00';
  document.getElementById('f-et').value = '22:00';
  setType('general');
  document.getElementById('ev-overlay').classList.add('open');
  setTimeout(() => document.getElementById('f-title').focus(), 80);
}

function openEditModal(ev) {
  editId = ev.id;
  document.getElementById('ev-title').textContent = '予定を編集';
  document.getElementById('br-new').style.display  = 'none';
  document.getElementById('br-edit').style.display = '';
  document.getElementById('f-title').value = ev.title || '';
  document.getElementById('f-desc').value  = ev.description || '';
  document.getElementById('f-pf').value    = ev.platform || '';
  const ad = ev.all_day || false;
  document.getElementById('f-allday').checked = ad;
  onAlldayChange();
  const sd = (ev.start_datetime||'').slice(0,10);
  const st = (ev.start_datetime||'').slice(11,16) || '20:00';
  const ed = (ev.end_datetime  ||'').slice(0,10) || sd;
  const et = (ev.end_datetime  ||'').slice(11,16) || '22:00';
  document.getElementById('f-sd').value    = sd;
  document.getElementById('f-st').value    = st;
  document.getElementById('f-ed').value    = ed;
  document.getElementById('f-et').value    = et;
  document.getElementById('f-sd-ad').value = sd;
  document.getElementById('f-ed-ad').value = ed;
  setType(ev.event_type || 'general');
  document.getElementById('gcal-info').innerHTML = ev.google_calendar_event_id
    ? '<div class="gcal-badge">📅 Google カレンダーと同期済み</div>' : '';
  document.getElementById('ev-overlay').classList.add('open');
}

function closeEvModal() {
  document.getElementById('ev-overlay').classList.remove('open');
  editId = null;
}
function onEvBg(e) { if (e.target===document.getElementById('ev-overlay')) closeEvModal(); }

async function saveEvent() {
  const title = document.getElementById('f-title').value.trim();
  if (!title) { toast('タイトルを入力してください'); return; }
  const ad = document.getElementById('f-allday').checked;
  let start, end;
  if (ad) {
    start = document.getElementById('f-sd-ad').value;
    end   = document.getElementById('f-ed-ad').value || start;
    if (!start) { toast('日付を入力してください'); return; }
  } else {
    const sd = document.getElementById('f-sd').value;
    const st = document.getElementById('f-st').value || '00:00';
    const ed = document.getElementById('f-ed').value || sd;
    const et = document.getElementById('f-et').value || st;
    if (!sd) { toast('日付を入力してください'); return; }
    start = `${sd}T${st}:00+09:00`;
    end   = `${ed}T${et}:00+09:00`;
  }
  const body = {
    title,
    description: document.getElementById('f-desc').value.trim(),
    event_type:  selType,
    platform:    document.getElementById('f-pf').value,
    start_datetime: start, end_datetime: end, all_day: ad,
  };
  try {
    const url = editId ? `/api/events/${editId}` : '/api/events';
    const r = await fetch(url, {
      method: editId ? 'PUT' : 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (d.ok) {
      closeEvModal(); await loadEvents();
      const synced = d.event && d.event.google_calendar_event_id;
      toast((editId ? '更新しました' : '保存しました') + (synced ? ' ✓ Google同期' : ''));
    } else { toast('保存に失敗しました'); }
  } catch(e) { toast('通信エラーが発生しました'); }
}

async function deleteEvent() {
  if (!editId) return;
  if (!confirm('この予定を削除しますか？\n（Googleカレンダーからも削除されます）')) return;
  try {
    const r = await fetch(`/api/events/${editId}`, { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) { closeEvModal(); await loadEvents(); toast('削除しました'); }
    else { toast('削除に失敗しました'); }
  } catch(e) { toast('通信エラーが発生しました'); }
}

/* ── Toast ──────────────────────────────────────────────────────── */
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
