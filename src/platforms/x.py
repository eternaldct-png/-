"""
X（Twitter）プラットフォームアダプター
tweepy を使って X API v2 で投稿する
"""
import os
import json
import tweepy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from platforms.base import PlatformAdapter

JST = ZoneInfo("Asia/Tokyo")
HISTORY_PATH = Path("posts/x_history.json")


class XAdapter(PlatformAdapter):
    """X（Twitter）投稿アダプター"""

    def get_history_path(self) -> Path:
        return HISTORY_PATH

    def get_constraints(self) -> dict:
        return {
            "max_length": 140,
            "max_hashtags": 2,
            "content_format": "text",
            "requires_media": False,
            "supports_media": True,
            "max_tokens_hint": 300,
        }

    def is_duplicate(self, text: str) -> bool:
        """ローカル履歴に同一投稿が存在するか確認する"""
        history = self._load_history()
        posted_texts = {item.get("text", "") for item in history}
        if text in posted_texts:
            print(f"[x] ローカル履歴に同一投稿あり、スキップします: {text[:40]}...")
            return True
        return False

    def post(self, content: dict, dry_run: bool = False) -> dict:
        """
        X に投稿する

        Args:
            content: {"text": "投稿文", ...}
            dry_run: Trueの場合はプレビューのみ

        Returns:
            {platform_id, text, timestamp, status}
        """
        text = content["text"]
        timestamp = datetime.now(JST).isoformat()

        if dry_run:
            print(f"\n{'='*50}")
            print(f"[X][DRY RUN] 投稿プレビュー ({len(text)}文字)")
            print(f"{'='*50}")
            print(text)
            print(f"{'='*50}\n")
            return {"platform_id": "dry_run", "text": text, "timestamp": timestamp, "status": "dry_run"}

        if self.is_duplicate(text):
            return {"platform_id": "skipped_duplicate", "text": text, "timestamp": timestamp, "status": "skipped"}

        client = self._get_client()
        try:
            response = client.create_tweet(text=text)
            tweet_id = response.data["id"]
            print(f"[x] 投稿成功！ tweet_id={tweet_id}")
            result = {"platform_id": tweet_id, "text": text, "timestamp": timestamp, "status": "posted"}
            self._save_history(result)
            return result
        except tweepy.Forbidden as e:
            if "duplicate" in str(e).lower() or "重複" in str(e):
                print(f"[x] X APIでも重複検知: {text[:40]}...")
                return {"platform_id": "skipped_duplicate", "text": text, "timestamp": timestamp, "status": "skipped"}
            print(f"[x] 投稿エラー (403): {e}")
            raise
        except tweepy.TweepyException as e:
            print(f"[x] 投稿エラー: {e}")
            raise

    # ── 内部メソッド ──────────────────────────────────────────

    def _get_client(self) -> tweepy.Client:
        """環境変数から X API クライアントを初期化する"""
        required_vars = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise EnvironmentError(
                f"以下の環境変数が設定されていません: {', '.join(missing)}\n"
                "README.md の「X API設定手順」を参照してください。"
            )
        return tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_SECRET"],
        )

    def _load_history(self) -> list[dict]:
        path = self.get_history_path()
        if not path.exists():
            # 旧パス（posts/history.json）からマイグレーション
            old_path = Path("posts/history.json")
            if old_path.exists():
                with open(old_path, "r", encoding="utf-8") as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        return []
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
        # platform_id を tweet_id としても保存（後方互換）
        entry = {**result, "tweet_id": result.get("platform_id")}
        history.append(entry)
        history = history[-200:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"[x] 履歴保存: {path} ({len(history)}件)")

    def get_recent_posts(self, n: int = 5) -> list[str]:
        """直近n件の投稿テキストを返す"""
        history = self._load_history()
        return [item.get("text", "") for item in history[-n:]]
