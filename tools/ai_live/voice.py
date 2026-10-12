"""セリフを音声にして再生する（VOICEVOX）。

VOICEVOX（無料）をPCで起動しておくと http://127.0.0.1:50021 で音声合成できる。
再生は追加ライブラリなしで動くようにしている:
  - Windows: winsound（標準ライブラリ）
  - Mac: afplay / Linux: aplay
sounddevice と numpy を入れて config の voice.output_device を指定すると、
仮想オーディオ（VB-CABLE など）に直接流せる（VTube Studio の口パク連動用）。
"""

from __future__ import annotations

import io
import logging
import os
import subprocess
import sys
import tempfile
import wave

import requests

log = logging.getLogger("ai_live.voice")


class Voice:
    def __init__(self, voice_cfg: dict):
        self.cfg = voice_cfg
        self.enabled = voice_cfg.get("engine", "voicevox") == "voicevox"
        self.url = voice_cfg.get("voicevox_url", "http://127.0.0.1:50021").rstrip("/")

    def check(self) -> bool:
        if not self.enabled:
            return False
        try:
            requests.get(f"{self.url}/version", timeout=3).raise_for_status()
            return True
        except requests.RequestException:
            log.error("VOICEVOX に接続できません（%s）。VOICEVOX を起動してください。字幕だけで続けます", self.url)
            self.enabled = False
            return False

    def synthesize(self, text: str) -> bytes | None:
        if not self.enabled or not text:
            return None
        speaker = self.cfg.get("speaker_id", 3)
        try:
            q = requests.post(f"{self.url}/audio_query", params={"text": text, "speaker": speaker}, timeout=10)
            q.raise_for_status()
            query = q.json()
            query["speedScale"] = self.cfg.get("speed", 1.0)
            s = requests.post(f"{self.url}/synthesis", params={"speaker": speaker}, json=query, timeout=30)
            s.raise_for_status()
            return s.content
        except requests.RequestException as e:
            log.error("音声合成に失敗しました: %s", e)
            return None

    def play(self, wav: bytes) -> None:
        device = self.cfg.get("output_device") or ""
        if device and _play_sounddevice(wav, device):
            return
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(wav, winsound.SND_MEMORY)
            return
        player = ["afplay"] if sys.platform == "darwin" else ["aplay", "-q"]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav)
            path = f.name
        try:
            subprocess.run(player + [path], check=False)
        finally:
            os.unlink(path)


def wav_seconds(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / float(w.getframerate())


def _play_sounddevice(wav: bytes, device_name: str) -> bool:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        log.warning("output_device を使うには `pip install sounddevice numpy` が必要です。既定のスピーカーで再生します")
        return False
    with wave.open(io.BytesIO(wav)) as w:
        frames = w.readframes(w.getnframes())
        rate, channels = w.getframerate(), w.getnchannels()
    data = np.frombuffer(frames, dtype=np.int16).reshape(-1, channels)
    try:
        sd.play(data, rate, device=device_name)
        sd.wait()
        return True
    except (ValueError, sd.PortAudioError) as e:
        log.warning("出力デバイス「%s」で再生できません（%s）。既定のスピーカーで再生します", device_name, e)
        return False
