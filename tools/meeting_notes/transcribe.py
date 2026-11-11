"""文字起こし。

- 音声・動画 → faster-whisper（ローカル。音声を外部に送らない）。未インストールなら分かるエラーを出す。
- 文字起こしテキスト（Zoom / Google Meet / Teams の .vtt、.srt、「名前: 発言」形式の .txt）→ 話者・時刻つきの行に直す。

戻り値の形はどちらも [{"speaker": str, "start": 秒, "end": 秒, "text": str}]。
"""
from __future__ import annotations

import re

_TIME = r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
_CUE = re.compile(rf"^\s*{_TIME}\s*-->\s*{_TIME}")
_VOICE = re.compile(r"<v(?:\.[^ >]*)?\s+([^>]+)>(.*?)(?:</v>|$)", re.S)
_TAG = re.compile(r"<[^>]+>")
# 「山田: こんにちは」「山田：こんにちは」「[00:01:02] 山田: …」「山田 (00:01): …」
_SPEAKER_LINE = re.compile(
    r"^\s*(?:\[?(?P<ts>(?:\d+:)?\d{1,2}:\d{2})\]?\s+)?(?P<who>[^:：\n]{1,30}?)\s*(?:\((?P<ts2>(?:\d+:)?\d{1,2}:\d{2})\))?\s*[:：]\s*(?P<text>.+)$"
)


class TranscriptionUnavailable(RuntimeError):
    pass


def _secs(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int((ms or "0").ljust(3, "0")[:3]) / 1000


def _clock(ts: str | None) -> float | None:
    if not ts:
        return None
    parts = [int(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def parse_cues(text: str) -> list[dict]:
    """WebVTT / SRT を読む。"""
    segs = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        m = _CUE.match(lines[i])
        if not m:
            i += 1
            continue
        start = _secs(*m.group(1, 2, 3, 4))
        end = _secs(*m.group(5, 6, 7, 8))
        i += 1
        body = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i].strip())
            i += 1
        raw = " ".join(body)
        speaker = ""
        v = _VOICE.search(raw)
        if v:
            speaker, raw = v.group(1).strip(), v.group(2)
        raw = _TAG.sub("", raw).strip()
        if not speaker:
            sm = re.match(r"^([^:：]{1,30})[:：]\s*(.+)$", raw)
            if sm:
                speaker, raw = sm.group(1).strip(), sm.group(2).strip()
        if raw:
            segs.append({"speaker": speaker, "start": start, "end": end, "text": raw})
    return merge_same_speaker(segs)


def merge_same_speaker(segs: list[dict], gap: float = 2.0) -> list[dict]:
    """同じ人が続けて話した短い字幕をつなげる（vtt は数秒ごとに切れているため）。"""
    out: list[dict] = []
    for s in segs:
        if (out and s["speaker"] and out[-1]["speaker"] == s["speaker"]
                and s["start"] - out[-1]["end"] <= gap and len(out[-1]["text"]) < 400):
            out[-1]["text"] += ("" if _is_cjk_end(out[-1]["text"]) else " ") + s["text"]
            out[-1]["end"] = s["end"]
        else:
            out.append(dict(s))
    return out


def _is_cjk_end(t: str) -> bool:
    return bool(t) and ord(t[-1]) > 0x2E80


def parse_plain(text: str) -> list[dict]:
    """「名前: 発言」の行、または段落だけのテキストを読む。時刻は分かるときだけ入れる。"""
    segs = []
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        m = _SPEAKER_LINE.match(line)
        if m and not re.match(r"^https?$", m.group("who").strip()):
            t = _clock(m.group("ts") or m.group("ts2"))
            segs.append({"speaker": m.group("who").strip(), "start": t, "end": t, "text": m.group("text").strip()})
        else:
            # 話者の無い行も1行ずつ分けておく（あとで行ごとに話者を付けられるように）
            segs.append({"speaker": "", "start": None, "end": None, "text": line})
    return segs


def parse_transcript_text(text: str, filename: str = "") -> list[dict]:
    text = (text or "").lstrip("﻿")
    if not text.strip():
        return []
    if filename.lower().endswith((".vtt", ".srt")) or text.lstrip().startswith("WEBVTT") or _CUE.search(text):
        segs = parse_cues(text)
        if segs:
            return segs
    return parse_plain(text)


def transcript_to_text(segs: list[dict], with_time: bool = True) -> str:
    lines = []
    for s in segs:
        head = ""
        if with_time and s.get("start") is not None:
            head = f"[{fmt_clock(s['start'])}] "
        who = f"{s['speaker']}: " if s.get("speaker") else ""
        lines.append(f"{head}{who}{s.get('text', '')}")
    return "\n".join(lines)


def fmt_clock(sec) -> str:
    if sec is None:
        return ""
    sec = int(float(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ── 音声 → 文字（faster-whisper） ────────────────────────

_MODELS: dict[str, object] = {}


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def transcribe_audio(path: str, *, model_size: str = "small", language: str = "ja", progress=None,
                     vocabulary: list[str] | None = None, quiet: bool = False):
    """音声ファイルを文字にする。progress(処理済み秒, 全体秒) を時々呼ぶ。戻り値は (segments, 長さ秒)。

    vocabulary: よく出る言葉・固有名詞。Whisper に「前置き」として渡すと、その表記で聞き取られやすくなる。
    quiet: 小さい声を拾うモード。無音カット（VAD）を切り、聞き取れない区間の判定も緩める。
    """
    try:
        from faster_whisper import WhisperModel
    except Exception as e:  # ImportError のほか、依存ライブラリの読み込み失敗もある
        raise TranscriptionUnavailable(
            "音声の文字起こしには faster-whisper が必要です。"
            "ターミナルで `pip install faster-whisper` を実行してから、アプリを起動し直してください。"
            "（または Zoom/Meet の文字起こしファイルを「文字起こしを入れる」から取り込んでください）"
        ) from e
    model = _MODELS.get(model_size)
    if model is None:
        try:
            # Mac（Apple Silicon 含む）では CPU で動く。int8 で軽くする
            model = WhisperModel(model_size, device="auto", compute_type="int8")
        except Exception as e:  # 初回のモデルのダウンロード失敗（オフライン・プロキシ）など
            raise TranscriptionUnavailable(
                f"Whisper のモデル（{model_size}）を読み込めませんでした。初回はモデルのダウンロード（small で約500MB）が必要です。"
                f"インターネットにつながっているか確認して「やり直す」を押してください。（詳細: {type(e).__name__}: {e}）"
            ) from e
        _MODELS[model_size] = model
    kwargs = {"language": language or None, "beam_size": 5, "vad_filter": not quiet}
    if vocabulary:
        kwargs["initial_prompt"] = "、".join(vocabulary)[:400]
    if quiet:
        kwargs["no_speech_threshold"] = 0.8   # 既定 0.6。小さい声を「無音」と判定しにくくする
        kwargs["log_prob_threshold"] = -1.5   # 既定 -1.0
    segments, info = model.transcribe(path, **kwargs)
    total = float(getattr(info, "duration", 0) or 0)
    out = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            out.append({"speaker": "", "start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
        if progress:
            progress(seg.end, total)
    return out, total
