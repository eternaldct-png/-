"""グッズ画像から「印刷範囲の枠線」を消して、動画用の素材を作る。

src/static/goods/ の商品画像はプリント範囲を示す細い枠線入りのモックアップなので、
長い直線の細線を検出して上下（左右）の画素で埋めてから media/promo/assets/ に保存する。
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/static/goods"
OUT = Path(__file__).resolve().parent / "assets"


def remove_thin_lines(a: np.ndarray, off: int = 4, thr: float = 18, min_run: int = 120) -> np.ndarray:
    a = a.astype(np.float32)
    g = a.mean(axis=2)
    out = a.copy()
    for axis in (0, 1):  # 0: 横線, 1: 縦線
        gg = g if axis == 0 else g.T
        aa = out if axis == 0 else out.transpose(1, 0, 2)
        h = gg.shape[0]
        up, dn = np.zeros_like(gg), np.zeros_like(gg)
        up[off:] = gg[:-off]
        dn[:-off] = gg[off:]
        mask = (np.abs(gg - up) > thr) & (np.abs(gg - dn) > thr) & (np.abs(up - dn) < thr)
        mask[:off] = mask[-off:] = False
        for y in range(off, h - off):
            row = mask[y]
            if row.sum() < min_run:
                continue
            # 長い連続区間だけを線とみなす
            idx = np.flatnonzero(row)
            runs = np.split(idx, np.flatnonzero(np.diff(idx) > 3) + 1)
            for r in runs:
                if len(r) >= min_run:
                    x0, x1 = r[0] - 2, r[-1] + 3
                    for yy in range(y - 1, y + 2):
                        aa[yy, x0:x1] = (aa[y - off, x0:x1] + aa[y + off, x0:x1]) / 2
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    jobs = {
        # 出力名: (元画像, クロップ範囲 left, top, right, bottom / None なら全体)
        "mug.png": ("chaco-mug.jpg", (335, 468, 675, 812)),
        "tshirt-charcoal.png": ("tshirt-charcoal-center.webp", None),
        "tshirt-white.png": ("tshirt-white-center.webp", None),
    }
    for name, (src, box) in jobs.items():
        im = Image.open(SRC / src).convert("RGB")
        a = remove_thin_lines(np.asarray(im))
        im = Image.fromarray(a)
        if box:
            im = im.crop(box)
        im.save(OUT / name)
        print("saved", OUT / name, im.size)


if __name__ == "__main__":
    main()
