#!/bin/bash
# note.com に下書きをアップロードするローカル実行スクリプト
# 使い方: bash push_note.sh

set -e

cd "$(dirname "$0")"

# 最新の記事を取得
echo "=== リポジトリを最新に更新 ==="
git pull origin main

# セッショントークンの入力
if [ -z "$NOTE_SESSION_TOKEN" ]; then
  echo ""
  echo "note.com の _note_session_v5 Cookie 値を入力してください:"
  echo "(Chrome DevTools > Application > Cookies > note.com > _note_session_v5)"
  read -r NOTE_SESSION_TOKEN
fi

export NOTE_SESSION_TOKEN

# アップロード実行
echo ""
echo "=== note.com にアップロード中 ==="
python src/push_note_drafts.py

echo ""
echo "完了しました。"
