"""eternaldct.net の固定ページ「動画制作」用のアイキャッチ画像（1200×630・OGP兼用）を作る。

使い方:
    python3 fetch_fonts.py      # 初回のみ（fonts/ にフォントを用意）
    python3 make_eyecatch.py    # → docs/wordpress_motion/eyecatch.jpg

作例のポスター画像（src/static/motion/*.jpg）を3枚並べ、見出しを重ねる。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = Path(__file__).resolve().parent / "fonts"
POSTER_DIR = ROOT / "src/static/motion"
OUT = ROOT / "docs/wordpress_motion/eyecatch.jpg"

W, H = 1200, 630
BG = (13, 11, 20)
TEXT = (244, 242, 248)
MUTED = (184, 178, 200)
GRAD = [(124, 58, 237), (217, 70, 239), (236, 72, 153)]

# (ポスター, 幅, 中心x, 中心y, 回転角)
POSTERS = [
    ("stream-opening.jpg", 400, 905, 205, 4),
    ("liver-profile.jpg", 200, 1060, 400, -6),
    ("stream-alert.jpg", 190, 800, 445, 3),
]


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size)


def gradient(size):
    """左上→右下の3色グラデーション"""
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for x in range(w):
        for y in range(h):
            t = (x / max(w - 1, 1) + y / max(h - 1, 1)) / 2
            a, b, u = (GRAD[0], GRAD[1], t * 2) if t < 0.5 else (GRAD[1], GRAD[2], t * 2 - 1)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return img


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return mask


def background():
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse((-120, -160, 520, 420), fill=(88, 40, 170))
    d.ellipse((700, 300, 1320, 860), fill=(150, 40, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    return Image.blend(img, glow, 0.85)


def paste_poster(canvas, filename, width, cx, cy, angle):
    poster = Image.open(POSTER_DIR / filename).convert("RGB")
    height = round(poster.height * width / poster.width)
    poster = poster.resize((width, height), Image.LANCZOS)

    card = Image.new("RGBA", (width + 6, height + 6), (255, 255, 255, 0))
    border = Image.new("RGBA", card.size, (255, 255, 255, 70))
    card.paste(border, (0, 0), rounded_mask(card.size, 16))
    card.paste(poster, (3, 3), rounded_mask(poster.size, 13))

    pad = 40
    shadow = Image.new("RGBA", (card.width + pad * 2, card.height + pad * 2), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", card.size, (0, 0, 0, 150)), (pad, pad + 10), rounded_mask(card.size, 16))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    shadow.alpha_composite(card, (pad, pad))

    rotated = shadow.rotate(angle, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(rotated, (cx - rotated.width // 2, cy - rotated.height // 2))


def main():
    canvas = background().convert("RGBA")
    for p in POSTERS:
        paste_poster(canvas, *p)

    # 左側の文字が読みやすいように、左から右へ暗くフェードする帯を重ねる
    fade = Image.new("L", (W, H))
    fp = fade.load()
    for x in range(W):
        v = 235 if x < 560 else max(0, round(235 * (1 - (x - 560) / 160)))
        for y in range(H):
            fp[x, y] = v
    shade = Image.new("RGBA", (W, H), BG + (0,))
    shade.putalpha(fade.point(lambda v: round(v * 0.55)))
    canvas.alpha_composite(shade)

    d = ImageDraw.Draw(canvas)
    x = 72

    # バッジ「MOTION WORKS」
    badge_font = font("Montserrat-800.ttf", 20)
    label = "M O T I O N   W O R K S"
    bw = round(d.textlength(label, font=badge_font)) + 44
    badge = gradient((bw, 42))
    canvas.paste(badge, (x, 118), rounded_mask((bw, 42), 21))
    d.text((x + 22, 139), label, font=badge_font, fill="white", anchor="lm")

    title_font = font("NotoSansJP-900.ttf", 74)
    d.text((x - 4, 190), "こんな動画、", font=title_font, fill=TEXT)
    d.text((x - 4, 290), "つくれます。", font=title_font, fill=TEXT)

    sub_font = font("NotoSansJP-700.ttf", 25)
    d.text((x, 418), "配信・音楽・SNS広告・店舗や企業のPRまで。", font=sub_font, fill=MUTED)
    d.text((x, 458), "モーション動画の作例集", font=sub_font, fill=MUTED)

    d.text((x, 540), "ETERNALd.c.t", font=font("Montserrat-800.ttf", 26), fill=TEXT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"saved {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
