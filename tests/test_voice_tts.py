import base64
import io
import os
import unittest
import wave
from unittest.mock import MagicMock, patch

from src import web_app
import voice_tts  # web_app と同じモジュール（src を sys.path に入れて読み込まれる）


def _api_response(data, mime_type="audio/L16;codec=pcm;rate=24000", status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"inlineData": {
            "mimeType": mime_type,
            "data": base64.b64encode(data).decode(),
        }}]}}]
    }
    return resp


SETTINGS = {"api_key": "test-key", "voice": "voice_abc123", "model": "gemini-3.8-flash-tts"}


class VoiceTTSTest(unittest.TestCase):
    def test_clean_text_removes_urls_and_hashtags(self):
        text = "今日も配信するよ！\nhttps://example.com/live\n#ColorSing #歌ってみた"
        self.assertEqual(voice_tts.clean_text_for_speech(text), "今日も配信するよ！")

    def test_replicated_voice_id_and_prebuilt_voice(self):
        body = voice_tts.build_request_body("こんにちは", "voice_abc123")
        self.assertEqual(body["generationConfig"]["responseModalities"], ["AUDIO"])
        self.assertEqual(
            body["generationConfig"]["speechConfig"]["voiceConfig"], {"voice": "voice_abc123"}
        )
        self.assertEqual(voice_tts.voice_config("voicekey_xyz"), {"voice": "voicekey_xyz"})
        self.assertEqual(
            voice_tts.voice_config("Kore"), {"prebuiltVoiceConfig": {"voiceName": "Kore"}}
        )

    def test_pcm_is_wrapped_as_wav_with_sample_rate(self):
        pcm = b"\x00\x01" * 2400
        with patch.object(voice_tts.requests, "post", return_value=_api_response(pcm)) as post:
            wav = voice_tts.synthesize("こんにちは", SETTINGS)

        url = post.call_args.args[0]
        self.assertTrue(url.endswith("/models/gemini-3.8-flash-tts:generateContent"))
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-key")
        with wave.open(io.BytesIO(wav)) as wf:
            self.assertEqual(wf.getframerate(), 24000)
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.readframes(wf.getnframes()), pcm)

    def test_wav_from_api_is_returned_as_is(self):
        wav = voice_tts.pcm_to_wav(b"\x00\x00" * 10, 48000)
        with patch.object(voice_tts.requests, "post", return_value=_api_response(wav, "audio/wav")):
            self.assertEqual(voice_tts.synthesize("こんにちは", SETTINGS), wav)

    def test_missing_settings_and_api_errors_raise_tts_error(self):
        with self.assertRaisesRegex(voice_tts.TTSError, "GEMINI_API_KEY"):
            voice_tts.synthesize("こんにちは", {**SETTINGS, "api_key": ""})
        with self.assertRaisesRegex(voice_tts.TTSError, "GEMINI_TTS_VOICE"):
            voice_tts.synthesize("こんにちは", {**SETTINGS, "voice": ""})

        error = MagicMock(status_code=404, reason="Not Found")
        error.json.return_value = {"error": {"message": "Voice not found"}}
        with patch.object(voice_tts.requests, "post", return_value=error):
            with self.assertRaisesRegex(voice_tts.TTSError, "404.*Voice not found"):
                voice_tts.synthesize("こんにちは", SETTINGS)


class VoiceTTSRouteTest(unittest.TestCase):
    def setUp(self):
        self.client = web_app.app.test_client()

    def test_generator_page_has_read_aloud_button(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("speakPost(${i})", html)
        self.assertIn('id="pwModal"', html)

    def test_tts_requires_login(self):
        with patch.object(voice_tts, "synthesize") as synth:
            response = self.client.post("/api/tts", json={"text": "こんにちは"})
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.get_json()["need_login"])
        synth.assert_not_called()

    def test_login_checks_web_password(self):
        with patch.dict(os.environ, {"WEB_PASSWORD": "secret"}):
            bad = self.client.post("/api/tts/login", json={"password": "wrong"})
            good = self.client.post("/api/tts/login", json={"password": "secret"})
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(good.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertTrue(session.get("tts_ok"))

    def test_login_is_disabled_without_web_password(self):
        with patch.dict(os.environ, {"WEB_PASSWORD": ""}):
            response = self.client.post("/api/tts/login", json={"password": ""})
        self.assertEqual(response.status_code, 503)

    def test_logged_in_user_gets_wav(self):
        with self.client.session_transaction() as session:
            session["tts_ok"] = True
        with patch.object(voice_tts, "synthesize", return_value=b"RIFFwav") as synth:
            response = self.client.post(
                "/api/tts", json={"text": "配信するよ！ #ColorSing https://example.com"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/wav")
        self.assertEqual(response.data, b"RIFFwav")
        synth.assert_called_once_with("配信するよ！")

    def test_tts_error_is_returned_as_message(self):
        with self.client.session_transaction() as session:
            session["tts_ok"] = True
        with patch.object(voice_tts, "synthesize", side_effect=voice_tts.TTSError("声IDが未設定")):
            response = self.client.post("/api/tts", json={"text": "こんにちは"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"], "声IDが未設定")

    def test_non_json_request_is_rejected(self):
        with self.client.session_transaction() as session:
            session["tts_ok"] = True
        with patch.object(voice_tts, "synthesize") as synth:
            response = self.client.post(
                "/api/tts", data='{"text": "こんにちは"}', content_type="text/plain"
            )
        self.assertEqual(response.status_code, 400)
        synth.assert_not_called()


if __name__ == "__main__":
    unittest.main()
