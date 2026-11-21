"""コマドリ（tools/anime_studio）のテスト。テスト計画は replica/anime/test-plan.md。

    python3 -m pytest tests/test_anime_studio.py
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.anime_studio import engine, render  # noqa: E402
from tools.anime_studio.app import create_app  # noqa: E402
from tools.anime_studio.store import Store  # noqa: E402

BASE = "http://127.0.0.1:5056"
H = {"X-Komadori": "1"}
IDEA = ("あまりんは歌うのが大好き。でも人前だと緊張してしまう。あまりん「今日こそ、最後まで歌う！」"
        "配信を始めると、みんなのコメントが背中を押してくれた。さな：がんばれ！最後は笑顔で歌いきった。")


def png_bytes(size=(64, 96), color=(200, 80, 120, 255)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture()
def app(tmp_path):
    a = create_app(tmp_path, start_worker=False, short_side=240)
    a.extensions["k_store"].save_settings({"ai_engine": "simple", "voice_engine": "none"})
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


def call(client, method, url, **kw):
    kw.setdefault("base_url", BASE)
    headers = {**H, **kw.pop("headers", {})}
    return client.open(url, method=method, headers=headers, **kw)


def drain(app):
    """キューにあるジョブを全部この場で実行する（バックグラウンドのスレッドの代わり）。"""
    w, st = app.extensions["k_worker"], app.extensions["k_store"]
    for _ in range(30):
        jobs = st.queued_jobs()
        if not jobs:
            return
        w.run_job(jobs[0])
    raise AssertionError("ジョブが終わりません")


def make_project(client, **extra) -> str:
    r = call(client, "POST", "/api/projects", json={"idea": IDEA, "duration_sec": 12, "aspect": "9:16", **extra})
    assert r.status_code == 200, r.get_json()
    return r.get_json()["id"]


def approve(client, app, pid, stage):
    r = call(client, "POST", f"/api/projects/{pid}/stages/{stage}/approve")
    assert r.status_code == 200, r.get_json()
    drain(app)


def get(client, pid) -> dict:
    return call(client, "GET", f"/api/projects/{pid}").get_json()


# ── 文章（AIなし） ─────────────────────────────────────────

def test_sentences_keep_quotes_together():
    s = engine._sentences("あ。あまりん「今日こそ！最後まで！」次へ。さな：がんばれ！")
    assert s == ["あ。", "あまりん「今日こそ！最後まで！」", "次へ。", "さな：がんばれ！"]


def test_simple_script_detects_speakers_and_scenes():
    sc = engine.simple_script({"idea": IDEA})
    lines = [l for s in sc["scenes"] for l in s["lines"]]
    assert {"speaker": "あまりん", "text": "今日こそ、最後まで歌う！"} in lines
    assert {"speaker": "さな", "text": "がんばれ！"} in lines
    assert len(sc["scenes"]) == 3
    assert sc["title"] == "あまりんは歌うのが大好き"


def test_simple_script_rejects_empty():
    with pytest.raises(engine.EngineError):
        engine.simple_script({"idea": "   "})


def test_simple_characters_default_and_honorific():
    p = {"idea": "ゆうくんとみかちゃんが公園で遊ぶ。", "script": engine.simple_script({"idea": "ゆうくんとみかちゃんが公園で遊ぶ。"})}
    names = [c["name"] for c in engine.simple_characters(p)]
    assert "ゆうくん" in names and "みかちゃん" in names
    assert [c["name"] for c in engine.simple_characters({"idea": "空が青い。", "script": {"scenes": []}})] == ["主人公"]


def test_fit_seconds_matches_total():
    shots = [{"seconds": 0, "dialogue": "あ" * n} for n in (4, 20, 40)]
    out = engine.fit_seconds(shots, 15)
    assert abs(sum(s["seconds"] for s in out) - 15) < 0.3
    assert out[2]["seconds"] > out[0]["seconds"]


def test_check_shots_warns_long_dialogue_and_total():
    p = {"duration_sec": 30}
    w = engine.check_shots(p, [{"seconds": 2, "dialogue": "あ" * 30}], {"chars_per_second": "8"})
    assert any("セリフが長すぎ" in x for x in w) and any("合計の尺" in x for x in w)


def test_resolve_engine_never_picks_claude_automatically(monkeypatch):
    monkeypatch.setattr(engine.local_ai, "ollama_models", lambda *a, **k: None)
    assert engine.resolve_engine({"ai_engine": "auto"}) == "simple"
    assert engine.resolve_engine({"ai_engine": "claude"}) == "claude"


# ── Claude（偽物）で脚本・絵コンテ ───────────────────────────

class FakeClaude:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        text = json.dumps(self.replies.pop(0), ensure_ascii=False)
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def test_claude_script_and_storyboard_are_normalized():
    fake = FakeClaude([
        {"title": "初ライブ", "logline": "緊張を越える", "scenes": [{"place": "部屋", "summary": "準備", "lines": [{"speaker": "あまりん", "text": "いくよ！"}]}]},
        {"shots": [{"seconds": 3, "scene": "部屋", "characters": ["あまりん", "知らない人"], "camera": "dolly", "action": "構える",
                    "speaker": "あまりん", "dialogue": "いくよ！", "caption": "", "image_prompt": "girl with mic"}]},
    ])
    p = {"idea": "x", "kind": "story", "style": "anime", "aspect": "9:16", "duration_sec": 6, "script": {}}
    s = engine.gen_script(p, {"chars_per_second": "8"}, "明るく", client=fake, engine="claude")
    assert s["title"] == "初ライブ" and s["scenes"][0]["lines"][0]["speaker"] == "あまりん"
    assert "明るく" in fake.calls[0]["messages"][0]["content"]
    assert fake.calls[0]["output_config"]["format"]["type"] == "json_schema"
    p["script"] = s
    shots = engine.gen_storyboard(p, {"chars_per_second": "8"}, [{"name": "あまりん", "look": ""}],
                                  [{"id": "sc1", "name": "部屋", "description": ""}], client=fake, engine="claude")
    assert shots[0]["characters"] == ["あまりん"]  # 一覧にない名前は落とす
    assert shots[0]["camera"] == "still"           # 知らないカメラは固定に
    assert shots[0]["scene_id"] == "sc1"
    assert shots[0]["seconds"] == 6


def test_claude_broken_json_fails_with_message():
    fake = FakeClaude(["not json", "still not"])
    fake.create = lambda **kw: SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="こんにちは")])
    with pytest.raises(engine.EngineError, match="読み取れません"):
        engine.gen_script({"idea": "x", "duration_sec": 10}, {}, client=fake, engine="claude")


# ── 守り ──────────────────────────────────────────────────

def test_rejects_other_hosts_and_missing_header(client):
    assert client.get("/", base_url="http://evil.example").status_code == 403
    r = client.post("/api/projects", json={"idea": "x"}, base_url=BASE)  # ヘッダーなし
    assert r.status_code == 403


def test_create_project_validation(client):
    assert call(client, "POST", "/api/projects", json={"idea": "  "}).status_code == 400
    assert call(client, "POST", "/api/projects", json={"idea": "あ" * 8001}).status_code == 400
    r = call(client, "POST", "/api/projects", json={"idea": "絵文字🎤とアクセントé", "aspect": "4:3", "kind": "x", "duration_sec": 9999})
    p = get(client, r.get_json()["id"])
    assert p["aspect"] == "9:16" and p["kind"] == "story" and p["duration_sec"] == 180


def test_files_route_blocks_traversal(client, app, tmp_path):
    pid = make_project(client)
    (tmp_path / "secret.txt").write_text("x")
    assert call(client, "GET", f"/files/{pid}/../../secret.txt").status_code == 404
    assert call(client, "GET", "/files/library/../komadori.db").status_code == 404


# ── コアループ（F01） ───────────────────────────────────────

def test_full_flow_to_mp4(client, app):
    pid = make_project(client)
    drain(app)
    p = get(client, pid)
    assert p["stages"]["script"] == "review"
    for st in ("script", "characters", "scenes", "storyboard", "art", "sound"):
        approve(client, app, pid, st)
    p = get(client, pid)
    assert p["stages"]["render"] == "approved", p["logs"][-1]
    assert p["render_url"]
    path = app.extensions["k_worker"].abs(pid, p["render_path"])
    assert path.stat().st_size > 1000
    dur = render.media_duration(path)
    assert abs(dur - p["total_seconds"]) < 0.5
    out = subprocess.run([render.ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    assert "Video: h264" in out and "Audio: aac" in out
    r = call(client, "GET", p["render_url"].split("?")[0] + "?download=1")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]


def test_auto_mode_runs_to_the_end(client, app):
    pid = make_project(client, auto=True)
    drain(app)
    p = get(client, pid)
    assert all(v == "approved" for v in p["stages"].values()), p["stages"]


def test_double_generate_is_refused(client, app):
    pid = make_project(client)
    r = call(client, "POST", f"/api/projects/{pid}/stages/script/generate", json={})
    assert r.status_code == 400 and "途中" in r.get_json()["error"]


# ── 直す（F03・F04） ───────────────────────────────────────

def test_editing_script_marks_later_stages_stale(client, app):
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters"):
        approve(client, app, pid, st)
    p = get(client, pid)
    script = p["script"]
    script["scenes"][0]["lines"][0]["text"] = "書き換えた"
    r = call(client, "PATCH", f"/api/projects/{pid}", json={"script": script})
    assert r.status_code == 200
    st = get(client, pid)["stages"]
    assert st["script"] == "approved" and st["characters"] == "stale" and st["scenes"] == "stale"


def test_shot_edit_reorder_add_delete(client, app):
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters", "scenes"):
        approve(client, app, pid, st)
    shots = get(client, pid)["shots"]
    ids = [s["id"] for s in shots]
    assert call(client, "POST", f"/api/projects/{pid}/shots/reorder", json={"ids": ids[:-1]}).status_code == 400
    rev = list(reversed(ids))
    assert call(client, "POST", f"/api/projects/{pid}/shots/reorder", json={"ids": rev}).status_code == 200
    assert [s["id"] for s in get(client, pid)["shots"]] == rev
    new = call(client, "POST", f"/api/projects/{pid}/shots", json={"after": rev[0], "seconds": 2}).get_json()
    assert get(client, pid)["shots"][1]["id"] == new["id"]
    assert call(client, "PATCH", f"/api/shots/{new['id']}", json={"seconds": "abc"}).status_code == 400
    assert call(client, "PATCH", f"/api/shots/{new['id']}", json={"seconds": 99, "camera": "bogus"}).get_json()["seconds"] == 30
    assert call(client, "DELETE", f"/api/shots/{new['id']}").status_code == 200
    assert len(get(client, pid)["shots"]) == len(ids)


def test_renaming_character_updates_shots(client, app):
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters", "scenes"):
        approve(client, app, pid, st)
    c = next(c for c in get(client, pid)["characters"] if c["name"] == "さな")
    call(client, "PATCH", f"/api/characters/{c['id']}", json={"name": "さなちゃん"})
    shots = get(client, pid)["shots"]
    assert any(s["speaker"] == "さなちゃん" for s in shots)
    assert not any("さな" in s["characters"] for s in shots)


# ── 画像（F05・F06） ──────────────────────────────────────

def test_uploads_are_checked_and_kept_on_regenerate(client, app):
    pid = make_project(client)
    drain(app)
    approve(client, app, pid, "script")
    c = get(client, pid)["characters"][0]
    bad = call(client, "POST", f"/api/upload/character/{c['id']}", data={"file": (io.BytesIO(b"hello"), "a.png")})
    assert bad.status_code == 400
    bad = call(client, "POST", f"/api/upload/character/{c['id']}", data={"file": (io.BytesIO(png_bytes()), "a.exe")})
    assert bad.status_code == 400
    ok = call(client, "POST", f"/api/upload/character/{c['id']}", data={"file": (io.BytesIO(png_bytes()), "a.png")})
    assert ok.status_code == 200 and ok.get_json()["image_path"]
    # キャラを作り直しても、同じ名前なら画像は残る
    call(client, "POST", f"/api/projects/{pid}/stages/characters/generate", json={})
    drain(app)
    again = next(x for x in get(client, pid)["characters"] if x["name"] == c["name"])
    assert again["image_url"]
    for st in ("characters", "scenes", "storyboard"):
        approve(client, app, pid, st)
    shot = get(client, pid)["shots"][0]
    call(client, "POST", f"/api/upload/shot/{shot['id']}", data={"file": (io.BytesIO(png_bytes((90, 160))), "mine.png")})
    call(client, "POST", f"/api/projects/{pid}/stages/art/generate", json={})
    drain(app)
    after = get(client, pid)["shots"][0]
    assert after["image_source"] == "upload"
    assert all(s["image_url"] for s in get(client, pid)["shots"])


def test_library_save_and_use_in_new_project(client, app):
    pid = make_project(client)
    drain(app)
    approve(client, app, pid, "script")
    c = get(client, pid)["characters"][0]
    call(client, "POST", f"/api/upload/character/{c['id']}", data={"file": (io.BytesIO(png_bytes()), "a.png")})
    lib = call(client, "PATCH", f"/api/characters/{c['id']}", json={"save_to_library": True}).get_json()
    assert lib["project_id"] is None and lib["image_path"]
    pid2 = make_project(client, library_ids=[lib["id"]])
    chars = get(client, pid2)["characters"]
    assert chars and chars[0]["name"] == c["name"] and chars[0]["image_url"]
    # キャラ帳から消しても作品のキャラは消えない
    call(client, "DELETE", f"/api/characters/{lib['id']}")
    assert get(client, pid2)["characters"]


# ── 音（F07） ───────────────────────────────────────────

def test_bgm_upload_and_fit(client, app, tmp_path):
    wav = tmp_path / "tone.wav"
    subprocess.run([render.ffmpeg_exe(), "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=7", str(wav)], check=True)
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters", "scenes"):
        approve(client, app, pid, st)
    assert call(client, "POST", f"/api/projects/{pid}/fit-to-bgm").status_code == 400
    assert call(client, "POST", f"/api/upload/bgm/{pid}", data={"file": (io.BytesIO(b"x" * 200), "a.txt")}).status_code == 400
    r = call(client, "POST", f"/api/upload/bgm/{pid}", data={"file": (io.BytesIO(wav.read_bytes()), "tone.wav")})
    assert r.status_code == 200 and r.get_json()["bgm_url"]
    p = call(client, "POST", f"/api/projects/{pid}/fit-to-bgm").get_json()
    assert abs(p["total_seconds"] - 7) < 0.3 and p["duration_sec"] == 7


# ── 費用・失敗・復旧 ────────────────────────────────────────

def test_fal_budget_stops_before_spending(client, app, monkeypatch):
    called = []
    monkeypatch.setattr("tools.anime_studio.art.fal_image", lambda *a, **k: called.append(a))
    app.extensions["k_store"].save_settings({"image_engine": "fal", "monthly_budget_jpy": "1", "fal_image_yen": "5"})
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters", "scenes", "storyboard"):
        approve(client, app, pid, st)
    p = get(client, pid)
    assert p["stages"]["art"] == "failed" and not called
    assert "上限" in p["jobs"][0]["error"]


def test_render_without_images_fails_with_reason(client, app):
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters", "scenes", "storyboard"):
        approve(client, app, pid, st)  # 絵コンテを承認すると絵も作られる
    first = get(client, pid)["shots"][0]
    assert call(client, "POST", f"/api/shots/{first['id']}/clear-image").status_code == 200
    call(client, "POST", f"/api/projects/{pid}/stages/render/generate", json={})
    drain(app)
    p = get(client, pid)
    assert p["stages"]["render"] == "failed"
    assert "絵がありません" in p["jobs"][0]["error"]


def test_recover_interrupted_jobs(tmp_path):
    st = Store(tmp_path / "k.db")
    p = st.create_project(idea="x")
    st.set_stage(p["id"], "script", "generating")
    j = st.add_job(p["id"], "script")
    st.set_job(j["id"], "running")
    assert st.recover_interrupted() == 1
    assert st.get_job(j["id"])["status"] == "failed"
    assert st.get_project(p["id"])["stages"]["script"] == "failed"


def test_delete_project_removes_files(client, app, tmp_path):
    pid = make_project(client)
    drain(app)
    call(client, "POST", f"/api/upload/bgm/{pid}", data={"file": (io.BytesIO(b"x" * 300), "a.mp3")})
    assert (tmp_path / "projects" / pid).exists()
    assert call(client, "DELETE", f"/api/projects/{pid}").status_code == 200
    assert not (tmp_path / "projects" / pid).exists()
    assert call(client, "GET", f"/api/projects/{pid}").status_code == 404


def test_pages_render(client, app):
    pid = make_project(client)
    for url in ("/", "/new", f"/p/{pid}", "/library", "/settings", "/design"):
        assert call(client, "GET", url).status_code == 200, url
    assert call(client, "GET", "/p/nope").status_code == 404


def test_settings_validation(client):
    assert call(client, "POST", "/api/settings", json={"image_engine": "midjourney"}).status_code == 400
    assert call(client, "POST", "/api/settings", json={"monthly_budget_jpy": "-1"}).status_code == 400
    assert call(client, "POST", "/api/settings", json={"monthly_budget_jpy": "500"}).get_json()["monthly_budget_jpy"] == "500"
