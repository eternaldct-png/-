"""
ベンチマーク分析モジュール
ColorSing・歌・ライバー関連の高エンゲージメントアカウントを分析し、
投稿パターンを抽出してkazutoのペルソナ改善に活用する
"""
import os
import re
import json
import yaml
import tweepy
import anthropic
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from ddgs import DDGS

JST = ZoneInfo("Asia/Tokyo")
ANALYSIS_DIR = Path("analysis")

# 分析対象ハッシュタグ（ターゲットオーディエンスが集まる場所）
TARGET_HASHTAGS = [
    "ColorSing",
    "歌好きと繋がりたい",
    "ライバー",
    "歌ってみた",
    "音楽好きと繋がりたい",
]

# エンゲージメントスコア計算式（analyze.py と統一）
def _score(metrics: dict) -> int:
    return (
        metrics.get("like_count", 0) * 3
        + metrics.get("retweet_count", 0) * 5
        + metrics.get("reply_count", 0) * 2
        + metrics.get("quote_count", 0) * 4
    )


def get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
    )


def search_benchmark_tweets(max_per_tag: int = 20) -> list[dict]:
    """
    ターゲットハッシュタグの高エンゲージメントツイートを収集する
    X APIの検索は直近7日間が対象
    """
    client = get_client()
    all_tweets = []
    seen_ids = set()

    for hashtag in TARGET_HASHTAGS:
        query = f"#{hashtag} -is:retweet lang:ja"
        try:
            response = client.search_recent_tweets(
                query=query,
                max_results=min(max_per_tag, 100),
                tweet_fields=["public_metrics", "created_at", "text", "author_id"],
                user_fields=["public_metrics", "username"],
                expansions=["author_id"],
            )
        except tweepy.TweepyException as e:
            print(f"[benchmark] 検索エラー (#{hashtag}): {e}")
            continue

        if not response.data:
            print(f"[benchmark] #{hashtag}: 結果なし")
            continue

        # ユーザー情報をマップ
        user_map = {}
        if response.includes and response.includes.get("users"):
            for u in response.includes["users"]:
                user_map[u.id] = {
                    "username": u.username,
                    "followers": u.public_metrics.get("followers_count", 0) if u.public_metrics else 0,
                }

        for tweet in response.data:
            if str(tweet.id) in seen_ids:
                continue
            seen_ids.add(str(tweet.id))

            metrics = tweet.public_metrics or {}
            score = _score(metrics)
            created_jst = tweet.created_at.astimezone(JST) if tweet.created_at else None
            author = user_map.get(tweet.author_id, {})

            all_tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "hashtag_source": hashtag,
                "username": author.get("username", ""),
                "followers": author.get("followers", 0),
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "quotes": metrics.get("quote_count", 0),
                "engagement_score": score,
                "created_at": created_jst.strftime("%Y-%m-%d %H:%M") if created_jst else "",
                "hour": created_jst.hour if created_jst else 0,
                "day_of_week": created_jst.strftime("%A") if created_jst else "",
            })

        print(f"[benchmark] #{hashtag}: {len(response.data)}件取得")

    all_tweets.sort(key=lambda x: x["engagement_score"], reverse=True)
    print(f"[benchmark] 合計 {len(all_tweets)} 件収集")
    return all_tweets


def extract_patterns(tweets: list[dict]) -> dict:
    """
    高エンゲージメント投稿からテキスト構造パターンを自動抽出する
    """
    top = tweets[:30]  # 上位30件を解析対象に

    patterns = {
        "hook_types": {},       # 書き出しのパターン
        "has_question": 0,      # 疑問文を含む割合
        "has_emoji": 0,         # 絵文字を含む割合
        "avg_length": 0,        # 平均文字数
        "has_line_breaks": 0,   # 改行を含む割合
        "hashtag_counts": {},   # ハッシュタグ数の分布
        "best_hours": {},       # 時間帯別スコア合計
        "best_days": {},        # 曜日別スコア合計
        "cta_patterns": 0,      # コメント・リプライ誘導を含む割合
        "top_examples": [],     # 上位5件の実例
    }

    emoji_re = re.compile(
        "[\U00010000-\U0010ffff"
        "\U0001F300-\U0001F9FF"
        "☀-⛿✀-➿]+",
        flags=re.UNICODE,
    )
    cta_keywords = ["教えて", "コメント", "教えてください", "リプ", "返信", "どう思う", "みんなは", "あなたは"]

    total = len(top)
    if total == 0:
        return patterns

    total_len = 0
    for t in top:
        text = t["text"]
        total_len += len(text)

        # 書き出しパターン（最初の5文字で分類）
        first = text[:5].strip()
        if first.startswith("【"):
            key = "【括弧始まり】"
        elif re.match(r"[0-9０-９]", first):
            key = "数字始まり"
        elif emoji_re.match(first):
            key = "絵文字始まり"
        elif "？" in first or "?" in first:
            key = "疑問文始まり"
        else:
            key = "テキスト始まり"
        patterns["hook_types"][key] = patterns["hook_types"].get(key, 0) + 1

        # 疑問文
        if "？" in text or "?" in text or "ですか" in text or "ませんか" in text:
            patterns["has_question"] += 1

        # 絵文字
        if emoji_re.search(text):
            patterns["has_emoji"] += 1

        # 改行
        if "\n" in text:
            patterns["has_line_breaks"] += 1

        # ハッシュタグ数
        tag_count = len(re.findall(r"#\S+", text))
        key_tag = f"{tag_count}個"
        patterns["hashtag_counts"][key_tag] = patterns["hashtag_counts"].get(key_tag, 0) + 1

        # CTA
        if any(kw in text for kw in cta_keywords):
            patterns["cta_patterns"] += 1

        # 時間帯・曜日
        h = t["hour"]
        d = t["day_of_week"]
        patterns["best_hours"][h] = patterns["best_hours"].get(h, 0) + t["engagement_score"]
        patterns["best_days"][d] = patterns["best_days"].get(d, 0) + t["engagement_score"]

    patterns["avg_length"] = total_len // total
    patterns["question_ratio"] = round(patterns["has_question"] / total * 100)
    patterns["emoji_ratio"] = round(patterns["has_emoji"] / total * 100)
    patterns["line_break_ratio"] = round(patterns["has_line_breaks"] / total * 100)
    patterns["cta_ratio"] = round(patterns["cta_patterns"] / total * 100)
    patterns["top_examples"] = [
        {"text": t["text"], "score": t["engagement_score"], "likes": t["likes"], "retweets": t["retweets"]}
        for t in tweets[:5]
    ]

    # 時間帯・曜日をスコア降順でソート
    patterns["best_hours"] = dict(
        sorted(patterns["best_hours"].items(), key=lambda x: x[1], reverse=True)[:5]
    )
    patterns["best_days"] = dict(
        sorted(patterns["best_days"].items(), key=lambda x: x[1], reverse=True)[:3]
    )

    return patterns


def ddg_research_best_practices() -> list[dict]:
    """
    DuckDuckGoで音楽ライバー・ColorSing関連の成功事例・ノウハウを検索する
    """
    queries = [
        "ColorSing 人気ライバー 配信 コツ",
        "X Twitter 音楽アカウント フォロワー増やす 投稿",
        "歌い手 SNS 人気 投稿 パターン 2024",
        "ライバー事務所 Twitter 発信 集客",
    ]
    results = []
    for query in queries:
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, region="jp-jp", max_results=2))
                for hit in hits:
                    results.append({
                        "query": query,
                        "title": hit.get("title", ""),
                        "snippet": hit.get("body", "")[:300],
                    })
        except Exception as e:
            print(f"[benchmark] DDG検索エラー ({query}): {e}")
    return results


def synthesize_with_claude(
    tweets: list[dict],
    patterns: dict,
    ddg_results: list[dict],
    persona: dict,
) -> str:
    """
    収集データをClaudeで総合分析し、kazuto向けの改善提案を生成する
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    top_examples = "\n\n".join([
        f"【スコア{e['score']} / いいね{e['likes']} / RT{e['retweets']}】\n{e['text']}"
        for e in patterns.get("top_examples", [])
    ])

    hook_summary = "\n".join(
        f"- {k}: {v}件" for k, v in patterns.get("hook_types", {}).items()
    )

    hour_summary = "\n".join(
        f"- {h}時台: スコア合計{s}" for h, s in list(patterns.get("best_hours", {}).items())[:5]
    )

    ddg_summary = "\n\n".join([
        f"【{r['title']}】\n{r['snippet']}" for r in ddg_results[:4]
    ])

    prompt = f"""あなたはXのSNS戦略コンサルタントです。
ColorSingで配信する歌い手「{persona.get('name', 'kazuto')}」（ライバー事務所代表）のX投稿を改善するため、
ターゲットハッシュタグ（#ColorSing #歌好きと繋がりたい #ライバー #歌ってみた）の
高エンゲージメント投稿を分析しました。

== 高エンゲージメント投稿 TOP5 ==
{top_examples}

== 書き出しパターン分布 ==
{hook_summary}

== 構造的特徴（上位30件の集計）==
- 疑問文を含む投稿の割合: {patterns.get('question_ratio', 0)}%
- 絵文字を含む投稿の割合: {patterns.get('emoji_ratio', 0)}%
- 改行を使う投稿の割合: {patterns.get('line_break_ratio', 0)}%
- コメント・返信誘導（CTA）の割合: {patterns.get('cta_ratio', 0)}%
- 平均文字数: {patterns.get('avg_length', 0)}文字
- ハッシュタグ数分布: {patterns.get('hashtag_counts', {})}

== エンゲージメントが高い時間帯 ==
{hour_summary}

== Web調査（音楽ライバー・SNS成功事例）==
{ddg_summary}

== kazutoの現在の投稿スタイル ==
口調: {persona.get('tone')}
1日の投稿数: {persona.get('posting_schedule', {}).get('times_per_day', 5)}回
興味テーマ: {persona.get('interests', [])}

以下の形式で日本語の分析レポートを書いてください：

## 1. 高エンゲージメント投稿の勝ちパターン（5点）
具体的な文章構造・フック・言葉選びのパターンを挙げてください

## 2. kazutoが今すぐ取り入れるべき投稿テクニック（5点）
現在のスタイルと比較して、差分となる改善点を具体的に

## 3. 最適な投稿時間帯・曜日の推奨
データに基づいた具体的な時間帯の推奨

## 4. 即使えるフック文の例（5例）
高エンゲージメント投稿のパターンを参考に、kazutoが実際に使えるオープニング文

## 5. ハッシュタグ戦略の更新提案
どのタグを優先し、どう組み合わせるべきか
"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def save_benchmark_report(tweets: list[dict], patterns: dict, analysis: str) -> Path:
    """分析結果をJSONとMarkdownで保存する"""
    ANALYSIS_DIR.mkdir(exist_ok=True)
    now = datetime.now(JST)
    ts = now.strftime("%Y%m%d_%H%M")

    # 生データJSON
    raw = {
        "generated_at": now.isoformat(),
        "tweet_count": len(tweets),
        "patterns": patterns,
        "top_tweets": tweets[:20],
    }
    raw_path = ANALYSIS_DIR / f"benchmark_raw_{ts}.json"
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    # 最新パターンJSON（persona_updaterが読み込む）
    latest_patterns_path = ANALYSIS_DIR / "benchmark_patterns_latest.json"
    latest_patterns_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdownレポート
    total = len(tweets)
    avg = sum(t["engagement_score"] for t in tweets) / total if total else 0
    top5_md = "\n".join([
        f"**{i+1}位** (スコア:{t['engagement_score']} / いいね:{t['likes']} / RT:{t['retweets']} / @{t['username']})\n"
        f"> {t['text'][:120]}\n"
        for i, t in enumerate(tweets[:5])
    ])

    report = f"""# ベンチマーク分析レポート
生成日時: {now.strftime('%Y年%m月%d日 %H:%M')} JST
対象ハッシュタグ: {', '.join('#' + h for h in TARGET_HASHTAGS)}
収集ツイート数: {total}件

## サマリー
| 指標 | 値 |
|------|---|
| 収集件数 | {total}件 |
| 平均エンゲージメントスコア | {avg:.1f} |
| 最高スコア | {tweets[0]['engagement_score'] if tweets else 0} |
| 平均文字数 | {patterns.get('avg_length', 0)}文字 |
| 疑問文含有率 | {patterns.get('question_ratio', 0)}% |
| 絵文字使用率 | {patterns.get('emoji_ratio', 0)}% |
| CTA（返信誘導）含有率 | {patterns.get('cta_ratio', 0)}% |

## 高エンゲージメント投稿 TOP5
{top5_md}

---

{analysis}

---
*このレポートはClaude AIによる自動分析です*
"""

    report_path = ANALYSIS_DIR / f"benchmark_report_{ts}.md"
    report_path.write_text(report, encoding="utf-8")

    latest_report_path = ANALYSIS_DIR / "benchmark_latest.md"
    latest_report_path.write_text(report, encoding="utf-8")

    print(f"[benchmark] レポート保存: {report_path}")
    print(f"[benchmark] 最新パターンJSON: {latest_patterns_path}")
    return report_path


def run_benchmark(max_per_tag: int = 20) -> str:
    """ベンチマーク分析のメインエントリーポイント"""
    print("[benchmark] ターゲットハッシュタグのツイートを収集中...")
    tweets = search_benchmark_tweets(max_per_tag)

    if not tweets:
        print("[benchmark] 収集できたツイートがありません。スキップします。")
        return ""

    print("[benchmark] パターン抽出中...")
    patterns = extract_patterns(tweets)

    print("[benchmark] Web調査中（DuckDuckGo）...")
    ddg_results = ddg_research_best_practices()

    print("[benchmark] ペルソナ設定を読み込み中...")
    persona_path = Path("persona/kazuto_config.yaml")
    if not persona_path.exists():
        persona_path = Path("persona/config.yaml")
    with open(persona_path, "r", encoding="utf-8") as f:
        persona = yaml.safe_load(f)

    print("[benchmark] Claude AIで総合分析中...")
    analysis = synthesize_with_claude(tweets, patterns, ddg_results, persona)

    report_path = save_benchmark_report(tweets, patterns, analysis)

    print(f"\n{'='*60}")
    print(analysis)
    print(f"{'='*60}\n")
    return str(report_path)
