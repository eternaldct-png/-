"""main.py に告知が正しく組み込まれているか"""
import io
import json
from contextlib import redirect_stdout
from unittest import mock

import pytest

import main
import promo

PERSONA = "persona/kazuto_config.yaml"


def set_counter(state_path, n):
    state_path.write_text(
        json.dumps({"posts_since_promo": n, "recent_combos": []}), encoding="utf-8"
    )


def every_n():
    return promo.load_promo_config()["every_n_posts"]


@pytest.fixture
def no_generation():
    """
    コンテンツ生成に入ったら分かるようにする。
    告知回では生成が走らない（＝Claude API の費用がかからない）ことを検証したい。
    """
    return mock.patch("main.build_research_context", side_effect=RuntimeError("生成に到達"))


def test_カウンター未達なら通常の生成に進む(promo_state, no_generation):
    set_counter(promo_state, 0)
    buf = io.StringIO()

    with no_generation, pytest.raises(RuntimeError, match="生成に到達"):
        with redirect_stdout(buf):
            main.run(dry_run=True, platform="x", persona_path=PERSONA)

    assert "診断ページの告知" not in buf.getvalue()


def test_カウンター到達で告知に差し替わる(promo_state, no_generation):
    set_counter(promo_state, every_n())
    buf = io.StringIO()

    # 生成に入ったら RuntimeError で落ちる = 告知回は生成しない、が確認できる
    with no_generation:
        with redirect_stdout(buf):
            main.run(dry_run=True, platform="x", persona_path=PERSONA)

    out = buf.getvalue()
    assert "今回は診断ページの告知を投稿します" in out
    assert "/diagnosis/" in out


def test_ドライランではカウンターを進めない(promo_state, no_generation):
    set_counter(promo_state, every_n())

    with no_generation:
        with redirect_stdout(io.StringIO()):
            main.run(dry_run=True, platform="x", persona_path=PERSONA)

    state = json.loads(promo_state.read_text(encoding="utf-8"))
    assert state["posts_since_promo"] == every_n()


def test_投稿成功でカウンターがリセットされる(promo_state, no_generation):
    set_counter(promo_state, every_n())
    posted = {"platform_id": "999", "text": "x", "timestamp": "t", "status": "posted"}

    with no_generation, mock.patch("platforms.x.XAdapter.post", return_value=posted):
        with redirect_stdout(io.StringIO()):
            main.run(dry_run=False, platform="x", persona_path=PERSONA)

    state = json.loads(promo_state.read_text(encoding="utf-8"))
    assert state["posts_since_promo"] == 0
    assert len(state["recent_combos"]) == 1


def test_重複スキップ時はカウンターを進めない(promo_state, no_generation):
    set_counter(promo_state, every_n())
    skipped = {"platform_id": "skipped_duplicate", "text": "x", "timestamp": "t", "status": "skipped"}

    with no_generation, mock.patch("platforms.x.XAdapter.post", return_value=skipped):
        with redirect_stdout(io.StringIO()):
            main.run(dry_run=False, platform="x", persona_path=PERSONA)

    state = json.loads(promo_state.read_text(encoding="utf-8"))
    assert state["posts_since_promo"] == every_n(), "投稿できていないのに機会を消費しています"
