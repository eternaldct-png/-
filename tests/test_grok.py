import base64
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import generate  # noqa: E402
import grok_client  # noqa: E402
import research  # noqa: E402

_spec = importlib.util.spec_from_file_location("grok_video", ROOT / "tools/grok/video.py")
video = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(video)

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _response(status=200, payload=None):
    res = MagicMock()
    res.status_code = status
    res.json.return_value = payload or {}
    res.text = str(payload)
    return res


class GrokClientTest(unittest.TestCase):
    def test_parse_response_output_collects_text_and_citations(self):
        data = {"output": [
            {"type": "reasoning", "summary": []},
            {"type": "x_search_call"},
            {"type": "message", "content": [{
                "type": "output_text", "text": "こんにちは",
                "annotations": [{"type": "url_citation", "url": "https://x.com/a/status/1"}],
            }]},
        ]}
        self.assertEqual(grok_client.parse_response_output(data), ("こんにちは", ["https://x.com/a/status/1"]))

    @patch.dict(os.environ, {"XAI_API_KEY": "test-key", "GROK_MODEL": "", "GROK_REASONING_EFFORT": ""})
    def test_chat_sends_tools_and_reasoning(self):
        payload = {"output": [{"type": "message", "content": [{"text": "ok"}]}]}
        with patch.object(grok_client.requests, "request", return_value=_response(payload=payload)) as req:
            text, _ = grok_client.chat("sys", "user", tools=[grok_client.x_search_tool(from_date="2026-10-01")])
        self.assertEqual(text, "ok")
        body = req.call_args.kwargs["json"]
        self.assertEqual(req.call_args.args[1], "https://api.x.ai/v1/responses")
        self.assertEqual(req.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(body["model"], "grok-latest")
        self.assertEqual(body["tools"], [{"type": "x_search", "from_date": "2026-10-01"}])
        self.assertEqual(body["reasoning"], {"effort": "low"})

    @patch.dict(os.environ, {"XAI_API_KEY": "k", "GROK_MODEL": "grok-4.20-non-reasoning"})
    def test_chat_skips_reasoning_for_grok_4_20(self):
        payload = {"output": [{"type": "message", "content": [{"text": "ok"}]}]}
        with patch.object(grok_client.requests, "request", return_value=_response(payload=payload)) as req:
            grok_client.chat("sys", "user")
        self.assertNotIn("reasoning", req.call_args.kwargs["json"])

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    def test_api_error_message(self):
        res = _response(400, {"error": {"message": "bad prompt"}})
        with patch.object(grok_client.requests, "request", return_value=res):
            with self.assertRaisesRegex(grok_client.GrokError, "400: bad prompt"):
                grok_client.chat("sys", "user")

    @patch.dict(os.environ, {"XAI_API_KEY": ""})
    def test_missing_key(self):
        self.assertFalse(grok_client.is_configured())
        with self.assertRaisesRegex(grok_client.GrokError, "XAI_API_KEY"):
            grok_client.chat("sys", "user")

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    def test_generate_images_saves_files(self):
        png = b"\x89PNG\r\n\x1a\nfake"
        payload = {"data": [{"b64_json": base64.b64encode(png).decode()}]}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(grok_client.requests, "request", return_value=_response(payload=payload)) as req:
            paths = grok_client.generate_images("cat", Path(tmp), aspect_ratio="4:5")
            self.assertEqual(paths[0].read_bytes(), png)
            self.assertEqual(paths[0].suffix, ".png")
        self.assertTrue(req.call_args.args[1].endswith("/images/generations"))
        self.assertEqual(req.call_args.kwargs["json"]["aspect_ratio"], "4:5")

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    def test_generate_images_with_reference_uses_edits(self):
        payload = {"data": [{"b64_json": base64.b64encode(b"\xff\xd8\xffjpg").decode()}]}
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(grok_client.requests, "request", return_value=_response(payload=payload)) as req:
            paths = grok_client.generate_images("same character", Path(tmp),
                                                references=[ROOT / "tools/motion_render/chars/c1.webp"])
            self.assertEqual(paths[0].suffix, ".jpg")
        body = req.call_args.kwargs["json"]
        self.assertTrue(req.call_args.args[1].endswith("/images/edits"))
        # webp は PNG に変換して渡す
        self.assertTrue(body["image"]["url"].startswith("data:image/png;base64,"))

    def test_video_status(self):
        self.assertIsNone(grok_client.video_url_from_status({"status": "pending"}))
        self.assertEqual(grok_client.video_url_from_status({"status": "done", "video": {"url": "https://v/1.mp4"}}),
                         "https://v/1.mp4")
        for status in ({"status": "failed", "error": {"message": "x"}}, {"status": "expired"},
                       {"status": "done", "video": {"url": "u", "respect_moderation": False}}):
            with self.assertRaises(grok_client.GrokError):
                grok_client.video_url_from_status(status)

    @patch.dict(os.environ, {"XAI_API_KEY": "k"})
    def test_submit_video_with_image_omits_aspect(self):
        with patch.object(grok_client.requests, "request", return_value=_response(payload={"request_id": "r1"})) as req:
            rid = grok_client.submit_video("p", duration=8, aspect_ratio="9:16", image="data:image/jpeg;base64,AA")
        self.assertEqual(rid, "r1")
        body = req.call_args.kwargs["json"]
        self.assertEqual(body["image"], {"url": "data:image/jpeg;base64,AA"})
        self.assertNotIn("aspect_ratio", body)
        self.assertEqual(body["duration"], 8)


class ResearchTest(unittest.TestCase):
    def setUp(self):
        research._grok_cache.clear()

    @patch.dict(os.environ, {"XAI_API_KEY": "k", "RESEARCH_PROVIDER": "auto"})
    def test_uses_grok_x_search(self):
        text = '結果です[1] [{"topic": "音楽", "title": "新曲が話題", "snippet": "みんな歌ってみたを投稿 [2]", "url": ""}] [3]'
        with patch.object(grok_client, "chat", return_value=(text, ["https://x.com/u/status/9"])) as chat, \
                patch.object(research, "_get_ddg_topics") as ddg:
            topics = research.get_trending_topics(["音楽"])
            research.get_trending_topics(["音楽"])  # 2回目はキャッシュ
        ddg.assert_not_called()
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(chat.call_args.kwargs["tools"][0]["type"], "x_search")
        self.assertEqual(topics[0]["title"], "新曲が話題")
        self.assertEqual(topics[0]["url"], "https://x.com/u/status/9")
        self.assertEqual(topics[0]["source"], "x")

    @patch.dict(os.environ, {"XAI_API_KEY": "k", "RESEARCH_PROVIDER": "auto"})
    def test_falls_back_to_ddg_on_error(self):
        with patch.object(grok_client, "chat", side_effect=grok_client.GrokError("down")), \
                patch.object(research, "_get_ddg_topics", return_value=[{"topic": "a"}]) as ddg:
            self.assertEqual(research.get_trending_topics(["音楽"]), [{"topic": "a"}])
        ddg.assert_called_once()

    @patch.dict(os.environ, {"XAI_API_KEY": ""})
    def test_without_key_uses_ddg(self):
        with patch.object(grok_client, "chat") as chat, \
                patch.object(research, "_get_ddg_topics", return_value=[]) as ddg:
            research.get_trending_topics(["音楽"])
        chat.assert_not_called()
        ddg.assert_called_once()


class GenerateProviderTest(unittest.TestCase):
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "a", "XAI_API_KEY": "k", "POST_LLM_PROVIDER": ""})
    def test_default_is_claude(self):
        with patch.object(generate, "_call_claude", return_value="claude text") as c, \
                patch.object(generate, "_call_grok") as g:
            self.assertEqual(generate.call_llm("s", "u", 100), ("claude text", "claude"))
        c.assert_called_once()
        g.assert_not_called()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "a", "XAI_API_KEY": "k", "POST_LLM_PROVIDER": "grok"})
    def test_grok_primary_falls_back_to_claude(self):
        with patch.object(generate, "_call_grok", side_effect=grok_client.GrokError("down")), \
                patch.object(generate, "_call_claude", return_value="claude text"):
            self.assertEqual(generate.call_llm("s", "u", 100), ("claude text", "claude"))

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "a", "XAI_API_KEY": "", "POST_LLM_PROVIDER": "grok"})
    def test_grok_without_key_uses_claude(self):
        with patch.object(generate, "_call_grok") as g, \
                patch.object(generate, "_call_claude", return_value="c"):
            self.assertEqual(generate.call_llm("s", "u", 100)[1], "claude")
        g.assert_not_called()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "a", "XAI_API_KEY": "k"})
    def test_explicit_provider_does_not_fall_back(self):
        with patch.object(generate, "_call_grok", side_effect=grok_client.GrokError("down")), \
                patch.object(generate, "_call_claude") as c:
            with self.assertRaises(grok_client.GrokError):
                generate.call_llm("s", "u", 100, provider="grok")
        c.assert_not_called()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "a", "XAI_API_KEY": "k", "POST_LLM_PROVIDER": "grok"})
    def test_generate_post_reports_provider(self):
        persona = {"name": "kazuto", "max_length": 140, "add_hashtags": False}
        meta = {}
        with patch.object(generate, "_call_grok", return_value="今日も歌うよ"):
            text = generate.generate_post(persona, {"trending_topics": []}, meta=meta)
        self.assertEqual(text, "今日も歌うよ")
        self.assertEqual(meta["provider"], "grok")


class WebGenerateApiTest(unittest.TestCase):
    def setUp(self):
        import web_app
        self.client = web_app.app.test_client()

    def _post(self, payload, fake):
        with patch("research.build_research_context", return_value={"trending_topics": []}), \
                patch("generate.generate_post", side_effect=fake):
            return self.client.post("/api/generate", json=payload)

    def test_compare_mode_returns_both(self):
        def fake(*args, provider=None, meta=None, **kwargs):
            meta["provider"] = provider
            return f"{provider}の投稿"
        res = self._post({"count": 1, "provider": "both"}, fake)
        data = res.get_json()
        self.assertEqual(data["posts"], ["claudeの投稿", "grokの投稿"])
        self.assertEqual(data["providers"], ["claude", "grok"])

    def test_compare_mode_partial_failure(self):
        def fake(*args, provider=None, meta=None, **kwargs):
            if provider == "grok":
                raise grok_client.GrokError("XAI_API_KEY が設定されていません")
            meta["provider"] = provider
            return "claudeの投稿"
        data = self._post({"count": 1, "provider": "both"}, fake).get_json()
        self.assertEqual(data["providers"], ["claude"])
        self.assertIn("XAI_API_KEY", data["errors"][0])

    def test_auto_mode_passes_no_provider(self):
        seen = []

        def fake(*args, provider=None, meta=None, **kwargs):
            seen.append(provider)
            meta["provider"] = "claude"
            return "投稿"
        data = self._post({"count": 2}, fake).get_json()
        self.assertEqual(seen, [None, None])
        self.assertEqual(data["providers"], ["claude", "claude"])


class StoryboardTest(unittest.TestCase):
    def _write(self, tmp, text):
        path = Path(tmp) / "sb.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_sample_storyboard_is_valid(self):
        sb = video.load_storyboard(ROOT / "tools/grok/storyboards/sample.yaml")
        self.assertEqual(sb["aspect_ratio"], "9:16")
        self.assertTrue(55 <= sum(s["duration"] for s in sb["scenes"]) <= 75)
        self.assertFalse(sb["scenes"][0]["continue"])

    def test_unquoted_aspect_ratio_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            sb = video.load_storyboard(self._write(tmp, "aspect_ratio: 9:16\nscenes:\n  - prompt: a\n"))
        self.assertEqual(sb["aspect_ratio"], "9:16")

    def test_invalid_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(video.StoryboardError, "シーン1"):
                video.load_storyboard(self._write(tmp, "scenes:\n  - prompt: a\n    duration: 20\n"))

    def test_continue_scene_hash_depends_on_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = video.scene_hashes(video.load_storyboard(self._write(
                tmp, "scenes:\n  - prompt: a\n  - prompt: b\n    continue: true\n  - prompt: c\n")))
            b = video.scene_hashes(video.load_storyboard(self._write(
                tmp, "scenes:\n  - prompt: A\n  - prompt: b\n    continue: true\n  - prompt: c\n")))
        self.assertNotEqual(a[1], b[1])
        self.assertEqual(a[2], b[2])

    def test_stitch_command_offsets(self):
        cmd, total = video.build_stitch_command(
            [Path("a"), Path("b"), Path("c")], [8.0, 8.0, 6.0], Path("o.mp4"), transition_seconds=0.5)
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("offset=7.500", graph)
        self.assertIn("offset=15.000", graph)
        self.assertAlmostEqual(total, 21.0)


def _make_clip(path: Path, size: str, seconds: float, audio: bool, color="blue"):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:size={size}:rate=24"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440"]
    cmd += ["-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac"] if audio else []
    subprocess.run(cmd + [str(path)], check=True)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg が必要")
class RenderTest(unittest.TestCase):
    def test_render_generates_resumes_and_stitches(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sb_path = tmp / "demo.yaml"
            sb_path.write_text(
                'aspect_ratio: "9:16"\nstyle: "anime"\n'
                "scenes:\n"
                "  - prompt: one\n    duration: 2\n"
                "  - prompt: two\n    duration: 2\n    continue: true\n"
                "  - prompt: three\n    duration: 3\n",
                encoding="utf-8",
            )
            # r1=シーン1, r2=シーン3（先に依頼）, r3=シーン2（シーン1の完成後に依頼）
            sources = {"r1": ("360x640", True, 2), "r2": ("240x426", True, 3), "r3": ("360x640", False, 2)}
            submitted = []

            def fake_submit(prompt, **kwargs):
                submitted.append((prompt, kwargs))
                return f"r{len(submitted)}"

            def fake_download(url, path):
                size, audio, seconds = sources[url]
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                _make_clip(Path(path), size, seconds, audio)
                return path

            sb = video.load_storyboard(sb_path)
            with patch.object(video, "WORK_ROOT", tmp / "work"), \
                    patch.dict(os.environ, {"XAI_API_KEY": "k"}), \
                    patch.object(grok_client, "submit_video", side_effect=fake_submit), \
                    patch.object(grok_client, "wait_video", side_effect=lambda rid, **kw: rid), \
                    patch.object(grok_client, "download", side_effect=fake_download):
                out = video.render(sb, yes=True)
                info = video.probe(out)
                # 2本目以降の実行では、できているクリップを作り直さない
                video.render(sb, yes=True)

            # 独立したシーン（1, 3）を先に依頼し、続きのシーン2は1本目の最後のコマから作る
            self.assertEqual([p.split("\n")[0] for p, _ in submitted], ["one", "three", "two"])
            self.assertEqual(submitted[0][0], "one\nanime")
            self.assertTrue(submitted[2][1]["image"].startswith("data:image/jpeg;base64,"))
            self.assertIsNone(submitted[0][1]["image"])
            self.assertEqual((info["width"], info["height"]), (360, 640))
            self.assertAlmostEqual(info["duration"], 7 - 0.5 * 2, delta=0.15)
            self.assertTrue(info["has_audio"])


if __name__ == "__main__":
    unittest.main()
