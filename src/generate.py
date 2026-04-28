"""
コンテンツ生成モジュール
Claude API を使ってペルソナに合ったコンテンツを生成する
プラットフォームごとに生成形式を切り替える（X / Instagram / note / TikTok）
"""
import os
import json
import random
import anthropic
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

JST = ZoneInfo("Asia/Tokyo")


def get_day_context(persona: dict, target_dt: Optional[datetime] = None) -> dict:
    """指定日時（省略時は現在）の曜日に応じたムードとハッシュタグを返す"""
    dt = target_dt if target_dt else datetime.now(JST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    day_names = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"]
    day_name = day_names[dt.weekday()]
    date_str = dt.strftime("%-m月%-d日")

    day_specific = persona.get("day_specific", {})
    day_info = day_specific.get(day_name, {})

    return {
        "day_name": day_name,
        "date_str": date_str,
        "mood": day_info.get("mood", ""),
        "hashtags": day_info.get("hashtags", []),
    }


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


def select_hashtags(persona: dict, topic: Optional[str] = None, day_tags: Optional[list] = None, max_tags: int = None) -> list[str]:
    """トピック・曜日に合ったハッシュタグを選択する"""
    hashtags = persona.get("hashtags", {})
    common = hashtags.get("common", [])
    topic_specific = hashtags.get("topic_specific", {})
    if max_tags is None:
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


# ── システムプロンプト構築 ─────────────────────────────────────

def build_system_prompt(persona: dict, constraints: dict = None, platform: str = "x") -> str:
    """プラットフォームに応じたシステムプロンプトを構築する"""
    content_format = (constraints or {}).get("content_format", "text")

    if content_format == "markdown":
        return _build_note_system_prompt(persona)
    if content_format == "video_script":
        return _build_tiktok_system_prompt(persona)
    if content_format == "visual_caption":
        return _build_instagram_system_prompt(persona, constraints or {})
    return _build_x_system_prompt(persona, constraints or {})


def _build_x_system_prompt(persona: dict, constraints: dict) -> str:
    """X（Twitter）用システムプロンプト"""
    personality_str = "\n".join(f"- {p}" for p in persona.get("personality", []))
    avoid_str = "\n".join(f"- {a}" for a in persona.get("avoid", []))
    styles = persona.get("post_styles", {})
    style_examples = [
        f"- {d.get('description', n)}"
        for n, d in styles.items()
        if isinstance(d, dict)
    ]
    max_length = constraints.get("max_length", persona.get("max_length", 140))
    max_hashtags = constraints.get("max_hashtags", persona.get("max_hashtags", 2))

    return f"""あなたは「{persona['name']}」というX（旧Twitter）ユーザーです。

【キャラクター設定】
{persona.get('bio', '')}

【性格・特徴】
{personality_str}

【投稿のルール】
- 日本語で投稿する
- 最大{max_length}文字以内（厳守）
- 自然な口語体で書く（硬すぎない、マニュアル的にならない）
- フォロワーに語りかけるような温かみのある文体
- 絵文字は1〜2個まで（多すぎない）
- ハッシュタグは文末にまとめて最大{max_hashtags}個

【投稿スタイルのバリエーション】
{chr(10).join(style_examples)}

【絶対に書かないこと】
{avoid_str}

【大切にすること】
- 「投稿感」を出さない。本当にその人がつぶやいているように見せる
- 毎回同じパターンにならないように変化をつける
- フォロワーが反応したくなる（共感・質問・面白い）要素を入れる
"""


def _build_instagram_system_prompt(persona: dict, constraints: dict) -> str:
    """Instagram用システムプロンプト"""
    personality_str = "\n".join(f"- {p}" for p in persona.get("personality", []))
    avoid_str = "\n".join(f"- {a}" for a in persona.get("avoid", []))
    max_length = constraints.get("max_length", 2200)
    max_hashtags = constraints.get("max_hashtags", 30)

    return f"""あなたは「{persona['name']}」というInstagramユーザーです。
ETERNALd.c.tの広報担当として、プロフェッショナルかつ等身大の投稿を行います。

【キャラクター設定】
{persona.get('bio', '')}

【性格・特徴】
{personality_str}

【Instagramキャプションのルール】
- 日本語で書く
- 最大{max_length}文字以内
- 構成: 1行フック → 改行 → 本文（3〜4段落） → 改行 → ハッシュタグブロック
- 絵文字を適度に使う（各段落に1〜2個）
- ハッシュタグは末尾にまとめて最大{max_hashtags}個
- 読者が保存・シェアしたくなる内容にする
- 「#ETERNALd.c.t」「#広報」は必ず含める

【絶対に書かないこと】
{avoid_str}

【出力形式】
以下のJSON形式で返してください（説明文・コードブロック不要、JSON のみ）:
{{"caption": "キャプション本文（ハッシュタグを含まない本文のみ）", "hashtags": ["#タグ1", "#タグ2", "#タグ3"]}}

注意:
- caption にハッシュタグは含めない
- hashtags は必ず配列形式（文字列結合は使わない）
- JSON以外のテキストは一切出力しない
"""


def _build_note_system_prompt(persona: dict) -> str:
    """note（ブログ）用システムプロンプト"""
    personality_str = "\n".join(f"- {p}" for p in persona.get("personality", []))
    avoid_str = "\n".join(f"- {a}" for a in persona.get("avoid", []))

    return f"""あなたは「{persona['name']}」です。ETERNALd.c.tの広報担当として、
noteに長文記事を書いています。読者に価値を届けながら、メンバーシップへの加入も促します。

【キャラクター設定】
{persona.get('bio', '')}

【性格・特徴】
{personality_str}

【note記事のルール】
- 日本語で書く（1,000〜5,000文字）
- Markdown形式で書く（##見出し、箇条書きなど活用）
- 構成: タイトル → リード文（フック） → 本文（## 見出し 3つ） → まとめ → メンバーシップCTA
- 専門的すぎず、でも読んで得した気持ちになれる内容
- 広報・PR・AIの実体験を交える
- 記事末尾に「メンバーシップ限定コンテンツへの誘導」を自然に入れる

【絶対に書かないこと】
{avoid_str}

【出力形式】
以下のJSON形式で返してください（説明文不要）:
{{"title": "記事タイトル", "body": "本文（Markdown）", "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"]}}
"""


def _build_tiktok_system_prompt(persona: dict) -> str:
    """TikTok用システムプロンプト"""
    avoid_str = "\n".join(f"- {a}" for a in persona.get("avoid", []))

    return f"""あなたは「{persona['name']}」です。ETERNALd.c.tの広報担当として、
TikTokで視聴者を引きつける60秒動画のスクリプトを書きます。

【スクリプトのルール】
- 最初の3秒で視聴者を掴むフックが命
- 話し言葉の日本語（テロップとして読まれることを意識）
- 構成: フック（3秒） → 本題（40秒） → CTA（17秒）
- トレンドのハッシュタグを5〜8個含める
- 広報・仕事・AIなどのテーマで共感・驚き・学びを提供する

【絶対に書かないこと】
{avoid_str}

【出力形式】
以下のJSON形式で返してください（説明文不要）:
{{
  "hook": "最初の3秒で掴む一文",
  "body": "本題の説明（箇条書きOK、40秒分）",
  "cta": "フォロー・コメント・保存を促すCTA",
  "on_screen_text": ["フック表示テキスト", "ポイント1", "ポイント2"],
  "hashtags": ["#広報", "#ETERNALdct", "#PR", "#ビジネス", "#働く女子"],
  "duration_estimate_sec": 60,
  "bgm_suggestion": "BGM提案"
}}
"""


def _safe_parse_json(raw: str, content_format: str) -> dict | None:
    """JSON文字列を複数の戦略で安全にパースする"""
    import re

    # 戦略1: コードブロック除去してそのままパース
    cleaned = raw
    if "```" in cleaned:
        lines = cleaned.split("\n")
        cleaned = "\n".join(l for l in lines if not l.strip().startswith("```"))
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    # 戦略2: 最初の { から最後の } を抽出してパース
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 戦略3: Instagram の場合 caption と hashtags を正規表現で個別抽出
    if content_format == "visual_caption":
        caption_match = re.search(r'"caption"\s*:\s*"(.*?)"(?:\s*,|\s*\})', cleaned, re.DOTALL)
        hashtags_match = re.findall(r'#[\w぀-鿿]+', cleaned)
        if caption_match:
            caption = caption_match.group(1).replace('\\"', '"')
            return {"caption": caption[:2200], "hashtags": hashtags_match[:30]}

    return None


# ── メイン生成関数 ─────────────────────────────────────────────

def generate_post(
    persona: dict,
    research_context: dict,
    target_dt: Optional[datetime] = None,
    platform: str = "x",
    constraints: dict = None,
    recent_posts: list[str] = None,
) -> str | dict:
    """
    Claude API を使ってコンテンツを生成する

    Args:
        persona: ペルソナ設定
        research_context: リサーチ結果
        target_dt: 投稿予定日時（省略時は現在時刻）
        platform: 投稿先プラットフォーム
        constraints: プラットフォーム制約（get_constraints()の戻り値）
        recent_posts: 直近の投稿テキスト（重複回避用）

    Returns:
        X: 投稿文字列
        Instagram: {"caption": ..., "hashtags": [...]}
        note: {"title": ..., "body": ..., "tags": [...]}
        TikTok: {"hook": ..., "body": ..., "cta": ..., "on_screen_text": [...], "hashtags": [...], ...}
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    constraints = constraints or {}
    content_format = constraints.get("content_format", "text")
    max_tokens = constraints.get("max_tokens_hint", 300)

    style = select_post_style(persona)
    seasonal = research_context.get("seasonal_context", "")
    topics = research_context.get("trending_topics", [])
    day_ctx = get_day_context(persona, target_dt)

    # トピック情報
    topic_text = ""
    if topics:
        topic = random.choice(topics)
        topic_text = f"""
【参考にできる最新トピック（使っても使わなくてもOK）】
テーマ: {topic.get('topic', '')}
内容: {topic.get('snippet', '')[:200]}
"""

    # 曜日ムード
    day_mood_text = ""
    if day_ctx["mood"]:
        day_mood_text = f"\n曜日の雰囲気: {day_ctx['day_name']}（{day_ctx['date_str']}）— {day_ctx['mood']}"

    # 直近の投稿（重複回避）
    if recent_posts is None:
        recent_posts = []
    recent_text = ""
    if recent_posts:
        recent_list = "\n".join(f"- {p}" for p in recent_posts)
        recent_text = f"""
【直近の投稿（これと被らない内容にすること）】
{recent_list}
"""

    # プラットフォーム別の指示文
    if content_format == "markdown":
        user_prompt = f"""
今の状況: {seasonal}{day_mood_text}

投稿スタイル（参考）: 「{style}」
{topic_text}{recent_text}
ETERNALd.c.tの広報担当として、読者の役に立つnote記事を1本書いてください。
指定のJSON形式で返してください。
"""
    elif content_format == "video_script":
        user_prompt = f"""
今の状況: {seasonal}{day_mood_text}

参考スタイル: 「{style}」
{topic_text}
ETERNALd.c.tの広報担当として、TikTok用60秒スクリプトを作成してください。
指定のJSON形式で返してください。
"""
    elif content_format == "visual_caption":
        user_prompt = f"""
今の状況: {seasonal}{day_mood_text}

投稿スタイル: 「{style}」
{topic_text}{recent_text}
ETERNALd.c.tの広報担当として、Instagram投稿のキャプションを書いてください。
指定のJSON形式で返してください。
"""
    else:
        # X（デフォルト）
        user_prompt = f"""
今の状況: {seasonal}{day_mood_text}

投稿スタイル: 「{style}」

{topic_text}{recent_text}
上記のスタイルと今日の曜日・雰囲気を活かした自然なツイートを1つ書いてください。
直近の投稿と話題・表現が被らないよう、新鮮な内容にしてください。
投稿文だけを返してください（説明文・前置き不要）。
"""

    system_prompt = build_system_prompt(persona, constraints, platform)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()

    # JSON形式が期待されるプラットフォームはパースして返す
    if content_format in ("markdown", "video_script", "visual_caption"):
        parsed = _safe_parse_json(raw, content_format)
        if parsed:
            return parsed
        # パース完全失敗時のフォールバック
        print(f"[generate] JSONパース失敗。テキストから直接抽出します。")
        if content_format == "visual_caption":
            # キャプション本文だけ取り出して返す
            text = raw.replace("```json", "").replace("```", "").strip()
            return {"caption": text[:2200], "hashtags": ["#ETERNALdct", "#広報"]}
        return {"text": raw, "title": raw[:50], "body": raw, "tags": []}

    # X: テキスト後処理（ハッシュタグ調整・文字数チェック）
    post_text = raw
    max_tags = constraints.get("max_hashtags", persona.get("max_hashtags", 2))
    hashtags = select_hashtags(persona, topics[0].get("topic") if topics else None, day_ctx["hashtags"], max_tags)

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

    max_len = constraints.get("max_length", persona.get("max_length", 140))
    if len(post_text) > max_len:
        post_text = post_text[:max_len].rstrip()

    return post_text.strip()
