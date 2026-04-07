"""
投稿文生成モジュール
Claude APIを使ってペルソナに合った自然な投稿文を生成する
"""
import os
import random
import anthropic
from typing import Optional


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


def select_hashtags(persona: dict, topic: Optional[str] = None) -> list[str]:
    """トピックに合ったハッシュタグを選択する"""
    hashtags = persona.get("hashtags", {})
    common = hashtags.get("common", [])
    topic_specific = hashtags.get("topic_specific", {})
    max_tags = persona.get("max_hashtags", 2)

    selected = []

    # トピック固有のタグを優先
    if topic:
        for key, tags in topic_specific.items():
            if key in (topic or "").lower():
                selected.extend(random.sample(tags, min(1, len(tags))))

    # 残り枠をcommonタグで埋める
    remaining = max_tags - len(selected)
    if remaining > 0 and common:
        selected.extend(random.sample(common, min(remaining, len(common))))

    return selected[:max_tags]


def generate_post(persona: dict, research_context: dict) -> str:
    """
    Claude APIを使って投稿文を生成する

    Args:
        persona: ペルソナ設定
        research_context: リサーチ結果（seasonal_context, trending_topics）

    Returns:
        生成された投稿文
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    style = select_post_style(persona)
    seasonal = research_context.get("seasonal_context", "")
    topics = research_context.get("trending_topics", [])

    # トピック情報を整形
    topic_text = ""
    if topics:
        topic = random.choice(topics)
        topic_text = f"""
【参考にできる最新トピック（使っても使わなくてもOK）】
テーマ: {topic.get('topic', '')}
内容: {topic.get('snippet', '')[:200]}
"""

    user_prompt = f"""
今の状況: {seasonal}

投稿スタイル: 「{style}」

{topic_text}

上記のスタイルで、今の時間帯・季節感を活かした自然なツイートを1つ書いてください。
投稿文だけを返してください（説明文・前置き不要）。
"""

    hashtags = select_hashtags(persona, topics[0].get("topic") if topics else None)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        system=build_system_prompt(persona),
        messages=[{"role": "user", "content": user_prompt}],
    )

    post_text = message.content[0].text.strip()

    # ハッシュタグを追加（重複チェック）
    if persona.get("add_hashtags", True) and hashtags:
        existing_tags = [w for w in post_text.split() if w.startswith("#")]
        new_tags = [t for t in hashtags if t not in existing_tags]
        if new_tags:
            post_text = post_text + " " + " ".join(new_tags)

    # 文字数チェック（念のため）
    max_len = persona.get("max_length", 140)
    if len(post_text) > max_len:
        # 超えたらハッシュタグなしで再生成シグナル（簡易処理）
        post_text = post_text[:max_len].rstrip()

    return post_text
