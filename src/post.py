"""
後方互換shim — X投稿の実体は platforms/x.py に移動済み

既存の auto_post.yml ワークフローや generate.py が
直接 post_to_x / get_recent_posts を import できるよう再エクスポートする
"""
from platforms.x import XAdapter

_adapter = XAdapter()


def post_to_x(text: str, dry_run: bool = False) -> dict:
    """X に投稿する（後方互換ラッパー）"""
    result = _adapter.post({"text": text}, dry_run=dry_run)
    # 旧インターフェース互換: platform_id を tweet_id としても返す
    return {
        "tweet_id": result.get("platform_id"),
        "text": result.get("text"),
        "timestamp": result.get("timestamp"),
    }


def get_recent_posts(n: int = 5) -> list[str]:
    """直近n件の投稿テキストを返す（後方互換ラッパー）"""
    return _adapter.get_recent_posts(n)


def is_duplicate(text: str) -> bool:
    """重複確認（後方互換ラッパー）"""
    return _adapter.is_duplicate(text)
