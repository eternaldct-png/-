#!/usr/bin/env bash
# 動画用フォント（Noto Sans JP / Montserrat, いずれも SIL OFL）を Google Fonts から取得する。
# フォントは容量が大きいので git には含めない（.gitignore 済み）。
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts
cd fonts
[ -f fonts.css ] && ls *.ttf >/dev/null 2>&1 && { echo "fonts: already present"; exit 0; }
# 古いUAで取得すると woff2 分割ではなく TTF 1ファイルずつの CSS が返る
curl -fsS -A "Mozilla/5.0" "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&family=Montserrat:wght@300;600;800&display=swap" > fonts.css
for u in $(grep -o 'https://[^)]*' fonts.css); do
  n=$(echo "$u" | awk -F/ '{print $5"-"$NF}')
  curl -fsS -o "$n" "$u"
  sed -i "s#$u#$n#" fonts.css
done
echo "fonts: downloaded"
