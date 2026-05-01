"""
Instagram 用ブランデッド画像生成モジュール
Pillow を使って 1080x1080px のテキストカード画像を生成する

デザイン:
  背景: ポップグラデーション（ピンク → パープル → コーラル）
  カード: 白・半透明
  テキスト: ダーク（#1A1A2E）
  アクセント: ビビッドピンク (#FF4D8D)
"""
import re
import textwrap
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def _wrap_japanese(text: str, max_chars: int) -> list[str]:
    """日本語禁則処理付きテキスト折り返し"""
    no_start = set('。、！？）』」】…')
    lines = []
    while len(text) > max_chars:
        pos = max_chars
        # 行頭禁則文字は前の行に引き取る
        while pos > 1 and text[pos] in no_start:
            pos -= 1
        lines.append(text[:pos])
        text = text[pos:]
    if text:
        lines.append(text)
    return lines


def _normalize_text(text: str) -> str:
    """リテラル \\n を改行に変換し、絵文字を除去する"""
    text = text.replace('\\n', '\n')
    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\U00002600-\U000027BF"
        "\U00002B00-\U00002BFF"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub('', text).strip()


def _draw_gradient(draw, width: int, height: int, colors: list[tuple]) -> None:
    """垂直グラデーションを水平ラインで描画"""
    n = len(colors) - 1
    for y in range(height):
        seg = min(int(y / height * n), n - 1)
        t = (y / height * n) - seg
        c1, c2 = colors[seg], colors[seg + 1]
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


JST = ZoneInfo("Asia/Tokyo")

FONT_DIR = Path("media/fonts")
OUTPUT_DIR = Path("posts/media")

FONT_URL_REGULAR = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
FONT_URL_BOLD = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf"

# POPグラデーション（淡めのピンク → パープル → コーラル）
GRADIENT_COLORS = [
    (255, 140, 180),   # 淡いピンク
    (200, 145, 255),   # 淡いパープル
    (255, 165, 140),   # 淡いコーラル
]

COLORS = {
    "card_bg":        (255, 255, 255),   # 白カード
    "text_primary":   (26, 26, 46),      # ダークネイビー
    "text_secondary": (120, 100, 140),   # パープルグレー
    "accent":         (255, 77, 141),    # ホットピンク
    "brand":          (168, 85, 247),    # パープル
}

CANVAS_SIZE = (1080, 1080)


def _ensure_fonts() -> tuple[Path, Path]:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    regular = FONT_DIR / "NotoSansCJKjp-Regular.otf"
    bold = FONT_DIR / "NotoSansCJKjp-Bold.otf"

    if not regular.exists():
        print(f"[image] フォントをダウンロード中: {regular.name}")
        try:
            urllib.request.urlretrieve(FONT_URL_REGULAR, regular)
        except Exception as e:
            print(f"[image] フォントDL失敗（フォールバック使用）: {e}")
            return None, None

    if not bold.exists():
        print(f"[image] フォントをダウンロード中: {bold.name}")
        try:
            urllib.request.urlretrieve(FONT_URL_BOLD, bold)
        except Exception as e:
            print(f"[image] フォントDL失敗（フォールバック使用）: {e}")
            return regular, None

    return regular, bold


def generate_instagram_image(
    caption_text: str,
    hashtags: list[str] = None,
    persona_name: str = "木村來未",
    brand_name: str = "ETERNALd.c.t",
    output_path: Path = None,
) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
    except ImportError:
        raise ImportError("Pillow が必要です: pip install pillow")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"{ts}_instagram.png"

    font_regular_path, font_bold_path = _ensure_fonts()

    def load_font(path, size):
        if path and path.exists():
            return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()

    caption_text = _normalize_text(caption_text)

    font_brand = load_font(font_bold_path, 34)
    font_main  = load_font(font_regular_path, 34)
    font_name  = load_font(font_regular_path, 26)

    # ── 背景グラデーション ──────────────────────────────
    img = Image.new("RGB", CANVAS_SIZE)
    draw = ImageDraw.Draw(img)
    _draw_gradient(draw, CANVAS_SIZE[0], CANVAS_SIZE[1], GRADIENT_COLORS)

    # ── 白カード（角丸・ドロップシャドウ風） ───────────
    card_margin = 70
    card_x1, card_y1 = card_margin, card_margin
    card_x2, card_y2 = CANVAS_SIZE[0] - card_margin, CANVAS_SIZE[1] - card_margin

    # シャドウ（暗い半透明矩形をずらして描画）
    shadow_offset = 8
    shadow_color = (100, 50, 150)
    draw.rounded_rectangle(
        [card_x1 + shadow_offset, card_y1 + shadow_offset,
         card_x2 + shadow_offset, card_y2 + shadow_offset],
        radius=24, fill=shadow_color,
    )

    # 白カード本体
    draw.rounded_rectangle(
        [card_x1, card_y1, card_x2, card_y2],
        radius=24, fill=COLORS["card_bg"],
    )

    # アクセントライン（カード上部・グラデーション風に2色）
    draw.rounded_rectangle(
        [card_x1, card_y1, card_x2, card_y1 + 6],
        radius=4, fill=COLORS["accent"],
    )

    # ── ブランド名 ──────────────────────────────────────
    brand_y = card_y1 + 38
    draw.text(
        (CANVAS_SIZE[0] // 2, brand_y),
        brand_name,
        font=font_brand,
        fill=COLORS["brand"],
        anchor="mm",
    )

    # セパレーター
    sep_y = brand_y + 44
    draw.line(
        [(card_x1 + 50, sep_y), (card_x2 - 50, sep_y)],
        fill=(220, 200, 240), width=1,
    )

    # ── メインテキスト（左揃え） ────────────────────────
    text_padding = 40
    text_x = card_x1 + text_padding
    card_text_width = card_x2 - card_x1 - text_padding * 2
    chars_per_line = max(8, card_text_width // 34)

    paragraphs = caption_text.split("\n")
    wrapped_lines = []
    for para in paragraphs:
        para = para.strip()
        if para:
            wrapped_lines.extend(_wrap_japanese(para, chars_per_line) or [para])
        else:
            if wrapped_lines and wrapped_lines[-1] != "":
                wrapped_lines.append("")

    while wrapped_lines and wrapped_lines[-1] == "":
        wrapped_lines.pop()

    max_lines = 10
    if len(wrapped_lines) > max_lines:
        display_lines = wrapped_lines[:max_lines - 1]
        display_lines.append("…")
    else:
        display_lines = wrapped_lines

    name_y = card_y2 - 44
    line_height = 54
    total_text_height = len(display_lines) * line_height
    text_area_top = sep_y + 40
    text_area_bottom = name_y - 20
    text_area_center = (text_area_top + text_area_bottom) // 2
    text_start_y = max(text_area_top, text_area_center - total_text_height // 2)

    for i, line in enumerate(display_lines):
        y = text_start_y + i * line_height
        if y + line_height > text_area_bottom:
            break
        color = (200, 180, 220) if line == "" else COLORS["text_primary"]
        draw.text(
            (text_x, y),
            line,
            font=font_main,
            fill=color,
            anchor="lm",
        )

    # ── ペルソナ名 ──────────────────────────────────────
    draw.text(
        (card_x2 - 44, name_y),
        f"— {persona_name}",
        font=font_name,
        fill=COLORS["accent"],
        anchor="rm",
    )

    img.save(str(output_path), "PNG", optimize=True)
    print(f"[image] 画像を生成しました: {output_path}")
    return output_path


if __name__ == "__main__":
    test_caption = "AIを使った広報活動、実はこんなに日常的になってきてます。\nプレスリリースの草案はもちろん、SNS投稿のアイデア出しも。\nまだ違和感あるけど、確実に仕事が変わってきてる感じ。"
    test_hashtags = ["#広報", "#ETERNALdct", "#AI活用", "#PR", "#マーケティング"]
    path = generate_instagram_image(test_caption, test_hashtags)
    print(f"生成完了: {path}")
