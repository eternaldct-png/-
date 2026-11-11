"""Claude でノートを書く・質問に答える。

呼び方は src/video_brief.py と同じ（構造化出力 + サーバー側フォールバック）。
テストでは client を差し替える（本物の API は呼ばない）。
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime

from . import local_ai
from .transcribe import transcript_to_text

# 1M トークンあたりのドル（2026-11 時点の公表価格。変わったらここを直す）
PRICES_USD_PER_MTOK = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

NOTES_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "summary", "sections", "decisions", "action_items"],
    "properties": {
        "title": {"type": "string", "description": "会議の中身が分かる短いタイトル（30文字以内）"},
        "summary": {"type": "string", "description": "3〜5文の要約"},
        "sections": {
            "type": "array",
            "description": "話題ごとのノート。話された順",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heading", "bullets"],
                "properties": {
                    "heading": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "decisions": {"type": "array", "items": {"type": "string"}, "description": "決まったこと"},
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "owner", "due", "evidence"],
                "properties": {
                    "text": {"type": "string", "description": "やること（動詞で終える）"},
                    "evidence": {"type": "string", "description": "このやることの根拠になった発言を、文字起こしから一字一句そのまま抜き出したもの（20〜60文字）"},
                    "owner": {"type": "string", "description": "担当者の名前。分からなければ空文字"},
                    "due": {"type": "string", "description": "期限（会話に出た言い方のまま）。無ければ空文字"},
                },
            },
        },
    },
}

NOTES_SYSTEM = """あなたは会議の記録係です。渡された文字起こしだけを根拠に、日本語で会議ノートを書きます。

- 話題ごとに見出しを立て、要点を箇条書きにする。1つの箇条書きは1〜2文。
- 数字・固有名詞・日付・金額は文字起こしの表記のまま残す。文字起こしに無いことは書かない。推測で補わない。
- 「決まったこと」と「やること（アクションアイテム）」は分けて書く。
- アクションアイテムは「誰が・何を」が分かるように。担当者が会話から分からなければ owner は空文字。
- アクションアイテムは、会話の中で実際に「やる」と合意・依頼された・本人が引き受けたものだけ。検討しただけ・案が出ただけのものは入れない。
- 各アクションアイテムの evidence には、根拠になった発言を文字起こしから一字一句そのまま抜き出す（言い換えない）。根拠を示せないものは入れない。
- 文字起こしの誤変換と思われる箇所は、文脈から明らかな場合だけ直す。
- 雑談やあいさつだけの部分はノートに入れない。"""

ASK_SYSTEM = """あなたは会議の記録を調べるアシスタントです。渡された会議の記録だけを根拠に、日本語で簡潔に答えます。
記録に答えが無いときは「記録には見当たりません」と答え、推測で埋めません。
根拠にした会議名と、分かれば時刻（[mm:ss]）を答えの中に示します。"""


class AIError(RuntimeError):
    pass


def _client():
    import anthropic
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise AIError("ANTHROPIC_API_KEY が設定されていません。起動する前に設定してください（README 参照）。")
    return anthropic.Anthropic()


class Meter:
    """AI の費用を記録し、月の上限を超えないようにする（不満: 高い・いくらかかるか分からない）。"""

    def __init__(self, store=None, settings=None, meeting_id=None, kind=""):
        self.store, self.settings, self.meeting_id, self.kind = store, settings or {}, meeting_id, kind

    def check_budget(self):
        if not self.store:
            return
        budget = _num(self.settings.get("monthly_budget_jpy"))
        if budget <= 0:
            return
        spent = self.store.usage_since(month_start_iso()) * _num(self.settings.get("usd_jpy"), 150)
        if spent >= budget:
            raise AIError(f"今月のAI費用が上限（{budget:,.0f}円）に達したので止めました。今月の使用額: 約{spent:,.0f}円。"
                          "「設定」で上限を上げるか、来月まで待ってください。")

    def record(self, model, usage):
        if not self.store or usage is None:
            return
        tin = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "cache_creation_input_tokens", 0) or 0) \
            + (getattr(usage, "cache_read_input_tokens", 0) or 0)
        tout = getattr(usage, "output_tokens", 0) or 0
        self.store.add_usage(self.meeting_id, self.kind, model, tin, tout, cost_usd(model, tin, tout))


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES_USD_PER_MTOK.get(model, PRICES_USD_PER_MTOK["claude-opus-5-5"])
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout


def month_start_iso() -> str:
    """このPCの暦で今月1日0時（UTC の ISO 文字列）。"""
    local = datetime.now().astimezone()
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from datetime import timezone
    return start.astimezone(timezone.utc).isoformat(timespec="seconds")


def _call(client, *, model, system, user, max_tokens, schema=None, effort="medium", meter=None):
    meter = meter or Meter()
    meter.check_budget()
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config=output_config,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except AIError:
        raise
    except Exception as e:  # anthropic の各種エラー（接続・429・5xx・400）
        raise AIError(f"AIの呼び出しに失敗しました: {type(e).__name__}: {getattr(e, 'message', e)}") from e
    meter.record(getattr(response, "model", None) or model, getattr(response, "usage", None))
    if response.stop_reason == "refusal":
        raise AIError("AIがこの内容の処理を断りました。")
    if response.stop_reason == "max_tokens":
        raise AIError("AIの出力が長すぎて途中で切れました。")
    return next((b.text for b in response.content if b.type == "text"), "")


# ── どのAIで書くか ────────────────────────────────────────
# claude: Claude API（外部に文字起こしを送る。お金がかかる）
# ollama: 端末内AI（Ollama。このPCの中だけで動く。無料）
# simple: AIなし（発言の抜き出し。何も入れなくても動く）
# auto  : Ollama が動いていれば ollama、無ければ simple。**Claude は自動では選ばない**（明示して選んだときだけ使う）

ENGINE_LABELS = {"claude": "Claude API", "ollama": "端末内AI（Ollama）", "simple": "AIなし（簡易まとめ）"}


def resolve_engine(settings: dict, client=None) -> str:
    choice = (settings.get("ai_engine") or "auto").strip()
    if choice in ("claude", "ollama", "simple"):
        return choice
    if client is not None:  # テストで Claude の代わりを渡したとき
        return "claude"
    models = local_ai.ollama_models()
    if models is not None and local_ai.has_model(models, settings.get("ollama_model") or local_ai.DEFAULT_OLLAMA_MODEL):
        return "ollama"
    return "simple"


def _llm(settings, client, *, system, user, max_tokens, schema=None, effort="medium", meter=None, engine=None) -> str:
    engine = engine or resolve_engine(settings, client)
    if engine == "ollama":
        try:
            return local_ai.ollama_chat(settings.get("ollama_model") or local_ai.DEFAULT_OLLAMA_MODEL, system, user, schema=schema)
        except local_ai.LocalAIError as e:
            raise AIError(str(e)) from e
    if engine == "claude":
        return _call(client or _client(), model=settings.get("model") or "claude-opus-5-5", system=system, user=user,
                     max_tokens=max_tokens, schema=schema, effort=effort, meter=meter)
    raise AIError("AIなしモードでは使えません。「設定」で端末内AI（Ollama）を選ぶと使えます。")


def meeting_header(meeting: dict) -> str:
    parts = [f"会議名: {meeting.get('title') or '（未設定）'}", f"日時(UTC): {meeting.get('started_at', '')}"]
    if meeting.get("participants"):
        parts.append("参加者: " + "、".join(meeting["participants"]))
    if meeting.get("tags"):
        parts.append("タグ: " + "、".join(meeting["tags"]))
    return "\n".join(parts)


def _system_extra(settings: dict) -> str:
    extra = ""
    if settings.get("custom_context", "").strip():
        extra += "\n\n# 書き手（あなたの依頼主）からの指示・前提\n" + settings["custom_context"].strip()
    words = vocabulary(settings)
    if words:
        extra += ("\n\n# よく出る言葉・固有名詞の正しい表記\n" + "、".join(words)
                  + "\n文字起こしでこれらが聞き間違えられていそうなときは、この表記に直してよい。")
    return extra


def vocabulary(settings: dict) -> list[str]:
    raw = str(settings.get("vocabulary", "") or "")
    out = []
    for w in re.split(r"[,、，\n]+", raw):
        w = w.strip()
        if w and w not in out:
            out.append(w)
    return out[:200]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "")
    return re.sub(r"[\s、。，．,.!?！？「」『』…・〜~ー-]+", "", t).lower()


def find_evidence(segs: list[dict], quote: str):
    """根拠の発言が文字起こしにあるか探す。あれば (True, 時刻)。言い換えられていたら (False, None)。"""
    q = _norm(quote)
    if len(q) < 4:
        return False, None
    for s in segs:
        if q in _norm(s.get("text", "")):
            return True, s.get("start")
    # 2行にまたがる引用
    for a, b in zip(segs, segs[1:]):
        if q in _norm(a.get("text", "") + b.get("text", "")):
            return True, a.get("start")
    return False, None


def generate_notes(meeting: dict, settings: dict, client=None, meter=None) -> dict:
    segs = meeting.get("transcript") or []
    text = transcript_to_text(segs)
    if not text.strip():
        raise AIError("文字起こしが空です。音声に声が入っているか確認してください。")
    engine = resolve_engine(settings, client)
    if engine == "simple":
        try:
            return local_ai.simple_notes(meeting)
        except local_ai.LocalAIError as e:
            raise AIError(str(e)) from e
    system = NOTES_SYSTEM + _system_extra(settings)
    if engine == "ollama" and len(text) > OLLAMA_CHUNK_CHARS:
        notes = _notes_in_chunks(meeting, segs, system, settings)
    else:
        user = (
            f"{meeting_header(meeting)}\n\n"
            f"<transcript>\n{text}\n</transcript>\n\n"
            "この会議のノートを書いてください。"
        )
        notes = _parse_json(_llm(settings, client, system=system, user=user, max_tokens=16000,
                                 schema=NOTES_SCHEMA, meter=meter, engine=engine))
    notes["engine"] = engine
    notes.setdefault("sections", [])
    notes.setdefault("decisions", [])
    notes.setdefault("action_items", [])
    # 作り話のやることを防ぐ: 根拠の発言が文字起こしに本当にあるかを機械的に確かめる（不満: AIが合意していないタスクを作る）
    for it in notes["action_items"]:
        ok, t = find_evidence(segs, it.get("evidence", ""))
        it["verified"] = ok
        it["evidence_time"] = t
    return notes


OLLAMA_CHUNK_CHARS = 12_000  # 端末内AIは一度に読める量が少ないので、長い会議は分けて読む


def _parse_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)  # 端末内AIが前後に文を付けたとき
        try:
            data = json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        raise AIError("AIの出力を読み取れませんでした。もう一度お試しください。")
    return data


def _notes_in_chunks(meeting, segs, system, settings) -> dict:
    """長い会議を区切って端末内AIに読ませ、あとで1つにまとめる。"""
    chunks, cur, size = [], [], 0
    for s in segs:
        line = transcript_to_text([s])
        if cur and size + len(line) > OLLAMA_CHUNK_CHARS:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(s)
        size += len(line) + 1
    if cur:
        chunks.append(cur)
    parts = []
    for i, part in enumerate(chunks, 1):
        user = (f"{meeting_header(meeting)}\n（長い会議の {i}/{len(chunks)} 番目の部分です）\n\n"
                f"<transcript>\n{transcript_to_text(part)}\n</transcript>\n\nこの部分のノートを書いてください。")
        parts.append(_parse_json(_llm(settings, None, system=system, user=user, max_tokens=8000,
                                      schema=NOTES_SCHEMA, engine="ollama")))
    summaries = "\n".join(f"{i}. {p.get('summary', '')}" for i, p in enumerate(parts, 1))
    summary = _llm(settings, None, engine="ollama", max_tokens=2000,
                   system="会議の部分ごとの要約を、1つの要約（3〜5文、日本語）にまとめます。書かれていないことは足しません。要約だけを返します。",
                   user=summaries).strip()
    out = {"title": parts[0].get("title", ""), "summary": summary, "sections": [], "decisions": [], "action_items": []}
    for p in parts:
        out["sections"] += p.get("sections", [])
        for key in ("decisions", "action_items"):
            for item in p.get(key, []):
                if item not in out[key]:
                    out[key].append(item)
    return out


def answer_about_meeting(meeting: dict, history: list[dict], question: str, settings: dict, client=None, meter=None) -> str:
    if resolve_engine(settings, client) == "simple":
        return local_ai.simple_answer([meeting], question)
    notes = meeting.get("notes") or {}
    user = (
        f"{meeting_header(meeting)}\n\n"
        f"<notes>\n{json.dumps(notes, ensure_ascii=False)}\n</notes>\n\n"
        f"<transcript>\n{transcript_to_text(meeting.get('transcript') or [])}\n</transcript>\n\n"
        + _history_text(history)
        + f"質問: {question}"
    )
    return _llm(settings, client, system=ASK_SYSTEM + _system_extra(settings), user=user, max_tokens=4000,
                effort="low", meter=meter).strip()


def answer_across(meetings: list[dict], hits: set[str], history: list[dict], question: str,
                  settings: dict, client=None, max_chars: int = 400_000, meter=None) -> str:
    """全会議への質問。全会議の要約＋ノートを渡し、キーワードが当たった会議は文字起こしも足す（上限あり）。"""
    engine = resolve_engine(settings, client)
    if engine == "simple":
        return local_ai.simple_answer([m for m in meetings if m.get("status") == "done"], question)
    if engine == "ollama":
        max_chars = min(max_chars, 40_000)  # 端末内AIが一度に読める量に合わせる
    blocks, used = [], 0
    for m in meetings:
        if m.get("status") != "done":
            continue
        notes = m.get("notes") or {}
        block = f"## {m.get('title') or '（無題）'}（{m.get('started_at', '')[:10]}）\n{json.dumps(notes, ensure_ascii=False)}"
        if m["id"] in hits:
            full = transcript_to_text(m.get("transcript") or [])
            if used + len(block) + len(full) <= max_chars:
                block += f"\n<transcript>\n{full}\n</transcript>"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    if not blocks:
        raise AIError("ノートが出来上がっている会議がまだありません。")
    user = "<meetings>\n" + "\n\n".join(blocks) + "\n</meetings>\n\n" + _history_text(history) + f"質問: {question}"
    return _llm(settings, client, system=ASK_SYSTEM + _system_extra(settings), user=user, max_tokens=6000,
                effort="low", meter=meter, engine=engine).strip()


def _history_text(history: list[dict]) -> str:
    if not history:
        return ""
    lines = [f"{'あなた' if h['role'] == 'assistant' else '質問'}: {h['content']}" for h in history[-10:]]
    return "<これまでのやりとり>\n" + "\n".join(lines) + "\n</これまでのやりとり>\n\n"


# ── 話者の推定（不満: 話者の取り違え） ─────────────────────────

SPEAKERS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["assignments"],
    "properties": {
        "assignments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["line", "speaker"],
                "properties": {
                    "line": {"type": "integer", "description": "行番号（0から）"},
                    "speaker": {"type": "string", "description": "参加者の名前。判断できなければ空文字"},
                },
            },
        }
    },
}

SPEAKERS_SYSTEM = """あなたは会議の文字起こしの各行を、誰が話したかを推定します。
- 使える名前は、渡された参加者の名前だけ。新しい名前を作らない。
- 呼びかけ（「山田さん、どうですか」の次の行は山田さんが答えている可能性が高い）、自己紹介、話の流れ、口調から判断する。
- 判断できない行は speaker を空文字にする。無理に埋めない。"""


def guess_speakers(meeting: dict, settings: dict, client=None, meter=None) -> list[dict]:
    """参加者の名前から各行の話者を推定する。結果は「推定」として扱い、人が確かめる前提。"""
    people = meeting.get("participants") or []
    if len(people) < 2:
        raise AIError("話者を推定するには、参加者を2人以上入れてください（会議の「編集」から）。")
    segs = meeting.get("transcript") or []
    lines = "\n".join(f"{i}: {s.get('text', '')}" for i, s in enumerate(segs))
    user = (f"参加者: {'、'.join(people)}\n\n<lines>\n{lines}\n</lines>\n\n各行の話者を推定してください。")
    data = _parse_json(_llm(settings, client, system=SPEAKERS_SYSTEM, user=user, max_tokens=16000,
                            schema=SPEAKERS_SCHEMA, effort="low", meter=meter))
    out = [dict(s) for s in segs]
    for a in data.get("assignments", []):
        i, name = a.get("line"), str(a.get("speaker", "")).strip()
        if isinstance(i, int) and 0 <= i < len(out) and name in people and not out[i].get("speaker"):
            out[i]["speaker"] = name
            out[i]["guessed"] = True
    return out
