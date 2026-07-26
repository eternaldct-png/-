"""
エンゲージメント分析モジュール
X APIから投稿データを取得してClaude AIで分析し、ペルソナ設定を改善する
"""
import os
import json
import yaml
import tweepy
import anthropic
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
ANALYSIS_DIR = Path("analysis")


def get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )


def fetch_tweets_with_metrics(max_results: int = 100) -> list[dict]:
    """自分のツイートをエンゲージメント指標付きで取得する"""
    client = get_client()

    # 自分のuser_idを取得
    me = client.get_me(user_fields=["public_metrics"])
    user_id = me.data.id
    print(f"[analyze] ユーザーID: {user_id}")

    try:
        response = client.get_users_tweets(
            id=user_id,
            max_results=min(max_results, 100),
            tweet_fields=["public_metrics", "created_at", "text"],
            exclude=["retweets"],
        )
    except tweepy.TweepyException as e:
        print(f"[analyze] ツイート取得エラー: {e}")
        return []

    if not response.data:
        print("[analyze] ツイートが見つかりませんでした")
        return []

    tweets = []
    for tweet in response.data:
        metrics = tweet.public_metrics or {}
        # エンゲージメントスコア（いいね×3 + RT×5 + 返信×2 + 引用×4）
        score = (
            metrics.get("like_count", 0) * 3
            + metrics.get("retweet_count", 0) * 5
            + metrics.get("reply_count", 0) * 2
            + metrics.get("quote_count", 0) * 4
        )
        created_jst = tweet.created_at.astimezone(JST) if tweet.created_at else None
        tweets.append({
            "id": str(tweet.id),
            "text": tweet.text,
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "quotes": metrics.get("quote_count", 0),
            "impressions": metrics.get("impression_count", 0),
            "engagement_score": score,
            "created_at": created_jst.strftime("%Y-%m-%d %H:%M") if created_jst else "",
            "day_of_week": created_jst.strftime("%A") if created_jst else "",
            "hour": created_jst.hour if created_jst else 0,
        })

    # スコア降順でソート
    tweets.sort(key=lambda x: x["engagement_score"], reverse=True)
    print(f"[analyze] {len(tweets)}件のツイートを取得しました")
    return tweets


def analyze_with_claude(tweets: list[dict], persona: dict) -> str:
    """Claude AIでエンゲージメントパターンを分析する"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if not tweets:
        return "分析対象のツイートがありませんでした。"

    top5 = tweets[:5]
    bottom5 = tweets[-5:] if len(tweets) >= 10 else []

    top_text = "\n".join([
        f"【スコア{t['engagement_score']}】いいね{t['likes']} RT{t['retweets']} 返信{t['replies']}\n"
        f"  投稿日時: {t['created_at']} ({t['day_of_week']})\n"
        f"  内容: {t['text']}"
        for t in top5
    ])
    bottom_text = "\n".join([
        f"【スコア{t['engagement_score']}】いいね{t['likes']} RT{t['retweets']} 返信{t['replies']}\n"
        f"  投稿日時: {t['created_at']} ({t['day_of_week']})\n"
        f"  内容: {t['text']}"
        for t in bottom5
    ]) if bottom5 else "（データ不足）"

    # 時間帯・曜日分析
    hour_scores: dict[int, list] = {}
    day_scores: dict[str, list] = {}
    for t in tweets:
        h = t["hour"]
        d = t["day_of_week"]
        hour_scores.setdefault(h, []).append(t["engagement_score"])
        day_scores.setdefault(d, []).append(t["engagement_score"])

    best_hours = sorted(
        hour_scores.items(),
        key=lambda x: sum(x[1]) / len(x[1]),
        reverse=True
    )[:3]
    best_days = sorted(
        day_scores.items(),
        key=lambda x: sum(x[1]) / len(x[1]),
        reverse=True
    )[:3]

    prompt = f"""あなたはSNSマーケティングの専門家です。
以下のXアカウント「{persona.get('name')}」の投稿データを分析してください。

== エンゲージメント上位5件 ==
{top_text}

== エンゲージメント下位5件 ==
{bottom_text}

== 時間帯別平均スコア（上位3時間）==
{chr(10).join(f"{h}時台: 平均{sum(s)/len(s):.1f}" for h, s in best_hours)}

== 曜日別平均スコア（上位3曜日）==
{chr(10).join(f"{d}: 平均{sum(s)/len(s):.1f}" for d, s in best_days)}

== 現在のペルソナ設定 ==
- 口調: {persona.get('tone')}
- 投稿スタイル: {list(persona.get('post_styles', {}).keys())}
- 興味テーマ: {persona.get('interests', [])}

以下の形式で分析レポートを日本語で作成してください：

## 1. エンゲージメントが高い投稿の共通パターン
（3〜5点のポイント）

## 2. エンゲージメントが低い投稿の問題点
（2〜3点のポイント）

## 3. 最適な投稿時間帯・曜日
（具体的な推奨時間を記載）

## 4. ペルソナ・投稿スタイルの改善提案
（具体的に何を変えるべきか。投稿スタイルの重みの変更提案も含める）

## 5. 今後の投稿で意識すべきポイント（3点）
"""

    message = client.messages.create(
        model="claude-opus-5",
        max_tokens=2000,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def save_analysis_report(tweets: list[dict], analysis: str, slug: str = "kurumi") -> Path:
    """分析レポートをMarkdownファイルで保存する（ペルソナごとに名前空間を分ける）"""
    ANALYSIS_DIR.mkdir(exist_ok=True)
    now = datetime.now(JST)
    report_path = ANALYSIS_DIR / f"{slug}_report_{now.strftime('%Y%m%d_%H%M')}.md"
    latest_path = ANALYSIS_DIR / f"{slug}_latest_report.md"

    total = len(tweets)
    avg_score = sum(t["engagement_score"] for t in tweets) / total if total else 0

    content = f"""# エンゲージメント分析レポート
生成日時: {now.strftime('%Y年%m月%d日 %H:%M')} JST
分析対象: {total}件のツイート

## サマリー
| 指標 | 値 |
|------|---|
| 分析件数 | {total}件 |
| 平均エンゲージメントスコア | {avg_score:.1f} |
| 最高スコア | {tweets[0]['engagement_score'] if tweets else 0} |
| 最高いいね数 | {max((t['likes'] for t in tweets), default=0)} |
| 最高RT数 | {max((t['retweets'] for t in tweets), default=0)} |

## 上位投稿 TOP5
{chr(10).join(f"**{i+1}位** (スコア:{t['engagement_score']} / いいね:{t['likes']} / RT:{t['retweets']}){chr(10)}> {t['text']}{chr(10)}" for i, t in enumerate(tweets[:5]))}

---

{analysis}

---
*このレポートはClaude AIによる自動分析です*
"""

    report_path.write_text(content, encoding="utf-8")
    latest_path.write_text(content, encoding="utf-8")
    print(f"[analyze] レポート保存: {report_path}")
    return report_path


def run_analysis(max_tweets: int = 100, persona_path: str = "persona/config.yaml") -> str:
    """エンゲージメント分析を実行してレポートを生成する"""
    from persona_utils import persona_slug
    slug = persona_slug(persona_path)

    print(f"[analyze] [{slug}] ツイートデータを取得中...")
    tweets = fetch_tweets_with_metrics(max_tweets)

    if not tweets:
        print("[analyze] 分析対象のツイートがありません")
        return ""

    print("[analyze] Claude AIで分析中...")
    with open(persona_path, "r", encoding="utf-8") as f:
        persona = yaml.safe_load(f)

    analysis = analyze_with_claude(tweets, persona)

    # 生データを保存（ペルソナごとに名前空間を分ける）
    ANALYSIS_DIR.mkdir(exist_ok=True)
    raw_path = ANALYSIS_DIR / f"{slug}_raw_metrics.json"
    raw_path.write_text(
        json.dumps(tweets, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_path = save_analysis_report(tweets, analysis, slug=slug)
    print(f"\n{'='*60}")
    print(analysis)
    print(f"{'='*60}\n")
    return str(report_path)
