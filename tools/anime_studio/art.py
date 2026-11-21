"""絵の段階: カットの絵を用意する（仮の絵の合成・アップロード画像の確認・fal.ai での生成）と字幕の画像。

- 仮の絵（無料・既定）: 場面の画像（無ければ場面の色のグラデーション）の上に、キャラの画像
  （無ければ色の人形と名前）を並べて合成する。キャラと場面に自分の画像を入れておけば、そのまま「本番の絵」になる。
- fal.ai（任意・従量）: FAL_KEY があり、設定で選んだときだけ。1枚ごとに見積もりを記録し、月の上限を超える前に止める。
"""
from __future__ import annotations

import io
import json
import os
import random
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_AUDIO_BYTES = 100 * 1024 * 1024

FONT_CANDIDATES = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/unifont/unifont_jp.otf",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
]


class ArtError(RuntimeError):
    pass


def frame_size(aspect: str, short_side: int = 1080) -> tuple[int, int]:
    long_side = short_side * 16 // 9
    long_side -= long_side % 2
    return {"16:9": (long_side, short_side), "1:1": (short_side, short_side)}.get(aspect, (short_side, long_side))


def font_path() -> str | None:
    env = os.environ.get("KOMADORI_FONT")
    for p in ([env] if env else []) + FONT_CANDIDATES:
        if p and Path(p).exists():
            return p
    return None


def font(size: int):
    p = font_path()
    if p:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def _hex(c: str, default=(200, 180, 160)) -> tuple[int, int, int]:
    c = (c or "").lstrip("#")
    if len(c) == 6:
        try:
            return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            pass
    return default


def _mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


# ── アップロードの確認 ─────────────────────────────────────────

def check_image(data: bytes, filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in IMAGE_EXT:
        raise ArtError("画像は PNG / JPG / WebP にしてください。")
    if len(data) > MAX_IMAGE_BYTES:
        raise ArtError("画像が大きすぎます（20MBまで）。")
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
    except Exception as e:
        raise ArtError("画像として読めませんでした。") from e
    return ".jpg" if ext == ".jpeg" else ext


def check_audio(data: bytes, filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in AUDIO_EXT:
        raise ArtError("音は MP3 / M4A / WAV / AAC / OGG / FLAC にしてください。")
    if len(data) > MAX_AUDIO_BYTES:
        raise ArtError("音のファイルが大きすぎます（100MBまで）。")
    if len(data) < 128:
        raise ArtError("音のファイルが空です。")
    return ext


# ── 仮の絵（合成） ───────────────────────────────────────────

def _cover(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    scale = max(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def _background(size, scene: dict | None, seed: int) -> Image.Image:
    w, h = size
    if scene and scene.get("image_abs") and Path(scene["image_abs"]).exists():
        with Image.open(scene["image_abs"]) as im:
            return _cover(im.convert("RGB"), size)
    base = _hex((scene or {}).get("color", ""), (120, 160, 200))
    top, bottom = _mix(base, (255, 255, 255), 0.55), _mix(base, (20, 20, 40), 0.35)
    bg = Image.new("RGB", size)
    d = ImageDraw.Draw(bg)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_mix(top, bottom, y / h))
    rnd = random.Random(seed)
    # 遠くの丘と光（毎回少しずつ違う形）
    for k in range(3):
        cy = int(h * (0.62 + 0.08 * k))
        col = _mix(base, (30, 40, 60), 0.25 + 0.15 * k)
        pts = [(0, h)]
        for x in range(0, w + 1, max(1, w // 8)):
            pts.append((x, cy + rnd.randint(-h // 25, h // 25)))
        pts.append((w, h))
        d.polygon(pts, fill=col)
    r = int(min(w, h) * 0.09)
    sx, sy = rnd.randint(r, w - r), rnd.randint(r, int(h * 0.35))
    glow = Image.new("RGBA", size, (255, 250, 230, 0))
    ImageDraw.Draw(glow).ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 250, 230, 200))
    out = bg.convert("RGBA")
    out.alpha_composite(glow.filter(ImageFilter.GaussianBlur(max(1, r // 3))))
    return out.convert("RGB")


def _figure(char: dict, height: int) -> Image.Image:
    """キャラの画像が無いときの、色の人形（頭と体と名前）。"""
    w = int(height * 0.55)
    im = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = _hex(char.get("color", ""), (224, 122, 95))
    head = int(w * 0.62)
    hx = (w - head) // 2
    d.rounded_rectangle([int(w * 0.08), int(head * 0.9), int(w * 0.92), height - 2], radius=int(w * 0.3),
                        fill=col + (255,), outline=(40, 30, 30, 255), width=max(2, height // 120))
    d.ellipse([hx, 2, hx + head, head], fill=(255, 236, 220, 255), outline=(40, 30, 30, 255), width=max(2, height // 120))
    lw = max(2, height // 120)  # 目と口（にっこり）
    ey, ex = int(head * 0.5), int(head * 0.17)
    for cx in (w // 2 - ex, w // 2 + ex):
        d.ellipse([cx - lw * 2, ey - lw * 3, cx + lw * 2, ey + lw * 3], fill=(40, 30, 30, 255))
    d.arc([w // 2 - ex // 2, int(head * 0.6), w // 2 + ex // 2, int(head * 0.78)], 20, 160, fill=(40, 30, 30, 255), width=lw)
    name = char.get("name", "")[:6]
    f = font(max(14, height // 10))
    tw = d.textlength(name, font=f)
    d.text(((w - tw) / 2, int(height * 0.62)), name, font=f, fill=(255, 255, 255, 255),
           stroke_width=max(1, height // 160), stroke_fill=(40, 30, 30, 255))
    return im


def _character_layer(char: dict, height: int) -> Image.Image:
    p = char.get("image_abs")
    if p and Path(p).exists():
        with Image.open(p) as im:
            im = im.convert("RGBA")
            scale = height / im.height
            return im.resize((max(1, int(im.width * scale)), height), Image.LANCZOS)
    return _figure(char, height)


def compose_shot(size, scene: dict | None, chars: list[dict], *, seed: int = 0, note: str = "") -> Image.Image:
    """場面の背景の上にキャラを並べた1枚を作る。"""
    w, h = size
    canvas = _background(size, scene, seed).convert("RGBA")
    if chars:
        ch = int(h * (0.55 if h > w else 0.62))
        layers = [_character_layer(c, ch) for c in chars[:4]]
        total = sum(l.width for l in layers)
        gap = max(0, (w - total) // (len(layers) + 1))
        if total > w * 0.95:  # 横に入りきらないときは縮める
            k = w * 0.95 / total
            layers = [l.resize((max(1, int(l.width * k)), max(1, int(l.height * k))), Image.LANCZOS) for l in layers]
            gap = int(w * 0.05 / (len(layers) + 1))
        x = gap
        for l in layers:
            canvas.alpha_composite(l, (int(x), h - l.height - int(h * 0.04)))
            x += l.width + gap
    if note:
        d = ImageDraw.Draw(canvas)
        f = font(max(16, min(w, h) // 36))
        d.rounded_rectangle([16, 16, 16 + int(d.textlength(note, font=f)) + 24, 16 + f.size + 18], radius=10, fill=(0, 0, 0, 110))
        d.text((28, 24), note, font=f, fill=(255, 255, 255, 235))
    return canvas.convert("RGB")


# ── 字幕（透過 PNG） ─────────────────────────────────────────

def _wrap(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if d.textlength(cur + ch, font=f) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines[:4]


def subtitle_png(size, text: str, *, speaker: str = "", caption: str = "") -> Image.Image:
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    unit = min(w, h)
    if caption:
        f = font(unit // 14)
        lines = _wrap(d, caption, f, int(w * 0.86))
        y = int(h * 0.08)
        for ln in lines:
            tw = d.textlength(ln, font=f)
            d.text(((w - tw) / 2, y), ln, font=f, fill=(255, 255, 255, 255), stroke_width=unit // 120 + 2, stroke_fill=(30, 20, 20, 255))
            y += int(f.size * 1.25)
    if text:
        f = font(unit // 20)
        lines = _wrap(d, text, f, int(w * 0.84))
        lh = int(f.size * 1.35)
        box_h = lh * len(lines) + int(f.size * 0.9)
        top = h - box_h - int(h * 0.06)
        d.rounded_rectangle([int(w * 0.05), top, int(w * 0.95), top + box_h], radius=unit // 40, fill=(15, 12, 20, 170))
        if speaker:
            sf = font(unit // 26)
            d.text((int(w * 0.07), top - int(sf.size * 1.3)), speaker, font=sf, fill=(255, 255, 255, 255),
                   stroke_width=3, stroke_fill=(30, 20, 20, 255))
        y = top + int(f.size * 0.45)
        for ln in lines:
            tw = d.textlength(ln, font=f)
            d.text(((w - tw) / 2, y), ln, font=f, fill=(255, 255, 255, 255))
            y += lh
    return im


# ── fal.ai（任意・従量） ─────────────────────────────────────

FAL_QUEUE = "https://queue.fal.run"


def fal_key() -> str:
    return os.environ.get("FAL_KEY", "").strip()


def _fal_request(url: str, payload: dict | None, timeout: float = 60) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET",
                                 headers={"Authorization": f"Key {fal_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise ArtError(f"fal.ai がエラーを返しました: {e.code} {e.read().decode('utf-8', 'replace')[:300]}") from e
    except (urllib.error.URLError, OSError) as e:
        raise ArtError(f"fal.ai につながりません: {e}") from e


def fal_run(model: str, payload: dict, timeout: float = 600, poll: float = 3.0) -> dict:
    if not fal_key():
        raise ArtError("FAL_KEY が設定されていません（~/Komadori/.env に書いて起動し直してください）。")
    sub = _fal_request(f"{FAL_QUEUE}/{model}", payload)
    status_url, response_url = sub.get("status_url"), sub.get("response_url")
    if not status_url or not response_url:
        raise ArtError("fal.ai の返事が想定と違いました。")
    end = time.time() + timeout
    while time.time() < end:
        st = _fal_request(status_url, None)
        if st.get("status") == "COMPLETED":
            return _fal_request(response_url, None)
        if st.get("status") in ("FAILED", "ERROR"):
            raise ArtError(f"fal.ai で失敗しました: {st}")
        time.sleep(poll)
    raise ArtError("fal.ai の生成が時間内に終わりませんでした。")


def download(url: str, dest: Path, max_bytes: int = 200 * 1024 * 1024) -> Path:
    if not url.startswith("https://"):
        raise ArtError("https:// 以外のURLはダウンロードしません。")
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ArtError("ダウンロードしたファイルが大きすぎます。")
    dest.write_bytes(data)
    return dest


def fal_image(model: str, prompt: str, size: tuple[int, int], dest: Path) -> Path:
    out = fal_run(model, {"prompt": prompt, "image_size": {"width": size[0], "height": size[1]}, "num_images": 1})
    imgs = out.get("images") or []
    if not imgs or not imgs[0].get("url"):
        raise ArtError("fal.ai から画像が返ってきませんでした。")
    return download(imgs[0]["url"], dest)


def fal_video(model: str, prompt: str, image_url: str, seconds: float, dest: Path) -> Path:
    out = fal_run(model, {"prompt": prompt, "image_url": image_url, "duration": "10" if seconds > 5 else "5"}, timeout=900)
    url = (out.get("video") or {}).get("url")
    if not url:
        raise ArtError("fal.ai から動画が返ってきませんでした。")
    return download(url, dest)


def data_uri(path: Path) -> str:
    import base64
    mime = {".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower(), "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
