"""
収益トラッキングモジュール

各プラットフォームの投稿・エンゲージメント・収益を記録し、
週次レポートを生成する。

収益はすべて「推定値」。実際の振込額は各プラットフォームの
ダッシュボードで確認すること。
"""
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
METRICS_PATH = Path("posts/monetization_metrics.json")

# 推定収益レート（実績値に基づいて随時更新）
RATE_ESTIMATES = {
    "x": {
        "ad_revenue_per_1k_impressions_jpy": 80,
        "description": "X Premium 収益シェア（インプレッション連動）",
    },
    "instagram": {
        "affiliate_commission_rate": 0.04,
        "sponsored_post_base_jpy": 5000,
        "description": "アフィリエイト4%  + スポンサード投稿",
    },
    "note": {
        "membership_monthly_jpy": 500,
        "paid_article_jpy": 300,
        "description": "メンバーシップ月額 + 有料記事",
    },
    "tiktok": {
        "creator_fund_per_1k_views_jpy": 50,
        "description": "Creator Fund（1000再生≈50円）",
    },
}


def load_metrics() -> dict:
    """収益メトリクスを読み込む"""
    if not METRICS_PATH.exists():
        return {"posts": [], "engagements": [], "revenue_events": []}
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"posts": [], "engagements": [], "revenue_events": []}


def save_metrics(metrics: dict) -> None:
    """収益メトリクスを保存する"""
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


def record_post(platform: str, post_result: dict) -> None:
    """
    投稿イベントを記録する

    Args:
        platform: "x" | "instagram" | "note" | "tiktok"
        post_result: adapter.post() の戻り値
    """
    metrics = load_metrics()
    entry = {
        "platform": platform,
        "platform_id": post_result.get("platform_id"),
        "text_preview": post_result.get("text", "")[:80],
        "timestamp": post_result.get("timestamp", datetime.now(JST).isoformat()),
        "status": post_result.get("status"),
    }
    metrics["posts"].append(entry)
    save_metrics(metrics)
    print(f"[monetization] 投稿記録: {platform} | {entry['text_preview'][:40]}...")


def record_engagement(platform: str, post_id: str, metrics_data: dict) -> None:
    """
    エンゲージメントメトリクスを記録する

    Args:
        platform: プラットフォーム名
        post_id: 投稿ID（platform_id）
        metrics_data: {
            "likes": 0, "views": 0, "shares": 0,
            "comments": 0, "new_followers": 0,
            "note_sales": 0, "affiliate_clicks": 0
        }
    """
    metrics = load_metrics()
    entry = {
        "platform": platform,
        "post_id": post_id,
        "timestamp": datetime.now(JST).isoformat(),
        **metrics_data,
    }
    entry["estimated_revenue_jpy"] = _estimate_revenue(platform, metrics_data)
    metrics["engagements"].append(entry)
    save_metrics(metrics)


def record_revenue_event(
    platform: str,
    event_type: str,
    amount_jpy: float,
    note: str = "",
) -> None:
    """
    実際の収益イベントを記録する（振込確認時など）

    Args:
        platform: プラットフォーム名
        event_type: "membership_fee" | "article_sale" | "affiliate" | "sponsored" | "creator_fund"
        amount_jpy: 金額（円）
        note: 備考
    """
    metrics = load_metrics()
    entry = {
        "platform": platform,
        "event_type": event_type,
        "amount_jpy": amount_jpy,
        "timestamp": datetime.now(JST).isoformat(),
        "note": note,
    }
    metrics["revenue_events"].append(entry)
    save_metrics(metrics)
    print(f"[monetization] 収益記録: {platform} | {event_type} | ¥{amount_jpy:,.0f}")


def _estimate_revenue(platform: str, metrics_data: dict) -> float:
    """エンゲージメントデータから推定収益（円）を計算する"""
    rates = RATE_ESTIMATES.get(platform, {})
    estimated = 0.0

    if platform == "x":
        views = metrics_data.get("views", 0)
        estimated = (views / 1000) * rates.get("ad_revenue_per_1k_impressions_jpy", 80)

    elif platform == "instagram":
        affiliate_clicks = metrics_data.get("affiliate_clicks", 0)
        estimated = affiliate_clicks * 500 * rates.get("affiliate_commission_rate", 0.04)

    elif platform == "note":
        note_sales = metrics_data.get("note_sales", 0)
        estimated = note_sales * rates.get("paid_article_jpy", 300)

    elif platform == "tiktok":
        views = metrics_data.get("views", 0)
        estimated = (views / 1000) * rates.get("creator_fund_per_1k_views_jpy", 50)

    return round(estimated, 2)


def generate_weekly_report() -> str:
    """週次収益レポートを Markdown で生成する"""
    metrics = load_metrics()
    now = datetime.now(JST)
    week_ago = now - timedelta(days=7)

    # 先週の投稿数をプラットフォーム別に集計
    posts_by_platform: dict[str, int] = {}
    for post in metrics.get("posts", []):
        try:
            ts = datetime.fromisoformat(post.get("timestamp", ""))
            if ts >= week_ago:
                p = post.get("platform", "unknown")
                posts_by_platform[p] = posts_by_platform.get(p, 0) + 1
        except Exception:
            pass

    # 先週のエンゲージメントを集計
    total_views = 0
    total_likes = 0
    total_estimated_jpy = 0.0
    for eng in metrics.get("engagements", []):
        try:
            ts = datetime.fromisoformat(eng.get("timestamp", ""))
            if ts >= week_ago:
                total_views += eng.get("views", 0)
                total_likes += eng.get("likes", 0)
                total_estimated_jpy += eng.get("estimated_revenue_jpy", 0)
        except Exception:
            pass

    # 確定収益（実際の振込ベース）
    confirmed_jpy = 0.0
    confirmed_by_type: dict[str, float] = {}
    for ev in metrics.get("revenue_events", []):
        try:
            ts = datetime.fromisoformat(ev.get("timestamp", ""))
            if ts >= week_ago:
                amount = ev.get("amount_jpy", 0)
                confirmed_jpy += amount
                etype = ev.get("event_type", "other")
                confirmed_by_type[etype] = confirmed_by_type.get(etype, 0) + amount
        except Exception:
            pass

    # レポート生成
    week_str = f"{week_ago.strftime('%m/%d')} 〜 {now.strftime('%m/%d')}"
    post_rows = "\n".join(
        f"| {p.upper()} | {c}件 |" for p, c in sorted(posts_by_platform.items())
    ) or "| （投稿なし） | 0件 |"

    revenue_rows = "\n".join(
        f"| {k} | ¥{v:,.0f} |" for k, v in sorted(confirmed_by_type.items())
    ) or "| （収益なし） | ¥0 |"

    report = f"""## 📊 週次収益レポート（{week_str}）

### 投稿実績
| プラットフォーム | 投稿数 |
|---|---|
{post_rows}

### エンゲージメント（先週合計）
- 総ビュー: {total_views:,}
- 総いいね: {total_likes:,}
- 推定収益: ¥{total_estimated_jpy:,.0f}（エンゲージメントベース推定）

### 確定収益（振込・購入ベース）
| 収益種別 | 金額 |
|---|---|
{revenue_rows}
**合計: ¥{confirmed_jpy:,.0f}**

### 収益化ステータス
| プラットフォーム | 状況 |
|---|---|
| X | X Premium 収益シェア（インプレッション連動） |
| Instagram | アフィリエイトリンク設定 → フォロワー獲得後スポンサー交渉 |
| note | メンバーシップ / 有料記事 → 最速で収益化可能 |
| TikTok | Creator Fund（1,000フォロワー達成後に申請） |

> ※ 推定値は実際の収益と異なる場合があります。各プラットフォームのダッシュボードで確認してください。

---
*自動生成: {now.strftime('%Y-%m-%d %H:%M')} JST*
"""
    return report


def main():
    parser = argparse.ArgumentParser(description="収益トラッカー")
    parser.add_argument("--report", action="store_true", help="週次レポートを生成して表示")
    parser.add_argument("--record-revenue", nargs=4,
                        metavar=("PLATFORM", "TYPE", "AMOUNT", "NOTE"),
                        help="収益イベントを記録: platform type amount note")
    args = parser.parse_args()

    if args.report:
        report = generate_weekly_report()
        print(report)
        # ワークフローから呼び出された場合はファイルにも書き出す
        report_path = Path("posts/monetization_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n[monetization] レポートを保存: {report_path}")

    elif args.record_revenue:
        platform, event_type, amount, note = args.record_revenue
        record_revenue_event(platform, event_type, float(amount), note)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
