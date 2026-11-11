"""Claude でノートを書く・質問に答える。

呼び方は src/video_brief.py と同じ（構造化出力 + サーバー側フォールバック）。
テストでは client を差し替える（本物の API は呼ばない）。
"""
from __future__ import annotations

import json
import os

from .transcribe import transcript_to_text

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
                "required": ["text", "owner", "due"],
                "properties": {
                    "text": {"type": "string", "description": "やること（動詞で終える）"},
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


def _call(client, *, model, system, user, max_tokens, schema=None, effort="medium"):
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
    if response.stop_reason == "refusal":
        raise AIError("AIがこの内容の処理を断りました。")
    if response.stop_reason == "max_tokens":
        raise AIError("AIの出力が長すぎて途中で切れました。")
    return next((b.text for b in response.content if b.type == "text"), "")


def meeting_header(meeting: dict) -> str:
    parts = [f"会議名: {meeting.get('title') or '（未設定）'}", f"日時(UTC): {meeting.get('started_at', '')}"]
    if meeting.get("participants"):
        parts.append("参加者: " + "、".join(meeting["participants"]))
    if meeting.get("tags"):
        parts.append("タグ: " + "、".join(meeting["tags"]))
    return "\n".join(parts)


def generate_notes(meeting: dict, settings: dict, client=None) -> dict:
    segs = meeting.get("transcript") or []
    text = transcript_to_text(segs)
    if not text.strip():
        raise AIError("文字起こしが空です。音声に声が入っているか確認してください。")
    system = NOTES_SYSTEM
    if settings.get("custom_context", "").strip():
        system += "\n\n# 書き手（あなたの依頼主）からの指示・前提\n" + settings["custom_context"].strip()
    user = (
        f"{meeting_header(meeting)}\n\n"
        f"<transcript>\n{text}\n</transcript>\n\n"
        "この会議のノートを書いてください。"
    )
    raw = _call(client or _client(), model=settings.get("model") or "claude-opus-5-5",
                system=system, user=user, max_tokens=16000, schema=NOTES_SCHEMA)
    try:
        notes = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AIError("AIの出力を読み取れませんでした。もう一度お試しください。") from e
    notes.setdefault("sections", [])
    notes.setdefault("decisions", [])
    notes.setdefault("action_items", [])
    return notes


def answer_about_meeting(meeting: dict, history: list[dict], question: str, settings: dict, client=None) -> str:
    notes = meeting.get("notes") or {}
    user = (
        f"{meeting_header(meeting)}\n\n"
        f"<notes>\n{json.dumps(notes, ensure_ascii=False)}\n</notes>\n\n"
        f"<transcript>\n{transcript_to_text(meeting.get('transcript') or [])}\n</transcript>\n\n"
        + _history_text(history)
        + f"質問: {question}"
    )
    return _call(client or _client(), model=settings.get("model") or "claude-opus-5-5",
                 system=ASK_SYSTEM, user=user, max_tokens=4000, effort="low").strip()


def answer_across(meetings: list[dict], hits: set[str], history: list[dict], question: str,
                  settings: dict, client=None, max_chars: int = 400_000) -> str:
    """全会議への質問。全会議の要約＋ノートを渡し、キーワードが当たった会議は文字起こしも足す（上限あり）。"""
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
    return _call(client or _client(), model=settings.get("model") or "claude-opus-5-5",
                 system=ASK_SYSTEM, user=user, max_tokens=6000, effort="low").strip()


def _history_text(history: list[dict]) -> str:
    if not history:
        return ""
    lines = [f"{'あなた' if h['role'] == 'assistant' else '質問'}: {h['content']}" for h in history[-10:]]
    return "<これまでのやりとり>\n" + "\n".join(lines) + "\n</これまでのやりとり>\n\n"
