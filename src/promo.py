"""
診断ページの告知投稿（src/main.py から利用）

既存の投稿文に URL を継ぎ足すと、140字前提で組み立てた文章が壊れるうえ、
無関係な話題に広告がぶら下がって読み味が悪くなる。そのため告知は
「通常投稿を N 件出したら 1 回だけ挟む独立した投稿」として扱う。

設定は persona/diagnosis_config.yaml の promo セクション。
"""
import json
from pathlib import Path

STATE_PATH = Path("posts/promo_state.json")

DEFAULT_EVERY_N = 6
# 直近この件数の組み合わせは選ばない（同じ文面が続くのを防ぐ）
RECENT_MEMORY = 6


def load_promo_config() -> dict:
    """diagnosis_config.yaml の promo セクションを読み込む"""
    from diagnosis import load_config

    return load_config().get("promo", {}) or {}


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"posts_since_promo": 0, "recent_combos": []}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"posts_since_promo": 0, "recent_combos": []}
    state.setdefault("posts_since_promo", 0)
    state.setdefault("recent_combos", [])
    return state


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_enabled(platform: str) -> bool:
    config = load_promo_config()
    if not config.get("enabled"):
        return False
    return platform in (config.get("platforms") or [])


def should_post_promo(platform: str) -> bool:
    """今回の投稿を告知に差し替えるべきか"""
    if not is_enabled(platform):
        return False
    config = load_promo_config()
    every_n = max(1, int(config.get("every_n_posts", DEFAULT_EVERY_N)))
    return _load_state()["posts_since_promo"] >= every_n


def _iter_combos(quizzes: list, templates: list, recent: list):
    """
    (診断 × 文面) の組み合わせを、最近使っていないものから順に返す。

    同じ文面が連続すると宣伝臭が強くなるうえ、X アダプターの重複判定に
    引っかかって投稿自体がスキップされるため、履歴を見て散らす。
    """
    # 文面を外側、診断を内側にして、連続する告知で診断が入れ替わるようにする
    # （同じ診断を何回も続けて宣伝すると、片方の診断に露出が偏る）
    combos = [
        (quiz, template, f"{quiz['id']}:{index}")
        for index, template in enumerate(templates)
        for quiz in quizzes
    ]
    # recent の末尾ほど新しい。含まれないものを優先し、次に古い順。
    def freshness(combo):
        key = combo[2]
        return recent.index(key) if key in recent else -1

    return sorted(combos, key=freshness)


def build_promo_post(platform: str, is_duplicate=None) -> dict | None:
    """
    告知投稿を組み立てる。

    Args:
        platform: 投稿先プラットフォーム
        is_duplicate: テキストを渡すと過去に投稿済みか返す関数（任意）

    Returns:
        {"text": ..., "combo_key": ...} / 出せるものが無ければ None
    """
    from diagnosis import load_config

    if not is_enabled(platform):
        return None

    config = load_promo_config()
    templates = config.get("templates") or []
    quizzes = load_config().get("quizzes", [])
    if not templates or not quizzes:
        return None

    base_url = str(config.get("base_url", "")).rstrip("/")
    if not base_url:
        print("[promo] base_url が未設定のため告知をスキップします")
        return None

    state = _load_state()
    for quiz, template, combo_key in _iter_combos(quizzes, templates, state["recent_combos"]):
        text = (template
                .replace("{title}", quiz.get("title", ""))
                .replace("{catch}", quiz.get("catch", ""))
                .replace("{emoji}", quiz.get("emoji", ""))
                .replace("{url}", f"{base_url}/diagnosis/{quiz['id']}")).strip()
        if is_duplicate is not None and is_duplicate(text):
            continue
        return {"text": text, "combo_key": combo_key}

    print("[promo] 出せる告知文がすべて重複していたため、今回はスキップします")
    return None


def record_post(platform: str, was_promo: bool, combo_key: str = "") -> None:
    """投稿後にカウンターを進める（告知したらリセット）"""
    if not is_enabled(platform):
        return

    state = _load_state()
    if was_promo:
        state["posts_since_promo"] = 0
        if combo_key:
            recent = [k for k in state["recent_combos"] if k != combo_key]
            recent.append(combo_key)
            state["recent_combos"] = recent[-RECENT_MEMORY:]
    else:
        state["posts_since_promo"] += 1
    _save_state(state)
