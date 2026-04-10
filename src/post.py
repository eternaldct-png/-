"""
X（Twitter）投稿モジュール
tweepyを使ってX APIv2で投稿する
"""
import os
import json
import tweepy
from datetime import datetime
from pathlib import Path

HISTORY_PATH = Path("posts/history.json")


def get_twitter_client() -> tweepy.Client:
    """環境変数からX APIクライアントを初期化する"""
    required_vars = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_SECRET",
    ]
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


def load_post_history() -> list[dict]:
    """投稿履歴を読み込む"""
    if not HISTORY_PATH.exists():
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def is_duplicate(text: str) -> bool:
    """過去に投稿した文章と完全一致するか確認する"""
    history = load_post_history()
    posted_texts = {item.get("text", "") for item in history}
    if text in posted_texts:
        print(f"[post] ローカル履歴に同一投稿あり、スキップします: {text[:40]}...")
        return True
    return False


def get_recent_posts(n: int = 5) -> list[str]:
    """直近n件の投稿文を返す（生成プロンプトに渡すため）"""
    history = load_post_history()
    return [item.get("text", "") for item in history[-n:]]


def post_to_x(text: str, dry_run: bool = False) -> dict:
    """
    X に投稿する（ローカル履歴で重複チェック済み）

    Args:
        text: 投稿文
        dry_run: Trueの場合は実際には投稿せずログのみ出力

    Returns:
        投稿結果（tweet_id, text, timestamp）
    """
    timestamp = datetime.now().isoformat()

    if dry_run:
        print(f"\n{'='*50}")
        print(f"[DRY RUN] 投稿プレビュー ({len(text)}文字)")
        print(f"{'='*50}")
        print(text)
        print(f"{'='*50}\n")
        return {"tweet_id": "dry_run", "text": text, "timestamp": timestamp}

    # ローカル履歴で重複チェック（X APIに送る前に弾く）
    if is_duplicate(text):
        return {"tweet_id": "skipped_duplicate", "text": text, "timestamp": timestamp}

    client = get_twitter_client()

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        print(f"[post] 投稿成功！ tweet_id={tweet_id}")
        result = {"tweet_id": tweet_id, "text": text, "timestamp": timestamp}
        save_post_history(result)
        return result
    except tweepy.Forbidden as e:
        if "duplicate" in str(e).lower() or "重複" in str(e):
            print(f"[post] X APIでも重複検知: {text[:40]}...")
            return {"tweet_id": "skipped_duplicate", "text": text, "timestamp": timestamp}
        print(f"[post] 投稿エラー (403): {e}")
        raise
    except tweepy.TweepyException as e:
        print(f"[post] 投稿エラー: {e}")
        raise


def save_post_history(result: dict) -> None:
    """投稿履歴をJSONファイルに保存する"""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    history = load_post_history()
    history.append(result)
    history = history[-200:]  # 最新200件を保持

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"[post] 履歴保存: {HISTORY_PATH} ({len(history)}件)")
