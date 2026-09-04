"""事業ビジュアル3枚を生成する（Luminous Notation）。 python3 site/assets/art/make_art.py"""
import math, random, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / 'site' / 'assets' / 'img'
FONTS = pathlib.Path('/root/.claude/skills/synced/4c2b9332-9a55-4edb-8e07-db9531131cc1_2ee5d1b5-8835-4bee-a270-317af0634841/canvas-design/canvas-fonts')
S = 2                      # スーパーサンプリング倍率
W, H = 1200 * S, 1500 * S
MAG = (217, 79, 230); CYA = (47, 214, 216); WHT = (255, 255, 255)

def canvas():
    return np.zeros((H, W, 3), dtype=np.float32)

def add_glow(buf, x, y, r, color, power=1.0, falloff=2.2):
    """加算合成の柔らかい光"""
    x0, x1 = max(0, int(x - r)), min(W, int(x + r) + 1)
    y0, y1 = max(0, int(y - r)), min(H, int(y + r) + 1)
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** falloff * power
    for c in range(3): buf[y0:y1, x0:x1, c] += a * color[c]

def add_dot(buf, x, y, r, color, power=1.0):
    add_glow(buf, x, y, r, color, power, falloff=1.2)

def to_image(buf, grain=6):
    img = np.clip(buf, 0, 255)
    rng = np.random.default_rng(7)
    img = img + rng.normal(0, grain, img.shape)          # 紙の粒子
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return im.resize((W // S, H // S), Image.LANCZOS)

def label(im, left, right, sub):
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(str(FONTS / 'Jura-Light.ttf'), 22)
    f2 = ImageFont.truetype(str(FONTS / 'GeistMono-Regular.ttf'), 13)
    w, h = im.size
    m = 56
    # 目盛り
    for i in range(0, 25):
        x = m + i * (w - 2 * m) / 24
        d.line([(x, h - m - 30), (x, h - m - 30 - (10 if i % 6 == 0 else 5))], fill=(120, 120, 120), width=1)
    d.line([(m, h - m - 30), (w - m, h - m - 30)], fill=(90, 90, 90), width=1)
    d.text((m, h - m - 4), left, font=f1, fill=(235, 235, 235), anchor='ls')
    d.text((w - m, h - m - 4), right, font=f2, fill=(150, 150, 150), anchor='rs')
    d.text((m, m + 16), sub, font=f2, fill=(120, 120, 120), anchor='ls')
    return im

# ── 01 LIVE: 光の観客席 ────────────────────────────────
def live():
    rng = random.Random(3)
    buf = canvas()
    cx, cy = W * 0.5, H * 0.40
    # 上からの光の帯
    for i, (col, ang) in enumerate([(WHT, -0.22), (MAG, 0.08), (CYA, 0.30)]):
        for t in np.linspace(0, 1, 140):
            x = cx + (ang * 1.6 + (t - 0.2) * ang * 2) * W * 0.5
            y = -H * 0.05 + t * H * 0.75
            add_glow(buf, x + ang * t * W * 0.35, y, 110 * S * (0.4 + t), col, power=0.028 * (1 - t) + 0.004, falloff=1.6)
    # 同心円の光の点（50人の声）
    n_ring = 9
    for k in range(n_ring):
        r = (0.11 + k * 0.041) * W
        n = int(16 + k * 8)
        for j in range(n):
            a = -math.pi * (0.5 + 0.5 * (j + 0.5) / n) - math.pi * 0.0  # 下半円
            a = math.pi * (j + 0.5) / n
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r * 0.62 + k * 7 * S
            size = (2.6 + rng.random() * 1.2) * S
            p = 0.55 + 0.45 * rng.random()
            add_dot(buf, x, y, size * 2.2, (230, 230, 230), power=p * 0.9)
    # 主役の発光体 数個（規則の破れ）
    stars = [(cx - W * 0.17, cy + H * 0.05, MAG, 1.0), (cx + W * 0.12, cy - H * 0.03, CYA, 0.9), (cx + W * 0.24, cy + H * 0.12, WHT, 0.8), (cx - W * 0.05, cy + H * 0.16, WHT, 0.55)]
    for x, y, col, p in stars:
        add_glow(buf, x, y, 120 * S, col, power=0.45 * p, falloff=3.0)
        add_dot(buf, x, y, 9 * S, WHT, power=1.0 * p)
        add_dot(buf, x, y, 4 * S, WHT, power=1.0)
    # 床の反射
    for t in np.linspace(0, 1, 60):
        add_glow(buf, cx, cy + H * 0.36 + t * H * 0.05, W * 0.5, (40, 40, 44), power=0.012, falloff=1.2)
    im = to_image(buf)
    return label(im, 'LIVE  —  fifty voices', 'FIG. 01   LIGHT FIELD   n = 50', 'ETERNAL d.c.t   /   01   LIVER AGENCY')

# ── 02 AI: 信号の格子 ─────────────────────────────────
def ai():
    rng = random.Random(11)
    buf = canvas()
    cols, rows = 21, 25
    x0, y0 = W * 0.12, H * 0.10
    gx, gy = W * 0.76 / (cols - 1), H * 0.56 / (rows - 1)
    pts = {}
    for i in range(cols):
        for j in range(rows):
            x, y = x0 + i * gx, y0 + j * gy
            pts[(i, j)] = (x, y)
            add_dot(buf, x, y, 2.4 * S, (170, 170, 176), power=0.85)
    # 走査線（横）
    for j in range(rows):
        if j % 4 == 1:
            y = y0 + j * gy
            for x in np.linspace(x0, x0 + (cols - 1) * gx, 400):
                add_dot(buf, x, y, 1.6 * S, (60, 60, 66), power=0.5)
    # 経路: 左から右へ流れる信号線（数本）
    paths = []
    for p in range(6):
        j = rng.randrange(3, rows - 3); path = [(0, j)]
        for i in range(1, cols):
            j = max(1, min(rows - 2, j + rng.choice([-1, 0, 0, 1])))
            path.append((i, j))
        paths.append(path)
    for pi, path in enumerate(paths):
        col = CYA if pi in (1, 4) else (MAG if pi == 3 else (210, 210, 215))
        for (a, b) in zip(path, path[1:]):
            (xa, ya), (xb, yb) = pts[a], pts[b]
            for t in np.linspace(0, 1, 40):
                add_dot(buf, xa + (xb - xa) * t, ya + (yb - ya) * t, 1.7 * S, col, power=0.75)
        for node in path[::5]:
            x, y = pts[node]
            add_glow(buf, x, y, 26 * S, col, power=0.35, falloff=2.5)
            add_dot(buf, x, y, 4 * S, WHT, power=0.9)
    # 中心の核（規則の破れ）
    cx, cy = pts[(cols // 2, rows // 2)]
    add_glow(buf, cx, cy, 190 * S, CYA, power=0.35, falloff=3.2)
    add_glow(buf, cx, cy, 40 * S, WHT, power=0.8, falloff=2.0)
    add_dot(buf, cx, cy, 6 * S, WHT, power=1.0)
    im = to_image(buf)
    return label(im, 'AI  —  signal lattice', 'FIG. 02   21 × 25   6 ROUTES', 'ETERNAL d.c.t   /   02   AI SOLUTIONS')

# ── 03 MUSIC: 波形の地層 ──────────────────────────────
def music():
    rng = np.random.default_rng(5)
    buf = canvas()
    lines = 44
    x0, x1 = W * 0.10, W * 0.90
    ytop, ybot = H * 0.14, H * 0.70
    xs = np.linspace(x0, x1, 1500)
    u = (xs - x0) / (x1 - x0)
    env_x = np.exp(-((u - 0.5) / 0.22) ** 2)
    for k in range(lines):
        v = k / (lines - 1)
        base = ytop + v * (ybot - ytop)
        env_y = math.exp(-((v - 0.48) / 0.28) ** 2)
        ph = rng.uniform(0, 6.28, 4)
        wave = (np.sin(u * 40 + ph[0]) * 0.55 + np.sin(u * 97 + ph[1]) * 0.25 + np.sin(u * 13 + ph[2]) * 0.35)
        wave = wave + np.convolve(rng.normal(0, 0.25, xs.size), np.ones(25) / 25, mode='same')  # 滑らかな揺らぎ
        amp = 50 * S * env_y
        ys = base - (np.abs(wave) * 0.7 + wave * 0.3) * env_x * amp
        if k == 17: col, p = MAG, 1.0
        elif k == 29: col, p = CYA, 1.0
        else:
            g = int(150 + 90 * env_y); col, p = (g, g, g + 4), 0.55 + 0.45 * env_y
        for x, y in zip(xs, ys):
            add_dot(buf, x, y, 1.3 * S, col, power=p * 0.8)
        if k in (17, 29):
            for x, y in zip(xs[::6], ys[::6]):
                add_glow(buf, x, y, 14 * S, col, power=0.09 * env_x[0] + 0.05, falloff=2.0)
    # 中央の発光（響きの核）
    add_glow(buf, (x0 + x1) / 2, (ytop + ybot) / 2, 320 * S, (255, 255, 255), power=0.08, falloff=2.6)
    im = to_image(buf)
    return label(im, 'MUSIC  —  waveform strata', 'FIG. 03   44 LAYERS   ∑ = one song', 'ETERNAL d.c.t   /   03   MUSIC PRODUCTION')

if __name__ == '__main__':
    for name, fn in [('biz-live', live), ('biz-ai', ai), ('biz-music', music)]:
        im = fn()
        im.save(OUT / f'{name}.webp', quality=86, method=6)
        im.save(OUT / f'{name}.png')
        print(name, im.size)
