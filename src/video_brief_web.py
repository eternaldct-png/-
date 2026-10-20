"""/video-brief（AI動画の制作指示書メーカー）の画面

ロジックは video_brief.py。web_app.py で Blueprint として登録している。
"""
import hmac
import json
import os
import secrets

from flask import Blueprint, jsonify, redirect, request, session
from markupsafe import escape

import video_brief as vb
from sales_leads_web import _BASE_CSS

bp = Blueprint("video_brief", __name__)
_store = None


def get_store():
    global _store
    if _store is None:
        _store = vb.DraftStore()
    return _store


def _html(body, status=200):
    return body, status, {"Content-Type": "text/html; charset=utf-8"}


def _csrf_token():
    token = session.get("video_brief_csrf")
    if not token:
        token = secrets.token_urlsafe(24)
        session["video_brief_csrf"] = token
    return token


def _form_page(config, error="", values=None):
    values = values or {}
    genres = config.get("genres", [])
    selected = values.get("genre") or (genres[0]["id"] if genres else "")
    genre_options = "".join(
        f'<option value="{escape(g["id"])}"{" selected" if g["id"] == selected else ""} '
        f'data-seconds="{g.get("default_seconds", 15)}" data-aspect="{escape(g.get("default_aspect", "16:9"))}">'
        f'{escape(g["name"])}</option>'
        for g in genres
    )
    aspect = values.get("aspect", "")
    aspect_options = "".join(
        f'<option{" selected" if a == aspect else ""}>{escape(a)}</option>' for a in config.get("aspects", [])
    )
    tips = "".join(
        f'<div class="tips" data-genre="{escape(g["id"])}"><b>このジャンルで先に用意するもの</b><ul>'
        + "".join(f"<li>{escape(r)}</li>" for r in g.get("references", []))
        + "</ul></div>"
        for g in genres
    )
    foundations = "".join(f"<li>{escape(f)}</li>" for f in config.get("foundations", []))
    d = config.get("draft", {})
    if d.get("enabled"):
        key_ok = bool(vb.draft_api_key(config))
        spent = vb.spent_this_month(get_store().all()) if key_ok else 0
        draft_status = (
            f'<p class="hint">🎬 下書きの自動生成（{escape(d.get("resolution", "480p"))}）: '
            + (f'今月 約{spent:,}円 / 上限{int(d.get("monthly_budget_jpy", 0)):,}円' if key_ok
               else f'⚠️ {escape(d.get("api_key_env", "FAL_KEY"))} 未設定（指示書だけ作れます）')
            + "</p>"
        )
    else:
        draft_status = ""
    v = lambda k: escape(values.get(k, ""))
    body = (
        FORM_HTML.replace("__TITLE__", str(escape(config.get("title", ""))))
        .replace("__CSRF__", _csrf_token())
        .replace("__GENRES__", genre_options)
        .replace("__ASPECTS__", aspect_options)
        .replace("__TIPS__", tips)
        .replace("__FOUNDATIONS__", foundations)
        .replace("__DRAFT_STATUS__", draft_status)
        .replace("__ERROR__", f'<p class="error">{escape(error)}</p>' if error else "")
        .replace("__SECONDS__", v("seconds"))
    )
    for key in ("subject", "goal", "assets", "tone", "memo"):
        body = body.replace(f"__{key.upper()}__", str(v(key)))
    return body


@bp.route("/video-brief", methods=["GET", "POST"])
def video_brief_page():
    web_password = os.environ.get("WEB_PASSWORD", "")
    if request.method == "POST" and "password" in request.form:
        if web_password and hmac.compare_digest(request.form.get("password", ""), web_password):
            session["video_brief_ok"] = True
            return redirect("/video-brief")
        return _html(LOGIN_HTML.replace("__ERROR__", '<p class="error">パスワードが違います</p>'), 401)
    if not session.get("video_brief_ok"):
        return _html(LOGIN_HTML.replace("__ERROR__", ""))
    return _html(_form_page(vb.load_config()))


@bp.route("/video-brief/generate", methods=["POST"])
def video_brief_generate():
    if not session.get("video_brief_ok"):
        return redirect("/video-brief")
    sent = str(request.form.get("csrf_token", ""))
    if not hmac.compare_digest(str(session.get("video_brief_csrf", "")), sent):
        return _html("<p>画面が古くなっています。戻って再読み込みしてください。</p>", 400)

    config = vb.load_config()
    form = {k: str(request.form.get(k, "")).strip()[:2000] for k in
            ("genre", "subject", "goal", "aspect", "assets", "tone", "memo", "seconds")}
    genre = vb.get_genre(config, form["genre"])
    try:
        form["seconds"] = int(form["seconds"])
    except ValueError:
        form["seconds"] = 0
    if not genre:
        return _html(_form_page(config, "ジャンルを選んでください", form), 400)
    if not form["subject"]:
        return _html(_form_page(config, "商品・案件名を入れてください", form), 400)
    if not 3 <= form["seconds"] <= 180:
        return _html(_form_page(config, "尺は3〜180秒で入れてください", form), 400)
    if form["aspect"] not in config.get("aspects", []):
        form["aspect"] = genre.get("default_aspect", "16:9")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _html(_form_page(config, "ANTHROPIC_API_KEY が未設定です（Renderの環境変数を確認）", form), 500)

    try:
        brief = vb.generate_brief(form, config)
    except Exception as e:
        print(f"[video_brief] generate failed: {e}")
        return _html(_form_page(config, f"指示書を作れませんでした: {e}", form), 502)

    markdown, issues = vb.to_markdown(brief, form, genre, config)
    ng = sum(1 for i in issues if i["level"] == "ng")
    status = (f'<p class="badge ng">❌ 直したほうがいい点が{ng}件あります（下の「自動チェック」）</p>' if ng
              else '<p class="badge ok">✅ 尺・つなぎ・セリフの文字数はチェック済み</p>')
    filename = f"brief_{genre['id']}.md"
    body = (
        RESULT_HTML.replace("__STATUS__", status)
        .replace("__DRAFTS__", _draft_section(brief, form, config))
        .replace("__MD__", str(escape(markdown)))
        .replace("__FILENAME__", str(escape(filename)))
        .replace("__CSRF__", _csrf_token())
    )
    return _html(body)


def _draft_section(brief, form, config):
    d = config.get("draft", {})
    if not d.get("enabled") or not vb.draft_api_key(config):
        return ""
    rows = []
    for i, cut in enumerate(brief.get("cuts", []), 1):
        sec = vb.draft_seconds(float(cut.get("end", 0)) - float(cut.get("start", 0)), config)
        data = json.dumps({"prompt": cut.get("video_prompt", ""), "seconds": sec, "aspect": form.get("aspect", "")},
                          ensure_ascii=False)
        rows.append(
            f'<div class="cut" data-cut="{escape(data)}"><b>カット{i}</b> {escape(cut.get("scene", ""))}'
            f'<input class="img" placeholder="最初の画像のURL（任意・https://）">'
            f'<button type="button" class="ghost" onclick="draft(this)">🎬 下書きを作る（{sec}秒・約{vb.draft_cost_jpy(sec, config):,}円）</button>'
            f'<div class="out"></div></div>'
        )
    return (f'<h2>🎬 下書き動画（{escape(d.get("resolution", "480p"))}）</h2>'
            '<p class="hint">OKが出たカットだけ、本番（1080p）を Higgsfield 等で手で作ってください。'
            '画像URLを入れると、その画像から動かします（キャラの見た目を固定したいとき）。</p>' + "".join(rows))


def _require_login_json():
    if not session.get("video_brief_ok"):
        return jsonify({"error": "ログインが切れました。再読み込みしてください"}), 401
    return None


@bp.route("/video-brief/draft", methods=["POST"])
def video_brief_draft():
    denied = _require_login_json()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    if not hmac.compare_digest(str(session.get("video_brief_csrf", "")), str(body.get("csrf_token", ""))):
        return jsonify({"error": "画面が古くなっています。再読み込みしてください"}), 400
    config = vb.load_config()
    aspect = str(body.get("aspect", ""))
    if aspect not in config.get("aspects", []):
        aspect = "16:9"
    image_url = str(body.get("image_url", "")).strip()
    if image_url and not vb._safe_https(image_url):
        return jsonify({"error": "画像URLは https:// で始まるURLにしてください"}), 400
    try:
        draft = vb.start_draft(body.get("prompt", ""), body.get("seconds", 5), aspect, config, get_store(), image_url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[video_brief] draft failed: {e}")
        return jsonify({"error": str(e)}), 502
    return jsonify({"id": draft["id"], "status": draft["status"], "cost_jpy": draft["cost_jpy"]})


@bp.route("/video-brief/draft/<draft_id>")
def video_brief_draft_status(draft_id):
    denied = _require_login_json()
    if denied:
        return denied
    store = get_store()
    draft = store.get(draft_id)
    if not draft:
        return jsonify({"error": "見つかりません"}), 404
    draft = vb.refresh_draft(draft, vb.load_config(), store)
    return jsonify({"status": draft["status"], "video_url": draft.get("video_url", ""), "error": draft.get("error", "")})


LOGIN_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>制作指示書メーカー ログイン</title><style>"""
    + _BASE_CSS
    + r"""
body { display: flex; align-items: center; justify-content: center; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; box-shadow: var(--shadow); padding: 32px 24px; max-width: 340px; width: 100%; }
h1 { font-size: 17px; margin-bottom: 18px; text-align: center; }
input { margin-bottom: 12px; } button { width: 100%; }
</style></head><body>
<div class="card"><h1>🎬 制作指示書メーカー</h1>
<form method="POST"><input type="password" name="password" placeholder="パスワード" autofocus required>
<button type="submit">ログイン</button></form>__ERROR__</div>
</body></html>"""
)

FORM_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title><style>"""
    + _BASE_CSS
    + r"""
.box { max-width: 640px; margin: 0 auto; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; box-shadow: var(--shadow); }
h1 { font-size: 18px; margin-bottom: 4px; }
label { display: block; font-weight: 700; margin: 14px 0 6px; font-size: 13px; }
.row { display: flex; gap: 10px; } .row > div { flex: 1; }
.tips { display: none; background: var(--surface2); border-radius: 10px; padding: 10px 12px; margin-top: 10px; font-size: 12px; }
.tips ul, details ul { padding-left: 18px; }
details { margin-top: 16px; font-size: 12px; color: var(--muted); }
button[type=submit] { width: 100%; margin-top: 18px; }
.error { text-align: left; }
</style></head><body><div class="box">
<h1>🎬 __TITLE__</h1>
<p class="hint">ジャンルと案件を入れると、秒割り台本・カットごとの生成プロンプト・チェックリストを作ります（30秒〜1分ほどかかります）。</p>
__DRAFT_STATUS__
__ERROR__
<form method="POST" action="/video-brief/generate" onsubmit="this.querySelector('button').textContent='作成中…しばらくお待ちください';">
<input type="hidden" name="csrf_token" value="__CSRF__">
<label>ジャンル</label><select name="genre" id="genre">__GENRES__</select>
__TIPS__
<label>商品・案件名</label><input name="subject" value="__SUBJECT__" placeholder="例: 秋の和菓子カフェの新メニュー『焼き餅ぜんざい』" required>
<label>目的・届けたい相手</label><input name="goal" value="__GOAL__" placeholder="例: Instagramで20〜30代の女性に来店してもらう">
<div class="row"><div><label>尺（秒）</label><input name="seconds" id="seconds" type="number" min="3" max="180" value="__SECONDS__" required></div>
<div><label>縦横比</label><select name="aspect" id="aspect">__ASPECTS__</select></div></div>
<label>手元にある素材</label><input name="assets" value="__ASSETS__" placeholder="例: キャラの三面図、店内の写真、商品写真">
<label>トーン・雰囲気</label><input name="tone" value="__TONE__" placeholder="例: あたたかい、紅葉、やさしいピアノ">
<label>依頼メモ（任意）</label><textarea name="memo" rows="4" placeholder="クライアントの要望、入れたいセリフなど">__MEMO__</textarea>
<button type="submit">指示書を作る</button>
</form>
<details><summary>全ジャンル共通のルール</summary><ul>__FOUNDATIONS__</ul></details>
</div>
<script>
const g = document.getElementById('genre'), s = document.getElementById('seconds'), a = document.getElementById('aspect');
function sync(first) {
  const opt = g.selectedOptions[0];
  document.querySelectorAll('.tips').forEach(t => t.style.display = t.dataset.genre === g.value ? 'block' : 'none');
  if (!opt || (first && s.value)) return;
  s.value = opt.dataset.seconds; a.value = opt.dataset.aspect;
}
g.addEventListener('change', () => sync(false)); sync(true);
</script>
</body></html>"""
)

RESULT_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>制作指示書</title><style>"""
    + _BASE_CSS
    + r"""
.box { max-width: 860px; margin: 0 auto; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; box-shadow: var(--shadow); }
.bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.badge { font-weight: 700; margin-bottom: 10px; } .badge.ng { color: var(--danger); } .badge.ok { color: var(--ok); }
textarea { font-family: ui-monospace, Menlo, monospace; font-size: 12px; min-height: 70vh; }
h2 { font-size: 15px; margin: 20px 0 4px; }
.cut { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin-top: 10px; }
.cut input { margin: 8px 0; } .cut video { width: 100%; max-height: 360px; margin-top: 8px; border-radius: 8px; background: #000; }
.out { font-size: 12px; margin-top: 6px; }
a.ghost { padding: 10px 14px; border-radius: 10px; background: var(--surface2); color: var(--accent); border: 1px solid var(--border); text-decoration: none; font-weight: 700; }
</style></head><body><div class="box">
__STATUS__
<div class="bar">
<button type="button" onclick="dl()">⬇ Markdownで保存</button>
<button type="button" class="ghost" onclick="navigator.clipboard.writeText(document.getElementById('md').value);this.textContent='コピーしました'">📋 コピー</button>
<a class="ghost" href="/video-brief">← もう1本作る</a>
</div>
<textarea id="md">__MD__</textarea>
__DRAFTS__
<p class="hint">案件フォルダ（Notion / Google ドライブ）に保存しておくと、次の案件で使い回せます。</p>
</div>
<script>
const CSRF = '__CSRF__';
async function draft(btn) {
  const box = btn.closest('.cut'), out = box.querySelector('.out'), d = JSON.parse(box.dataset.cut);
  if (!confirm(btn.textContent.replace('🎬 ', '') + 'で作ります。よろしいですか？')) return;
  btn.disabled = true; out.textContent = '送信中…';
  try {
    const r = await fetch('/video-brief/draft', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...d, image_url: box.querySelector('.img').value, csrf_token: CSRF})});
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.status);
    poll(j.id, out, btn, 0);
  } catch (e) { out.textContent = '❌ ' + e.message; btn.disabled = false; }
}
async function poll(id, out, btn, n) {
  try {
    const r = await fetch('/video-brief/draft/' + id), j = await r.json();
    if (j.status === 'done') {
      out.innerHTML = '✅ できました（URLは一定期間で消えるので、必要なら保存してください） <a target="_blank" rel="noopener">⬇ 開く</a><video controls loop muted playsinline></video>';
      out.querySelector('a').href = j.video_url; out.querySelector('video').src = j.video_url; btn.disabled = false; return;
    }
    if (j.status === 'failed' || !r.ok) { out.textContent = '❌ ' + (j.error || '失敗しました'); btn.disabled = false; return; }
    out.textContent = (j.status === 'running' ? '生成中' : '順番待ち') + '…（' + (n * 5) + '秒経過）';
  } catch (e) { out.textContent = '確認中…（通信エラー、再試行します）'; }
  if (n < 240) setTimeout(() => poll(id, out, btn, n + 1), 5000);
  else { out.textContent = '時間がかかっています。あとでページを開き直して確認してください（id: ' + id + '）'; btn.disabled = false; }
}
function dl() {
  const blob = new Blob([document.getElementById('md').value], {type: 'text/markdown'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = '__FILENAME__'; a.click();
}
</script>
</body></html>"""
)
