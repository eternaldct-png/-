"""
LINEスタンプ加工モジュール

ChatGPT などで手動生成したキャラクター画像（ポーズ・表情違いを16枚）を受け取り、
- 背景を透過
- 白いふちを付与
- セリフ（キャプション）を合成
- LINEスタンプの規定サイズ（最大370x320px）に収める
処理を行う。外部APIは使わず Pillow のみで完結する。
"""
import io
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

LINE_MAX_WIDTH = 370
LINE_MAX_HEIGHT = 320

BORDER_PX = 8
BG_TOLERANCE = 30
CAPTION_AREA_H = 70
CAPTION_FILL = (255, 70, 130, 255)
CAPTION_STROKE = (255, 255, 255, 255)


def _ensure_font(size: int) -> ImageFont.FreeTypeFont:
    """投稿画像生成と同じフォントディレクトリ（media/fonts）を共有して再利用する"""
    from media.image_generator import _ensure_fonts

    _, bold_path = _ensure_fonts()
    if bold_path and Path(bold_path).exists():
        return ImageFont.truetype(str(bold_path), size)
    return ImageFont.load_default()


def remove_background(img: Image.Image, tolerance: int = BG_TOLERANCE) -> Image.Image:
    """四隅の色を背景色とみなし、色距離がしきい値以下のピクセルを透過する"""
    rgb = img.convert("RGB")
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((rgb.width - 1, 0)),
               rgb.getpixel((0, rgb.height - 1)), rgb.getpixel((rgb.width - 1, rgb.height - 1))]
    bg_color = tuple(sum(c[i] for c in corners) // len(corners) for i in range(3))

    bg_layer = Image.new("RGB", rgb.size, bg_color)
    diff = ImageChops.difference(rgb, bg_layer).convert("L")
    mask = diff.point(lambda p: 255 if p > tolerance else 0)
    mask = mask.filter(ImageFilter.MedianFilter(3))

    out = img.convert("RGBA")
    out.putalpha(mask)
    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)
    return out


def add_white_outline(img: Image.Image, border_px: int = BORDER_PX) -> Image.Image:
    """透過画像の輪郭に沿って白いふちを付ける（アルファチャンネルの膨張差分）"""
    pad = border_px + 4
    padded = ImageOps.expand(img, border=pad, fill=(0, 0, 0, 0))
    alpha = padded.getchannel("A")

    kernel = border_px * 2 + 1
    dilated = alpha.filter(ImageFilter.MaxFilter(kernel))
    outline_only = ImageChops.subtract(dilated, alpha)

    white_layer = Image.new("RGBA", padded.size, (255, 255, 255, 255))
    white_layer.putalpha(outline_only)

    base = Image.new("RGBA", padded.size, (0, 0, 0, 0))
    base = Image.alpha_composite(base, white_layer)
    base = Image.alpha_composite(base, padded)
    return base


def draw_caption(img: Image.Image, text: str) -> Image.Image:
    """画像下に透過の余白を追加し、太字+白縁取りのセリフを合成する"""
    text = text.strip()
    if not text:
        return img

    canvas = Image.new("RGBA", (img.width, img.height + CAPTION_AREA_H), (0, 0, 0, 0))
    canvas.paste(img, (0, 0), img)
    draw = ImageDraw.Draw(canvas)

    size = 36
    font = _ensure_font(size)
    max_w = img.width - 16
    while size > 14:
        font = _ensure_font(size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
        if bbox[2] - bbox[0] <= max_w:
            break
        size -= 2

    cx = img.width // 2
    cy = img.height + CAPTION_AREA_H // 2
    draw.text(
        (cx, cy), text, font=font, fill=CAPTION_FILL,
        stroke_width=3, stroke_fill=CAPTION_STROKE, anchor="mm",
    )
    return canvas


def fit_to_line_size(img: Image.Image) -> Image.Image:
    """LINEスタンプの最大サイズ（370x320）を超える場合のみ縮小する"""
    if img.width <= LINE_MAX_WIDTH and img.height <= LINE_MAX_HEIGHT:
        return img
    ratio = min(LINE_MAX_WIDTH / img.width, LINE_MAX_HEIGHT / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    return img.resize(new_size, Image.LANCZOS)


def process_sticker(image_bytes: bytes, caption: str = "") -> bytes:
    """1枚分の元画像から、透過+白ふち+セリフ入りのスタンプPNGを生成する"""
    img = Image.open(io.BytesIO(image_bytes))
    img = remove_background(img)
    img = add_white_outline(img)
    img = draw_caption(img, caption)
    img = fit_to_line_size(img)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
