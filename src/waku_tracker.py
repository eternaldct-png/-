"""
枠周り記録（/waku）— 歌推しの条件とプルダウンの選択肢を読み込む

記録そのものはサーバーに保存せず、各自のブラウザ（localStorage）に保存する。
サーバー側は persona/waku_config.yaml（歌推し計算ツールと同じ数値）をページに埋め込むだけ。
"""
from pathlib import Path

WAKU_CONFIG_PATH = Path("persona/waku_config.yaml")

MAX_VIEWING_MINUTES = 24 * 60
MAX_COINS = 100_000_000

_DEFAULT_PATTERN_NAMES = ["コイン節約型", "バランス型", "コイン一括型"]


def _number(value, default=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return int(number) if number.is_integer() else number


def _pattern(raw):
    raw = raw if isinstance(raw, dict) else {}
    return {
        "coins": max(0, int(_number(raw.get("coins")))),
        "viewing_hours": max(0, _number(raw.get("viewing_hours"))),
        "super_like_days": max(0, int(_number(raw.get("super_like_days")))),
    }


def _high_tiers(raw):
    """50K以上の推しPtを計算式から作る（歌推し計算ツールと同じ式）。"""
    if not isinstance(raw, dict):
        return []
    try:
        from_k = int(raw.get("from_k", 50))
        to_k = int(raw.get("to_k", from_k - 1))
        base_coins = [int(v) for v in raw.get("base_coins") or []]
        coins_per_k = int(raw.get("coins_per_k", 0))
        viewing = [_number(v) for v in raw.get("viewing_hours") or []]
        super_likes = [int(_number(v)) for v in raw.get("super_like_days") or []]
    except (TypeError, ValueError):
        return []
    if not (len(base_coins) == len(viewing) == len(super_likes) == 3):
        return []

    return [
        {
            "label": f"{k}K",
            "pt": k * 1000,
            "patterns": [
                {
                    "coins": base_coins[i] + (k - 49) * coins_per_k,
                    "viewing_hours": viewing[i],
                    "super_like_days": super_likes[i],
                }
                for i in range(3)
            ],
        }
        for k in range(from_k, to_k + 1)
    ]


def load_config():
    """persona/waku_config.yaml を読み込み、画面で使う形に整えて返す。"""
    import yaml

    data = {}
    if WAKU_CONFIG_PATH.exists():
        with open(WAKU_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    page = data.get("page") or {}
    viewing = sorted({
        int(_number(v)) for v in data.get("viewing_minutes") or []
        if 0 < _number(v) <= MAX_VIEWING_MINUTES
    })
    coins = sorted({
        int(_number(v)) for v in data.get("coin_presets") or []
        if 0 < _number(v) <= MAX_COINS
    })

    uta = data.get("uta_oshi") or {}
    tiers = []
    for t in uta.get("tiers") or []:
        if not isinstance(t, dict) or not t.get("label") or len(t.get("patterns") or []) != 3:
            continue
        tiers.append({
            "label": str(t["label"]),
            "pt": int(_number(t.get("pt"))),
            "patterns": [_pattern(p) for p in t["patterns"]],
        })
    known = {t["label"] for t in tiers}
    tiers += [t for t in _high_tiers(uta.get("high_tiers")) if t["label"] not in known]
    tiers.sort(key=lambda t: t["pt"])

    names = [str(n) for n in uta.get("pattern_names") or []]
    if len(names) != 3:
        names = list(_DEFAULT_PATTERN_NAMES)

    default_target = str(uta.get("default_target") or "")
    if tiers and default_target not in {t["label"] for t in tiers}:
        default_target = tiers[0]["label"]

    return {
        "title": str(page.get("title") or "枠周り記録"),
        "viewing_minutes": viewing,
        "coin_presets": coins,
        "pattern_names": names,
        "tiers": tiers,
        "default_target": default_target,
    }
