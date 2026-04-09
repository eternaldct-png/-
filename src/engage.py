"""
自動いいね・リポストモジュール
対象アカウントやハッシュタグの投稿に自動で反応する
"""
import os
import json
import tweepy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

JST = ZoneInfo("Asia/Tokyo")
ENGAGE_LOG_PATH = Path("posts/engage_log.json")


def get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )


def load_engage_log() -> list[dict]:
    if not ENGAGE_LOG_PATH.exists():
        return []
    with open(ENGAGE_LOG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_engage_log(log: list[dict]) -> None:
    ENGAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ENGAGE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log[-200:], f, ensure_ascii=False, indent=2)


def already_engaged(tweet_id: str, action: str, log: list[dict]) -> bool:
    """同じツイートに同じアクションを重複して行わないチェック"""
    return any(
        item.get("tweet_id") == tweet_id and item.get("action") == action
        for item in log
    )


def record_engage(tweet_id: str, action: str, text: str, log: list[dict]) -> None:
    log.append({
        "tweet_id": tweet_id,
        "action": action,
        "text": text[:80],
        "timestamp": datetime.now(JST).isoformat(),
    })


def search_recent_tweets(client: tweepy.Client, query: str, max_results: int = 10) -> list:
    """直近24時間のツイートを検索する"""
    since = (datetime.now(JST) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        response = client.search_recent_tweets(
            query=query + " -is:retweet lang:ja",
            max_results=max_results,
            tweet_fields=["public_metrics", "author_id", "text"],
            start_time=since,
        )
        return response.data or []
    except tweepy.TweepyException as e:
        print(f"[engage] 検索エラー ({query}): {e}")
        return []


def auto_like(config: dict, dry_run: bool = False) -> int:
    """対象アカウント・ハッシュタグの投稿にいいねする"""
    client = get_client()
    log = load_engage_log()
    max_likes = config.get("max_likes_per_run", 5)
    liked = 0

    target_accounts = [a for a in config.get("target_accounts", []) if a]
    target_hashtags = [h for h in config.get("target_hashtags", []) if h]

    # アカウントの最新ツイートにいいね
    for account in target_accounts:
        if liked >= max_likes:
            break
        tweets = search_recent_tweets(client, f"from:{account}", max_results=5)
        for tweet in tweets:
            if liked >= max_likes:
                break
            tweet_id = str(tweet.id)
            if already_engaged(tweet_id, "like", log):
                continue
            if dry_run:
                print(f"[engage][DRY RUN] いいね → @{account}: {tweet.text[:50]}...")
            else:
                try:
                    client.like(tweet_id)
                    print(f"[engage] いいね → @{account}: {tweet.text[:50]}...")
                    record_engage(tweet_id, "like", tweet.text, log)
                    liked += 1
                except tweepy.TweepyException as e:
                    print(f"[engage] いいねエラー: {e}")

    # ハッシュタグの投稿にいいね
    for hashtag in target_hashtags:
        if liked >= max_likes:
            break
        tweets = search_recent_tweets(client, f"#{hashtag}", max_results=10)
        for tweet in tweets:
            if liked >= max_likes:
                break
            tweet_id = str(tweet.id)
            if already_engaged(tweet_id, "like", log):
                continue
            if dry_run:
                print(f"[engage][DRY RUN] いいね → #{hashtag}: {tweet.text[:50]}...")
            else:
                try:
                    client.like(tweet_id)
                    print(f"[engage] いいね → #{hashtag}: {tweet.text[:50]}...")
                    record_engage(tweet_id, "like", tweet.text, log)
                    liked += 1
                except tweepy.TweepyException as e:
                    print(f"[engage] いいねエラー: {e}")

    if not dry_run:
        save_engage_log(log)

    print(f"[engage] いいね完了: {liked}件")
    return liked


def auto_repost(config: dict, dry_run: bool = False) -> int:
    """対象アカウント・ハッシュタグの投稿をリポストする"""
    client = get_client()
    log = load_engage_log()
    max_reposts = config.get("max_reposts_per_run", 2)
    min_likes = config.get("repost_min_likes", 5)
    reposted = 0

    target_accounts = [a for a in config.get("target_accounts", []) if a]
    target_hashtags = [h for h in config.get("target_hashtags", []) if h]

    queries = [f"from:{a}" for a in target_accounts] + [f"#{h}" for h in target_hashtags]

    for query in queries:
        if reposted >= max_reposts:
            break
        tweets = search_recent_tweets(client, query, max_results=10)
        # いいね数でフィルタ・ソート
        qualified = [
            t for t in tweets
            if (t.public_metrics or {}).get("like_count", 0) >= min_likes
        ]
        qualified.sort(key=lambda t: (t.public_metrics or {}).get("like_count", 0), reverse=True)

        for tweet in qualified:
            if reposted >= max_reposts:
                break
            tweet_id = str(tweet.id)
            if already_engaged(tweet_id, "repost", log):
                continue
            if dry_run:
                print(f"[engage][DRY RUN] リポスト → {tweet.text[:50]}...")
            else:
                try:
                    client.retweet(tweet_id)
                    print(f"[engage] リポスト → {tweet.text[:50]}...")
                    record_engage(tweet_id, "repost", tweet.text, log)
                    reposted += 1
                except tweepy.TweepyException as e:
                    print(f"[engage] リポストエラー: {e}")

    if not dry_run:
        save_engage_log(log)

    print(f"[engage] リポスト完了: {reposted}件")
    return reposted


def run_engagement(persona: dict, dry_run: bool = False) -> None:
    """いいね・リポストをまとめて実行する"""
    config = persona.get("engagement", {})
    if not config.get("enabled", False):
        print("[engage] engagement.enabled = false のためスキップ")
        return

    print("[engage] 自動いいね・リポスト開始...")
    auto_like(config, dry_run=dry_run)
    auto_repost(config, dry_run=dry_run)
    print("[engage] 完了")
