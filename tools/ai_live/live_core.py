"""AIキャラ配信の中核ロジック（ネット接続なし・テストしやすい部分）。

- 設定の読み込み
- コメントの安全チェック（NGワード・URL・長すぎ）
- ギフトのランク判定
- 「次に何をしゃべるか」の優先順位キュー（ギフト > フォロー > オペレーター > コメント > 雑談）
- AI代の集計
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.yaml"

URL_RE = re.compile(r"https?://|www\.|\.com\b|\.jp\b", re.IGNORECASE)

# 数字が小さいほど先にしゃべる
PRIORITY = {"operator": 0, "gift": 1, "follow": 2, "comment": 3, "join": 4, "idle": 5}


def load_config(path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize(text: str) -> str:
    # 全角英数・大文字小文字の違いでNGワードをすり抜けられないようにする
    import unicodedata

    return unicodedata.normalize("NFKC", text).lower().replace(" ", "").replace("　", "")


def check_comment(text: str, safety: dict) -> str | None:
    """読んではいけないコメントなら理由を返す。問題なければ None。"""
    if not text or not text.strip():
        return "empty"
    if len(text) > safety.get("max_comment_chars", 120):
        return "too_long"
    if safety.get("skip_urls", True) and URL_RE.search(text):
        return "url"
    norm = _normalize(text)
    for word in safety.get("ng_words", []):
        if _normalize(word) in norm:
            return "ng_word"
    return None


def clean_reply(text: str, safety: dict, max_chars: int) -> str:
    """AIの返事を配信で読み上げられる形に整える。危ない言葉が入っていたら差し替える。"""
    text = (text or "").strip().replace("\n", " ")
    text = re.sub(r"[*#`>_]", "", text)  # マークダウン記号は読み上げない
    norm = _normalize(text)
    for word in safety.get("output_ng_words", []):
        if _normalize(word) in norm:
            return safety["fallback_line"]
    if not text:
        return safety["fallback_line"]
    if len(text) > max_chars:
        cut = text[:max_chars]
        # 文の途中で切れないよう、最後の句読点までに縮める
        last = max(cut.rfind(p) for p in "。！？!?")
        text = cut[: last + 1] if last >= max_chars // 2 else cut
    return text


def gift_tier(total_diamonds: int, tiers: list[dict]) -> dict:
    for tier in tiers:
        if total_diamonds >= tier.get("min_diamonds", 0):
            return tier
    return tiers[-1]


@dataclass(order=True)
class Task:
    priority: int
    seq: int
    kind: str = field(compare=False)
    user: str = field(compare=False, default="")
    text: str = field(compare=False, default="")
    extra: dict = field(compare=False, default_factory=dict)


class TaskQueue:
    """しゃべる順番を決めるキュー。

    コメントは全部には返事できないので、上限を超えたら古いものから捨てる。
    同じ人のコメントには cooldown 秒のあいだ続けて返事しない。
    """

    def __init__(self, comment_max: int = 15, user_cooldown: float = 30, clock=time.monotonic):
        self._urgent: list[Task] = []
        self._comments: deque[Task] = deque()
        self._comment_max = comment_max
        self._cooldown = user_cooldown
        self._last_replied: dict[str, float] = {}
        self._seq = 0
        self._clock = clock
        self.dropped = 0

    def push(self, kind: str, user: str = "", text: str = "", **extra) -> Task:
        self._seq += 1
        task = Task(PRIORITY[kind], self._seq, kind, user, text, extra)
        if kind == "comment":
            self._comments.append(task)
            while len(self._comments) > self._comment_max:
                self._comments.popleft()
                self.dropped += 1
        else:
            self._urgent.append(task)
            self._urgent.sort()
        return task

    def pop(self) -> Task | None:
        if self._urgent:
            return self._urgent.pop(0)
        now = self._clock()
        # 新しいコメントから順に、クールダウン中でない人を選ぶ
        for task in reversed(self._comments):
            last = self._last_replied.get(task.user)
            if last is None or now - last >= self._cooldown:
                self._comments.remove(task)
                self._last_replied[task.user] = now
                return task
        return None

    def __len__(self) -> int:
        return len(self._urgent) + len(self._comments)


class CostMeter:
    """AI代の集計（トークン数 × 単価）。"""

    def __init__(self, ai_cfg: dict):
        self.prices = ai_cfg.get("price_usd_per_mtok", {})
        self.usd_jpy = ai_cfg.get("usd_jpy", 160)
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.usd = 0.0
        self.started = time.time()

    def add(self, model: str, input_tokens: int, output_tokens: int) -> None:
        price = self.prices.get(model, {"input": 0, "output": 0})
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.usd += input_tokens / 1e6 * price["input"] + output_tokens / 1e6 * price["output"]

    @property
    def jpy(self) -> float:
        return self.usd * self.usd_jpy

    def summary(self) -> str:
        hours = max((time.time() - self.started) / 3600, 1e-9)
        return (
            f"AI呼び出し {self.calls}回 / 入力 {self.input_tokens:,} / 出力 {self.output_tokens:,} トークン"
            f" / 約{self.jpy:,.1f}円（${self.usd:.4f}）/ 1時間あたり約{self.jpy / hours:,.0f}円"
        )
