import tempfile
import unittest
from pathlib import Path

from src import narration_builder as nb

GeminiTTSError = nb.gemini_tts.GeminiTTSError

REPO = Path(__file__).resolve().parent.parent


class LoadCuesTest(unittest.TestCase):
    def _load(self, body: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cues.yaml"
            path.write_text(body, encoding="utf-8")
            return nb.load_cues(path)

    def test_promo_cue_sheet_is_valid(self):
        config = nb.load_cues(REPO / "media" / "narration" / "eternaldct_promo_60s.yaml")
        self.assertEqual(len(config["cues"]), 9)
        self.assertLessEqual(config["cues"][-1]["until"], 60.0)

    def test_rejects_overlap_and_empty_text(self):
        with self.assertRaisesRegex(GeminiTTSError, "重なって"):
            self._load("cues:\n- {at: 0, until: 5, text: a}\n- {at: 4, until: 8, text: b}\n")
        with self.assertRaisesRegex(GeminiTTSError, "空"):
            self._load("cues:\n- {at: 0, until: 5, text: ''}\n")
        with self.assertRaisesRegex(GeminiTTSError, "until"):
            self._load("cues:\n- {at: 5, until: 3, text: a}\n")


class TimingTest(unittest.TestCase):
    def test_speed_for(self):
        self.assertEqual(nb.speed_for(3.0, 5.0), 1.0)
        self.assertAlmostEqual(nb.speed_for(5.5, 5.0), 1.1)
        self.assertEqual(nb.speed_for(10.0, 5.0), nb.MAX_SPEEDUP)

    def test_clip_cache_key_changes_with_text_voice_style(self):
        base = nb.clip_path(Path("/x"), 1, "こんにちは", "Sulafat", "明るく")
        self.assertEqual(base, nb.clip_path(Path("/x"), 1, "こんにちは", "Sulafat", "明るく"))
        self.assertNotEqual(base, nb.clip_path(Path("/x"), 1, "こんばんは", "Sulafat", "明るく"))
        self.assertNotEqual(base, nb.clip_path(Path("/x"), 1, "こんにちは", "Kore", "明るく"))
        self.assertNotEqual(base, nb.clip_path(Path("/x"), 1, "こんにちは", "Sulafat", "静かに"))

    def test_ducking_expression_depth(self):
        expr = nb.ducking_expression([{"at": 1.0, "end": 3.0}, {"at": 5.0, "end": 6.0}], duck_db=20)
        self.assertTrue(expr.startswith("1-0.9000*max("))
        self.assertEqual(expr.count("clip("), 2)


if __name__ == "__main__":
    unittest.main()
