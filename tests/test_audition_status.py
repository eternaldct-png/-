import os
import unittest
from unittest.mock import patch

from src.web_app import app


class AuditionStatusTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_closed_is_the_safe_default_and_blocks_submissions(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUDITION_STATUS", None)

            page = self.client.get("/audition")
            self.assertEqual(page.status_code, 200)
            self.assertIn("受付は終了しました", page.get_data(as_text=True))
            self.assertNotIn("auditionForm", page.get_data(as_text=True))

            response = self.client.post("/api/audition/submit", json={})
            self.assertEqual(response.status_code, 410)
            self.assertEqual(
                response.get_json(),
                {"error": "オーディションの受付は終了しました"},
            )

    def test_open_restores_the_saved_form_and_submission_validation(self):
        with patch.dict(os.environ, {"AUDITION_STATUS": "open"}):
            page = self.client.get("/audition")
            html = page.get_data(as_text=True)
            self.assertEqual(page.status_code, 200)
            self.assertIn("auditionForm", html)
            self.assertIn("北海道", html)

            response = self.client.post("/api/audition/submit", json={})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json(), {"error": "必須項目が未入力です"})


if __name__ == "__main__":
    unittest.main()
