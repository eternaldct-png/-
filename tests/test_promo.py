"""自動投稿に挟む診断告知のロジック"""
import json

import pytest

import promo


def set_counter(state_path, n, recent=None):
    state_path.write_text(
        json.dumps({"posts_since_promo": n, "recent_combos": recent or []}),
        encoding="utf-8",
    )


# ── 対象プラットフォーム ──────────────────────────────────────────

def test_Xでのみ有効(promo_state):
    assert promo.is_enabled("x")
    # Instagram はキャプションのリンクが押せず、note/TikTok は記事・台本
    for platform in ("instagram", "note", "tiktok"):
        assert not promo.is_enabled(platform), f"{platform} で告知が有効になっています"


def test_設定で完全に止められる(promo_state, monkeypatch):
    original = promo.load_promo_config()
    monkeypatch.setattr(promo, "load_promo_config", lambda: {**original, "enabled": False})

    assert not promo.should_post_promo("x")
    assert promo.build_promo_post("x") is None


def test_base_urlがなければ投稿しない(promo_state, monkeypatch):
    original = promo.load_promo_config()
    monkeypatch.setattr(promo, "load_promo_config", lambda: {**original, "base_url": ""})

    assert promo.build_promo_post("x") is None


# ── 頻度 ─────────────────────────────────────────────────────────

def test_通常投稿N件ごとに1回だけ挟む(promo_state):
    every_n = promo.load_promo_config()["every_n_posts"]
    timeline = []

    for _ in range(every_n * 3 + 3):
        if promo.should_post_promo("x"):
            item = promo.build_promo_post("x")
            timeline.append("告知")
            promo.record_post("x", was_promo=True, combo_key=item["combo_key"])
        else:
            timeline.append("通常")
            promo.record_post("x", was_promo=False)

    positions = [i for i, kind in enumerate(timeline) if kind == "告知"]
    gaps = [b - a for a, b in zip(positions, positions[1:])]
    assert gaps, "一度も告知が発火していません"
    assert all(gap == every_n + 1 for gap in gaps), f"間隔が一定ではありません: {gaps}"


def test_投稿できなかった回は次に持ち越す(promo_state):
    """重複などで投稿が飛んだ回にカウンターを進めると、告知の機会が失われる"""
    every_n = promo.load_promo_config()["every_n_posts"]
    set_counter(promo_state, every_n)

    assert promo.should_post_promo("x")
    # record_post を呼ばない = 投稿できなかった
    assert promo.should_post_promo("x"), "投稿していないのに機会が消えています"


# ── 文面 ─────────────────────────────────────────────────────────

def test_連続する告知で文面が重複しない(promo_state):
    seen = []
    for _ in range(6):
        item = promo.build_promo_post("x")
        seen.append(item["combo_key"])
        promo.record_post("x", was_promo=True, combo_key=item["combo_key"])

    assert len(set(seen)) == len(seen), f"同じ文面が使い回されています: {seen}"


def test_診断が交互に宣伝される(promo_state):
    """片方の診断ばかり宣伝すると、もう片方に人が流れない"""
    quiz_ids = []
    for _ in range(4):
        item = promo.build_promo_post("x")
        quiz_ids.append(item["combo_key"].split(":")[0])
        promo.record_post("x", was_promo=True, combo_key=item["combo_key"])

    if len(promo.load_promo_config().get("templates", [])) > 1:
        assert len(set(quiz_ids)) > 1, f"同じ診断ばかり宣伝しています: {quiz_ids}"


def test_投稿文が組み立てられている(promo_state):
    import diagnosis

    base_url = promo.load_promo_config()["base_url"].rstrip("/")
    valid_urls = {f"{base_url}/diagnosis/{q['id']}" for q in diagnosis.load_config()["quizzes"]}

    for _ in range(5):
        item = promo.build_promo_post("x")
        text = item["text"]

        assert "{" not in text and "}" not in text, f"未置換のプレースホルダ: {text}"
        assert any(url in text for url in valid_urls), f"診断URLが入っていません: {text}"
        assert len(text) <= 280, f"X の上限280字を超えています（{len(text)}字）"
        promo.record_post("x", was_promo=True, combo_key=item["combo_key"])


def test_投稿済みの文面は避ける(promo_state):
    first = promo.build_promo_post("x")
    second = promo.build_promo_post("x", is_duplicate=lambda t: t == first["text"])

    assert second is not None
    assert second["text"] != first["text"]


def test_全部投稿済みなら告知を見送る(promo_state):
    """出せる文面が尽きたときに、重複投稿を強行しない"""
    assert promo.build_promo_post("x", is_duplicate=lambda t: True) is None


# ── 状態ファイル ──────────────────────────────────────────────────

def test_壊れた状態ファイルでも落ちない(promo_state):
    promo_state.write_text("{壊れたJSON", encoding="utf-8")
    assert promo.build_promo_post("x") is not None


def test_告知後にカウンターがリセットされる(promo_state):
    every_n = promo.load_promo_config()["every_n_posts"]
    set_counter(promo_state, every_n)

    item = promo.build_promo_post("x")
    promo.record_post("x", was_promo=True, combo_key=item["combo_key"])

    state = json.loads(promo_state.read_text(encoding="utf-8"))
    assert state["posts_since_promo"] == 0
    assert item["combo_key"] in state["recent_combos"]
