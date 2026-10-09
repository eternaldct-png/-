"""
投稿文を「自分の声」で読み上げる — Gemini TTS（Gemini API）呼び出し

声は Google AI Studio の「Voice Replication」で作っておき、返ってきた声ID
（voice_... / voicekey_...）を環境変数 GEMINI_TTS_VOICE に入れて使う。
動作確認用に、Kore などの既製の声の名前を入れることもできる。

環境変数:
  GEMINI_API_KEY    — Gemini API キー（必須。有料枠のプロジェクトのキー推奨）
  GEMINI_TTS_VOICE  — 声ID（voice_... / voicekey_...）または既製の声の名前
  GEMINI_TTS_MODEL  — 省略時 gemini-3.8-flash-tts（安くするなら gemini-3.8-flash-lite-tts）
"""
import base64
import io
import os
import re
import wave

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash-tts"
MAX_CHARS = 2000          # 投稿ジェネレーターの最大文字数（note 用）に合わせる
REQUEST_TIMEOUT = 90      # gunicorn の --timeout 120 より短くする
DEFAULT_SAMPLE_RATE = 24000

_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_RE = re.compile(r"[#＃][^\s#＃]+")
_BLANK_RE = re.compile(r"[ \t　]+")


class TTSError(Exception):
    """読み上げに失敗したとき（メッセージはそのまま画面に出す）"""


def tts_settings():
    return {
        "api_key": os.environ.get("GEMINI_API_KEY", "").strip(),
        "voice": os.environ.get("GEMINI_TTS_VOICE", "").strip(),
        "model": os.environ.get("GEMINI_TTS_MODEL", "").strip() or DEFAULT_MODEL,
    }


def clean_text_for_speech(text):
    """URL とハッシュタグは読み上げても意味がないので外す"""
    text = _URL_RE.sub("", text or "")
    text = _HASHTAG_RE.sub("", text)
    lines = [_BLANK_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def voice_config(voice):
    # Voice Replication / Voice Design で作った声は ID で指定する
    if voice.startswith(("voice_", "voicekey_")):
        return {"voice": voice}
    return {"prebuiltVoiceConfig": {"voiceName": voice}}


def build_request_body(text, voice):
    return {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": voice_config(voice)},
        },
    }


def pcm_to_wav(pcm, sample_rate=DEFAULT_SAMPLE_RATE):
    """16bit・モノラルの生PCMに WAV ヘッダーを付ける"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def audio_to_wav(data, mime_type):
    """API が返した音声を WAV にそろえる（WAV ならそのまま、生PCMならヘッダーを付ける）"""
    if data[:4] == b"RIFF":
        return data
    m = re.search(r"rate=(\d+)", mime_type or "")
    return pcm_to_wav(data, int(m.group(1)) if m else DEFAULT_SAMPLE_RATE)


def _api_error_message(resp):
    try:
        message = resp.json().get("error", {}).get("message", "")
    except ValueError:
        message = ""
    return f"Gemini API エラー（{resp.status_code}）: {message or resp.reason}"[:300]


def synthesize(text, settings=None):
    """テキストを読み上げた WAV（bytes）を返す"""
    settings = settings or tts_settings()
    if not settings["api_key"]:
        raise TTSError("GEMINI_API_KEY が未設定です（Render の環境変数を確認してください）")
    if not settings["voice"]:
        raise TTSError("GEMINI_TTS_VOICE（自分の声のID）が未設定です")
    if len(text) > MAX_CHARS:
        raise TTSError(f"読み上げは {MAX_CHARS} 文字までです")

    try:
        resp = requests.post(
            f"{API_BASE}/models/{settings['model']}:generateContent",
            headers={"x-goog-api-key": settings["api_key"], "Content-Type": "application/json"},
            json=build_request_body(text, settings["voice"]),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        raise TTSError("音声の生成に時間がかかりすぎました。文章を短くしてもう一度お試しください")
    except requests.RequestException:
        raise TTSError("Gemini API に接続できませんでした")

    if resp.status_code != 200:
        raise TTSError(_api_error_message(resp))

    try:
        for part in resp.json()["candidates"][0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime_type = inline.get("mimeType") or inline.get("mime_type") or ""
                return audio_to_wav(base64.b64decode(inline["data"]), mime_type)
    except (ValueError, KeyError, IndexError, TypeError):
        pass
    raise TTSError("音声が返ってきませんでした。文章を変えてもう一度お試しください")
