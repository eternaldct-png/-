"""コマドリ — アイデアからショートアニメを作る自分用の制作ツール。設計の記録は replica/anime/。

起動: python3 tools/anime_studio/run.py  →  http://127.0.0.1:5056
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

from . import art, engine, render
from .store import ASPECTS, CAMERAS, DEFAULT_SETTINGS, KINDS, STAGE_KEYS, STAGE_LABELS, STAGES, STYLES, Store, new_id
from .worker import Worker, month_start_iso

HERE = Path(__file__).resolve().parent
HEADER = "X-Komadori"


def default_data_dir() -> Path:
    return Path(os.environ.get("KOMADORI_DIR") or Path.home() / "Komadori")


def create_app(data_dir: str | Path | None = None, *, ai_client=None, start_worker: bool = True, short_side: int | None = None) -> Flask:
    data_dir = Path(data_dir or default_data_dir())
    data_dir.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, template_folder=str(HERE / "templates"), static_folder=str(HERE / "static"))
    app.config["MAX_CONTENT_LENGTH"] = 110 * 1024 * 1024
    store = Store(data_dir / "komadori.db")
    worker = Worker(store, data_dir, ai_client=ai_client, short_side=short_side)
    app.extensions["k_store"] = store
    app.extensions["k_worker"] = worker
    if start_worker:
        worker.start()

    # ── 守り（ログインなしの代わり） ─────────────────────────
    # 1) 127.0.0.1 / localhost 以外の Host は断る（DNS リバインディング対策）
    # 2) 書き換える API は独自ヘッダー必須（他サイトからのなりすまし送信を防ぐ）
    @app.before_request
    def guard():
        host = (request.host or "").rsplit(":", 1)[0] if not (request.host or "").startswith("[") else "[::1]"
        if host not in ("127.0.0.1", "localhost", "[::1]"):
            abort(403)
        if request.method in ("POST", "PATCH", "PUT", "DELETE") and request.headers.get(HEADER) != "1":
            abort(403)

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        return resp

    @app.errorhandler(ValueError)
    def bad_value(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(art.ArtError)
    def bad_art(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(413)
    def too_big(e):
        return jsonify(error="ファイルが大きすぎます。"), 413

    @app.context_processor
    def globals_():
        return {"nav": request.endpoint, "STAGES": STAGES, "KINDS": KINDS, "STYLES": STYLES, "ASPECTS": ASPECTS, "CAMERAS": CAMERAS}

    def project_or_404(pid):
        p = store.get_project(pid)
        if not p:
            abort(404)
        return p

    def body() -> dict:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("送られてきた内容が読めませんでした。")
        return data

    def file_url(pid, rel):
        return f"/files/{pid}/{rel}?v={int(time.time() // 1)}" if rel and worker.abs(pid, rel) else ""

    def full(pid) -> dict:
        p = project_or_404(pid)
        s = store.settings()
        shots = store.shots(pid)
        for sh in shots:
            sh["image_url"] = file_url(pid, sh["image_path"])
            sh["video_url"] = file_url(pid, sh["video_path"])
            sh["max_chars"] = engine.max_chars(sh["seconds"], s)
        chars = store.characters(pid)
        for c in chars:
            c["image_url"] = file_url(pid, c["image_path"])
        scenes = store.scenes(pid)
        for sc in scenes:
            sc["image_url"] = file_url(pid, sc["image_path"])
        voices = worker.voice_files(pid)
        p.update(
            characters=chars, scenes=scenes, shots=shots,
            warnings=engine.check_shots(p, shots, s) if shots else [],
            total_seconds=round(sum(x["seconds"] for x in shots), 1),
            jobs=store.jobs(pid, 5), active_job=store.active_job(pid), progress=worker.progress.get(pid, ""),
            logs=store.logs(pid), render_url=file_url(pid, p["render_path"]),
            bgm_url=file_url(pid, p["bgm_path"]), bgm_name=Path(p["bgm_path"]).name if p["bgm_path"] else "",
            voice_count=len(voices), say_available=render.say_available(),
            engine=engine.ENGINE_LABELS[engine.resolve_engine(s, ai_client)],
        )
        return p

    # ── 画面 ────────────────────────────────────────────

    @app.get("/")
    def index():
        projects = store.list_projects()
        for p in projects:
            p["thumb_url"] = file_url(p["id"], p["thumb"])
            p["current"] = next((STAGE_LABELS[k] for k in STAGE_KEYS if p["stages"][k] != "approved"), "完成")
        return render_template("index.html", projects=projects)

    @app.get("/new")
    def new():
        return render_template("new.html", engine=engine.ENGINE_LABELS[engine.resolve_engine(store.settings(), ai_client)])

    @app.get("/p/<pid>")
    def workspace(pid):
        p = project_or_404(pid)
        return render_template("project.html", p=p)

    @app.get("/library")
    def library():
        chars = store.characters(None)
        for c in chars:
            c["image_url"] = f"/files/library/{c['image_path']}" if c["image_path"] else ""
        return render_template("library.html", chars=chars)

    @app.get("/api/library")
    def api_library():
        chars = store.characters(None)
        for c in chars:
            c["image_url"] = f"/files/library/{c['image_path']}" if c["image_path"] else ""
        return jsonify(chars)

    @app.post("/api/library")
    def api_library_add():
        d = body()
        name = str(d.get("name") or "").strip()
        if not name:
            raise ValueError("名前を入れてください。")
        return jsonify(store.add_character(None, name=name[:60], look=str(d.get("look") or "")[:600],
                                           personality=str(d.get("personality") or "")[:400],
                                           color=engine.PALETTE[len(store.characters(None)) % len(engine.PALETTE)]))

    @app.get("/settings")
    def settings_page():
        s = store.settings()
        return render_template("settings.html", s=s, fal_key=bool(art.fal_key()), say=render.say_available(),
                               voices=render.say_voices(), font=art.font_path(), engine=engine.resolve_engine(s, ai_client),
                               engine_labels=engine.ENGINE_LABELS, spent=store.spend_since(month_start_iso()),
                               claude_key=bool(os.environ.get("ANTHROPIC_API_KEY")), data_dir=str(data_dir))

    @app.get("/design")
    def design():
        return render_template("design.html")

    # ── 作品 API ─────────────────────────────────────────

    @app.post("/api/projects")
    def create_project():
        d = body()
        idea = str(d.get("idea") or "").strip()
        if not idea:
            raise ValueError("アイデアを書いてください。")
        if len(idea) > 8000:
            raise ValueError("アイデアは8000文字までにしてください。")
        kind = d.get("kind") if d.get("kind") in KINDS else "story"
        style = d.get("style") if d.get("style") in STYLES else "anime"
        aspect = d.get("aspect") if d.get("aspect") in ASPECTS else "9:16"
        try:
            dur = int(d.get("duration_sec") or 30)
        except (TypeError, ValueError):
            dur = 30
        dur = min(180, max(5, dur))
        p = store.create_project(title=str(d.get("title") or "").strip()[:80], kind=kind, idea=idea, style=style, aspect=aspect,
                                 duration_sec=dur, language=str(d.get("language") or "ja")[:10], mood=str(d.get("mood") or "")[:200],
                                 auto=bool(d.get("auto")))
        store.log(p["id"], "director", "はじめまして。脚本 → キャラ → 場面 → 絵コンテ → 絵と動き → 音 → 書き出し の順に進めます。"
                  + ("おまかせなので、最後まで自動で進めます。" if p["auto"] else "各段階で確認してから次へ進みます。"))
        for cid in d.get("library_ids") or []:
            src = store.get_character(str(cid))
            if src and src["project_id"] is None:
                copy_from_library(p["id"], src)
        worker.enqueue(p["id"], "script")
        return jsonify(id=p["id"])

    def copy_from_library(pid: str, src: dict) -> dict:
        rel = ""
        if src["image_path"]:
            s_abs = data_dir / "library" / src["image_path"]
            if s_abs.exists():
                rel = f"chars/{new_id()}{s_abs.suffix}"
                (worker.pdir(pid) / "chars").mkdir(exist_ok=True)
                shutil.copy(s_abs, worker.pdir(pid) / rel)
        return store.add_character(pid, name=src["name"], look=src["look"], personality=src["personality"], voice=src["voice"],
                                   color=src["color"], image_path=rel, library_id=src["id"])

    @app.get("/api/projects/<pid>")
    def get_project(pid):
        return jsonify(full(pid))

    @app.patch("/api/projects/<pid>")
    def patch_project(pid):
        p = project_or_404(pid)
        d = body()
        f = {}
        for k in ("title", "mood", "idea"):
            if k in d:
                f[k] = str(d[k])[:8000 if k == "idea" else 200]
        if "kind" in d and d["kind"] in KINDS:
            f["kind"] = d["kind"]
        if "style" in d and d["style"] in STYLES:
            f["style"] = d["style"]
        if "aspect" in d and d["aspect"] in ASPECTS:
            f["aspect"] = d["aspect"]
            if p["aspect"] != d["aspect"]:
                store.set_stage(pid, "storyboard", p["stages"]["storyboard"], invalidate_after=True)
        if "duration_sec" in d:
            f["duration_sec"] = min(180, max(5, int(d["duration_sec"])))
        if "auto" in d:
            f["auto"] = bool(d["auto"])
        if "bgm_volume" in d:
            f["bgm_volume"] = min(1.0, max(0.0, float(d["bgm_volume"])))
        if "script" in d:
            script = engine.normalize_script(d["script"], p)
            f["script"] = script
            store.set_stage(pid, "script", "review" if p["stages"]["script"] != "approved" else "approved", invalidate_after=True)
            store.log(pid, "me", "脚本を直接書き換えました。")
        store.update_project(pid, **f)
        return jsonify(full(pid))

    @app.delete("/api/projects/<pid>")
    def delete_project(pid):
        project_or_404(pid)
        if store.active_job(pid):
            raise ValueError("作っている途中の作品は消せません。終わってから消してください。")
        store.delete_project(pid)
        shutil.rmtree(data_dir / "projects" / pid, ignore_errors=True)
        return jsonify(ok=True)

    @app.post("/api/projects/<pid>/stages/<stage>/generate")
    def generate(pid, stage):
        project_or_404(pid)
        if stage not in STAGE_KEYS:
            abort(404)
        d = request.get_json(silent=True) or {}
        instruction = str(d.get("instruction") or "").strip()[:2000]
        if instruction:
            store.log(pid, "me", instruction)
        job = worker.enqueue(pid, stage, instruction)
        return jsonify(job=job, project=full(pid))

    @app.post("/api/projects/<pid>/stages/<stage>/approve")
    def approve(pid, stage):
        p = project_or_404(pid)
        if stage not in STAGE_KEYS or stage == "render":
            abort(404)
        if p["stages"][stage] not in ("review", "stale", "approved"):
            raise ValueError(f"「{STAGE_LABELS[stage]}」はまだ確認できる状態ではありません。")
        if store.active_job(pid):
            raise ValueError("作っている途中です。終わってから押してください。")
        if stage == "storyboard" and not store.shots(pid):
            raise ValueError("カットが1つもありません。")
        if stage == "characters" and not store.characters(pid):
            raise ValueError("キャラが1人もいません（ナレーションだけの作品でも、背景用に1人は置いてください）。")
        worker.approve(pid, stage)
        return jsonify(full(pid))

    def mark_edited(pid, stage):
        p = store.get_project(pid)
        st = p["stages"][stage]
        store.set_stage(pid, stage, st if st in ("review", "approved") else "review", invalidate_after=True)

    # ── キャラ ───────────────────────────────────────────

    @app.post("/api/projects/<pid>/characters")
    def add_character(pid):
        project_or_404(pid)
        d = body()
        if d.get("from_id"):
            src = store.get_character(str(d["from_id"]))
            if not src or src["project_id"] is not None:
                raise ValueError("ライブラリのキャラが見つかりません。")
            c = copy_from_library(pid, src)
        else:
            c = store.add_character(pid, name=str(d.get("name") or "新しいキャラ")[:60], look=str(d.get("look") or "")[:600],
                                    personality=str(d.get("personality") or "")[:400],
                                    color=engine.PALETTE[len(store.characters(pid)) % len(engine.PALETTE)])
        mark_edited(pid, "characters")
        return jsonify(c)

    @app.patch("/api/characters/<cid>")
    def patch_character(cid):
        c = store.get_character(cid) or abort(404)
        d = body()
        f = {k: str(d[k])[:600] for k in ("name", "look", "personality", "voice") if k in d}
        if "name" in f and not f["name"].strip():
            raise ValueError("名前を入れてください。")
        if d.get("save_to_library"):
            if c["project_id"] is None:
                raise ValueError("もうライブラリにあります。")
            lib = store.add_character(None, name=c["name"], look=c["look"], personality=c["personality"], voice=c["voice"], color=c["color"])
            if c["image_path"] and worker.abs(c["project_id"], c["image_path"]):
                src = worker.abs(c["project_id"], c["image_path"])
                (data_dir / "library").mkdir(exist_ok=True)
                name = f"{lib['id']}{src.suffix}"
                shutil.copy(src, data_dir / "library" / name)
                store.update_character(lib["id"], image_path=name)
            return jsonify(store.get_character(lib["id"]))
        if c["project_id"] and "name" in f and f["name"] != c["name"]:
            # カットに書いてある名前も一緒に変える
            for sh in store.shots(c["project_id"]):
                if c["name"] in sh["characters"] or sh["speaker"] == c["name"]:
                    store.update_shot(sh["id"], characters=[f["name"] if n == c["name"] else n for n in sh["characters"]],
                                      speaker=f["name"] if sh["speaker"] == c["name"] else sh["speaker"])
        out = store.update_character(cid, **f)
        if c["project_id"]:
            mark_edited(c["project_id"], "characters")
        return jsonify(out)

    @app.delete("/api/characters/<cid>")
    def delete_character(cid):
        c = store.get_character(cid) or abort(404)
        store.delete_character(cid)
        if c["project_id"]:
            mark_edited(c["project_id"], "characters")
        elif c["image_path"]:
            (data_dir / "library" / c["image_path"]).unlink(missing_ok=True)
        return jsonify(ok=True)

    # ── 場面 ────────────────────────────────────────────

    @app.post("/api/projects/<pid>/scenes")
    def add_scene(pid):
        project_or_404(pid)
        d = body()
        sc = store.add_scene(pid, name=str(d.get("name") or "新しい場面")[:60], description=str(d.get("description") or "")[:600],
                             color=engine.PALETTE[len(store.scenes(pid)) % len(engine.PALETTE)])
        mark_edited(pid, "scenes")
        return jsonify(sc)

    @app.patch("/api/scenes/<sid>")
    def patch_scene(sid):
        sc = store.get_scene(sid) or abort(404)
        d = body()
        out = store.update_scene(sid, **{k: str(d[k])[:600] for k in ("name", "description") if k in d})
        mark_edited(sc["project_id"], "scenes")
        return jsonify(out)

    @app.delete("/api/scenes/<sid>")
    def delete_scene(sid):
        sc = store.get_scene(sid) or abort(404)
        store.delete_scene(sid)
        mark_edited(sc["project_id"], "scenes")
        return jsonify(ok=True)

    # ── カット ───────────────────────────────────────────

    SHOT_EDIT = ("seconds", "scene_id", "characters", "camera", "action", "speaker", "dialogue", "caption", "image_prompt")

    @app.post("/api/projects/<pid>/shots")
    def add_shot(pid):
        project_or_404(pid)
        d = request.get_json(silent=True) or {}
        f = {k: d[k] for k in SHOT_EDIT if k in d}
        f.setdefault("seconds", 3)
        after = d.get("after")
        sh = store.add_shot(pid, **f)
        if after:
            ids = [s["id"] for s in store.shots(pid) if s["id"] != sh["id"]]
            if after in ids:
                ids.insert(ids.index(after) + 1, sh["id"])
                store.reorder_shots(pid, ids)
        mark_edited(pid, "storyboard")
        return jsonify(store.get_shot(sh["id"]))

    @app.patch("/api/shots/<sid>")
    def patch_shot(sid):
        sh = store.get_shot(sid) or abort(404)
        d = body()
        f = {k: d[k] for k in SHOT_EDIT if k in d}
        if "seconds" in f:
            try:
                f["seconds"] = float(f["seconds"])
            except (TypeError, ValueError):
                raise ValueError("秒数は数字で入れてください。")
        if "scene_id" in f and f["scene_id"] and not store.get_scene(f["scene_id"]):
            raise ValueError("場面が見つかりません。")
        for k in ("action", "speaker", "dialogue", "caption", "image_prompt"):
            if k in f:
                f[k] = str(f[k])[:1000]
        out = store.update_shot(sid, **f)
        mark_edited(sh["project_id"], "storyboard")
        return jsonify(out)

    @app.delete("/api/shots/<sid>")
    def delete_shot(sid):
        sh = store.get_shot(sid) or abort(404)
        store.delete_shot(sid)
        mark_edited(sh["project_id"], "storyboard")
        return jsonify(ok=True)

    @app.post("/api/projects/<pid>/shots/reorder")
    def reorder(pid):
        project_or_404(pid)
        ids = body().get("ids") or []
        store.reorder_shots(pid, [str(i) for i in ids])
        mark_edited(pid, "storyboard")
        return jsonify(ok=True)

    @app.post("/api/projects/<pid>/fit-to-bgm")
    def fit_to_bgm(pid):
        p = project_or_404(pid)
        bgm = worker.abs(pid, p["bgm_path"])
        if not bgm:
            raise ValueError("BGM（曲）を先に入れてください。")
        dur = render.media_duration(bgm)
        if not dur:
            raise ValueError("曲の長さを読み取れませんでした。")
        dur = min(180.0, dur)
        shots = store.shots(pid)
        if shots:
            k = dur / sum(s["seconds"] for s in shots)
            for s in shots:
                store.update_shot(s["id"], seconds=round(min(30, max(0.5, s["seconds"] * k)), 2))
        store.update_project(pid, duration_sec=int(round(dur)))
        store.set_stage(pid, "storyboard", p["stages"]["storyboard"] if p["stages"]["storyboard"] != "todo" else "todo", invalidate_after=True)
        store.log(pid, "sound", f"カットの秒数を曲の長さ（{dur:.1f}秒）に合わせました。")
        return jsonify(full(pid))

    # ── アップロード・ファイル ─────────────────────────────

    @app.post("/api/upload/<kind>/<oid>")
    def upload(kind, oid):
        f = request.files.get("file")
        if not f:
            raise ValueError("ファイルを選んでください。")
        data = f.read()
        if kind == "bgm":
            p = project_or_404(oid)
            ext = art.check_audio(data, f.filename)
            rel = f"audio/bgm_{new_id()[:8]}{ext}"
            (worker.pdir(oid) / "audio").mkdir(exist_ok=True)
            (worker.pdir(oid) / rel).write_bytes(data)
            old = worker.abs(oid, p["bgm_path"])
            if old:
                old.unlink(missing_ok=True)
            store.update_project(oid, bgm_path=rel)
            store.log(oid, "sound", f"BGM「{Path(f.filename).name[:60]}」を入れました。")
            return jsonify(full(oid))
        ext = art.check_image(data, f.filename)
        if kind == "character":
            c = store.get_character(oid) or abort(404)
            if c["project_id"] is None:  # ライブラリ
                (data_dir / "library").mkdir(exist_ok=True)
                name = f"{oid}_{new_id()[:8]}{ext}"
                (data_dir / "library" / name).write_bytes(data)
                if c["image_path"]:
                    (data_dir / "library" / c["image_path"]).unlink(missing_ok=True)
                return jsonify(store.update_character(oid, image_path=name))
            pid, folder, setter = c["project_id"], "chars", lambda rel: store.update_character(oid, image_path=rel)
            stage, old = "characters", c["image_path"]
        elif kind == "scene":
            sc = store.get_scene(oid) or abort(404)
            pid, folder, setter = sc["project_id"], "scenes", lambda rel: store.update_scene(oid, image_path=rel)
            stage, old = "scenes", sc["image_path"]
        elif kind == "shot":
            sh = store.get_shot(oid) or abort(404)
            pid, folder, setter = sh["project_id"], "shots", lambda rel: store.update_shot(oid, image_path=rel, image_source="upload", video_path="")
            stage, old = "art", sh["image_path"]
        else:
            abort(404)
        rel = f"{folder}/{oid}_{new_id()[:8]}{ext}"
        (worker.pdir(pid) / folder).mkdir(exist_ok=True)
        (worker.pdir(pid) / rel).write_bytes(data)
        o = worker.abs(pid, old)
        if o and old != rel:
            o.unlink(missing_ok=True)
        out = setter(rel)
        mark_edited(pid, stage)
        return jsonify(out)

    @app.post("/api/shots/<sid>/clear-image")
    def clear_shot_image(sid):
        sh = store.get_shot(sid) or abort(404)
        o = worker.abs(sh["project_id"], sh["image_path"])
        if o:
            o.unlink(missing_ok=True)
        store.update_shot(sid, image_path="", image_source="", video_path="")
        mark_edited(sh["project_id"], "art")
        return jsonify(ok=True)

    @app.get("/files/<pid>/<path:rel>")
    def files(pid, rel):
        if pid == "library":
            base = (data_dir / "library").resolve()
            p = (base / rel).resolve()
            if not p.is_relative_to(base) or not p.is_file():
                abort(404)
        else:
            if not store.get_project(pid):
                abort(404)
            p = worker.abs(pid, rel)
            if not p or not p.is_file():
                abort(404)
        dl = request.args.get("download") == "1"
        name = None
        if dl:
            proj = store.get_project(pid)
            name = f"{(proj or {}).get('title') or 'komadori'}.mp4"
        resp = send_file(p, as_attachment=dl, download_name=name, conditional=True)
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ── 設定 ────────────────────────────────────────────

    @app.post("/api/settings")
    def save_settings():
        d = body()
        allowed = {
            "ai_engine": ("auto", "ollama", "simple", "claude"), "image_engine": ("placeholder", "fal"),
            "video_engine": ("camera", "fal"), "voice_engine": ("say", "none"), "subtitles": ("0", "1"),
        }
        out = {}
        for k, v in d.items():
            if k not in DEFAULT_SETTINGS:
                continue
            v = str(v).strip()
            if k in allowed and v not in allowed[k]:
                raise ValueError(f"{k} の値が正しくありません。")
            if k in ("monthly_budget_jpy", "fal_image_yen", "fal_video_yen_per_sec", "chars_per_second"):
                try:
                    if float(v) < 0:
                        raise ValueError
                except ValueError:
                    raise ValueError("数字で入れてください。") from None
            out[k] = v[:200]
        return jsonify(store.save_settings(out))

    return app
