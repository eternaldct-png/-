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

# アップロード実行（件数は bash push_note.sh --limit 5 のように指定。既定は新しい順に3件）
echo ""
echo "=== note.com にアップロード中 ==="
status=0
python src/push_note_drafts.py "$@" || status=$?

# 結果（下書き作成済み・失敗理由）を GitHub に反映して /note-drafts に表示させる
git add posts/note/articles/ posts/note/history.json
if ! git diff --staged --quiet; then
  git commit -m "chore: note下書きアップロード結果を記録 [skip ci]"
  git push origin HEAD
fi

echo ""
if [ "$status" -eq 0 ]; then
  echo "完了しました。"
else
  echo "一部の記事がアップロードできませんでした（理由は /note-drafts に表示されます）。"
fi
exit "$status"
