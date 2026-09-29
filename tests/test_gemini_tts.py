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


def _gemini_wav(pcm: bytes, rate: int = 24000) -> bytes:
    """Gemini 3.8 系が返す形式: fmt / data の後ろに C2PA チャンクが付いた完全な WAV"""
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    body = buf.getvalue()
    c2pa = b"C2PA" + (8).to_bytes(4, "little") + b"metadata"
    riff_size = (len(body) - 8 + len(c2pa)).to_bytes(4, "little")
    return b"RIFF" + riff_size + body[8:] + c2pa


class WavResponseTest(unittest.TestCase):
    def test_wav_response_is_not_played_as_pcm(self):
        """ヘッダーや C2PA を音声として鳴らさない（「ブツッ」「ザザザ」ノイズの原因だった）"""
        pcm = b"\x10\x00" * 240
        blob = _gemini_wav(pcm, rate=24000)
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"candidates": [{"content": {"parts": [{"inlineData": {
            "mimeType": "audio/wav", "data": base64.b64encode(blob).decode()}}]}}]}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, {"GEMINI_API_KEY": "k"}), \
                patch.object(gemini_tts.requests, "post", return_value=resp):
            path, _ = gemini_tts.text_to_speech("テスト", output=Path(tmp) / "out.wav")
            # 保存したファイルは API が返した WAV そのもの（C2PA の来歴情報を保持）
            self.assertEqual(path.read_bytes(), blob)
            with wave.open(str(path)) as wf:
                self.assertEqual(wf.readframes(wf.getnframes()), pcm)


class BuildRequestTest(unittest.TestCase):
    def test_single_speaker(self):
        body = gemini_tts.build_request("こんにちは", voice="Puck")
        self.assertEqual(body["contents"][0]["parts"][0]["text"], "こんにちは")
        cfg = body["generationConfig"]
        self.assertEqual(cfg["responseModalities"], ["AUDIO"])
        self.assertEqual(
            cfg["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"], "Puck")

    def test_style_goes_to_speech_metadata_not_text(self):
        # 本文に混ぜると指示文まで読み上げられてしまう（実機で確認済み）
        part = gemini_tts.build_request("こんにちは", style="明るく")["contents"][0]["parts"][0]
        self.assertEqual(part["text"], "こんにちは")
        self.assertEqual(part["speechMetadata"], {"style": "明るく"})
        self.assertNotIn("speechMetadata", gemini_tts.build_request("こんにちは")["contents"][0]["parts"][0])

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
            path, used = gemini_tts.text_to_speech("テスト", output=Path(tmp) / "out.wav")
            self.assertEqual(used, gemini_tts.DEFAULT_MODEL)
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


def _quota_response(retry_delay: str | None = None, daily: bool = False) -> MagicMock:
    details = []
    if retry_delay:
        details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay})
    quota_id = "GenerateRequestsPerDayPerProjectPerModel-FreeTier" if daily \
        else "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"
    details.append({"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaId": quota_id}]})
    resp = MagicMock(status_code=429)
    resp.json.return_value = {"error": {"code": 429, "message": "quota", "details": details}}
    return resp


class FreeTierQuotaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "out.wav"
        env = patch.dict(os.environ, {"GEMINI_API_KEY": "k"})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GEMINI_TTS_MODEL", None)
        os.environ.pop("GEMINI_TTS_FALLBACK_MODELS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_per_minute_limit_waits_and_retries(self):
        responses = [_quota_response("5s"), _fake_response(b"\x00\x00")]
        with patch.object(gemini_tts.requests, "post", side_effect=responses) as post, \
                patch.object(gemini_tts.time, "sleep") as sleep:
            _, used = gemini_tts.text_to_speech("テスト", output=self.out)
        sleep.assert_called_once_with(6.0)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(used, gemini_tts.DEFAULT_MODEL)

    def test_daily_limit_falls_back_to_lite_without_waiting(self):
        responses = [_quota_response("30s", daily=True), _fake_response(b"\x00\x00")]
        with patch.object(gemini_tts.requests, "post", side_effect=responses) as post, \
                patch.object(gemini_tts.time, "sleep") as sleep:
            _, used = gemini_tts.text_to_speech("テスト", output=self.out)
        sleep.assert_not_called()
        self.assertEqual(used, "gemini-3.8-flash-lite-tts")
        self.assertIn("/gemini-3.8-flash-lite-tts:", post.call_args_list[1].args[0])

    def test_all_models_exhausted(self):
        with patch.object(gemini_tts.requests, "post", return_value=_quota_response(daily=True)):
            with self.assertRaisesRegex(gemini_tts.GeminiQuotaError, "1日あたり"):
                gemini_tts.text_to_speech("テスト", output=self.out)
        self.assertFalse(self.out.exists())

    def test_fallback_can_be_disabled(self):
        os.environ["GEMINI_TTS_FALLBACK_MODELS"] = "none"
        with patch.object(gemini_tts.requests, "post", return_value=_quota_response(daily=True)) as post:
            with self.assertRaises(gemini_tts.GeminiQuotaError):
                gemini_tts.text_to_speech("テスト", output=self.out)
        self.assertEqual(post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
