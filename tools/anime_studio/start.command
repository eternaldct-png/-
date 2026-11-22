#!/bin/bash
# ツヅリを起動する（Mac ではこのファイルをダブルクリック）
# 初回だけ、必要なものを .venv にインストールする（1〜2分）
cd "$(dirname "$0")" || exit 1
DATA="${TSUZURI_DIR:-$HOME/Tsuzuri}"
mkdir -p "$DATA"
# APIキー（使うときだけ）は ~/Tsuzuri/.env に置く（リポジトリには入れない）
if [ -f "$DATA/.env" ]; then set -a; . "$DATA/.env"; set +a; fi
if [ ! -x .venv/bin/python ]; then
  echo "初回の準備をしています（1〜2分）…"
  python3 -m venv .venv || { echo "python3 が見つかりません。README の「準備」を見てください。"; read -r; exit 1; }
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt || { echo "インストールに失敗しました。"; read -r; exit 1; }
fi
exec .venv/bin/python run.py
