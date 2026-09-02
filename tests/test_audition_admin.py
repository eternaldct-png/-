import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import web_app


SAMPLE_APPLICATION = {
    "id": "sample-id",
    "created_at": "2026-09-01 12:00",
    "name": "応募 太郎",
    "furigana": "おうぼ たろう",
    "gender": "男性",
    "email": "sample@example.com",
    "prefecture": "大阪府",
    "minor_consent": "成人",
    "activity_name": "サンプル歌手",
    "experience": "あり",
    "history": "ライブ出演経験あり",
    "genre": "J-POP",
    "frequency": "週3〜4回",
    "sns": "@sample",
    "self_pr": "自己PRのサンプル",
    "motivation": "応募動機のサンプル",
    "other": "",
}


class AuditionAdminTest(unittest.TestCase):
    def setUp(self):
        self.client = web_app.app.test_client()
        with self.client.session_transaction() as session:
            session["audition_admin_ok"] = True

    def test_admin_has_switchable_views_search_edit_and_delete(self):
        with patch.object(
            web_app, "_load_audition_applications", return_value=[SAMPLE_APPLICATION]
        ):
            with patch.object(web_app, "_audition_db_ready", return_value=True):
                response = self.client.get("/audition/admin")

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-view="cards"', html)
        self.assertIn('data-view="table"', html)
        self.assertIn('id="applicant-search"', html)
        self.assertIn("自己PR・応募動機を表示", html)
        self.assertIn('/audition/admin/edit/sample-id', html)
        self.assertIn('/audition/admin/delete/sample-id', html)
        self.assertIn('name="csrf_token"', html)

    def test_admin_highlights_missing_activity_name(self):
        missing_activity = {**SAMPLE_APPLICATION, "activity_name": ""}
        with patch.object(
            web_app, "_load_audition_applications", return_value=[missing_activity]
        ):
            with patch.object(web_app, "_audition_db_ready", return_value=True):
                response = self.client.get("/audition/admin")

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<span class="missing-badge">⚠ 未記入</span>', html)

    def test_edit_page_shows_current_application_values(self):
        with self.client.session_transaction() as session:
            session["audition_admin_csrf"] = "valid-token"

        with patch.object(
            web_app, "_load_audition_applications", return_value=[SAMPLE_APPLICATION]
        ):
            response = self.client.get("/audition/admin/edit/sample-id")

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("応募データを編集", html)
        self.assertIn('name="activity_name" value="サンプル歌手"', html)
        self.assertIn('name="csrf_token" value="valid-token"', html)
        self.assertIn("変更を保存する", html)

    def test_edit_route_requires_valid_csrf_token(self):
        with self.client.session_transaction() as session:
            session["audition_admin_csrf"] = "valid-token"

        with patch.object(
            web_app, "_load_audition_applications", return_value=[SAMPLE_APPLICATION]
        ):
            with patch.object(web_app, "_update_audition_application") as update:
                response = self.client.post(
                    "/audition/admin/edit/sample-id",
                    data={"csrf_token": "wrong-token"},
                )

        self.assertEqual(response.status_code, 403)
        update.assert_not_called()

    def test_edit_route_updates_and_redirects_to_application(self):
        with self.client.session_transaction() as session:
            session["audition_admin_csrf"] = "valid-token"

        submitted = {
            field: SAMPLE_APPLICATION.get(field, "")
            for field in web_app.AUDITION_EDITABLE_FIELDS
        }
        submitted["activity_name"] = "新しい活動名"
        submitted["csrf_token"] = "valid-token"

        with patch.object(
            web_app, "_load_audition_applications", return_value=[SAMPLE_APPLICATION]
        ):
            with patch.object(
                web_app, "_update_audition_application", return_value=True
            ) as update:
                response = self.client.post(
                    "/audition/admin/edit/sample-id",
                    data=submitted,
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "/audition/admin#app-sample-id",
        )
        saved_updates = update.call_args.args[1]
        self.assertEqual(update.call_args.args[0], "sample-id")
        self.assertEqual(saved_updates["activity_name"], "新しい活動名")
        self.assertNotIn("csrf_token", saved_updates)

    def test_delete_route_requires_valid_csrf_token(self):
        with self.client.session_transaction() as session:
            session["audition_admin_csrf"] = "valid-token"

        with patch.object(web_app, "_delete_audition_application") as delete:
            response = self.client.post(
                "/audition/admin/delete/sample-id",
                data={"csrf_token": "wrong-token"},
            )

        self.assertEqual(response.status_code, 403)
        delete.assert_not_called()

    def test_delete_route_deletes_and_redirects(self):
        with self.client.session_transaction() as session:
            session["audition_admin_csrf"] = "valid-token"

        with patch.object(web_app, "_delete_audition_application", return_value=True) as delete:
            response = self.client.post(
                "/audition/admin/delete/sample-id",
                data={"csrf_token": "valid-token"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/audition/admin")
        delete.assert_called_once_with("sample-id")

    def test_file_only_delete_removes_just_the_target(self):
        with tempfile.TemporaryDirectory() as directory:
            audition_file = Path(directory) / "applications.json"
            audition_file.write_text(
                json.dumps([
                    SAMPLE_APPLICATION,
                    {**SAMPLE_APPLICATION, "id": "keep-id", "name": "残す 花子"},
                ], ensure_ascii=False),
                encoding="utf-8",
            )

            with patch.object(web_app, "AUDITION_FILE", audition_file):
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("DATABASE_URL", None)
                    deleted = web_app._delete_audition_application("sample-id")

            remaining = json.loads(audition_file.read_text(encoding="utf-8"))

        self.assertTrue(deleted)
        self.assertEqual([row["id"] for row in remaining], ["keep-id"])

    def test_file_only_edit_updates_just_the_target(self):
        with tempfile.TemporaryDirectory() as directory:
            audition_file = Path(directory) / "applications.json"
            audition_file.write_text(
                json.dumps([
                    {**SAMPLE_APPLICATION, "activity_name": ""},
                    {**SAMPLE_APPLICATION, "id": "keep-id", "name": "残す 花子"},
                ], ensure_ascii=False),
                encoding="utf-8",
            )
            updates = {
                field: SAMPLE_APPLICATION.get(field, "")
                for field in web_app.AUDITION_EDITABLE_FIELDS
            }
            updates["activity_name"] = "追記した活動名"

            with patch.object(web_app, "AUDITION_FILE", audition_file):
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("DATABASE_URL", None)
                    updated = web_app._update_audition_application(
                        "sample-id",
                        updates,
                    )

            applications = json.loads(audition_file.read_text(encoding="utf-8"))

        self.assertTrue(updated)
        self.assertEqual(applications[0]["activity_name"], "追記した活動名")
        self.assertEqual(applications[1]["activity_name"], "サンプル歌手")
        self.assertEqual(applications[1]["name"], "残す 花子")


if __name__ == "__main__":
    unittest.main()
