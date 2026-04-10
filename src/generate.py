"""
投稿文生成モジュール
Claude APIを使ってペルソナに合った自然な投稿文を生成する
"""
import os
import random
import anthropic
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from post import get_recent_posts

JST = ZoneInfo("Asia/Tokyo")


def get_day_context(persona: dict, target_dt: Optional[datetime] = None) -> dict:
    """指定日時（省略時は現在）の曜日に応じたムードとハッシュタグを返す"""
    dt = target_dt if target_dt else datetime.now(JST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    day_names = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"]
    day_name = day_names[dt.weekday()]
    date_str = dt.strftime("%-m月%-d日")  # 例: 4月9日

    day_specific = persona.get("day_specific", {})
    day_info = day_specific.get(day_name, {})

    return {
        "day_name": day_name,
        "date_str": date_str,
        "mood": day_info.get("mood", ""),
        "hashtags": day_info.get("hashtags", []),
    }


def build_system_prompt(persona: dict) -> str:
    """ペルソナ設定からシステムプロンプトを構築する"""
    personality_str = "\n".join(f"- {p}" for p in persona.get("personality", []))
    avoid_str = "\n".join(f"- {a}" for a in persona.get("avoid", []))
    styles = persona.get("post_styles", {})
    style_examples = []
    for style_name, style_data in styles.items():
        if isinstance(style_data, dict):
            style_examples.append(f"- {style_data.get('description', style_name)}")

    return f"""あなたは「{persona['name']}」というX（旧Twitter）ユーザーです。

【キャラクター設定】
{persona.get('bio', '')}

【性格・特徴】
{personality_str}

【投稿のルール】
- 日本語で投稿する
- 最大{persona.get('max_length', 140)}文字以内（厳守）
- 自然な口語体で書く（硬すぎない、マニュアル的にならない）
- フォロワーに語りかけるような温かみのある文体
- 絵文字は1〜2個まで（多すぎない）
- ハッシュタグは文末にまとめて最大{persona.get('max_hashtags', 2)}個

【投稿スタイルのバリエーション】
{chr(10).join(style_examples)}

【絶対に書かないこと】
{avoid_str}

【大切にすること】
- 「投稿感」を出さない。本当にその人がつぶやいているように見せる
- 毎回同じパターンにならないように変化をつける
- フォロワーが反応したくなる（共感・質問・面白い）要素を入れる
"""


def select_post_style(persona: dict) -> str:
    """重みに基づいて投稿スタイルをランダム選択する"""
    styles = persona.get("post_styles", {})
    weights = []
    names = []
    for name, data in styles.items():
        if isinstance(data, dict):
            weights.append(data.get("weight", 20))
            names.append(data.get("description", name))
    if not names:
        return "日常の一コマをシェア"
    return random.choices(names, weights=weights, k=1)[0]


def select_hashtags(persona: dict, topic: Optional[str] = None, day_tags: Optional[list] = None) -> list[str]:
    """トピック・曜日に合ったハッシュタグを選択する"""
    hashtags = persona.get("hashtags", {})
    common = hashtags.get("common", [])
    topic_specific = hashtags.get("topic_specific", {})
    max_tags = persona.get("max_hashtags", 2)

    selected = []

    # 曜日タグを最優先（1個まで）
    if day_tags:
        selected.append(day_tags[0])

    # トピック固有のタグ
    if topic and len(selected) < max_tags:
        for key, tags in topic_specific.items():
            if key in (topic or "").lower():
                candidates = [t for t in tags if t not in selected]
                if candidates:
                    selected.append(random.choice(candidates))
                break

    # 残り枠をcommonタグで埋める
    remaining = max_tags - len(selected)
    if remaining > 0 and common:
        candidates = [t for t in common if t not in selected]
        selected.extend(random.sample(candidates, min(remaining, len(candidates))))

    return selected[:max_tags]


def generate_post(persona: dict, research_context: dict, target_dt: Optional[datetime] = None) -> str:
    """
    Claude APIを使って投稿文を生成する（曜日・日付対応）

    Args:
        persona: ペルソナ設定
        research_context: リサーチ結果（seasonal_context, trending_topics）
        target_dt: 投稿予定日時（省略時は現在時刻）

    Returns:
        生成された投稿文
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style = select_post_style(persona)
    seasonal = research_context.get("seasonal_context", "")
    topics = research_context.get("trending_topics", [])
    day_ctx = get_day_context(persona, target_dt)  # ← 投稿予定日の曜日を使う

    # トピック情報を整形
    topic_text = ""
    if topics:
        topic = random.choice(topics)
        topic_text = f"""
【参考にできる最新トピック（使っても使わなくてもOK）】
テーマ: {topic.get('topic', '')}
内容: {topic.get('snippet', '')[:200]}
"""

    # 曜日ムードの指示
    day_mood_text = ""
    if day_ctx["mood"]:
        day_mood_text = f"\n曜日の雰囲気: {day_ctx['day_name']}（{day_ctx['date_str']}）— {day_ctx['mood']}"

    # 直近の投稿を取得して重複を避ける
    recent_posts = get_recent_posts(5)
    recent_text = ""
    if recent_posts:
        recent_list = "\n".join(f"- {p}" for p in recent_posts)
        recent_text = f"""
【直近の投稿（これと被らない内容にすること）】
{recent_list}
"""

    user_prompt = f"""
今の状況: {seasonal}{day_mood_text}

投稿スタイル: 「{style}」

{topic_text}{recent_text}
上記のスタイルと今日の曜日・雰囲気を活かした自然なツイートを1つ書いてください。
直近の投稿と話題・表現が被らないよう、新鮮な内容にしてください。
投稿文だけを返してください（説明文・前置き不要）。
"""

    hashtags = select_hashtags(
        persona,
        topics[0].get("topic") if topics else None,
        day_ctx["hashtags"],
    )

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        system=build_system_prompt(persona),
        messages=[{"role": "user", "content": user_prompt}],
    )

    post_text = message.content[0].text.strip()

    # ハッシュタグを追加（上限を厳守）
    max_tags = persona.get("max_hashtags", 2)
    if persona.get("add_hashtags", True):
        existing_tags = [w for w in post_text.split() if w.startswith("#")]
        if len(existing_tags) > max_tags:
            for tag in existing_tags[max_tags:]:
                post_text = post_text.replace(" " + tag, "").replace(tag, "")
            post_text = post_text.strip()
        elif len(existing_tags) < max_tags:
            new_tags = [t for t in hashtags if t not in existing_tags]
            slots = max_tags - len(existing_tags)
            post_text = post_text + " " + " ".join(new_tags[:slots])

    # 文字数チェック
    max_len = persona.get("max_length", 140)
    if len(post_text) > max_len:
        post_text = post_text[:max_len].rstrip()

    return post_text.strip()
