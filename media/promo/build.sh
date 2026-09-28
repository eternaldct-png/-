#!/usr/bin/env bash
# ETERNAL d.c.t プロモ映像（60秒）を一括生成する。
#   bash media/promo/build.sh            → media/promo/out/eternaldct_promo_60s.mp4
#   bash media/promo/build.sh --stills 5,20,56   → 指定秒の静止画だけ書き出す（確認用）
# 必要なもの: python3（pillow numpy scipy imageio-ffmpeg）, node + playwright（Chromium）
set -euo pipefail
cd "$(dirname "$0")/../.."
bash media/promo/fetch_fonts.sh
python3 media/promo/prep_assets.py
python3 media/promo/bgm.py
NODE_PATH="${NODE_PATH:-$(npm root -g)}" node media/promo/render.mjs "$@"
