"""
トレンドリサーチモジュール
DuckDuckGo検索を使って最新の話題を収集する
"""
import random
from datetime import datetime
from typing import Optional
from ddgs import DDGS


def get_trending_topics(interests: list[str], max_results: int = 3) -> list[dict]:
    """
    ペルソナの興味分野からトレンドトピックを取得する

    Args:
        interests: ペルソナの興味リスト
        max_results: 取得する結果数

    Returns:
        トピックのリスト（title, snippet, url）
    """
    results = []

    # 興味リストからランダムに1〜2つ選んで検索
    selected = random.sample(interests, min(2, len(interests)))

    for interest in selected:
        query = f"{interest} 最新 {datetime.now().strftime('%Y年%m月')}"
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, region="jp-jp", max_results=max_results))
                for hit in hits:
                    results.append({
                        "topic": interest,
                        "title": hit.get("title", ""),
                        "snippet": hit.get("body", ""),
                        "url": hit.get("href", ""),
                    })
        except Exception as e:
            print(f"[research] 検索エラー ({interest}): {e}")

    return results[:5]  # 最大5件


def get_seasonal_context() -> str:
    """現在の季節・時間帯のコンテキストを返す"""
    now = datetime.now()
    month = now.month
    hour = now.hour

    season_map = {
        (3, 4, 5): "春",
        (6, 7, 8): "夏",
        (9, 10, 11): "秋",
        (12, 1, 2): "冬",
    }
    season = next(s for months, s in season_map.items() if month in months)

    if 5 <= hour < 10:
        time_of_day = "朝"
    elif 10 <= hour < 14:
        time_of_day = "昼"
    elif 14 <= hour < 18:
        time_of_day = "午後"
    elif 18 <= hour < 22:
        time_of_day = "夜"
    else:
        time_of_day = "深夜"

    day_of_week = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"][now.weekday()]

    return f"{season}・{day_of_week}の{time_of_day}"


def build_research_context(interests: list[str]) -> dict:
    """
    リサーチ結果をまとめて生成AIに渡すコンテキストを作る
    """
    topics = get_trending_topics(interests)
    seasonal = get_seasonal_context()

    return {
        "seasonal_context": seasonal,
        "trending_topics": topics,
        "timestamp": datetime.now().isoformat(),
    }
