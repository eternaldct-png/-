"""端末の中だけで動くノート作成（外部の API を使わない）。

2つの方法がある:
- **端末内AI（Ollama）**: Mac で動く無料のAI（https://ollama.com）。このPCの中だけで動き、文字起こしを外に送らない。
  呼び先は 127.0.0.1:11434（自分のPCの中）だけ。
- **AIなし（簡易まとめ）**: 何も入れなくても動く。文字起こしから決まりごと・やることらしい発言を、言葉のパターンで拾う。
  文章を「書く」ことはせず、発言をそのまま抜き出すので、作り話は起きない（そのかわり要約の質は低い）。
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA_HOST.startswith("http"):
    OLLAMA_HOST = "http://" + OLLAMA_HOST
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"

_cache: dict[str, tuple[float, object]] = {}
# 端末内AI は自分のPCの中なので、プロキシ（会社や回線の設定）を通さずに直接つなぐ
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class LocalAIError(RuntimeError):
    pass


# ── Ollama ───────────────────────────────────────────────


def _is_local_host(url: str) -> bool:
    host = re.sub(r"^https?://", "", url).split("/")[0].rsplit(":", 1)[0].strip("[]")
    return host in ("127.0.0.1", "localhost", "::1")


def ollama_models(timeout: float = 1.5) -> list[str] | None:
    """Ollama が動いていればダウンロード済みのモデル名の一覧、動いていなければ None。5秒だけ覚えておく。"""
    hit = _cache.get("models")
    if hit and time.time() - hit[0] < 5:
        return hit[1]  # type: ignore[return-value]
    models = None
    if _is_local_host(OLLAMA_HOST):  # 自分のPCの中以外には問い合わせない
        try:
            with _OPENER.open(f"{OLLAMA_HOST}/api/tags", timeout=timeout) as r:
                models = [m.get("name", "") for m in json.load(r).get("models", [])]
        except (urllib.error.URLError, OSError, ValueError):
            models = None
    _cache["models"] = (time.time(), models)
    return models


def has_model(models: list[str] | None, name: str) -> bool:
    if not models:
        return False
    name = name.strip()
    return any(m == name or m == f"{name}:latest" or m.split(":")[0] == name for m in models)


def ollama_chat(model: str, system: str, user: str, schema: dict | None = None,
                timeout: float = 1800, num_ctx: int = 32768) -> str:
    if not _is_local_host(OLLAMA_HOST):
        raise LocalAIError("OLLAMA_HOST が自分のPC以外を指しています。端末の外には送らないので止めました。")
    body = {
        "model": model,
        "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": 0.2, "num_ctx": num_ctx},
    }
    if schema:
        body["format"] = schema  # Ollama 0.5 以降は JSON スキーマで形をそろえられる
    req = urllib.request.Request(f"{OLLAMA_HOST}/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 404 or "not found" in detail:
            raise LocalAIError(f"端末内AIのモデル「{model}」がまだありません。ターミナルで `ollama pull {model}` を実行してください。") from e
        raise LocalAIError(f"端末内AI（Ollama）がエラーを返しました: {e.code} {detail}") from e
    except (urllib.error.URLError, OSError) as e:
        raise LocalAIError("端末内AI（Ollama）につながりません。Ollama のアプリを起動してから「やり直す」を押してください。") from e
    text = (data.get("message") or {}).get("content", "")
    if not text.strip():
        raise LocalAIError("端末内AIの返事が空でした。もう一度お試しください。")
    return text


# ── AIなし（簡易まとめ） ───────────────────────────────────

_SENT_END = re.compile(r"(?<=[。！？!?])\s*|\n+")
_WORD = re.compile(r"[一-龥々〆ヵヶ]{2,}|[ァ-ヴー]{3,}|[A-Za-z][A-Za-z0-9]{2,}")
_STOP = set("こと もの これ それ あれ ため よう ところ 感じ 本当 今日 自分 大丈夫 お願い 確認 一応 全然 結構 多分 OK ok".split())

_DECISION = re.compile(r"(決定|決まり|決めました|決めましょう|確定|にしましょう|でいきましょう|で行きましょう|でいこう|に決め|合意|承認)")
_ACTION = re.compile(r"(までに|やります|やっておきます|しておきます|しておく|お願いします|お願いできますか|お願いしたい|送ります|送っておきます|"
                     r"対応します|確認します|確認しておきます|連絡します|共有します|準備します|作ります|調べます|手配します|担当します|宿題)")
_DUE = re.compile(r"(\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2}|明日|明後日|今日中|今週中|今週|来週[月火水木金土日]?曜?日?|今月中|来月|"
                  r"[月火水木金土日]曜(日)?|週明け|月末|\d+日(まで|中)?)")
_ASK_SOMEONE = re.compile(r"([^\s、。,:：「」]{1,10})さん[、,\s]*(?:に|が|は)?.{0,30}(お願い|やって|送って|確認して|対応して|準備して)")


def _sentences(segs: list[dict]) -> list[dict]:
    out = []
    for s in segs:
        for part in _SENT_END.split(s.get("text", "")):
            part = part.strip()
            if len(part) >= 4:
                out.append({"text": part, "speaker": s.get("speaker", ""), "start": s.get("start")})
    return out


def _keywords(sents: list[dict], n: int = 8) -> list[str]:
    c = Counter(w for s in sents for w in _WORD.findall(s["text"]) if w not in _STOP)
    return [w for w, _ in c.most_common(n)]


def _top_sentences(sents: list[dict], k: int) -> list[dict]:
    kw = Counter(w for s in sents for w in _WORD.findall(s["text"]) if w not in _STOP)
    scored = []
    for i, s in enumerate(sents):
        words = _WORD.findall(s["text"])
        if not words:
            continue
        score = sum(kw[w] for w in words) / (1 + len(s["text"]) / 40)
        scored.append((score, i))
    best = sorted(sorted(scored, reverse=True)[:k], key=lambda x: x[1])  # 話された順に戻す
    return [sents[i] for _, i in best]


def simple_notes(meeting: dict) -> dict:
    """AIを使わずに、発言の抜き出しでノートを作る。書き換えはしない（発言そのまま）。"""
    segs = meeting.get("transcript") or []
    sents = _sentences(segs)
    if not sents:
        raise LocalAIError("文字起こしが空です。")
    kw = _keywords(sents)
    title = meeting.get("title") or ("・".join(kw[:3]) + "の話" if kw else "会議のメモ")
    summary_sents = _top_sentences(sents, 3)
    summary = "（AIなしの簡易まとめ: 話によく出た言葉を含む発言の抜き出しです）\n" + "\n".join(f"「{s['text']}」" for s in summary_sents)

    # 話題: 15発言ずつ区切り、区切りごとに多く出た言葉を見出しに、代表的な発言を箇条書きに
    sections = []
    for i in range(0, len(sents), 15):
        block = sents[i:i + 15]
        words = _keywords(block, 2)
        heading = "・".join(words) if words else f"{i // 15 + 1}つ目の話題"
        if sections and sections[-1]["heading"] == heading:
            heading += "（続き）"
        bullets = [s["text"] for s in _top_sentences(block, 3)]
        sections.append({"heading": heading, "bullets": bullets})

    decisions = list(dict.fromkeys(s["text"] for s in sents if _DECISION.search(s["text"])))[:10]

    actions = []
    for s in sents:
        t = s["text"]
        if not _ACTION.search(t) or (t.endswith(("？", "?")) and "お願い" not in t):
            continue
        owner = ""
        m = _ASK_SOMEONE.search(t)
        if m:
            owner = m.group(1)
        elif re.search(r"(やります|やっておきます|しておきます|しておく|送ります|送っておきます|対応します|確認します|確認しておきます|"
                       r"連絡します|共有します|準備します|作ります|調べます|手配します|担当します)", t):
            owner = s["speaker"]  # 「〜します」は話した本人が引き受けた
        due = _DUE.search(t)
        actions.append({"text": t[:120], "owner": owner, "due": due.group(0) if due else "",
                        "evidence": t, "verified": True, "evidence_time": s["start"]})
    # 同じ発言の重複を消す
    seen, uniq = set(), []
    for a in actions:
        if a["text"] not in seen:
            seen.add(a["text"])
            uniq.append(a)
    return {"title": title[:60], "summary": summary, "sections": sections[:12], "decisions": decisions,
            "action_items": uniq[:20], "engine": "simple"}


def simple_answer(meetings: list[dict], question: str, limit: int = 12) -> str:
    """AIなしの「質問」: 質問の言葉が出てくる発言を、会議ごとに抜き出して返す。"""
    words = [w for w in re.findall(r"[一-龥々〆ヵヶァ-ヴーA-Za-z0-9０-９Ａ-Ｚａ-ｚ]{2,}", question) if w not in _STOP][:8]
    if not words:
        return "AIなしモードでは、質問の中の言葉（2文字以上の漢字・カタカナ・英数字）で発言を探します。言葉を含めて質問してください。"
    found = []
    for m in meetings:
        for s in m.get("transcript") or []:
            text = s.get("text", "")
            hit = sum(1 for w in words if w.lower() in text.lower())
            if hit:
                found.append((hit, m, s))
    if not found:
        return f"「{'」「'.join(words)}」を含む発言は見つかりませんでした。（AIなしモードは言葉の一致で探します）"
    found.sort(key=lambda x: -x[0])
    from .transcribe import fmt_clock
    lines = [f"（AIなしモード: 「{'」「'.join(words)}」を含む発言を抜き出しました）"]
    for _, m, s in found[:limit]:
        when = f"[{fmt_clock(s['start'])}] " if s.get("start") is not None else ""
        who = f"{s['speaker']}: " if s.get("speaker") else ""
        title = m.get("title") or "（無題）"
        lines.append(f"・{title} {when}{who}{s.get('text', '')}")
    return "\n".join(lines)
