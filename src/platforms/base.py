"""
プラットフォームアダプター抽象基底クラス
全プラットフォーム（X, Instagram, note, TikTok）が実装するインターフェース
"""
from abc import ABC, abstractmethod
from pathlib import Path


class PlatformAdapter(ABC):
    """全投稿プラットフォームの共通インターフェース"""

    @abstractmethod
    def post(self, content: dict, dry_run: bool = False) -> dict:
        """
        コンテンツを投稿する

        Args:
            content: {text, media_path(optional), metadata(optional)}
            dry_run: Trueの場合はプレビューのみ（実際には投稿しない）

        Returns:
            {platform_id, text, timestamp, status}
        """
        ...

    @abstractmethod
    def get_constraints(self) -> dict:
        """
        プラットフォーム固有の制約を返す（generate.pyに渡す）

        Returns:
            {max_length, max_hashtags, content_format, requires_media,
             supports_media, max_tokens_hint}
        """
        ...

    @abstractmethod
    def is_duplicate(self, text: str) -> bool:
        """ローカル履歴に同一コンテンツが存在するか確認する"""
        ...

    def get_history_path(self) -> Path:
        """プラットフォーム固有の履歴ファイルパスを返す（サブクラスでオーバーライド可）"""
        return Path("posts/history.json")

    def get_recent_posts(self, n: int = 5) -> list[str]:
        """直近n件の投稿テキストを返す（重複回避のために generate.py へ渡す）"""
        import json
        path = self.get_history_path()
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
            return [item.get("text", "") for item in history[-n:]]
        except (json.JSONDecodeError, Exception):
            return []
