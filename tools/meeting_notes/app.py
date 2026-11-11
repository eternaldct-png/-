"""会議ノート（自分専用）。Circleback のコア機能を、自分のPCだけで動くように作り直したもの。

起動: python3 tools/meeting_notes/run.py  →  http://127.0.0.1:5055
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, url_for

from . import ai, transcribe
from .store import BUSY, Store, clean_list, new_id, split_terms
from .worker import Worker

HERE = Path(__file__).resolve().parent
AUDIO_EXT = {".webm", ".ogg", ".oga", ".mp3", ".m4a", ".mp4", ".mov", ".wav", ".aac", ".flac", ".mkv", ".mpeg", ".mpga"}
TEXT_EXT = {".txt", ".vtt", ".srt", ".md"}
HEADER = "X-Meeting-Notes"


def default_data_dir() -> Path:
    return Path(os.environ.get("MEETING_NOTES_DIR") or Path.home() / "MeetingNotes")


def create_app(data_dir: str | Path | None = None, *, transcriber=None, ai_client=None, start_worker=True) -> Flask:
    data_dir = Path(data_dir or default_data_dir())
    audio_dir = data_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, template_folder=str(HERE / "templates"), static_folder=str(HERE / "static"))
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB
    store = Store(data_dir / "meeting_notes.db")
    worker = Worker(store, audio_dir, transcriber=transcriber, ai_client=ai_client)
    app.extensions["mn_store"] = store
    app.extensions["mn_worker"] = worker
    app.extensions["mn_ai_client"] = ai_client
    app.config["MN_DATA_DIR"] = str(data_dir)
    if start_worker:
        worker.start()

    # ── 守り（ログインなしの代わり） ─────────────────────────
    # 1) 127.0.0.1 / localhost 以外の Host は断る（DNS リバインディング対策）
    # 2) 書き換える API は独自ヘッダー必須（他サイトからのなりすまし送信＝CSRF 対策。ブラウザは他サイトから独自ヘッダーを付けられない）

    @app.before_request
    def guard():
        host = (request.host or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "[::1]"):
            abort(403)
        if request.method in ("POST", "PATCH", "PUT", "DELETE") and request.headers.get(HEADER) != "1":
            abort(403)

    @app.after_request
    def no_store(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp

    @app.context_processor
    def globals_():
        return {"nav": request.endpoint, "fmt_clock": transcribe.fmt_clock,
                "whisper_ok": transcribe.whisper_available(),
                "api_key_ok": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or ai_client)}

    def get_or_404(mid):
        m = store.get_meeting(mid)
        if not m:
            abort(404)
        return m

    # ── 画面 ────────────────────────────────────────────

    @app.get("/")
    def index():
        q = request.args.get("q", "").strip()
        tag = request.args.get("tag", "").strip()
        meetings = store.list_meetings(q=q, tag=tag)
        for m in meetings:
            m["snippet"] = snippet(m, q) if q else (m["notes"].get("summary", "") if m["notes"] else "")
        return render_template("index.html", meetings=meetings, q=q, tag=tag, tags=store.all_tags())

    @app.get("/new")
    def new():
        return render_template("new.html", tags=store.all_tags())

    @app.get("/m/<mid>")
    def meeting(mid):
        m = get_or_404(mid)
        speakers = sorted({s.get("speaker", "") for s in m["transcript"] if s.get("speaker")})
        return render_template("meeting.html", m=m, actions=store.actions_for(mid), chat=store.chat_for(mid),
                               speakers=speakers, tags=store.all_tags())

    @app.get("/actions")
    def actions():
        owner = request.args.get("owner", "")
        state = request.args.get("state", "open")
        if state not in ("open", "done", "all"):
            state = "open"
        return render_template("actions.html", items=store.list_actions(owner=owner, state=state),
                               owners=store.action_owners(), owner=owner, state=state)

    @app.get("/ask")
    def ask_page():
        return render_template("ask.html", chat=store.chat_for(None))

    @app.get("/settings")
    def settings_page():
        return render_template("settings.html", s=store.settings(), data_dir=str(data_dir))

    @app.get("/design")
    def design():
        return render_template("design.html")

    # ── 会議 API ─────────────────────────────────────────

    @app.post("/api/meetings")
    def create_meeting():
        f = request.form
        source = f.get("source", "")
        title = f.get("title", "").strip()[:200]
        started_at = to_utc(f.get("started_at", "")) or datetime.now(timezone.utc).isoformat(timespec="seconds")
        kwargs = dict(title=title, started_at=started_at, participants=f.get("participants", ""),
                      tags=f.get("tags", ""), language=store.settings().get("language", "ja"))
        if source in ("record", "upload"):
            up = request.files.get("audio")
            if not up or not up.filename:
                return err("音声ファイルがありません。")
            ext = Path(up.filename).suffix.lower() or ".webm"
            if ext not in AUDIO_EXT:
                return err(f"この形式（{ext}）には対応していません。mp3 / m4a / wav / mp4 / webm などを選んでください。")
            # faster-whisper が未インストールでも録音は必ず保存する（録り直せない会議を失わないため）。
            # その場合は処理が「失敗」になり、インストール後に「やり直す」で文字起こしできる。
            name = f"{new_id()}{ext}"
            up.save(audio_dir / name)
            dur = to_float(f.get("duration_sec"))
            mid = store.create_meeting(source=source, audio_path=name, duration_sec=dur, **kwargs)
        elif source == "transcript":
            text = f.get("transcript_text", "")
            filename = ""
            up = request.files.get("transcript_file")
            if up and up.filename:
                filename = up.filename
                if Path(filename).suffix.lower() not in TEXT_EXT:
                    return err("文字起こしは .txt / .vtt / .srt / .md を選んでください。")
                text = up.read().decode("utf-8", errors="replace")
            segs = transcribe.parse_transcript_text(text, filename)
            if not segs:
                return err("文字起こしが空です。")
            speakers = [s["speaker"] for s in segs if s["speaker"]]
            if not kwargs["participants"] and speakers:
                kwargs["participants"] = list(dict.fromkeys(speakers))
            ends = [s["end"] for s in segs if s.get("end") is not None]
            mid = store.create_meeting(source="transcript", transcript=segs,
                                       duration_sec=max(ends) if ends else None, **kwargs)
        else:
            return err("入力の種類が不明です。")
        worker.enqueue(mid)
        return jsonify({"id": mid, "url": url_for("meeting", mid=mid)})

    @app.get("/api/meetings/<mid>/status")
    def status(mid):
        m = get_or_404(mid)
        done, total = worker.progress.get(mid, (0, 0))
        return jsonify({"status": m["status"], "error": m["error"], "done_sec": done, "total_sec": total})

    @app.patch("/api/meetings/<mid>")
    def patch_meeting(mid):
        get_or_404(mid)
        data = request.get_json(silent=True) or {}
        fields = {}
        if "title" in data:
            fields["title"] = str(data["title"]).strip()[:200]
        if "started_at" in data:
            utc = to_utc(str(data["started_at"]))
            if not utc:
                return err("日時の形式が正しくありません。")
            fields["started_at"] = utc
        for key in ("participants", "tags"):
            if key in data:
                fields[key] = clean_list(data[key])
        store.update_meeting(mid, **fields)
        return jsonify({"ok": True})

    @app.post("/api/meetings/<mid>/regenerate")
    def regenerate(mid):
        m = get_or_404(mid)
        if m["status"] in BUSY or worker.is_pending(mid):
            return err("処理中です。終わってからもう一度押してください。", 409)
        if not m["transcript"]:
            return err("文字起こしが無いので、ノートを作り直せません。", 400)
        store.update_meeting(mid, status="queued", error="")
        worker.enqueue(mid)
        return jsonify({"ok": True})

    @app.post("/api/meetings/<mid>/retry")
    def retry(mid):
        m = get_or_404(mid)
        if worker.is_pending(mid):
            return err("処理中です。", 409)
        if m["status"] != "failed":
            return err("失敗した会議だけやり直せます。", 400)
        store.update_meeting(mid, status="queued", error="")
        worker.enqueue(mid)
        return jsonify({"ok": True})

    @app.post("/api/meetings/<mid>/speakers")
    def rename_speaker(mid):
        get_or_404(mid)
        data = request.get_json(silent=True) or {}
        old, new_name = str(data.get("from", "")), str(data.get("to", "")).strip()[:40]
        if not new_name:
            return err("新しい名前を入れてください。")
        n = store.rename_speaker(mid, old, new_name)
        return jsonify({"ok": True, "changed": n})

    @app.delete("/api/meetings/<mid>")
    def delete_meeting(mid):
        if worker.is_pending(mid):
            return err("処理中の会議は削除できません。終わってからもう一度お試しください。", 409)
        m = store.delete_meeting(mid)
        if not m:
            abort(404)
        if m["audio_path"]:
            (audio_dir / m["audio_path"]).unlink(missing_ok=True)
        return jsonify({"ok": True})

    @app.get("/m/<mid>/audio")
    def audio(mid):
        m = get_or_404(mid)
        if not m["audio_path"]:
            abort(404)
        path = (audio_dir / m["audio_path"]).resolve()
        if audio_dir.resolve() not in path.parents or not path.exists():
            abort(404)
        return send_file(path, conditional=True)

    @app.get("/m/<mid>/export.md")
    def export_md(mid):
        m = get_or_404(mid)
        md = to_markdown(m, store.actions_for(mid))
        name = re.sub(r'[\\/:*?"<>|\s]+', "_", m["title"] or "meeting")[:60] or "meeting"
        return Response(md, mimetype="text/markdown; charset=utf-8",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}.md"})

    @app.post("/api/meetings/<mid>/ask")
    def ask_meeting(mid):
        m = get_or_404(mid)
        question = str((request.get_json(silent=True) or {}).get("question", "")).strip()
        if not question:
            return err("質問を入れてください。")
        if not m["transcript"]:
            return err("文字起こしがまだ無いので質問できません。")
        history = store.chat_for(mid)
        try:
            answer = ai.answer_about_meeting(m, history, question, store.settings(),
                                             client=app.extensions["mn_ai_client"])
        except ai.AIError as e:
            return err(str(e), 502)
        store.add_chat(mid, "user", question)
        store.add_chat(mid, "assistant", answer)
        return jsonify({"answer": answer})

    @app.delete("/api/meetings/<mid>/chat")
    def clear_meeting_chat(mid):
        get_or_404(mid)
        store.clear_chat(mid)
        return jsonify({"ok": True})

    # ── アクション API ────────────────────────────────────

    @app.post("/api/actions")
    def add_action():
        data = request.get_json(silent=True) or {}
        mid = str(data.get("meeting_id", ""))
        get_or_404(mid)
        text = str(data.get("text", "")).strip()
        if not text:
            return err("やることを入れてください。")
        aid = store.add_action(mid, text[:500], str(data.get("owner", ""))[:60], str(data.get("due", ""))[:60])
        return jsonify({"id": aid})

    @app.patch("/api/actions/<aid>")
    def patch_action(aid):
        if not store.get_action(aid):
            abort(404)
        data = request.get_json(silent=True) or {}
        fields = {k: data[k] for k in ("text", "owner", "due", "done") if k in data}
        if "text" in fields and not str(fields["text"]).strip():
            return err("やることを空にはできません。")
        store.update_action(aid, **fields)
        return jsonify({"ok": True})

    @app.delete("/api/actions/<aid>")
    def delete_action(aid):
        if not store.get_action(aid):
            abort(404)
        store.delete_action(aid)
        return jsonify({"ok": True})

    # ── 横断質問・設定・バックアップ ─────────────────────────

    @app.post("/api/ask")
    def ask_all():
        question = str((request.get_json(silent=True) or {}).get("question", "")).strip()
        if not question:
            return err("質問を入れてください。")
        meetings = store.list_meetings()
        hits = {m["id"] for m in keyword_hits(store, question)}
        try:
            answer = ai.answer_across(meetings, hits, store.chat_for(None), question, store.settings(),
                                      client=app.extensions["mn_ai_client"])
        except ai.AIError as e:
            return err(str(e), 502)
        store.add_chat(None, "user", question)
        store.add_chat(None, "assistant", answer)
        sources = [{"id": m["id"], "title": m["title"] or "（無題）", "url": url_for("meeting", mid=m["id"])}
                   for m in meetings if m["id"] in hits][:8]
        return jsonify({"answer": answer, "sources": sources})

    @app.delete("/api/ask")
    def clear_ask():
        store.clear_chat(None)
        return jsonify({"ok": True})

    @app.post("/api/settings")
    def save_settings():
        data = request.get_json(silent=True) or {}
        if data.get("whisper_model") and data["whisper_model"] not in ("tiny", "base", "small", "medium", "large-v3", "turbo"):
            return err("Whisper のモデル名が正しくありません。")
        if "custom_context" in data:
            data["custom_context"] = str(data["custom_context"])[:4000]
        store.save_settings(**{k: v for k, v in data.items() if isinstance(v, str)})
        return jsonify({"ok": True})

    @app.get("/api/backup")
    def backup():
        body = json.dumps(store.export_all(), ensure_ascii=False, indent=1)
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        return Response(body, mimetype="application/json",
                        headers={"Content-Disposition": f"attachment; filename=meeting-notes-backup-{stamp}.json"})

    @app.errorhandler(413)
    def too_big(_e):
        return err("ファイルが大きすぎます（上限 1GB）。", 413)

    return app


# ── 補助 ─────────────────────────────────────────────────


def err(message: str, code: int = 400):
    return jsonify({"error": message}), code


def quote(s: str) -> str:
    from urllib.parse import quote as q
    return q(s)


def to_float(v):
    try:
        return round(float(v), 1) if v not in (None, "") else None
    except ValueError:
        return None


def to_utc(value: str) -> str:
    """ブラウザから来た日時（ISO8601、Z やオフセット付き）を UTC の ISO 文字列にする。読めなければ空文字。"""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.astimezone()  # タイムゾーンなし＝このPCのローカル時刻とみなす
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def snippet(m: dict, q: str, width: int = 60) -> str:
    """検索語の前後を抜き出す（ノート→文字起こしの順に探す）。"""
    terms = split_terms(q)
    texts = [m["notes"].get("summary", "") if m["notes"] else ""]
    for sec in (m["notes"] or {}).get("sections", []):
        texts += [sec.get("heading", "")] + list(sec.get("bullets", []))
    texts += [s.get("text", "") for s in m["transcript"]]
    for t in texts:
        for term in terms:
            i = t.lower().find(term.lower())
            if i >= 0:
                start = max(0, i - width // 2)
                return ("…" if start else "") + t[start:start + width] + ("…" if start + width < len(t) else "")
    return texts[0][:width] if texts and texts[0] else ""


_STOP = set("の は が を に で と も や か な て た だ です ます について とは どう なに 何 いつ 誰 だれ どこ ? ？ 教えて".split())


def keyword_hits(store: Store, question: str, limit: int = 5) -> list[dict]:
    """横断質問で文字起こしまで渡す会議を、質問の言葉から選ぶ（素朴なキーワード一致）。"""
    # 日本語は単語の間に空白が無いので、漢字・カタカナ・英数字が2文字以上続くところを言葉とみなす
    words = [w for w in re.findall(r"[一-龥々〆ヵヶァ-ヴーA-Za-z0-9０-９Ａ-Ｚａ-ｚ]{2,}", question) if w not in _STOP and not re.fullmatch(r"[ぁ-ん]+", w)]
    words = list(dict.fromkeys(words))[:12]
    scored = {}
    for w in words:
        for m in store.list_meetings(q=w):
            scored.setdefault(m["id"], [m, 0])[1] += 1
    ranked = sorted(scored.values(), key=lambda x: x[0]["started_at"], reverse=True)  # 新しい順
    ranked.sort(key=lambda x: -x[1])  # 当たった言葉が多い順（同点は新しい順のまま）
    return [m for m, _ in ranked[:limit]]


def to_markdown(m: dict, actions: list[dict]) -> str:
    notes = m["notes"] or {}
    try:
        when = datetime.fromisoformat(m["started_at"]).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        when = m["started_at"]
    lines = [f"# {m['title'] or '（無題の会議）'}", "", f"- 日時: {when}"]
    if m["participants"]:
        lines.append("- 参加者: " + "、".join(m["participants"]))
    if m["tags"]:
        lines.append("- タグ: " + "、".join(m["tags"]))
    if notes.get("summary"):
        lines += ["", "## 要約", "", notes["summary"]]
    if notes.get("decisions"):
        lines += ["", "## 決まったこと", ""] + [f"- {d}" for d in notes["decisions"]]
    if actions:
        lines += ["", "## やること", ""]
        for a in actions:
            extra = "".join(f"（{x}）" for x in (a["owner"], a["due"]) if x)
            lines.append(f"- [{'x' if a['done'] else ' '}] {a['text']}{extra}")
    for sec in notes.get("sections", []):
        lines += ["", f"## {sec.get('heading', '')}", ""] + [f"- {b}" for b in sec.get("bullets", [])]
    if m["transcript"]:
        lines += ["", "## 文字起こし", "", transcribe.transcript_to_text(m["transcript"])]
    return "\n".join(lines) + "\n"
