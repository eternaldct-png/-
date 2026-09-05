"""生成AIなどで作った事業画像を、サイト用の規格（4:5・1200×1500・WebP）に整えて配置する。

使い方:
  python3 scripts/import_biz_images.py generated/biz-live.png generated/biz-ai.png generated/biz-music.png
  python3 scripts/import_biz_images.py --live foo.png --ai bar.jpg --music baz.png

ファイル名に live / ai / music が含まれていれば自動で対応先を判定する。
出力先: site/assets/img/biz-{live,ai,music}.webp（index.html はこの名前を参照しているので変更不要）
"""
import argparse, pathlib, re, sys
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'site' / 'assets' / 'img'
W, H = 1200, 1500
KEYS = ('live', 'ai', 'music')


def guess_key(path: pathlib.Path):
    name = path.stem.lower()
    for k in KEYS:
        if re.search(rf'(^|[^a-z]){k}([^a-z]|$)', name):
            return k
    return None


def convert(src: pathlib.Path, key: str):
    im = Image.open(src)
    im = ImageOps.exif_transpose(im).convert('RGB')
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.5))  # 4:5 に中央で切り抜き
    dst = OUT / f'biz-{key}.webp'
    im.save(dst, quality=88, method=6)
    print(f'{src} -> {dst} ({dst.stat().st_size // 1024} KB)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    for k in KEYS:
        ap.add_argument(f'--{k}')
    a = ap.parse_args()
    jobs = {k: pathlib.Path(v) for k in KEYS if (v := getattr(a, k))}
    for f in a.files:
        p = pathlib.Path(f)
        k = guess_key(p)
        if not k:
            sys.exit(f'{p}: ファイル名から live/ai/music を判定できません。--live などで指定してください')
        jobs[k] = p
    if not jobs:
        ap.print_help(); sys.exit(1)
    for k, p in jobs.items():
        if not p.exists():
            sys.exit(f'{p}: ファイルが見つかりません')
        convert(p, k)


if __name__ == '__main__':
    main()
