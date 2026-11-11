#!/bin/bash
# 会議ノートを起動する（Mac ではこのファイルをダブルクリック）
# 初回だけ、必要なものを .venv にインストールする（数分かかります）
cd "$(dirname "$0")" || exit 1
DATA="${MEETING_NOTES_DIR:-$HOME/MeetingNotes}"
mkdir -p "$DATA"
# APIキーは ~/MeetingNotes/.env に置く（リポジトリには入れない）
if [ -f "$DATA/.env" ]; then set -a; . "$DATA/.env"; set +a; fi
if [ ! -x .venv/bin/python ]; then
  echo "初回の準備をしています（数分かかります）…"
  python3 -m venv .venv || { echo "python3 が見つかりません。README の「準備」を見てください。"; read -r; exit 1; }
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt || { echo "インストールに失敗しました。"; read -r; exit 1; }
fi
exec .venv/bin/python run.py
