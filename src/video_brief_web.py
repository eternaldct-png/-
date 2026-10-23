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


_char_store = None


def get_char_store():
    global _char_store
    if _char_store is None:
        _char_store = vb.CharacterStore()
    return _char_store


def _ref_lines(images):
    return "\n".join((r["url"] + " " + r.get("label", "")).strip() for r in images)


def _html(body, status=200):
    return body, status, {"Content-Type": "text/html; charset=utf-8"}


def _csrf_token():
    token = session.get("video_brief_csrf")
    if not token:
        token = secrets.token_urlsafe(24)
        session["video_brief_csrf"] = token
    return token


def _key_hint_html(config):
    hint, warnings = vb.draft_key_hint(config)
    html = f'<br>🔑 使っているキー: <code>{escape(hint)}</code>（fal.ai の Keys 画面と見比べてください）'
    for w in warnings:
        html += f'<br>⚠️ {escape(w)}'
    return html


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
            + (f'今月 約{spent:,}円 / 上限{int(d.get("monthly_budget_jpy", 0)):,}円' + _key_hint_html(config) if key_ok
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
        .replace("__TELOPS__", _telop_section(brief))
        .replace("__MD__", str(escape(markdown)))
        .replace("__FILENAME__", str(escape(filename)))
        .replace("__CSRF__", _csrf_token())
    )
    return _html(body)


def _telop_section(brief):
    """テロップ一覧（表）と、CSV・SRT のダウンロードボタン"""
    items = vb.telops(brief)
    if not items:
        return '<h2>📝 テロップ</h2><p class="hint">セリフも画面の文字もないため、テロップはありません。</p>'
    rows = "".join(
        f'<tr><td>{x["start"]:g}–{x["end"]:g}</td><td>{escape(x["cut"])}</td><td>{escape(x["kind"])}</td>'
        f'<td>{escape(x["text"])}</td></tr>' for x in items
    )
    data = json.dumps({"csv": vb.to_telop_csv(items), "srt": vb.to_srt(items)}, ensure_ascii=False).replace("<", "\\u003c")
    has_srt = any(x["kind"] == "セリフ" for x in items)
    return (
        '<h2>📝 テロップ一覧</h2>'
        '<p class="hint">CapCut などで編集するときの手元資料です。セリフは字幕1枚16文字までに分け、時間はそのカットの中で文字数に合わせて割り振っています。'
        '実際の声の長さに合わせて、編集画面で微調整してください。</p>'
        '<div class="bar"><button type="button" class="ghost" onclick="dlText(\'csv\', \'telops.csv\', \'text/csv\')">📝 テロップ一覧（CSV）</button>'
        + ('<button type="button" class="ghost" onclick="dlText(\'srt\', \'subtitles.srt\', \'application/x-subrip\')">💬 セリフ字幕（SRT）</button>'
           if has_srt else '')
        + '</div>'
        f'<table class="telops"><tr><th>秒</th><th>カット</th><th>種類</th><th>文言</th></tr>{rows}</table>'
        f'<script>const TELOPS = {data};</script>'
    )


def _draft_section(brief, form, config):
    d = config.get("draft", {})
    if not d.get("enabled") or not vb.draft_api_key(config):
        return ""
    sets = get_char_store().sets()
    set_options = "".join(f'<option value="{escape(c["id"])}">{escape(c["name"])}（{len(c.get("images", []))}枚）</option>'
                          for c in sets)
    set_json = json.dumps({c["id"]: _ref_lines(c.get("images", [])) for c in sets}, ensure_ascii=False).replace("<", "\\u003c")
    rows = []
    for i, cut in enumerate(brief.get("cuts", []), 1):
        no = cut.get("no", i)
        sec = vb.draft_seconds(float(cut.get("end", 0)) - float(cut.get("start", 0)), config)
        data = json.dumps({"prompt": cut.get("video_prompt", ""), "seconds": sec, "aspect": form.get("aspect", ""),
                           "cut": no, "subject": form.get("subject", "")}, ensure_ascii=False)
        rows.append(
            f'<div class="cut" data-cut="{escape(data)}"><b>カット{no}</b> {escape(cut.get("scene", ""))}'
            f'<input class="img" value="{escape(cut.get("image_url", ""))}" placeholder="最初の画像のURL（任意・https://）">'
            f'<textarea class="refs" rows="2" placeholder="参照画像（任意・1行に1つ「URL 説明」例: https://… キャラ三面図）">'
            f'{escape(_ref_lines(cut.get("references", [])))}</textarea>'
            + (f'<select class="charset" onchange="addSet(this)"><option value="">＋ キャラの参照画像セットを追加</option>{set_options}</select>'
               if sets else '')
            + f'<button type="button" class="ghost" onclick="draft(this)">🎬 下書きを作る（{sec}秒・約{vb.draft_cost_jpy(sec, config):,}円）</button>'
            f'<div class="out"></div></div>'
        )
    return (f'<h2>🎬 下書き動画（{escape(d.get("resolution", "480p"))}）</h2>'
            '<p class="hint">OKが出たカットだけ、本番（1080p）を Higgsfield 等で手で作ってください。'
            '画像URLを入れると、その画像から動かします。参照画像（三面図・商品・背景など）を入れると、複数の画像を参考に作ります（キャラや商品の見た目をそろえたいとき）。'
            '指示書の各カットの「- 最初の画像:」の行に https:// のURLを書いて保存しておくと、読み込んだときに自動で入ります。'
            ' <a href="/video-brief/characters" target="_blank">🧑‍🎨 キャラの参照画像セットを登録・編集</a>'
            ' ／ <a href="/video-brief/drafts" target="_blank">🎞 できた下書きをつないで1本にする</a></p>'
            + f'<script>const CHARSETS = {set_json};</script>'
            + "".join(rows))


@bp.route("/video-brief/load", methods=["POST"])
def video_brief_load():
    """保存した指示書（Markdown）を読み込んで、同じカット割りで下書きボタンを出す"""
    if not session.get("video_brief_ok"):
        return redirect("/video-brief")
    sent = str(request.form.get("csrf_token", ""))
    if not hmac.compare_digest(str(session.get("video_brief_csrf", "")), sent):
        return _html("<p>画面が古くなっています。戻って再読み込みしてください。</p>", 400)
    config = vb.load_config()
    text = str(request.form.get("markdown", ""))
    if len(text) > 200_000:
        return _html(_form_page(config, "指示書が大きすぎます（200KBまで）"), 400)
    try:
        form, brief = vb.parse_markdown(text, config)
    except ValueError as e:
        return _html(_form_page(config, str(e)), 400)
    missing = vb.expand_sets(brief, get_char_store().sets())
    with_image = sum(1 for c in brief["cuts"] if c.get("image_url") or c.get("references"))
    status = (f'<p class="badge ok">📂 「{escape(form["subject"] or "指示書")}」を読み込みました'
              f'（カット{len(brief["cuts"])}本・画像URLあり{with_image}本）</p>')
    if missing:
        status += (f'<p class="hint">⚠️ 登録されていない参照セット: {escape("、".join(missing))}'
                   '（<a href="/video-brief/characters" target="_blank">登録画面</a>で名前を確認してください）</p>')
    if not vb.draft_api_key(config) or not config.get("draft", {}).get("enabled"):
        status += '<p class="hint">⚠️ FAL_KEY 未設定のため、下書きボタンは出ません。</p>'
    body = (
        RESULT_HTML.replace("__STATUS__", status)
        .replace("__DRAFTS__", _draft_section(brief, form, config))
        .replace("__TELOPS__", _telop_section(brief))
        .replace("__MD__", str(escape(text)))
        .replace("__FILENAME__", "brief.md")
        .replace("__CSRF__", _csrf_token())
    )
    return _html(body)


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
        refs = vb.parse_reference_lines(body.get("references", ""), config)
        draft = vb.start_draft(body.get("prompt", ""), body.get("seconds", 5), aspect, config, get_store(), image_url,
                               references=refs, meta={"cut": body.get("cut", ""), "subject": body.get("subject", "")})
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


@bp.route("/video-brief/characters", methods=["GET", "POST"])
def video_brief_characters():
    """キャラごとの参照画像セット（三面図・衣装・表情など）の登録・編集・削除"""
    if not session.get("video_brief_ok"):
        return redirect("/video-brief")
    config = vb.load_config()
    store = get_char_store()
    error, msg, values = "", "", {}
    if request.method == "POST":
        if not hmac.compare_digest(str(session.get("video_brief_csrf", "")), str(request.form.get("csrf_token", ""))):
            return _html("<p>画面が古くなっています。戻って再読み込みしてください。</p>", 400)
        char_id = str(request.form.get("id", "")).strip()
        if request.form.get("action") == "delete" and char_id:
            store.delete(char_id)
            msg = "削除しました"
        else:
            values = {"id": char_id, "name": request.form.get("name", ""), "images": request.form.get("images", "")}
            try:
                if char_id and not store.get(char_id):
                    raise ValueError("このセットは見つかりません（削除された可能性があります）")
                char = vb.make_character(values["name"], values["images"], config, char_id or None)
                if any(c["name"] == char["name"] and c["id"] != char["id"] for c in store.sets()):
                    raise ValueError(f"「{char['name']}」はもう登録されています。別の名前にしてください")
                store.save(char)
                msg, values = f"「{char['name']}」を保存しました", {}
            except ValueError as e:
                error = str(e)
    elif request.args.get("edit"):
        c = store.get(request.args["edit"])
        if c:
            values = {"id": c["id"], "name": c["name"], "images": _ref_lines(c.get("images", []))}
    csrf = _csrf_token()
    cards = "".join(
        f'<div class="set"><b>{escape(c["name"])}</b> <span class="hint">（{len(c.get("images", []))}枚）</span>'
        + "<ul>" + "".join(f'<li><a href="{escape(r["url"])}" target="_blank" rel="noopener">{escape(r.get("label") or r["url"])}</a></li>'
                           for r in c.get("images", [])) + "</ul>"
        f'<a class="ghost" href="/video-brief/characters?edit={escape(c["id"])}">✏️ 編集</a>'
        f'<form method="POST" onsubmit="return confirm(\'「{escape(c["name"])}」を削除しますか？\')">'
        f'<input type="hidden" name="csrf_token" value="{csrf}"><input type="hidden" name="id" value="{escape(c["id"])}">'
        f'<input type="hidden" name="action" value="delete"><button class="danger" type="submit">削除</button></form></div>'
        for c in store.sets()
    ) or '<p class="hint">まだ登録がありません。</p>'
    limit = int(config.get("draft", {}).get("max_reference_images", 9))
    body = (
        CHARS_HTML.replace("__CSRF__", csrf)
        .replace("__MSG__", f'<p class="ok">✅ {escape(msg)}</p>' if msg else "")
        .replace("__ERROR__", f'<p class="error">{escape(error)}</p>' if error else "")
        .replace("__FORM_TITLE__", "✏️ セットを編集" if values.get("id") else "＋ 新しいセットを登録")
        .replace("__ID__", str(escape(values.get("id", ""))))
        .replace("__NAME__", str(escape(values.get("name", ""))))
        .replace("__IMAGES__", str(escape(values.get("images", ""))))
        .replace("__LIMIT__", str(limit))
        .replace("__CARDS__", cards)
        .replace("__STORAGE__", "データベースに保存" if os.environ.get("DATABASE_URL") else "⚠️ DATABASE_URL 未設定（再起動で消えます）")
    )
    return _html(body)


def _default_order(drafts):
    """いちばん新しい案件の、カットごとの最新の下書きに、カット番号を順番として入れておく"""
    latest = next((d for d in drafts if d.get("subject") and d.get("cut")), None)
    if not latest:
        return {}
    order, seen = {}, set()
    for d in drafts:  # 新しい順
        if d.get("subject") == latest["subject"] and d.get("cut") and d["cut"] not in seen:
            seen.add(d["cut"])
            order[d["id"]] = d["cut"]
    return order


@bp.route("/video-brief/drafts", methods=["GET", "POST"])
def video_brief_drafts():
    """完成した下書きを選んで、順番どおりにつないだ確認用の動画を作る"""
    if not session.get("video_brief_ok"):
        return redirect("/video-brief")
    store = get_store()
    drafts = vb.done_drafts(store.all())
    error, result = "", ""
    order = _default_order(drafts)
    if request.method == "POST":
        if not hmac.compare_digest(str(session.get("video_brief_csrf", "")), str(request.form.get("csrf_token", ""))):
            return _html("<p>画面が古くなっています。戻って再読み込みしてください。</p>", 400)
        by_id = {d["id"]: d for d in drafts}
        order, picked = {}, []
        for key, value in request.form.items():
            if key.startswith("order_") and str(value).strip():
                did = key[len("order_"):]
                try:
                    n = float(value)
                except ValueError:
                    error = "順番は数字で入れてください"
                    continue
                order[did] = str(value).strip()
                if did in by_id:
                    picked.append((n, by_id[did]))
        if not error:
            try:
                job_id, _ = vb.make_concat([d for _, d in sorted(picked, key=lambda x: x[0])])
                total = sum(int(d.get("seconds", 0)) for _, d in picked)
                result = (f'<div class="box"><h2>✅ {len(picked)}本をつなぎました（約{total}秒・音なし）</h2>'
                          f'<video controls playsinline src="/video-brief/concat/{job_id}.mp4"></video>'
                          f'<p><a class="ghost" href="/video-brief/concat/{job_id}.mp4" download="connected.mp4">⬇ ダウンロード</a></p>'
                          '<p class="hint">このファイルは2時間で消えます。必要なら今のうちに保存してください。</p></div>')
            except ValueError as e:
                error = str(e)
            except Exception as e:
                print(f"[video_brief] concat failed: {e}")
                error = str(e)
    csrf = _csrf_token()
    rows = "".join(
        f'<div class="draft"><video preload="metadata" muted playsinline controls src="{escape(d["video_url"])}#t=0.5"></video>'
        f'<div class="meta"><label>順番 <input type="number" step="any" min="0" name="order_{escape(d["id"])}" '
        f'value="{escape(order.get(d["id"], ""))}"></label>'
        f'<b>{escape(d.get("subject") or "（案件名なし）")}</b> {("カット" + escape(d["cut"])) if d.get("cut") else ""}'
        f'<br><span class="hint">{escape(str(d.get("created_at", ""))[:16].replace("T", " "))}・{escape(d.get("seconds", ""))}秒・'
        f'{escape(d.get("aspect", ""))}</span><br><span class="hint">{escape(str(d.get("prompt", ""))[-120:])}</span></div></div>'
        for d in drafts
    ) or '<p class="hint">完成した下書きがまだありません。</p>'
    body = (
        DRAFTS_HTML.replace("__CSRF__", csrf)
        .replace("__RESULT__", result)
        .replace("__ERROR__", f'<p class="error">{escape(error)}</p>' if error else "")
        .replace("__ROWS__", rows)
    )
    return _html(body)


@bp.route("/video-brief/concat/<job_id>.mp4")
def video_brief_concat_file(job_id):
    if not session.get("video_brief_ok"):
        return redirect("/video-brief")
    path = vb.concat_path(job_id)
    if not path:
        return _html("<p>ファイルが見つかりません（2時間で消えます）。もう一度つないでください。</p>", 404)
    from flask import send_file
    return send_file(path, mimetype="video/mp4", conditional=True)


DRAFTS_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>下書きをつなぐ</title><style>"""
    + _BASE_CSS
    + r"""
.box { max-width: 760px; margin: 0 auto 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; box-shadow: var(--shadow); }
h1 { font-size: 18px; margin-bottom: 6px; } h2 { font-size: 15px; margin-bottom: 8px; }
video { width: 100%; border-radius: 10px; background: #000; max-height: 420px; }
.draft { display: flex; gap: 12px; border: 1px solid var(--border); border-radius: 12px; padding: 10px; margin-top: 10px; align-items: flex-start; }
.draft video { width: 200px; flex: none; max-height: 200px; }
.draft .meta { font-size: 13px; word-break: break-all; }
.draft label { display: block; font-weight: 700; margin-bottom: 6px; } .draft input { width: 90px; margin-left: 6px; }
button[type=submit] { width: 100%; margin-top: 14px; }
a.ghost { display: inline-block; margin-top: 10px; padding: 10px 14px; border-radius: 10px; background: var(--surface2); color: var(--accent); border: 1px solid var(--border); text-decoration: none; font-weight: 700; }
.error { text-align: left; }
@media (max-width: 520px) { .draft { flex-direction: column; } .draft video { width: 100%; } }
</style></head><body>
<div class="box">
<h1>🎞 下書きをつないで1本にする</h1>
<p class="hint">つなぎたい下書きに「順番」（1, 2, 3…）を入れて「つなぐ」を押すと、確認用の動画を1本作ります。生成はしないので<b>追加の費用はかかりません</b>。
音は入りません（下書きは音なしで作っているため）。縦横比は1本目に合わせます。<a href="/video-brief">← 指示書メーカーに戻る</a></p>
__ERROR__
</div>
__RESULT__
<form method="POST" action="/video-brief/drafts" onsubmit="this.querySelector('button').textContent='つないでいます…（1分ほどかかります）';">
<input type="hidden" name="csrf_token" value="__CSRF__">
<div class="box"><h2>完成した下書き（新しい順）</h2>__ROWS__
<button type="submit">🎞 順番どおりにつなぐ</button></div>
</form>
</body></html>"""
)


CHARS_HTML = (
    r"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>キャラの参照画像セット</title><style>"""
    + _BASE_CSS
    + r"""
.box { max-width: 640px; margin: 0 auto 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; box-shadow: var(--shadow); }
h1 { font-size: 18px; margin-bottom: 6px; } h2 { font-size: 15px; margin-bottom: 8px; }
label { display: block; font-weight: 700; margin: 12px 0 6px; font-size: 13px; }
button[type=submit] { margin-top: 12px; }
.set { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin-top: 10px; }
.set ul { padding-left: 18px; margin: 6px 0; font-size: 12px; word-break: break-all; }
.set form { display: inline; } .set button { margin-top: 0; padding: 6px 10px; font-size: 12px; }
a.ghost { display: inline-block; padding: 6px 10px; border-radius: 10px; background: var(--surface2); color: var(--accent); border: 1px solid var(--border); text-decoration: none; font-weight: 700; font-size: 12px; }
.ok { color: var(--ok); font-weight: 700; } .error { text-align: left; }
</style></head><body>
<div class="box">
<h1>🧑‍🎨 キャラの参照画像セット</h1>
<p class="hint">キャラごとに三面図・衣装・表情などの画像URLをまとめて登録しておくと、下書きを作るときにプルダウンで参照画像に追加できます。指示書では「- 参照セット: キャラ名」と書けば自動で入ります。<a href="/video-brief">← 指示書メーカーに戻る</a></p>
__MSG____ERROR__
</div>
<div class="box">
<h2>__FORM_TITLE__</h2>
<form method="POST" action="/video-brief/characters">
<input type="hidden" name="csrf_token" value="__CSRF__"><input type="hidden" name="id" value="__ID__">
<label>キャラ名</label><input name="name" value="__NAME__" placeholder="例: しー" maxlength="40" required>
<label>画像（1行に1つ「URL 説明」・__LIMIT__枚まで）</label>
<textarea name="images" rows="5" placeholder="https://drive.google.com/file/d/…/view 三面図&#10;https://drive.google.com/file/d/…/view 配信衣装" required>__IMAGES__</textarea>
<p class="hint">Googleドライブの共有リンクはそのまま貼れます（「リンクを知っている全員」に共有しておく）。1カットで使える画像は、最初の画像・ほかの参照画像と合わせて__LIMIT__枚までです。</p>
<button type="submit">保存する</button>
</form>
</div>
<div class="box"><h2>登録済み</h2>__CARDS__<p class="hint" style="margin-top:12px">保存先: __STORAGE__</p></div>
</body></html>"""
)


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
.load { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border); }
.load h2 { font-size: 15px; margin-bottom: 4px; } .load input[type=file] { margin: 10px 0 8px; }
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
<form method="POST" action="/video-brief/load" class="load">
<input type="hidden" name="csrf_token" value="__CSRF__">
<h2>📂 保存した指示書から下書きを作る</h2>
<p class="hint">前に保存したMarkdownを読み込むと、同じカット割り（カット1・カット2…）のまま下書きボタンが出ます。作っておいた画像と合わせたいときに。</p>
<input type="file" accept=".md,.markdown,.txt,text/markdown,text/plain" onchange="loadMd(this)">
<textarea name="markdown" id="loadmd" rows="4" placeholder="ファイルを選ぶか、指示書のMarkdownをここに貼り付け" required></textarea>
<button type="submit" class="ghost">読み込む</button>
</form>
<p class="hint" style="margin-top:16px"><a href="/video-brief/characters">🧑‍🎨 キャラの参照画像セットを登録・編集</a>
 ／ <a href="/video-brief/drafts">🎞 できた下書きをつないで1本にする</a></p>
<details><summary>全ジャンル共通のルール</summary><ul>__FOUNDATIONS__</ul></details>
</div>
<script>
function loadMd(input) {
  const f = input.files[0]; if (!f) return;
  const r = new FileReader(); r.onload = () => { document.getElementById('loadmd').value = r.result; }; r.readAsText(f);
}
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
table.telops { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
table.telops th, table.telops td { border-bottom: 1px solid var(--border); padding: 6px; text-align: left; vertical-align: top; }
table.telops td:first-child { white-space: nowrap; }
.cut { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin-top: 10px; }
.cut input, .cut textarea.refs, .cut select.charset { margin: 8px 0 0; } .cut button { margin-top: 8px; } .cut video { width: 100%; max-height: 360px; margin-top: 8px; border-radius: 8px; background: #000; }
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
__TELOPS__
__DRAFTS__
<p class="hint">案件フォルダ（Notion / Google ドライブ）に保存しておくと、次の案件で使い回せます。</p>
</div>
<script>
const CSRF = '__CSRF__';
function addSet(sel) {
  const lines = (typeof CHARSETS !== 'undefined' && CHARSETS[sel.value]) || '';
  const ta = sel.closest('.cut').querySelector('.refs');
  const have = new Set(ta.value.split('\n').map(l => l.trim().split(' ')[0]).filter(Boolean));
  const add = lines.split('\n').filter(l => l && !have.has(l.split(' ')[0]));
  if (add.length) ta.value = (ta.value.trim() ? ta.value.trim() + '\n' : '') + add.join('\n');
  sel.value = '';
}
async function draft(btn) {
  const box = btn.closest('.cut'), out = box.querySelector('.out'), d = JSON.parse(box.dataset.cut);
  if (!confirm(btn.textContent.replace('🎬 ', '') + 'で作ります。よろしいですか？')) return;
  btn.disabled = true; out.textContent = '送信中…';
  try {
    const r = await fetch('/video-brief/draft', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...d, image_url: box.querySelector('.img').value,
        references: box.querySelector('.refs').value, csrf_token: CSRF})});
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
function dlText(key, name, type) {
  const blob = new Blob([TELOPS[key]], {type: type + ';charset=utf-8'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
}
function dl() {
  const blob = new Blob([document.getElementById('md').value], {type: 'text/markdown'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = '__FILENAME__'; a.click();
}
</script>
</body></html>"""
)
