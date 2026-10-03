"""
トレンドリサーチモジュール
XAI_API_KEY があれば Grok の X検索で「いまXで話題のこと」を集め、
なければ（または失敗したら）DuckDuckGo検索で最新の話題を収集する

環境変数:
  RESEARCH_PROVIDER … auto（既定: Grokが使えればGrok）/ grok / ddg（DuckDuckGoのみ）
"""
import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from ddgs import DDGS

# Grok の検索結果を使い回す時間（同じプロセス内。Webアプリの連続生成・再生成でAPI代を節約）
_GROK_CACHE_TTL = 30 * 60
_grok_cache: dict = {}


def get_x_trending_topics(interests: list[str], max_topics: int = 5, days: int = 3) -> list[dict]:
    """
    Grok の X検索で、興味分野について直近のXで話題になっていることを集める

    Returns:
        トピックのリスト（topic, title, snippet, url）。get_trending_topics と同じ形
    """
    import grok_client

    key = tuple(interests)
    cached = _grok_cache.get(key)
    if cached and time.monotonic() - cached[0] < _GROK_CACHE_TTL:
        return cached[1]

    selected = random.sample(interests, min(2, len(interests)))
    today = datetime.now().date()
    themes = "\n".join(f"- {t}" for t in selected)
    system = (
        "あなたは日本のSNSトレンドリサーチャーです。x_search ツールで日本語のX（旧Twitter）の投稿を検索し、"
        "実際に話題になっていることだけを報告します。検索で確認できなかったことは書きません。"
    )
    user = f"""次のテーマについて、直近{days}日間に日本のXで話題になっている具体的なトピックを最大{max_topics}件挙げてください。

【テーマ】
{themes}

【除外】
- 特定の個人への誹謗中傷・炎上中の個人の話題
- 政治・宗教・事件事故など、配信者の日常投稿で触れるには重い話題

【出力】JSON配列のみ（説明文・コードブロック不要）:
[{{"topic": "上のテーマのどれか（そのまま）", "title": "話題の見出し（30字以内）", "snippet": "何が話題か・どんな反応が多いか（120字以内）", "url": "代表的なポストのURL"}}]
"""
    text, citations = grok_client.chat(
        system,
        user,
        model=os.environ.get("GROK_RESEARCH_MODEL", "").strip() or None,
        tools=[grok_client.x_search_tool(
            from_date=(today - timedelta(days=days)).isoformat(),
            to_date=today.isoformat(),
        )],
        max_turns=3,
        include=["no_inline_citations"],
        timeout=45,
    )
    topics = _parse_grok_topics(text, selected, citations)[:max_topics]
    if not topics:
        raise ValueError(f"Grok の検索結果を読み取れませんでした: {text[:200]}")
    _grok_cache[key] = (time.monotonic(), topics)
    return topics


def _find_json_list(text: str) -> list:
    """文中の最初の JSON 配列（[{...}, ...]）を取り出す。[1] のような引用番号は読み飛ばす"""
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\[", text):
        try:
            items, _ = decoder.raw_decode(text, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(items, list) and any(isinstance(x, dict) for x in items):
            return items
    return []


def _parse_grok_topics(text: str, selected: list[str], citations: list[str]) -> list[dict]:
    topics = []
    for i, item in enumerate(_find_json_list(text)):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        if not (title or snippet):
            continue
        url = str(item.get("url", "")).strip()
        if not url.startswith("https://") and i < len(citations):
            url = citations[i]
        topics.append({
            "topic": str(item.get("topic", "")).strip() or selected[0],
            "title": title,
            "snippet": snippet or title,
            "url": url,
            "source": "x",
        })
    return topics


def get_trending_topics(interests: list[str], max_results: int = 3) -> list[dict]:
    """
    ペルソナの興味分野からトレンドトピックを取得する
    Grok（X検索）が使えればそれを優先し、失敗したら DuckDuckGo に切り替える

    Args:
        interests: ペルソナの興味リスト
        max_results: 取得する結果数

    Returns:
        トピックのリスト（title, snippet, url）
    """
    import grok_client

    provider = os.environ.get("RESEARCH_PROVIDER", "auto").strip().lower()
    if interests and provider != "ddg" and grok_client.is_configured():
        try:
            topics = get_x_trending_topics(interests)
            print(f"[research] Grok の X検索で {len(topics)} 件の話題を取得")
            return topics
        except Exception as e:
            print(f"[research] Grok の X検索に失敗。DuckDuckGo に切り替えます: {e}")

    return _get_ddg_topics(interests, max_results)


def _get_ddg_topics(interests: list[str], max_results: int = 3) -> list[dict]:
    """DuckDuckGo 検索で興味分野の最新情報を集める"""
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
