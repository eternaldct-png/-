"""
LINEスタンプ加工モジュール

ChatGPT などで手動生成したキャラクター画像（ポーズ・表情違いを16枚）を受け取り、
- 背景を透過（四隅から地続きの背景のみ除去）
- 白いふちを付与
- LINEスタンプの規定サイズ（最大370x320px）に収める
処理を行う。外部APIは使わず Pillow のみで完結する。
"""
import io

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

LINE_MAX_WIDTH = 370
LINE_MAX_HEIGHT = 320

BORDER_PX = 8
BG_TOLERANCE = 30


def remove_background(img: Image.Image, tolerance: int = BG_TOLERANCE) -> Image.Image:
    """四隅から塗り取り（flood fill）し、背景と地続きの領域だけを透過する。
    キャラクター内部の白目・歯など孤立した白い部分は地続きでないため透過されない。"""
    out = img.convert("RGBA")
    w, h = out.size
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for seed in seeds:
        if out.getpixel(seed)[3] != 0:
            ImageDraw.floodfill(out, seed, (0, 0, 0, 0), thresh=tolerance)

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


def fit_to_line_size(img: Image.Image) -> Image.Image:
    """LINEスタンプの最大サイズ（370x320）を超える場合のみ縮小する"""
    if img.width <= LINE_MAX_WIDTH and img.height <= LINE_MAX_HEIGHT:
        return img
    ratio = min(LINE_MAX_WIDTH / img.width, LINE_MAX_HEIGHT / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    return img.resize(new_size, Image.LANCZOS)


def process_sticker(image_bytes: bytes) -> bytes:
    """1枚分の元画像から、背景透過+白ふちのスタンプPNGを生成する"""
    img = Image.open(io.BytesIO(image_bytes))
    img = remove_background(img)
    img = add_white_outline(img)
    img = fit_to_line_size(img)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
