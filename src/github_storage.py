"""
GitHub API を使った queue.json の永続化モジュール

Render.com 等のエフェメラルなホスティングでも
queue.json の内容を GitHub リポジトリに保存・同期する。

環境変数:
  GITHUB_TOKEN  - Personal Access Token (contents:write 権限)
  GITHUB_REPO   - "owner/repo" 形式 (例: eternaldct-png/-)
  GITHUB_BRANCH - 対象ブランチ (デフォルト: main)
"""
import os
import json
import base64
import requests
from pathlib import Path

GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO   = os.environ.get("GITHUB_REPO", "eternaldct-png/-")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
QUEUE_FILE    = "posts/queue.json"
LOCAL_QUEUE   = Path("posts/queue.json")

_API = "https://api.github.com"


class GithubStorage:
    """
    GitHub Contents API で queue.json を読み書きする。
    GITHUB_TOKEN が未設定の場合はローカルファイルにフォールバックする。
    """

    def __init__(self):
        self._sha: str | None = None  # 最後に取得したファイルの SHA
        self._headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _use_github(self) -> bool:
        return bool(GITHUB_TOKEN)

    # ── ローカル I/O ─────────────────────────────────────────

    def _read_local(self) -> list[dict]:
        if not LOCAL_QUEUE.exists():
            return []
        with open(LOCAL_QUEUE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _write_local(self, queue: list[dict]) -> None:
        LOCAL_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCAL_QUEUE, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)

    # ── GitHub API I/O ────────────────────────────────────────

    def read(self) -> list[dict]:
        """GitHub から queue.json を取得する（失敗時はローカルにフォールバック）"""
        if not self._use_github():
            return self._read_local()

        url = f"{_API}/repos/{GITHUB_REPO}/contents/{QUEUE_FILE}"
        try:
            r = requests.get(
                url,
                headers=self._headers,
                params={"ref": GITHUB_BRANCH},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                self._sha = data.get("sha")
                content = base64.b64decode(data["content"]).decode("utf-8")
                queue = json.loads(content)
                # ローカルにも同期しておく（generate 系モジュールが使うため）
                self._write_local(queue)
                return queue
            if r.status_code == 404:
                return []
            print(f"[storage] GitHub read error: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"[storage] GitHub read exception: {e}")

        # フォールバック
        return self._read_local()

    def write(self, queue: list[dict]) -> bool:
        """
        queue.json を GitHub にコミットする。
        SHA が古い場合は再取得してリトライする。
        """
        # ローカルには常に書く
        self._write_local(queue)

        if not self._use_github():
            return True

        content_b64 = base64.b64encode(
            json.dumps(queue, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")

        url = f"{_API}/repos/{GITHUB_REPO}/contents/{QUEUE_FILE}"

        # SHA が未取得の場合は先に読む
        if self._sha is None:
            self._fetch_sha(url)

        payload: dict = {
            "message": "chore: update queue.json via web dashboard [skip ci]",
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if self._sha:
            payload["sha"] = self._sha

        try:
            r = requests.put(url, headers=self._headers, json=payload, timeout=15)
            if r.status_code in (200, 201):
                self._sha = r.json()["content"]["sha"]
                return True

            # 409 Conflict = SHA が古い → 再取得してリトライ
            if r.status_code == 409:
                print("[storage] SHA conflict, retrying...")
                self._fetch_sha(url)
                if self._sha:
                    payload["sha"] = self._sha
                    r2 = requests.put(url, headers=self._headers, json=payload, timeout=15)
                    if r2.status_code in (200, 201):
                        self._sha = r2.json()["content"]["sha"]
                        return True

            print(f"[storage] GitHub write error: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"[storage] GitHub write exception: {e}")

        return False

    def _fetch_sha(self, url: str) -> None:
        """現在のファイルの SHA だけ取得する"""
        try:
            r = requests.get(
                url,
                headers=self._headers,
                params={"ref": GITHUB_BRANCH},
                timeout=8,
            )
            if r.status_code == 200:
                self._sha = r.json().get("sha")
        except Exception:
            pass


# シングルトン（アプリ全体で共有）
storage = GithubStorage()
