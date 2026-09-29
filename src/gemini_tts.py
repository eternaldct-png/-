"""
Gemini TTS（Gemini 3.8 Flash TTS）で音声を生成するモジュール

Claude Code からは MCP サーバー（src/mcp_gemini_tts.py）経由で呼び出すほか、
CLI としても直接使える:

    python3 src/gemini_tts.py "こんにちは、ETERNAL d.c.t です" --voice Kore --style "明るく元気に"
    python3 src/gemini_tts.py --file script.txt -o media/tts_output/intro.wav
    python3 src/gemini_tts.py "kazuto: やあ\\nあまりん: こんにちは" --speakers "kazuto=Puck,あまりん=Kore"

必要な環境変数:
    GEMINI_API_KEY    Google AI Studio で発行した API キー
    GEMINI_TTS_MODEL  （任意）使うモデル。デフォルト: gemini-3.8-flash-tts
                      安く大量に作るなら gemini-3.8-flash-lite-tts
    GEMINI_TTS_FALLBACK_MODELS
                      （任意）無料枠の上限（HTTP 429）に達したときに順に試すモデル（カンマ区切り）。
                      デフォルト: gemini-3.8-flash-lite-tts。無効にするなら "none"
                      無料枠の上限はモデルごとに別枠なので、切り替えると続けて作れることがある。

API のレスポンスは生の PCM（16bit / 24kHz / モノラル）なので、WAV ヘッダーを付けて保存する。
.mp3 を指定した場合は ffmpeg があれば変換する。
"""
import argparse
import base64
import io
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.8-flash-tts"
DEFAULT_FALLBACK_MODELS = "gemini-3.8-flash-lite-tts"
DEFAULT_VOICE = "Kore"
# 1分あたりの上限に当たったとき、この秒数以内の待ち指示なら待って1回だけ再試行する
MAX_RETRY_WAIT_SECONDS = 60
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "media" / "tts_output"
REQUEST_TIMEOUT = 180

# Gemini TTS のプリセット音声（30種）。キャラクターは Google 公式の説明より
PREBUILT_VOICES = {
    "Zephyr": "明るい", "Puck": "アップビート", "Charon": "情報的",
    "Kore": "しっかり", "Fenrir": "興奮気味", "Leda": "若々しい",
    "Orus": "しっかり", "Aoede": "軽やか", "Callirrhoe": "おおらか",
    "Autonoe": "明るい", "Enceladus": "息まじり", "Iapetus": "クリア",
    "Umbriel": "おおらか", "Algieba": "なめらか", "Despina": "なめらか",
    "Erinome": "クリア", "Algenib": "しゃがれ声", "Rasalgethi": "情報的",
    "Laomedeia": "アップビート", "Achernar": "ソフト", "Alnilam": "しっかり",
    "Schedar": "落ち着き", "Gacrux": "大人っぽい", "Pulcherrima": "前向き",
    "Achird": "親しみやすい", "Zubenelgenubi": "カジュアル",
    "Vindemiatrix": "やさしい", "Sadachbia": "生き生き",
    "Sadaltager": "知的", "Sulafat": "あたたかい",
}


class GeminiTTSError(RuntimeError):
    pass


class GeminiQuotaError(GeminiTTSError):
    """無料枠などの利用上限（HTTP 429）に達した"""

    def __init__(self, message: str, retry_after: float | None = None, daily: bool = False):
        super().__init__(message)
        self.retry_after = retry_after
        self.daily = daily


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise GeminiTTSError(
            "GEMINI_API_KEY が設定されていません。"
            "Google AI Studio（https://aistudio.google.com/apikey）でキーを発行して環境変数に設定してください。"
        )
    return key


def _voice_config(voice: str) -> dict:
    return {"prebuiltVoiceConfig": {"voiceName": voice}}


def build_request(text: str, voice: str = DEFAULT_VOICE, style: str = "",
                  speakers: dict[str, str] | None = None) -> dict:
    """generateContent 用のリクエストボディを組み立てる

    style: 読み上げ方の指示（例: "明るく元気に"、"ささやくように"）。speechMetadata.style として渡す。
    speakers: {話者名: 音声名}。2人までの掛け合い。text は「話者名: セリフ」の行で書く。
    """
    if not text.strip():
        raise GeminiTTSError("読み上げるテキストが空です。")
    # 読み方の指示は本文に混ぜると指示文まで読み上げられるため、speechMetadata.style で渡す
    part = {"text": text}
    if style:
        part["speechMetadata"] = {"style": style}

    if speakers:
        if len(speakers) > 2:
            raise GeminiTTSError("複数話者は2人までです。")
        speech_config = {
            "multiSpeakerVoiceConfig": {
                "speakerVoiceConfigs": [
                    {"speaker": name, "voiceConfig": _voice_config(v)}
                    for name, v in speakers.items()
                ]
            }
        }
    else:
        speech_config = {"voiceConfig": _voice_config(voice)}

    return {
        "contents": [{"parts": [part]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": speech_config,
        },
    }


def _decode_wav(blob: bytes) -> tuple[bytes, int]:
    """WAV ファイルのバイト列から PCM（16bit モノラル）とサンプリングレートを取り出す

    Gemini 3.8 系は生の PCM ではなく完全な WAV（fmt / data / C2PA チャンク）を返す。
    そのまま PCM 扱いするとヘッダーや C2PA（AI生成の来歴情報）を音として鳴らしてしまい、
    「ブツ」「ザザザ」というノイズになる。wave モジュールは data チャンクだけを読むので安全。
    """
    try:
        with wave.open(io.BytesIO(blob)) as wf:
            channels, width, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    except (wave.Error, EOFError) as e:
        raise GeminiTTSError(f"返ってきた WAV を読み取れませんでした: {e}")
    if channels != 1 or width != 2:
        raise GeminiTTSError(f"未対応の音声形式です（{channels}ch / {width * 8}bit）")
    return frames, rate


def _extract_audio(data: dict) -> tuple[bytes, int, bytes | None]:
    """レスポンスから (PCM, サンプリングレート, 元の WAV ファイル or None) を取り出す

    元の WAV は C2PA（AI生成であることを示す来歴情報）を含むので、保存時はそのまま書き出す。
    """
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        reason = (data.get("promptFeedback") or {}).get("blockReason") or \
            ((data.get("candidates") or [{}])[0].get("finishReason"))
        raise GeminiTTSError(f"音声が返ってきませんでした（理由: {reason or '不明'}）")

    pcm = b""
    rate = 24000
    wav_files = []
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if not inline:
            continue
        blob = base64.b64decode(inline["data"])
        if blob[:4] == b"RIFF":
            chunk, rate = _decode_wav(blob)
            pcm += chunk
            wav_files.append(blob)
            continue
        pcm += blob  # 旧モデル（2.5 系など）は生の PCM（16bit little-endian）
        m = re.search(r"rate=(\d+)", inline.get("mimeType") or inline.get("mime_type") or "")
        if m:
            rate = int(m.group(1))
    if not pcm:
        raise GeminiTTSError("レスポンスに音声データが含まれていませんでした。")
    original = wav_files[0] if len(wav_files) == 1 and len(parts) == 1 else None
    return pcm, rate, original


def _quota_error(resp, model: str) -> GeminiQuotaError:
    """429 レスポンスから待ち秒数（RetryInfo）と「1日の上限かどうか」（QuotaFailure）を読み取る"""
    try:
        error = resp.json()["error"]
    except Exception:
        error = {}
    retry_after = None
    daily = False
    for detail in error.get("details") or []:
        m = re.fullmatch(r"([\d.]+)s", str(detail.get("retryDelay", "")))
        if m:
            retry_after = float(m.group(1))
        for violation in detail.get("violations") or []:
            if "PerDay" in str(violation.get("quotaId", "")):
                daily = True
    kind = "1日あたり" if daily else "1分あたり"
    return GeminiQuotaError(
        f"{model} の{kind}の利用上限に達しました（HTTP 429）。"
        + ("明日（日本時間16〜17時ごろ＝米国太平洋時間の0時）にリセットされます。" if daily else "少し待ってから再実行してください。"),
        retry_after=retry_after, daily=daily,
    )


def synthesize(text: str, voice: str = DEFAULT_VOICE, style: str = "",
               speakers: dict[str, str] | None = None,
               model: str | None = None) -> tuple[bytes, int, bytes | None]:
    """Gemini TTS を呼び出して (PCM バイト列, サンプリングレート, 元の WAV or None) を返す

    1分あたりの上限（429）で API が短い待ち時間を指示してきた場合は、待って1回だけ再試行する。
    """
    model = model or os.environ.get("GEMINI_TTS_MODEL") or DEFAULT_MODEL
    body = build_request(text, voice=voice, style=style, speakers=speakers)
    for attempt in range(2):
        resp = requests.post(
            f"{API_BASE}/{model}:generateContent",
            headers={"x-goog-api-key": _api_key(), "Content-Type": "application/json"},
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            return _extract_audio(resp.json())
        if resp.status_code != 429:
            try:
                message = resp.json()["error"]["message"]
            except Exception:
                message = resp.text[:500]
            raise GeminiTTSError(f"Gemini API エラー（HTTP {resp.status_code}, model={model}）: {message}")

        err = _quota_error(resp, model)
        wait = err.retry_after
        if attempt == 0 and not err.daily and wait is not None and wait <= MAX_RETRY_WAIT_SECONDS:
            print(f"[gemini_tts] {model} の1分あたりの上限に達したため {wait:.0f} 秒待って再試行します",
                  file=sys.stderr)
            time.sleep(wait + 1)
            continue
        raise err


def _model_chain(model: str | None) -> list[str]:
    """最初に使うモデル + 無料枠切れのときの切り替え先（重複なし）"""
    first = model or os.environ.get("GEMINI_TTS_MODEL") or DEFAULT_MODEL
    fallbacks = os.environ.get("GEMINI_TTS_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS)
    chain = [first]
    if fallbacks.strip().lower() != "none":
        chain += [m.strip() for m in fallbacks.split(",") if m.strip()]
    return list(dict.fromkeys(chain))


def ffmpeg_exe() -> str | None:
    """ffmpeg のパス。PATH になければ pip の imageio-ffmpeg に同梱のバイナリを使う"""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def save_audio(pcm: bytes, rate: int, output: Path, original_wav: bytes | None = None) -> Path:
    """音声を .wav で保存する。拡張子が .mp3 なら ffmpeg で変換する

    original_wav（API が返した WAV ファイル）があれば、C2PA の来歴情報ごとそのまま書き出す。
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    wav_path = output.with_suffix(".wav")
    if original_wav:
        wav_path.write_bytes(original_wav)
    else:
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    if output.suffix.lower() != ".mp3":
        return wav_path
    ffmpeg = ffmpeg_exe()
    if not ffmpeg:
        raise GeminiTTSError(f"mp3 変換には ffmpeg が必要です（WAV は保存済み: {wav_path}）")
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav_path), "-b:a", "192k", str(output)],
        check=True,
    )
    wav_path.unlink()
    return output


def default_output_path(fmt: str = "wav") -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"tts_{stamp}.{fmt}"


def text_to_speech(text: str, output: str | Path | None = None, voice: str = DEFAULT_VOICE,
                   style: str = "", speakers: dict[str, str] | None = None,
                   model: str | None = None) -> tuple[Path, str]:
    """テキストを読み上げて音声ファイルに保存し、(保存先パス, 実際に使ったモデル) を返す

    利用上限（429）に当たったら GEMINI_TTS_FALLBACK_MODELS のモデルに切り替えて作り直す。
    """
    errors = []
    for m in _model_chain(model):
        try:
            pcm, rate, original = synthesize(text, voice=voice, style=style, speakers=speakers, model=m)
        except GeminiQuotaError as e:
            errors.append(str(e))
            continue
        path = Path(output) if output else default_output_path()
        return save_audio(pcm, rate, path, original), m
    raise GeminiQuotaError(" / ".join(errors))


def parse_speakers(spec: str) -> dict[str, str]:
    """ "kazuto=Puck,あまりん=Kore" → {"kazuto": "Puck", "あまりん": "Kore"} """
    result = {}
    for item in filter(None, (s.strip() for s in spec.split(","))):
        if "=" not in item:
            raise GeminiTTSError(f"話者指定の形式が不正です: {item}（例: kazuto=Puck）")
        name, voice = (s.strip() for s in item.split("=", 1))
        result[name] = voice
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gemini TTS で音声ファイルを生成する")
    parser.add_argument("text", nargs="?", help="読み上げるテキスト（\\n で改行）")
    parser.add_argument("--file", help="読み上げるテキストファイル")
    parser.add_argument("-o", "--output", help="保存先（.wav / .mp3）。省略時は media/tts_output/")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"音声名（デフォルト: {DEFAULT_VOICE}）")
    parser.add_argument("--style", default="", help="読み上げ方の指示（例: 明るく元気に）")
    parser.add_argument("--speakers", help="2人の掛け合い。例: kazuto=Puck,あまりん=Kore")
    parser.add_argument("--model", help=f"モデル名（デフォルト: $GEMINI_TTS_MODEL または {DEFAULT_MODEL}）")
    parser.add_argument("--list-voices", action="store_true", help="使える音声の一覧を表示")
    args = parser.parse_args(argv)

    if args.list_voices:
        for name, desc in PREBUILT_VOICES.items():
            print(f"{name:15s} {desc}")
        return 0

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text.replace("\\n", "\n")
    else:
        parser.error("テキストか --file を指定してください")

    try:
        path, used_model = text_to_speech(
            text, output=args.output, voice=args.voice, style=args.style,
            speakers=parse_speakers(args.speakers) if args.speakers else None,
            model=args.model,
        )
    except GeminiTTSError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(f"{path}  (model: {used_model})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
