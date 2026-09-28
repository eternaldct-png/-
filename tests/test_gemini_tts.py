import base64
import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from src import gemini_tts


def _fake_response(pcm: bytes, rate: int = 24000, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "candidates": [{
            "content": {"parts": [{
                "inlineData": {
                    "mimeType": f"audio/L16;codec=pcm;rate={rate}",
                    "data": base64.b64encode(pcm).decode(),
                }
            }]}
        }]
    }
    return resp


class BuildRequestTest(unittest.TestCase):
    def test_single_speaker(self):
        body = gemini_tts.build_request("こんにちは", voice="Puck")
        self.assertEqual(body["contents"][0]["parts"][0]["text"], "こんにちは")
        cfg = body["generationConfig"]
        self.assertEqual(cfg["responseModalities"], ["AUDIO"])
        self.assertEqual(
            cfg["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"], "Puck")

    def test_style_is_prepended(self):
        body = gemini_tts.build_request("こんにちは", style="明るく")
        text = body["contents"][0]["parts"][0]["text"]
        self.assertIn("明るく", text)
        self.assertTrue(text.endswith("こんにちは"))

    def test_multi_speaker(self):
        body = gemini_tts.build_request(
            "kazuto: やあ\nあまりん: こんにちは", speakers={"kazuto": "Puck", "あまりん": "Kore"})
        configs = body["generationConfig"]["speechConfig"]["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]
        self.assertEqual([c["speaker"] for c in configs], ["kazuto", "あまりん"])
        self.assertEqual(configs[1]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"], "Kore")

    def test_rejects_empty_text_and_three_speakers(self):
        with self.assertRaises(gemini_tts.GeminiTTSError):
            gemini_tts.build_request("  ")
        with self.assertRaises(gemini_tts.GeminiTTSError):
            gemini_tts.build_request("a", speakers={"a": "Kore", "b": "Puck", "c": "Leda"})

    def test_parse_speakers(self):
        self.assertEqual(gemini_tts.parse_speakers("kazuto=Puck, あまりん=Kore"),
                         {"kazuto": "Puck", "あまりん": "Kore"})
        with self.assertRaises(gemini_tts.GeminiTTSError):
            gemini_tts.parse_speakers("kazuto")


class TextToSpeechTest(unittest.TestCase):
    def test_saves_wav_with_rate_from_response(self):
        pcm = b"\x01\x00" * 480
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False), \
                patch.object(gemini_tts.requests, "post", return_value=_fake_response(pcm, 16000)) as post:
            path = gemini_tts.text_to_speech("テスト", output=Path(tmp) / "out.wav")
            with wave.open(str(path)) as wf:
                self.assertEqual(wf.getframerate(), 16000)
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.readframes(wf.getnframes()), pcm)
        url = post.call_args.args[0]
        self.assertTrue(url.endswith(f"/{gemini_tts.DEFAULT_MODEL}:generateContent"))
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")

    def test_model_env_override(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, {"GEMINI_API_KEY": "k", "GEMINI_TTS_MODEL": "gemini-3.8-flash-lite-tts"}), \
                patch.object(gemini_tts.requests, "post", return_value=_fake_response(b"\x00\x00")) as post:
            gemini_tts.text_to_speech("テスト", output=Path(tmp) / "out.wav")
        self.assertIn("/gemini-3.8-flash-lite-tts:generateContent", post.call_args.args[0])

    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(gemini_tts.GeminiTTSError):
                gemini_tts.synthesize("テスト")

    def test_api_error_message(self):
        resp = MagicMock(status_code=404)
        resp.json.return_value = {"error": {"message": "model not found"}}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k"}), \
                patch.object(gemini_tts.requests, "post", return_value=resp):
            with self.assertRaisesRegex(gemini_tts.GeminiTTSError, "model not found"):
                gemini_tts.synthesize("テスト")

    def test_no_audio_in_response(self):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"promptFeedback": {"blockReason": "SAFETY"}}
        with patch.dict(os.environ, {"GEMINI_API_KEY": "k"}), \
                patch.object(gemini_tts.requests, "post", return_value=resp):
            with self.assertRaisesRegex(gemini_tts.GeminiTTSError, "SAFETY"):
                gemini_tts.synthesize("テスト")


if __name__ == "__main__":
    unittest.main()
