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
    assert p["aspect"] == "9:16" and p["kind"] == "story" and p["duration_sec"] == 600


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


# ── 口コミの不満への対応（replica/anime/fixes.md） ─────────────────────

def to_storyboard(client, app, pid):
    drain(app)
    for st in ("script", "characters", "scenes", "storyboard"):
        approve(client, app, pid, st)  # 絵コンテを承認すると絵も作られる


def test_fix_rules_are_sent_to_ai_every_time(client, app):
    """FX1: いつもの決まりごと＋作品の決まりごとが、毎回AIに最優先で渡る（指示より流れが優先される・記憶がない）。"""
    fake = FakeClaude([{"title": "t", "logline": "l", "scenes": [{"place": "部屋", "summary": "s", "lines": [{"speaker": "あまりん", "text": "やで"}]}]}])
    app.extensions["k_worker"].ai_client = fake
    app.extensions["k_store"].save_settings({"ai_engine": "claude", "house_rules": "悪口は入れない"})
    pid = make_project(client, notes="あまりんは関西弁")
    drain(app)
    sent = fake.calls[0]["messages"][0]["content"]
    assert "必ず守る決まりごと" in sent and "悪口は入れない" in sent and "あまりんは関西弁" in sent
    assert "決まり文句" in fake.calls[0]["system"]
    r = call(client, "PATCH", f"/api/projects/{pid}", json={"notes": "標準語にする"})
    assert r.get_json()["notes"] == "標準語にする"


def test_fix_rewrite_one_shot_only(client, app):
    """FX2: 1カットだけAIで直せる。ほかのカットは変わらない。AIなしモードでは理由つきで断る。"""
    pid = make_project(client)
    to_storyboard(client, app, pid)
    shots = get(client, pid)["shots"]
    r = call(client, "POST", f"/api/shots/{shots[1]['id']}/rewrite", json={"note": "驚いた顔に"})
    assert r.status_code == 400 and "AIなし" in r.get_json()["error"]
    fake = FakeClaude([{"seconds": 2, "scene": "なかほど", "characters": ["あまりん"], "camera": "zoom_in", "action": "驚く",
                        "speaker": "あまりん", "dialogue": "えっ！", "caption": "", "image_prompt": "surprised"}])
    app.extensions["k_worker"].ai_client = fake
    app.extensions["k_store"].save_settings({"ai_engine": "claude"})
    assert call(client, "POST", f"/api/shots/{shots[1]['id']}/rewrite", json={"note": "驚いた顔に"}).status_code == 200
    drain(app)
    after = get(client, pid)["shots"]
    assert after[1]["dialogue"] == "えっ！" and after[1]["camera"] == "zoom_in"
    assert [s["dialogue"] for i, s in enumerate(after) if i != 1] == [s["dialogue"] for i, s in enumerate(shots) if i != 1]
    assert "驚いた顔に" in fake.calls[0]["messages"][0]["content"]


def test_fix_regenerate_one_image_only(client, app):
    """FX2: この絵だけ作り直す。ほかのカットの絵はそのまま。"""
    pid = make_project(client)
    to_storyboard(client, app, pid)
    before = {s["id"]: s["image_path"] for s in get(client, pid)["shots"]}
    target = next(iter(before))
    assert call(client, "POST", f"/api/shots/{target}/regenerate-image", json={"note": "もっと明るく"}).status_code == 200
    drain(app)
    after = {s["id"]: s["image_path"] for s in get(client, pid)["shots"]}
    assert after[target] != before[target]
    assert all(after[k] == v for k, v in before.items() if k != target)
    assert get(client, pid)["stages"]["sound"] in ("todo", "stale", "generating", "review")


def test_fix_one_failed_shot_does_not_stop_others_and_retry_only_missing(client, app, monkeypatch):
    """FX3: 1カットの失敗で全部を止めない。失敗したカットだけやり直せる（できたカットの分は二度払わない）。"""
    from tools.anime_studio import art
    calls = []

    def fake_fal(model, prompt, size, dest, seed=None):
        calls.append(prompt)
        if len(calls) == 2:
            raise art.ArtError("fal.ai がエラーを返しました: 500")
        from PIL import Image
        Image.new("RGB", size, (10, 20, 30)).save(dest)
        return dest

    monkeypatch.setattr(art, "fal_image", fake_fal)
    monkeypatch.setattr(art, "fal_key", lambda: "x")
    app.extensions["k_store"].save_settings({"image_engine": "fal", "monthly_budget_jpy": "0", "fal_image_yen": "3"})
    pid = make_project(client)
    to_storyboard(client, app, pid)
    p = get(client, pid)
    n = len(p["shots"])
    assert p["stages"]["art"] == "review"  # 1カット失敗しても段階は止まらない
    failed = [s for s in p["shots"] if s["error"]]
    assert len(failed) == 1 and len(calls) == n
    assert p["cost"]["missing_count"] == 1 and p["cost"]["missing"] == 3
    assert any("失敗" in l["text"] for l in p["logs"])
    call(client, "POST", f"/api/projects/{pid}/stages/art/generate", json={"only_missing": True})
    drain(app)
    p = get(client, pid)
    assert len(calls) == n + 1  # 失敗した1カットだけ作り直した
    assert not any(s["error"] for s in p["shots"])
    assert app.extensions["k_store"].spend_since("2000") == pytest.approx(3 * n)  # 失敗した分は数えない


def test_fix_consistency_prompt_and_seed(client, app, monkeypatch):
    """FX4: AI画像のプロンプトに毎回キャラの見た目・背景を入れ、作品ごとに同じ種を使う。足りなければ警告。"""
    from tools.anime_studio import art
    got = []

    def fake_fal(model, prompt, size, dest, seed=None):
        got.append((prompt, seed))
        from PIL import Image
        Image.new("RGB", size).save(dest)
        return dest

    monkeypatch.setattr(art, "fal_image", fake_fal)
    pid = make_project(client)
    drain(app)
    for st in ("script", "characters", "scenes"):
        approve(client, app, pid, st)
    p = get(client, pid)
    assert any("画像も見た目の説明もありません" in w for w in p["consistency"])
    c = next(c for c in p["characters"] if c["name"] == "あまりん")
    call(client, "PATCH", f"/api/characters/{c['id']}", json={"look": "pink twin tails, purple hoodie"})
    app.extensions["k_store"].save_settings({"image_engine": "fal", "monthly_budget_jpy": "0"})
    approve(client, app, pid, "storyboard")
    prompts = [g[0] for g in got]
    assert any("pink twin tails, purple hoodie" in x for x in prompts)
    assert len({g[1] for g in got}) == 1 and got[0][1] is not None


def test_fix_cost_estimate_shown_before_paid_generation(client, app):
    """FX5: 有料の設定なら、押す前に見積もりが出る。無料の設定なら 0 円。"""
    pid = make_project(client)
    to_storyboard(client, app, pid)
    assert get(client, pid)["cost"]["paid"] is False
    app.extensions["k_store"].save_settings({"image_engine": "fal", "fal_image_yen": "4", "video_engine": "fal", "fal_video_yen_per_sec": "2"})
    c = get(client, pid)["cost"]
    shots = get(client, pid)["shots"]
    expected = len(shots) * 4 + sum((10 if s["seconds"] > 5 else 5) * 2 for s in shots)
    assert c["paid"] is True and c["all"] == expected


def test_fix_sequel_keeps_characters_rules_and_story(client, app):
    """FX6: 続きを作る。キャラ（画像も）・決まりごと・前の回のあらすじを引きつぐ。尺は600秒まで。"""
    fake = FakeClaude([
        {"title": "第1話", "logline": "はじまり", "scenes": [{"place": "部屋", "summary": "歌の練習", "lines": [{"speaker": "あまりん", "text": "いくよ"}]}]},
        {"characters": [{"name": "あまりん", "look": "pink hair", "personality": "元気"}]},
        {"title": "第2話", "logline": "つづき", "scenes": [{"place": "ステージ", "summary": "本番", "lines": [{"speaker": "あまりん", "text": "本番だ"}]}]},
    ])
    app.extensions["k_worker"].ai_client = fake
    app.extensions["k_store"].save_settings({"ai_engine": "claude"})
    pid = make_project(client, notes="関西弁")
    drain(app)
    approve(client, app, pid, "script")
    c = get(client, pid)["characters"][0]
    call(client, "POST", f"/api/upload/character/{c['id']}", data={"file": (io.BytesIO(png_bytes()), "a.png")})
    r = call(client, "POST", "/api/projects", json={"idea": "本番の日", "sequel_of": pid, "duration_sec": 600})
    pid2 = r.get_json()["id"]
    drain(app)
    p2 = get(client, pid2)
    assert p2["notes"] == "関西弁" and p2["duration_sec"] == 600 and p2["sequel_of"] == pid
    assert p2["characters"][0]["name"] == "あまりん" and p2["characters"][0]["image_url"]
    sent = fake.calls[-1]["messages"][0]["content"]
    assert "前の回のあらすじ" in sent and "歌の練習" in sent
    assert call(client, "GET", f"/new?from={pid}").status_code == 200


def test_fix_similar_idea_warning(client, app):
    """FX7: 前の作品とアイデアがほぼ同じなら知らせる（似た動画ばかりになる）。"""
    make_project(client)
    pid2 = make_project(client)
    assert any("よく似ています" in l["text"] for l in get(client, pid2)["logs"])


def test_fix_recorded_voice_replaces_tts(client, app, tmp_path):
    """FX8: 読み上げが不自然なカットは、自分で録った声に差し替えられる（書き出しに入る）。"""
    wav = tmp_path / "v.wav"
    subprocess.run([render.ffmpeg_exe(), "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=1", str(wav)], check=True)
    pid = make_project(client)
    to_storyboard(client, app, pid)
    sh = get(client, pid)["shots"][0]
    assert call(client, "POST", f"/api/upload/voice/{sh['id']}", data={"file": (io.BytesIO(b"x" * 10), "v.exe")}).status_code == 400
    r = call(client, "POST", f"/api/upload/voice/{sh['id']}", data={"file": (io.BytesIO(wav.read_bytes()), "v.wav")})
    assert r.status_code == 200 and r.get_json()["voice_path"]
    w = app.extensions["k_worker"]
    assert sh["id"] in w.voice_files(pid)
    for st in ("art", "sound"):
        approve(client, app, pid, st)
    p = get(client, pid)
    assert p["stages"]["render"] == "approved"
    assert call(client, "POST", f"/api/shots/{sh['id']}/clear-voice").status_code == 200
    assert sh["id"] not in w.voice_files(pid)
    c = p["characters"][0]
    assert call(client, "PATCH", f"/api/characters/{c['id']}", json={"voice_rate": "abc"}).status_code == 400
    assert call(client, "PATCH", f"/api/characters/{c['id']}", json={"voice_rate": 999}).get_json()["voice_rate"] == 400


def test_fix_preflight_checklist(client, app):
    """FX9: 書き出す前の確認（自動の確認＋BGMの権利・出演の了承）。"""
    pid = make_project(client)
    to_storyboard(client, app, pid)
    pf = {i["key"]: i for i in get(client, pid)["preflight"]}
    assert pf["images"]["ok"] and not pf["stages"]["ok"] and not pf["cast_ok"]["ok"]
    call(client, "PATCH", f"/api/projects/{pid}", json={"checks": {"cast_ok": True, "evil": True}})
    p = get(client, pid)
    assert {i["key"]: i for i in p["preflight"]}["cast_ok"]["ok"] and "evil" not in p["checks"]


def test_fix_old_database_gets_new_columns(tmp_path):
    """古い DB（列が足りない）でも起動できる。"""
    import sqlite3
    db = tmp_path / "old.db"
    c = sqlite3.connect(db)
    c.executescript((Path(__file__).resolve().parents[1] / "tools/anime_studio/schema.sql").read_text())
    c.execute("INSERT INTO projects(id, created_at, updated_at) VALUES('p1', 'x', 'x')")
    c.commit()
    c.close()
    st = Store(db)
    assert st.get_project("p1")["notes"] == ""
