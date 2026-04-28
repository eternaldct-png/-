"""
Instagram プラットフォームアダプター
Instagram Graph API v21.0 を使って画像投稿する

投稿フロー:
  1. 画像を Pillow で生成 → posts/media/ に保存
  2. リポジトリにコミット（GitHub Actions の別ジョブ）
  3. GitHub raw URL を使ってメディアコンテナを作成
  4. コンテナを公開
"""
import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from platforms.base import PlatformAdapter

JST = ZoneInfo("Asia/Tokyo")
HISTORY_PATH = Path("posts/instagram_history.json")
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class InstagramAdapter(PlatformAdapter):
    """Instagram Graph API 投稿アダプター"""

    def get_history_path(self) -> Path:
        return HISTORY_PATH

    def get_constraints(self) -> dict:
        return {
            "max_length": 2200,
            "max_hashtags": 30,
            "content_format": "visual_caption",
            "requires_media": True,
            "supports_media": True,
            "max_tokens_hint": 600,
        }

    def is_duplicate(self, text: str) -> bool:
        """キャプション先頭100文字で重複確認"""
        history = self._load_history()
        captions = {item.get("text", "")[:100] for item in history}
        key = text[:100]
        if key in captions:
            print(f"[instagram] 同一キャプションが履歴にあります: {key[:40]}...")
            return True
        return False

    def post(self, content: dict, dry_run: bool = False) -> dict:
        """
        Instagram に画像投稿する

        Args:
            content: {"caption": ..., "hashtags": [...]}
                     または {"text": ..., "media_path": ...}
            dry_run: Trueの場合はプレビューのみ

        Returns:
            {platform_id, text, timestamp, status, media_path}
        """
        # キャプション取得（generate_post の dict 形式に対応）
        if "caption" in content:
            caption = content["caption"]
            hashtags = content.get("hashtags", [])
        else:
            caption = content.get("text", "")
            hashtags = []

        # フルキャプション（本文 + ハッシュタグ）
        if hashtags:
            hashtag_block = " ".join(hashtags)
            full_caption = f"{caption}\n\n{hashtag_block}"
        else:
            full_caption = caption

        media_path = content.get("media_path")
        timestamp = datetime.now(JST)

        # 画像が未生成なら生成する
        if not media_path:
            from media.image_generator import generate_instagram_image
            ts = timestamp.strftime("%Y%m%d_%H%M%S")
            media_path = str(Path("posts/media") / f"{ts}_instagram.png")
            generate_instagram_image(
                caption_text=caption,
                hashtags=hashtags[:8],
                output_path=Path(media_path),
            )

        if dry_run:
            print(f"\n{'='*60}")
            print(f"[Instagram][DRY RUN] 投稿プレビュー")
            print(f"{'='*60}")
            print(f"キャプション ({len(full_caption)}文字):")
            print(full_caption[:200] + ("..." if len(full_caption) > 200 else ""))
            print(f"\n画像: {media_path}")
            print(f"{'='*60}\n")
            return {
                "platform_id": "dry_run",
                "text": full_caption,
                "timestamp": timestamp.isoformat(),
                "status": "dry_run",
                "media_path": str(media_path),
            }

        # Graph API で投稿
        user_id = os.environ.get("INSTAGRAM_USER_ID")
        access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        github_repo = os.environ.get("GITHUB_REPOSITORY", "")

        if not user_id or not access_token:
            print("[instagram] INSTAGRAM_USER_ID / INSTAGRAM_ACCESS_TOKEN が未設定です。")
            print("[instagram] .env.example を参考に GitHub Secrets を設定してください。")
            return {
                "platform_id": "missing_credentials",
                "text": full_caption,
                "timestamp": timestamp.isoformat(),
                "status": "error",
            }

        # GitHub raw URL で画像を公開（public リポジトリ前提）
        image_url = self._get_public_image_url(media_path, github_repo)
        if not image_url:
            print("[instagram] 画像の公開 URL を取得できませんでした。コミット後に再実行してください。")
            return {
                "platform_id": "image_not_public",
                "text": full_caption,
                "timestamp": timestamp.isoformat(),
                "status": "error",
            }

        print(f"[instagram] メディアコンテナ作成中... image_url={image_url[:60]}...")
        container_id = self._create_container(user_id, access_token, image_url, full_caption)

        print(f"[instagram] コンテナ公開中... container_id={container_id}")
        media_id = self._publish_container(user_id, access_token, container_id)

        print(f"[instagram] 投稿成功！ media_id={media_id}")
        result = {
            "platform_id": media_id,
            "text": full_caption,
            "timestamp": timestamp.isoformat(),
            "status": "posted",
            "media_path": str(media_path),
        }
        self._save_history(result)
        return result

    # ── 内部メソッド ──────────────────────────────────────────

    @staticmethod
    def _get_public_image_url(media_path: str, github_repo: str) -> str | None:
        """GitHub raw URL を生成する"""
        if not github_repo:
            return None
        filename = Path(media_path).name
        # GITHUB_REF_NAME または main ブランチを使う
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        return f"https://raw.githubusercontent.com/{github_repo}/{branch}/posts/media/{filename}"

    @staticmethod
    def _create_container(user_id: str, token: str, image_url: str, caption: str) -> str:
        """Instagram メディアコンテナを作成する"""
        # 画像URLのアクセス確認
        try:
            chk = requests.head(image_url, timeout=10, allow_redirects=True)
            print(f"[instagram] 画像URLチェック: {image_url}")
            print(f"[instagram] HTTP {chk.status_code} Content-Type={chk.headers.get('Content-Type', '?')}")
        except Exception as e:
            print(f"[instagram] 画像URLチェック失敗: {e}")

        url = f"{GRAPH_API_BASE}/{user_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        }
        resp = requests.post(url, data=params, timeout=30)
        if not resp.ok:
            print(f"[instagram] API エラーレスポンス ({resp.status_code}):")
            print(resp.text[:1000])
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"[instagram] コンテナ作成エラー: {data['error']}")
        return data["id"]

    @staticmethod
    def _publish_container(user_id: str, token: str, container_id: str) -> str:
        """コンテナを公開する（最大10秒待機して状態確認）"""
        # コンテナが ready になるまで待機（最大30秒）
        status_url = f"{GRAPH_API_BASE}/{container_id}"
        for _ in range(6):
            resp = requests.get(
                status_url,
                params={"fields": "status_code", "access_token": token},
                timeout=15,
            )
            resp.raise_for_status()
            status = resp.json().get("status_code", "")
            if status == "FINISHED":
                break
            if status == "ERROR":
                raise RuntimeError(f"[instagram] メディア処理エラー: {resp.json()}")
            time.sleep(5)

        publish_url = f"{GRAPH_API_BASE}/{user_id}/media_publish"
        resp = requests.post(
            publish_url,
            data={"creation_id": container_id, "access_token": token},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"[instagram] 公開エラー: {data['error']}")
        return data["id"]

    def _load_history(self) -> list[dict]:
        path = self.get_history_path()
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _save_history(self, result: dict) -> None:
        path = self.get_history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        history = self._load_history()
        history.append(result)
        history = history[-200:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"[instagram] 履歴保存: {path} ({len(history)}件)")

    def get_recent_posts(self, n: int = 5) -> list[str]:
        """直近n件のキャプション先頭100文字を返す"""
        history = self._load_history()
        return [item.get("text", "")[:100] for item in history[-n:]]
