#!/usr/bin/env python3
"""
Grok で画像を作る（Codex / ChatGPT で作れないときの予備）

使い方:
  python tools/grok/image.py "夜の配信部屋でマイクに向かって歌う青髪の青年、アニメ調" --aspect 4:5
  python tools/grok/image.py "同じキャラがグッズのマグカップを持って笑っている" \\
      --ref tools/motion_render/chars/c1.webp -n 2
  python tools/grok/image.py "..." --pro -o src/static/goods/

保存先の既定: posts/grok_images/
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import grok_client  # noqa: E402

ASPECTS = ("1:1", "4:5", "3:4", "2:3", "9:16", "16:9", "4:3", "3:2")
PRO_MODEL = "grok-imagine-image-pro"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Grok で画像を生成する")
    parser.add_argument("prompt", help="どんな画像か（日本語OK）")
    parser.add_argument("--aspect", default="1:1", choices=ASPECTS, help="縦横比。既定: 1:1（Instagram縦長は 4:5）")
    parser.add_argument("-n", type=int, default=1, help="枚数（1〜4）。既定: 1")
    parser.add_argument("--ref", action="append", default=[], help="参考画像（キャラ・商品など）。複数指定可")
    parser.add_argument("--pro", action="store_true", help=f"高品質モデル（{PRO_MODEL}）を使う。単価は上がる")
    parser.add_argument("-o", "--output", default=str(ROOT / "posts" / "grok_images"), help="保存先フォルダ")
    args = parser.parse_args(argv)

    if not grok_client.is_configured():
        raise SystemExit("XAI_API_KEY が設定されていません（https://console.x.ai で発行）")
    refs = [Path(r) for r in args.ref]
    for r in refs:
        if not r.exists():
            raise SystemExit(f"参考画像が見つかりません: {r}")

    try:
        paths = grok_client.generate_images(
            args.prompt,
            Path(args.output),
            n=max(1, min(4, args.n)),
            aspect_ratio=args.aspect,
            model=PRO_MODEL if args.pro else None,
            references=refs or None,
        )
    except grok_client.GrokError as e:
        raise SystemExit(f"エラー: {e}")
    for p in paths:
        print(f"🖼 保存しました: {p}")


if __name__ == "__main__":
    main()
