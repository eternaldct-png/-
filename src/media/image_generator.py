"""
Instagram 用ブランデッド画像生成モジュール
Pillow を使って 1080x1080px のテキストカード画像を生成する

ETERNALd.c.t ブランドカラー:
  背景: ディープネイビー (#0F1428)
  テキスト: ウォームクリーム (#F5F0E4)
  アクセント: ゴールド (#D4AF37)
"""
import os
import textwrap
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

FONT_DIR = Path("media/fonts")
OUTPUT_DIR = Path("posts/media")

# Noto Sans JP フォント URL（Google Fonts）
FONT_URL_REGULAR = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
FONT_URL_BOLD = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf"

# ブランドカラー
COLORS = {
    "background": (15, 20, 40),       # ディープネイビー
    "card_bg": (25, 32, 55),          # カードネイビー
    "text_primary": (245, 240, 228),  # ウォームクリーム
    "text_secondary": (180, 170, 150),
    "accent": (212, 175, 55),         # ゴールド
    "hashtag": (140, 180, 220),       # ライトブルー
}

CANVAS_SIZE = (1080, 1080)


def _ensure_fonts() -> tuple[Path, Path]:
    """フォントファイルを確保する（なければダウンロード）"""
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
    """
    Instagram 用ブランデッドテキストカード画像を生成する

    Args:
        caption_text: 投稿キャプション本文（画像中央に表示）
        hashtags: ハッシュタグリスト（画像下部に表示）
        persona_name: ペルソナ名（カード右下に表示）
        brand_name: ブランド名（カード上部に表示）
        output_path: 保存先パス（省略時は自動生成）

    Returns:
        保存した画像ファイルのパス
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
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

    font_brand = load_font(font_bold_path, 32)
    font_main = load_font(font_regular_path, 42)
    font_name = load_font(font_regular_path, 28)
    font_hashtag = load_font(font_regular_path, 22)

    img = Image.new("RGB", CANVAS_SIZE, COLORS["background"])
    draw = ImageDraw.Draw(img)

    # 背景のサブタイルパターン（薄いグリッド）
    for x in range(0, CANVAS_SIZE[0], 60):
        draw.line([(x, 0), (x, CANVAS_SIZE[1])], fill=(255, 255, 255, 8), width=1)
    for y in range(0, CANVAS_SIZE[1], 60):
        draw.line([(0, y), (CANVAS_SIZE[0], y)], fill=(255, 255, 255, 8), width=1)

    # カード枠
    card_margin = 80
    card_x1, card_y1 = card_margin, card_margin
    card_x2, card_y2 = CANVAS_SIZE[0] - card_margin, CANVAS_SIZE[1] - card_margin
    draw.rounded_rectangle(
        [card_x1, card_y1, card_x2, card_y2],
        radius=20,
        fill=COLORS["card_bg"],
    )

    # ゴールドのトップボーダーライン
    draw.rectangle(
        [card_x1, card_y1, card_x2, card_y1 + 4],
        fill=COLORS["accent"],
    )

    # ブランド名（カード上部中央）
    brand_y = card_y1 + 30
    draw.text(
        (CANVAS_SIZE[0] // 2, brand_y),
        brand_name,
        font=font_brand,
        fill=COLORS["accent"],
        anchor="mm",
    )

    # セパレーターライン
    sep_y = brand_y + 40
    draw.line(
        [(card_x1 + 40, sep_y), (card_x2 - 40, sep_y)],
        fill=COLORS["text_secondary"],
        width=1,
    )

    # メインテキスト（カード中央）
    card_width = card_x2 - card_x1 - 80
    # 1行あたりの文字数（フォントサイズ42px ≈ 20文字/行）
    chars_per_line = max(8, card_width // 43)
    wrapped_lines = []
    for paragraph in caption_text.split("\n"):
        wrapped_lines.extend(textwrap.wrap(paragraph, width=chars_per_line) or [""])

    # 最大8行まで表示
    display_lines = wrapped_lines[:8]
    line_height = 56
    total_text_height = len(display_lines) * line_height

    text_start_y = (card_y1 + card_y2) // 2 - total_text_height // 2

    for i, line in enumerate(display_lines):
        y = text_start_y + i * line_height
        draw.text(
            (CANVAS_SIZE[0] // 2, y),
            line,
            font=font_main,
            fill=COLORS["text_primary"],
            anchor="mm",
        )

    # ペルソナ名（カード右下）
    name_y = card_y2 - 40
    draw.text(
        (card_x2 - 40, name_y),
        f"— {persona_name}",
        font=font_name,
        fill=COLORS["text_secondary"],
        anchor="rm",
    )

    # ハッシュタグ帯（カード外下部）
    if hashtags:
        hashtag_text = "  ".join(hashtags[:8])
        hashtag_y = card_y2 + 20
        draw.text(
            (CANVAS_SIZE[0] // 2, hashtag_y),
            hashtag_text,
            font=font_hashtag,
            fill=COLORS["hashtag"],
            anchor="mm",
        )

    img.save(str(output_path), "PNG", optimize=True)
    print(f"[image] 画像を生成しました: {output_path}")
    return output_path


if __name__ == "__main__":
    # テスト実行
    test_caption = "AIを使った広報活動、実はこんなに日常的になってきてます。\nプレスリリースの草案はもちろん、SNS投稿のアイデア出しも。\nまだ違和感あるけど、確実に仕事が変わってきてる感じ。"
    test_hashtags = ["#広報", "#ETERNALdct", "#AI活用", "#PR", "#マーケティング"]
    path = generate_instagram_image(test_caption, test_hashtags)
    print(f"生成完了: {path}")
