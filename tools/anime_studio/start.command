#!/bin/bash
# ツヅリを起動する（Mac ではこのファイルをダブルクリック）
# 初回（と requirements.txt が変わったとき）だけ、必要なものを .venv にインストールする（1〜2分）
cd "$(dirname "$0")" || exit 1
PORT="${TSUZURI_PORT:-5056}"
URL="http://127.0.0.1:$PORT"

stop() {  # エラーのとき、画面を閉じずに理由を読めるようにする
  echo ""
  echo "⚠️  $1"
  echo "（この画面の文字をそのままコピーして Claude に送ってください）"
  read -r -p "Enter キーで閉じます" _
  exit 1
}

# もう起動しているなら、ブラウザで開くだけ
if curl -s -o /dev/null --max-time 2 "$URL/"; then
  echo "ツヅリはもう起動しています: $URL"
  open "$URL" 2>/dev/null || true
  exit 0
fi

DATA="${TSUZURI_DIR:-$HOME/Tsuzuri}"
mkdir -p "$DATA"
# APIキー（使うときだけ）は ~/Tsuzuri/.env に置く（リポジトリには入れない）
if [ -f "$DATA/.env" ]; then set -a; . "$DATA/.env"; set +a; fi

# いちばん新しい Python を使う（Mac にもとからある python3 は 3.9 のことが多い）
PY=""
for c in python3.13 python3.12 python3.11 python3.10 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || stop "Python 3.9 以上が見つかりません。https://www.python.org/downloads/ から入れて、もう一度ダブルクリックしてください。"
echo "使う Python: $("$PY" --version 2>&1)（$PY）"

# インストールが最後まで終わった印（.venv/.installed）と requirements.txt の中身がそろっていなければ、入れ直す
WANT="$(cat requirements.txt) | $("$PY" --version 2>&1)"
if [ ! -x .venv/bin/python ] || [ "$(cat .venv/.installed 2>/dev/null)" != "$WANT" ]; then
  echo "準備をしています（1〜2分）…"
  rm -rf .venv
  "$PY" -m venv .venv || stop "Python の仮想環境を作れませんでした。"
  .venv/bin/python -m pip install -q --upgrade pip || stop "pip の更新に失敗しました（ネットにつながっているか確かめてください）。"
  .venv/bin/python -m pip install -r requirements.txt || stop "必要なもののインストールに失敗しました。上の英語のメッセージが原因です。"
  printf '%s' "$WANT" > .venv/.installed
fi

.venv/bin/python run.py --port "$PORT" || stop "ツヅリが止まりました。上のメッセージが原因です。"
