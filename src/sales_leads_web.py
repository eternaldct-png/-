"""/leads（X営業リスト）の画面とcron用エンドポイント

ロジックは sales_leads.py。web_app.py で Blueprint として登録している。
"""
import hmac
import os
import secrets
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, redirect, request, session
from markupsafe import escape

import sales_leads as sl

bp = Blueprint("sales_leads", __name__)

# 担当者への通知（web_app.py が LINE 通知の関数を差し込む）
NOTIFY = None
_store = None


def get_store():
    global _store
    if _store is None:
        _store = sl.LeadStore()
    return _store


def _notify(text):
    if NOTIFY:
        try:
            NOTIFY(text)
        except Exception as e:
            print(f"[sales_leads] notify failed: {e}")


def _html(body, status=200):
    return body, status, {"Content-Type": "text/html; charset=utf-8"}


def _csrf_token():
    token = session.get("leads_admin_csrf")
    if not token:
        token = secrets.token_urlsafe(24)
        session["leads_admin_csrf"] = token
    return token


def _check_admin():
    """ログイン済み・CSRFトークン一致なら None、ダメならエラーレスポンスを返す"""
    if not session.get("leads_admin_ok"):
        return redirect("/leads/admin")
    if request.method == "POST":
        sent = str(request.form.get("csrf_token", ""))
        if not hmac.compare_digest(str(session.get("leads_admin_csrf", "")), sent):
            return _html("<p>画面が古くなっています。戻って再読み込みしてください。</p>", 400)
    return None


def _back(lead_id="", msg="", tab=""):
    params = []
    if tab:
        params.append(f"tab={quote(tab)}")
    if msg:
        params.append(f"msg={quote(msg)}")
    query = ("?" + "&".join(params)) if params else ""
    anchor = f"#lead-{lead_id}" if lead_id else ""
    return redirect(f"/leads/admin{query}{anchor}")


def _tab_of(lead):
    return request.form.get("tab") or lead.get("status", "")


# ── 画面 ─────────────────────────────────────────────────────


@bp.route("/leads/admin", methods=["GET", "POST"])
def leads_admin():
    web_password = os.environ.get("WEB_PASSWORD", "")
    if request.method == "POST" and "password" in request.form:
        if web_password and hmac.compare_digest(request.form.get("password", ""), web_password):
            session["leads_admin_ok"] = True
            return redirect("/leads/admin")
        return _html(LOGIN_HTML.replace("__ERROR__", '<p class="error">パスワードが違います</p>'), 401)
    if not session.get("leads_admin_ok"):
        return _html(LOGIN_HTML.replace("__ERROR__", ""))

    config = sl.load_config()
    store = get_store()
    leads = store.leads()
    csrf = _csrf_token()
    tab = request.args.get("tab", "")
    if tab not in sl.STATUSES:
        tab = "new"

    counts = {key: 0 for key in sl.STATUSES}
    for lead in leads:
        counts[lead.get("status", "new")] = counts.get(lead.get("status", "new"), 0) + 1
    tabs = "".join(
        f'<a class="tab{" active" if key == tab else ""}" href="/leads/admin?tab={key}">'
        f'{escape(label)}<span>{counts.get(key, 0)}</span></a>'
        for key, label in sl.STATUSES.items()
    )
    shown = [l for l in leads if l.get("status", "new") == tab]
    cards = "".join(_lead_card(l, csrf, tab) for l in shown) or '<p class="empty">この状態のリストはありません。</p>'

    today = sl.sent_today(leads)
    limit = int(config.get("daily_send_limit", 20))
    sent_class = "warn" if today >= limit else ""
    query_options = "".join(
        f'<option value="{escape(q)}">{escape(q)}</option>' for q in config.get("collect", {}).get("queries", [])
    )

    def status_dot(ok, on, off):
        return f'<li class="{"ok" if ok else "ng"}">{"✅" if ok else "⚠️"} {on if ok else off}</li>'

    setup = "".join([
        status_dot(sl.xai_configured(), "Grok（XAI_API_KEY）設定済み", "XAI_API_KEY 未設定（Grok検索が使えません）"),
        status_dot(bool(os.environ.get("ANTHROPIC_API_KEY")), "Claude（ANTHROPIC_API_KEY）設定済み", "ANTHROPIC_API_KEY 未設定（下書き・自動返信が使えません）"),
        status_dot(sl.x_configured(), "営業用Xアカウント連携済み", "営業用Xアカウントのキー未設定（ワンクリック送信は「コピー＋プロフィールを開く」になり、自動返信は動きません）"),
        status_dot(bool(os.environ.get("LEADS_TASK_SECRET")), "自動返信の定期実行トークン設定済み", "LEADS_TASK_SECRET 未設定（自動返信が動きません）"),
        status_dot(store.uses_db(), "データベースに保存中", "ファイル保存のみ（再デプロイで消えます。DATABASE_URL を設定してください）"),
    ])
    agent = config.get("agent", {})
    agent_text = (
        f'自動返信: <b>{"ON" if agent.get("enabled", True) else "OFF"}</b>'
        f'（{"自動送信" if agent.get("mode", "auto") == "auto" else "承認してから送信"}・'
        f'{escape(str((agent.get("active_hours") or [0, 24])[0]))}〜{escape(str((agent.get("active_hours") or [0, 24])[1]))}時・'
        f'1人{escape(str(agent.get("max_auto_replies", 4)))}回まで）'
    )

    msg = request.args.get("msg", "")
    html = (
        ADMIN_HTML.replace("__TITLE__", str(escape(config.get("title", "X営業リスト"))))
        .replace("__MSG__", f'<div class="flash">{escape(msg)}</div>' if msg else "")
        .replace("__TABS__", tabs)
        .replace("__CARDS__", cards)
        .replace("__CSRF__", str(escape(csrf)))
        .replace("__QUERY_OPTIONS__", query_options)
        .replace("__SENT_TODAY__", f'<span class="{sent_class}">今日の送信 {today} / 目安 {limit}件</span>')
        .replace("__SETUP__", setup)
        .replace("__AGENT__", agent_text)
    )
    return _html(html)


def _lead_card(lead, csrf, tab):
    lid = escape(lead.get("id", ""))
    username = lead.get("username", "")
    hidden = (
        f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
        f'<input type="hidden" name="tab" value="{escape(tab)}">'
    )

    def form(action, label, cls="", confirm="", extra="", target=""):
        onsubmit = f' onsubmit="return confirm(\'{confirm}\')"' if confirm else ""
        tgt = f' target="{target}"' if target else ""
        return (
            f'<form method="POST" action="/leads/admin/{lid}/{action}"{onsubmit}{tgt}>{hidden}{extra}'
            f'<button class="{cls}" type="submit">{label}</button></form>'
        )

    def status_btn(status, label, cls="ghost"):
        return form("status", label, cls, extra=f'<input type="hidden" name="status" value="{status}">')

    post_link = (
        f'<a href="{escape(lead["post_url"])}" target="_blank" rel="noopener">投稿を見る ↗</a>'
        if lead.get("post_url") else ""
    )
    profile = (
        f'<a href="{escape(sl.profile_url(lead))}" target="_blank" rel="noopener">@{escape(username)}</a>'
        if username else f'ID {escape(lead.get("x_user_id", ""))}'
    )
    messages = "".join(
        f'<div class="msg {escape(m.get("role", ""))}"><span class="who">'
        f'{ {"them": "相手", "me": "自分", "agent": "AI", "human": "担当者"}.get(m.get("role"), "")}'
        f' · {escape(m.get("at", ""))}</span>{escape(m.get("text", ""))}</div>'
        for m in lead.get("messages", [])[-12:]
    )
    status = lead.get("status", "new")
    parts = [
        f'<article class="lead" id="lead-{lid}">',
        '<div class="lead-head">',
        f'<div><div class="who-line">{profile} <span class="name">{escape(lead.get("display_name", ""))}</span></div>',
        f'<div class="meta">{escape(lead.get("industry", ""))} · {escape(lead.get("source", ""))} · {escape(lead.get("created_at", ""))}</div></div>',
        f'<span class="badge s-{escape(status)}">{escape(sl.STATUSES.get(status, status))}</span>',
        "</div>",
    ]
    if lead.get("post_text"):
        parts.append(f'<blockquote>{escape(lead["post_text"])}<div class="post-link">{post_link}</div></blockquote>')
    if lead.get("reason"):
        parts.append(f'<p class="reason">💡 {escape(lead["reason"])}</p>')
    if lead.get("last_error"):
        parts.append(f'<p class="error-line">⚠️ {escape(lead["last_error"])}</p>')

    if status in ("new", "ready"):
        parts.append(
            f'<form class="draft-form" method="POST" action="/leads/admin/{lid}/open" target="_blank" '
            f'onsubmit="setTimeout(function(){{location.reload()}},1500)">{hidden}'
            f'<textarea name="draft" rows="5" placeholder="DMの文面（「AIで下書き」で作れます）">{escape(lead.get("draft", ""))}</textarea>'
            '<div class="row">'
            '<button class="primary" type="submit">📩 Xで送る（文面入りで開く）</button>'
            f'<button class="ghost" type="submit" formaction="/leads/admin/{lid}/save" formtarget="_self">保存</button>'
            "</div>"
            '<p class="hint">Xが開いたら内容を確認して送信を押してください。押すと「送信済み」に移動します。</p>'
            "</form>"
        )
        parts.append('<div class="row">')
        parts.append(form("draft", "✍️ AIで下書き", "ghost"))
        parts.append(status_btn("skipped", "見送り"))
        parts.append("</div>")
    if messages:
        parts.append(f'<div class="thread">{messages}</div>')
    if lead.get("pending_reply"):
        parts.append(
            f'<form method="POST" action="/leads/admin/{lid}/reply">{hidden}'
            '<p class="label">✍️ AIの返信案（承認待ち）</p>'
            f'<textarea name="text" rows="4">{escape(lead["pending_reply"])}</textarea>'
            '<input type="hidden" name="approve" value="1">'
            '<div class="row"><button class="primary" type="submit">この内容で送る</button></div></form>'
        )
    if status not in ("new", "ready", "skipped"):
        parts.append(
            f'<form method="POST" action="/leads/admin/{lid}/reply">{hidden}'
            '<textarea name="text" rows="2" placeholder="担当者として返信する（APIで送信）"></textarea>'
            '<div class="row"><button class="ghost" type="submit">返信を送る</button></div></form>'
        )
        parts.append('<div class="row">')
        paused = lead.get("agent_paused")
        parts.append(form("agent", "▶️ 自動返信を再開" if paused else "⏸ 自動返信を止める", "ghost"))
        if status != "meeting":
            parts.append(status_btn("meeting", "📅 面談予約"))
        if status != "won":
            parts.append(status_btn("won", "🎉 成約"))
        if status == "sent":
            parts.append(status_btn("ready", "未送信に戻す"))
        if status == "handoff":
            parts.append(status_btn("replied", "自動返信に戻す"))
        parts.append("</div>")
    if status in ("skipped", "stopped", "won"):
        parts.append(f'<div class="row">{status_btn("new", "候補に戻す")}</div>')

    parts.append(
        f'<details><summary>メモ・削除</summary>'
        f'<form method="POST" action="/leads/admin/{lid}/save">{hidden}'
        f'<textarea name="memo" rows="2" placeholder="メモ">{escape(lead.get("memo", ""))}</textarea>'
        '<div class="row"><button class="ghost" type="submit">メモを保存</button></div></form>'
        f'{form("delete", "削除", "danger", confirm="このリストを削除します。よろしいですか？")}'
        "</details>"
    )
    parts.append("</article>")
    return "".join(parts)


# ── 操作 ─────────────────────────────────────────────────────


@bp.route("/leads/admin/collect", methods=["POST"])
def leads_collect():
    denied = _check_admin()
    if denied:
        return denied
    query = (request.form.get("query_text") or request.form.get("query") or "").strip()[:100]
    if not query:
        return _back(msg="検索キーワードを入れてください")
    try:
        candidates = sl.collect_with_grok(query, sl.load_config())
    except Exception as e:
        return _back(msg=f"Grok検索に失敗しました: {e}"[:300])
    added, skipped = sl.add_candidates(get_store(), candidates, "grok")
    return _back(msg=f"「{query}」で {added}件 追加しました（重複・不正 {skipped}件はスキップ）", tab="new")


@bp.route("/leads/admin/add", methods=["POST"])
def leads_add():
    denied = _check_admin()
    if denied:
        return denied
    target = request.form.get("username", "")
    candidate = {
        "username": target,
        "post_url": target if "/status/" in target else request.form.get("post_url", ""),
        "post_text": request.form.get("post_text", ""),
        "memo": request.form.get("memo", ""),
    }
    added, _ = sl.add_candidates(get_store(), [candidate], "manual")
    return _back(msg="追加しました" if added else "追加できませんでした（ユーザー名が不正か、すでに登録済み）", tab="new")


def _load_lead(lead_id):
    lead = get_store().get(lead_id)
    if not lead:
        return None, _back(msg="見つかりませんでした")
    return lead, None


@bp.route("/leads/admin/<lead_id>/draft", methods=["POST"])
def leads_draft(lead_id):
    denied = _check_admin()
    if denied:
        return denied
    lead, missing = _load_lead(lead_id)
    if missing:
        return missing
    try:
        lead["draft"] = sl.draft_dm(lead, sl.load_config())
        if lead.get("status") == "new":
            lead["status"] = "ready"
        get_store().save(lead)
        return _back(lead_id, "下書きを作りました。内容を確認してください", tab=lead["status"])
    except Exception as e:
        return _back(lead_id, f"下書きの作成に失敗しました: {e}"[:300], tab=_tab_of(lead))


@bp.route("/leads/admin/<lead_id>/save", methods=["POST"])
def leads_save(lead_id):
    denied = _check_admin()
    if denied:
        return denied
    lead, missing = _load_lead(lead_id)
    if missing:
        return missing
    if "draft" in request.form:
        lead["draft"] = request.form.get("draft", "").strip()[:1000]
        if lead["draft"] and lead.get("status") == "new":
            lead["status"] = "ready"
    if "memo" in request.form:
        lead["memo"] = request.form.get("memo", "").strip()[:500]
    get_store().save(lead)
    return _back(lead_id, "保存しました", tab=_tab_of(lead))


@bp.route("/leads/admin/<lead_id>/open", methods=["POST"])
def leads_open(lead_id):
    """ワンクリック送信: 文面を保存し、文面入りのDM画面へ飛ばす（送信ボタンは人が押す）"""
    denied = _check_admin()
    if denied:
        return denied
    lead, missing = _load_lead(lead_id)
    if missing:
        return missing
    text = request.form.get("draft", lead.get("draft", "")).strip()[:1000]
    if not text:
        return _html(SIMPLE_HTML.replace("__BODY__", "<p>文面が空です。下書きを作ってから送ってください。</p>"), 400)
    lead["draft"] = text
    if not lead.get("x_user_id") and sl.x_configured():
        try:
            lead["x_user_id"] = sl.resolve_user_id(sl.x_client(), lead["username"])
        except Exception as e:
            lead["last_error"] = f"ユーザーIDの取得に失敗: {e}"[:300]
    lead["status"] = "sent"
    lead["sent_at"] = sl._stamp()
    get_store().save(lead)

    url = sl.compose_url(lead, text)
    if url:
        return redirect(url)
    # IDが分からないときは、文面をコピーしてプロフィールを開いてもらう
    body = (
        "<h1>📋 文面をコピーしてDMを送ってください</h1>"
        f'<textarea id="t" rows="8">{escape(text)}</textarea>'
        '<button onclick="navigator.clipboard.writeText(document.getElementById(\'t\').value);'
        f'location.href=\'{escape(sl.profile_url(lead))}\'">コピーして @{escape(lead["username"])} を開く</button>'
        '<p class="hint">営業用Xアカウントの API キーを設定すると、文面入りのDM画面が直接開くようになります。</p>'
    )
    return _html(SIMPLE_HTML.replace("__BODY__", body))


@bp.route("/leads/admin/<lead_id>/status", methods=["POST"])
def leads_status(lead_id):
    denied = _check_admin()
    if denied:
        return denied
    lead, missing = _load_lead(lead_id)
    if missing:
        return missing
    status = request.form.get("status", "")
    if status not in sl.STATUSES:
        return _back(lead_id, "不正な状態です")
    lead["status"] = status
    if status in ("new", "ready"):
        lead["sent_at"] = ""
    get_store().save(lead)
    return _back(lead_id, f"「{sl.STATUSES[status]}」にしました", tab=_tab_of(lead))


@bp.route("/leads/admin/<lead_id>/agent", methods=["POST"])
def leads_agent_toggle(lead_id):
    denied = _check_admin()
    if denied:
        return denied
    lead, missing = _load_lead(lead_id)
    if missing:
        return missing
    lead["agent_paused"] = not lead.get("agent_paused")
    get_store().save(lead)
    return _back(lead_id, "自動返信を止めました" if lead["agent_paused"] else "自動返信を再開しました", tab=_tab_of(lead))


@bp.route("/leads/admin/<lead_id>/reply", methods=["POST"])
def leads_reply(lead_id):
    """担当者の返信、またはAIの返信案の承認送信（相手とのやり取り中の返信なのでAPIで送る）"""
    denied = _check_admin()
    if denied:
        return denied
    lead, missing = _load_lead(lead_id)
    if missing:
        return missing
    text = request.form.get("text", "").strip()[:1000]
    if not text:
        return _back(lead_id, "返信が空です", tab=_tab_of(lead))
    if lead.get("status") == "stopped":
        return _back(lead_id, "配信停止の相手には送れません", tab=_tab_of(lead))
    approve = request.form.get("approve") == "1"
    if not lead.get("x_user_id") or not sl.x_configured():
        return _back(lead_id, "営業用Xアカウントが未連携のため送れません", tab=_tab_of(lead))
    try:
        event_id = sl.send_dm(sl.x_client(), lead["x_user_id"], text)
    except Exception as e:
        lead["last_error"] = f"送信に失敗: {e}"[:300]
        get_store().save(lead)
        return _back(lead_id, "送信に失敗しました", tab=_tab_of(lead))
    sl._record(lead, "agent" if approve else "human", text, event_id)
    if approve:
        lead["auto_reply_count"] = int(lead.get("auto_reply_count", 0)) + 1
    lead["pending_reply"] = ""
    lead["needs_reply"] = False
    lead["last_error"] = ""
    get_store().save(lead)
    return _back(lead_id, "送信しました", tab=_tab_of(lead))


@bp.route("/leads/admin/<lead_id>/delete", methods=["POST"])
def leads_delete(lead_id):
    denied = _check_admin()
    if denied:
        return denied
    get_store().delete(lead_id)
    return _back(msg="削除しました", tab=request.form.get("tab", ""))


@bp.route("/leads/admin/export.csv")
def leads_export():
    if not session.get("leads_admin_ok"):
        return redirect("/leads/admin")
    csv_text = sl.to_csv(get_store().leads())
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_leads.csv"},
    )


@bp.route("/leads/admin/logout")
def leads_logout():
    session.pop("leads_admin_ok", None)
    return redirect("/leads/admin")


@bp.route("/tasks/leads-agent", methods=["GET", "POST"])
def leads_agent_task():
    """cron（cron-job.org 等）から10〜15分おきに叩く。?token=LEADS_TASK_SECRET"""
    secret = os.environ.get("LEADS_TASK_SECRET", "")
    token = request.args.get("token", "")
    if not secret or not hmac.compare_digest(token, secret):
        return jsonify({"ok": False, "error": "unauthorized"}), 403
    config = sl.load_config()
    if not config.get("agent", {}).get("enabled", True):
        return jsonify({"ok": True, "skipped": "agent disabled"})
    if not sl.x_configured():
        return jsonify({"ok": False, "error": "営業用Xアカウントのキーが未設定"}), 503
    try:
        summary = sl.run_agent(get_store(), config, notify=_notify)
    except Exception as e:
        print(f"[sales_leads] agent failed: {e}")
        return jsonify({"ok": False, "error": str(e)[:300]}), 500
    return jsonify({"ok": True, **summary})


# ── HTML ─────────────────────────────────────────────────────

_BASE_CSS = r"""
:root {
  --bg: #f7f7fb; --surface: #ffffff; --surface2: #f7f5fc;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent: #7c3aed; --text: #1f2333; --muted: #6b7280; --border: #e7e3f0;
  --danger: #dc2626; --ok: #059669; --warn: #d97706;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding: 16px; font-size: 14px; line-height: 1.6;
}
textarea, input, select {
  width: 100%; padding: 10px 12px; background: var(--bg); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--text); font-size: 14px; font-family: inherit; outline: none;
}
textarea:focus, input:focus, select:focus { border-color: var(--accent); }
button {
  padding: 10px 14px; border: none; border-radius: 10px; font-size: 14px; font-weight: 700;
  cursor: pointer; background: var(--grad); color: white;
}
button.ghost { background: var(--surface2); color: var(--accent); border: 1px solid var(--border); }
button.danger { background: #fff1f2; color: var(--danger); border: 1px solid #fecdd3; }
.hint { color: var(--muted); font-size: 12px; margin-top: 6px; }
.error { color: #ef4444; font-size: 13px; text-align: center; margin-top: 14px; }
"""

LOGIN_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>X営業リスト ログイン</title><style>"""
    + _BASE_CSS
    + r"""
body { display: flex; align-items: center; justify-content: center; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; box-shadow: var(--shadow); padding: 32px 24px; max-width: 340px; width: 100%; }
h1 { font-size: 17px; margin-bottom: 18px; text-align: center; }
input { margin-bottom: 12px; } button { width: 100%; }
</style></head><body>
<div class="card"><h1>🔒 X営業リスト</h1>
<form method="POST"><input type="password" name="password" placeholder="パスワード" autofocus required>
<button type="submit">ログイン</button></form>__ERROR__</div>
</body></html>"""
)

SIMPLE_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DMを送る</title><style>"""
    + _BASE_CSS
    + r"""
.box { max-width: 520px; margin: 24px auto; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; }
h1 { font-size: 16px; margin-bottom: 12px; } button { width: 100%; margin-top: 10px; }
</style></head><body><div class="box">__BODY__</div></body></html>"""
)

ADMIN_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title><style>"""
    + _BASE_CSS
    + r"""
.page { max-width: 760px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
h1 { font-size: 20px; }
.header a { font-size: 13px; color: var(--accent); text-decoration: none; font-weight: 700; margin-left: 10px; }
.flash { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 10px 12px; border-radius: 10px; margin-bottom: 12px; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin-bottom: 12px; box-shadow: var(--shadow); }
.panel h2 { font-size: 14px; margin-bottom: 8px; }
.panel form { display: grid; gap: 8px; }
.setup { list-style: none; font-size: 12px; display: grid; gap: 2px; }
.setup .ng { color: var(--warn); }
.stats { display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px; color: var(--muted); margin-bottom: 10px; }
.stats .warn { color: var(--danger); font-weight: 700; }
.tabs { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 10px; }
.tab { white-space: nowrap; padding: 6px 12px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); color: var(--text); text-decoration: none; font-size: 13px; }
.tab span { margin-left: 6px; color: var(--muted); font-size: 12px; }
.tab.active { background: var(--grad); color: white; border-color: transparent; }
.tab.active span { color: white; }
.lead { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin-bottom: 10px; display: grid; gap: 8px; }
.lead-head { display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; }
.who-line a { font-weight: 800; color: var(--accent); text-decoration: none; }
.name { color: var(--muted); font-size: 13px; }
.meta { color: var(--muted); font-size: 12px; }
.badge { font-size: 12px; padding: 2px 10px; border-radius: 999px; background: var(--surface2); white-space: nowrap; }
.s-replied, .s-handoff { background: #fef3c7; } .s-meeting, .s-won { background: #d1fae5; } .s-stopped { background: #fee2e2; }
blockquote { background: var(--surface2); border-left: 3px solid var(--accent); padding: 8px 10px; border-radius: 6px; white-space: pre-wrap; font-size: 13px; }
.post-link { margin-top: 4px; font-size: 12px; } .post-link a { color: var(--accent); }
.reason { font-size: 13px; color: var(--muted); }
.error-line { font-size: 12px; color: var(--danger); }
.row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.row form { display: inline; }
.draft-form button.primary { flex: 1; }
.thread { display: grid; gap: 6px; background: var(--bg); padding: 8px; border-radius: 10px; }
.msg { padding: 8px 10px; border-radius: 10px; white-space: pre-wrap; font-size: 13px; max-width: 92%; }
.msg .who { display: block; font-size: 11px; color: var(--muted); }
.msg.them { background: var(--surface); border: 1px solid var(--border); }
.msg.me, .msg.agent, .msg.human { background: #ede9fe; justify-self: end; }
.label { font-size: 12px; font-weight: 700; color: var(--warn); }
details summary { cursor: pointer; font-size: 12px; color: var(--muted); }
details form { margin-top: 6px; }
.empty { color: var(--muted); text-align: center; padding: 24px; }
</style></head><body><div class="page">
<div class="header"><h1>📮 __TITLE__</h1>
<div><a href="/leads/admin/export.csv">⬇ CSV（スプシ用）</a><a href="/leads/admin/logout">ログアウト</a></div></div>
__MSG__
<div class="stats">__SENT_TODAY__<span>__AGENT__</span></div>

<div class="panel"><h2>🔎 Grokで見込み客を探す</h2>
<form method="POST" action="/leads/admin/collect" onsubmit="this.querySelector('button').disabled=true;this.querySelector('button').textContent='Grokが検索中…（30秒〜1分）'">
<input type="hidden" name="csrf_token" value="__CSRF__">
<select name="query">__QUERY_OPTIONS__</select>
<input name="query_text" placeholder="自由入力（入れるとこちらを優先）">
<button type="submit">探す</button></form></div>

<details class="panel"><summary>＋ 手動で追加（ユーザー名 または 投稿URL）</summary>
<form method="POST" action="/leads/admin/add" style="margin-top:8px">
<input type="hidden" name="csrf_token" value="__CSRF__">
<input name="username" placeholder="@username または https://x.com/…/status/…" required>
<textarea name="post_text" rows="2" placeholder="気になった投稿の内容（下書きの材料になります）"></textarea>
<input name="memo" placeholder="メモ（任意）">
<button type="submit">追加</button></form></details>

<div class="tabs">__TABS__</div>
__CARDS__

<details class="panel"><summary>設定の状態</summary><ul class="setup" style="margin-top:8px">__SETUP__</ul>
<p class="hint">文面・自動返信のルールは persona/sales_leads_config.yaml で変更できます。</p></details>
</div></body></html>"""
)
