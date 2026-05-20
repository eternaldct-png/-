"""
note.com 非公式 API クライアント

note.com には公式 API がないため、ブラウザと同等のリクエストを再現する。
認証方式: email/password ログイン または セッショントークン直接指定
"""
import os
import requests
from typing import Optional


class NoteAPIError(Exception):
    pass


class NoteAPIClient:
    BASE_URL = "https://note.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://note.com/notes/new",
            "Origin": "https://note.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "X-Requested-With": "XMLHttpRequest",
        })
        self._authenticated = False
        self._urlname: Optional[str] = None

    # ── 認証 ─────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> bool:
        """email/password でログインしてセッションを取得する"""
        # トップページにアクセスしてセッション Cookie を初期化
        self.session.get(self.BASE_URL, timeout=10)

        # CSRF トークン取得
        csrf = self._get_csrf_token()
        if csrf:
            self.session.headers["X-CSRF-Token"] = csrf

        resp = self.session.post(
            f"{self.BASE_URL}/api/v1/sessions",
            json={"login": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json().get("data", {})
            self._urlname = data.get("urlname") or data.get("id")
            self._authenticated = True
            print(f"[note_api] ログイン成功: @{self._urlname}")
            return True

        print(f"[note_api] ログイン失敗 (HTTP {resp.status_code}): {resp.text[:300]}")
        return False

    def login_with_session(self, session_token: str) -> None:
        """既存のセッショントークン (_note_session_v5) で認証する"""
        self.session.cookies.set("_note_session_v5", session_token, domain=".note.com")

        # 自分のプロフィールを取得して urlname を確認
        resp = self.session.get(f"{self.BASE_URL}/api/v2/creators/me", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            self._urlname = data.get("urlname") or data.get("id")
            print(f"[note_api] セッショントークンで認証: @{self._urlname}")
        else:
            print(f"[note_api] 警告: プロフィール取得失敗 (HTTP {resp.status_code})")

        csrf = self._get_csrf_token()
        if csrf:
            self.session.headers["X-CSRF-Token"] = csrf

        self._authenticated = True

    # ── 記事操作 ──────────────────────────────────────────────────

    def create_draft(
        self,
        title: str,
        body: str,
        tags: Optional[list] = None,
    ) -> Optional[dict]:
        """
        note.com に下書き記事を作成する

        Returns:
            {"id": ..., "key": ..., "url": ..., "edit_url": ...} または None（失敗時）
        """
        if not self._authenticated:
            raise NoteAPIError("ログインが必要です")

        tags = [t.lstrip("#") for t in (tags or [])][:10]

        payload = {
            "name": title,
            "body": body,
            "hashtag_list": tags,
            "disclose_scope": 1,       # 1: 全体公開（下書きなので実際には非公開）
            "note_status": "draft",
        }

        resp = self.session.post(
            f"{self.BASE_URL}/api/v2/text_notes",
            json=payload,
            timeout=20,
        )

        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            key = data.get("key", "")
            urlname = self._urlname or "me"
            note_url = f"https://note.com/{urlname}/n/{key}"
            edit_url = f"https://note.com/notes/{key}/edit"
            print(f"[note_api] 下書き作成成功: 「{title}」")
            print(f"[note_api] 編集URL: {edit_url}")
            return {
                "id": data.get("id"),
                "key": key,
                "url": note_url,
                "edit_url": edit_url,
                "status": "draft",
            }

        print(f"[note_api] 下書き作成失敗 (HTTP {resp.status_code}): {resp.text[:500]}")
        return None

    # ── 内部ユーティリティ ────────────────────────────────────────

    def _get_csrf_token(self) -> str:
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/api/v1/sessions/csrf_token",
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("csrf_token", "")
        except Exception:
            pass
        return ""
