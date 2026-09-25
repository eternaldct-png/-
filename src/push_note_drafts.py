"""
posts/note/articles/ にある下書き記事を note.com にアップロードするスクリプト

使い方:
  python src/push_note_drafts.py               # 新しい順に最大3件アップロード
  python src/push_note_drafts.py --limit 5     # 最大5件（環境変数 NOTE_MAX_UPLOADS でも指定可）
  python src/push_note_drafts.py --dry-run     # 確認のみ（実際には投稿しない）

- ログインは1回の実行につき1回だけ。失敗したらその時点で中止する
  （何十回もログインし直すと note 側でブロックされるため）
- /note-drafts で手動で「下書き作成済」「公開済」にした記事はスキップする
  （DATABASE_URL が設定されている場合）
- 失敗した記事は history.json に理由と日時を記録し、/note-drafts に表示する
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import note_status as ns
from note_api_client import NoteAPIClient

DEFAULT_LIMIT = 3
WAIT_BETWEEN_UPLOADS = 10  # 秒


# ── 対象ファイル取得 ──────────────────────────────────────────────

def get_draft_articles() -> list[Path]:
    """note にまだ無い記事を新しい順に返す"""
    if not ns.ARTICLES_DIR.exists():
        return []

    manual, db_ok = ns.load_manual_statuses()
    if not db_ok:
        # 手動で付けた状態が読めないと、手作業で作った下書きと二重になる恐れがある
        print("[push_note_drafts] エラー: データベースに接続できないため中止します")
        sys.exit(1)

    result = []
    for fp in sorted(ns.ARTICLES_DIR.glob("*.md"), reverse=True):
        a = ns.read_article(fp)
        status = ns.merge_status(a["note_status"], manual.get(fp.name, {}).get("status"))
        if status == "draft":
            result.append(fp)
    return result


# ── ステータス更新 ────────────────────────────────────────────────

def mark_uploaded(filepath: Path, result: dict) -> None:
    """frontmatter の note_status と note_url を更新する"""
    ns.update_frontmatter(filepath, {
        "note_status": "uploaded_draft",
        "note_url": result.get("edit_url", result.get("url", "")),
    })


def update_history(filepath: Path, result: dict | None, error: str = "") -> None:
    """history.json の該当エントリにアップロード結果（成功時は note URL、失敗時は理由）を書く"""
    if not ns.HISTORY_PATH.exists():
        return
    with open(ns.HISTORY_PATH, encoding="utf-8") as f:
        history = json.load(f)

    for entry in history:
        if Path(entry.get("filepath", "")).name == filepath.name:
            entry["note_upload_attempted_at"] = datetime.now(ns.JST).isoformat(timespec="seconds")
            if result:
                entry["note_url"] = result.get("edit_url", result.get("url", ""))
                entry["note_id"] = result.get("id")
                entry["note_key"] = result.get("key")
                entry.pop("note_upload_error", None)
            else:
                entry["note_upload_error"] = error or "不明なエラー"
            break

    with open(ns.HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_limit() -> int:
    value = os.environ.get("NOTE_MAX_UPLOADS", "") or DEFAULT_LIMIT
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        if i + 1 < len(sys.argv):
            value = sys.argv[i + 1]
    try:
        return max(1, int(value))
    except ValueError:
        return DEFAULT_LIMIT


# ── メイン ────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv
    limit = get_limit()

    # 認証情報
    email = os.environ.get("NOTE_EMAIL", "")
    password = os.environ.get("NOTE_PASSWORD", "")
    session_token = os.environ.get("NOTE_SESSION_TOKEN", "")

    if not email and not session_token:
        print(
            "[push_note_drafts] エラー: 以下のいずれかを .env に設定してください\n"
            "  NOTE_EMAIL + NOTE_PASSWORD\n"
            "  NOTE_SESSION_TOKEN (_note_session_v5 Cookie の値)"
        )
        sys.exit(1)

    articles = get_draft_articles()

    if not articles:
        print("[push_note_drafts] アップロード対象の下書き記事がありません")
        return

    targets = articles[:limit]
    print(f"\n[push_note_drafts] note未作成 {len(articles)}件のうち、新しい順に {len(targets)}件をアップロードします")
    for fp in targets:
        print(f"  - {ns.read_article(fp)['title']}")

    if dry_run:
        print("\n[push_note_drafts] --dry-run モード: 実際には投稿しません")
        return

    # セッショントークンがあれば API、無ければブラウザ（ログインは1回だけ）。
    # メール/パスワードでの API ログインは何度も失敗して note 側のブロックを招くため使わない
    client = None
    if session_token:
        client = NoteAPIClient()
        client.login_with_session(session_token)

    browser = None
    browser_ctx = None
    login_error = ""

    success = 0
    failed = []

    try:
        for n, fp in enumerate(targets):
            if n:
                time.sleep(WAIT_BETWEEN_UPLOADS)
            a = ns.read_article(fp)
            title = a["title"]
            print(f"\n→ アップロード中: 「{title}」")

            result = None
            error = ""
            if client:
                result = client.create_draft(title, a["body"], a["tags"])
                if result is None:
                    error = "note API での下書き作成に失敗（NOTE_SESSION_TOKEN の期限切れの可能性）"

            if result is None and email:
                if browser is None:
                    from note_browser_client import NoteBrowserSession
                    browser_ctx = NoteBrowserSession()
                    browser = browser_ctx.__enter__()
                    print(f"\n[push_note_drafts] ブラウザでログイン中: {email}")
                    if not browser.login(email, password):
                        login_error = browser.last_error or "note へのログインに失敗"
                if login_error:
                    error = login_error
                else:
                    result = browser.create_draft(title, a["body"], a["tags"])
                    if result is None:
                        error = browser.last_error or "下書き作成に失敗"

            if result:
                mark_uploaded(fp, result)
                update_history(fp, result)
                success += 1
                print(f"  ✓ 下書き保存完了: {result.get('edit_url', result.get('url', ''))}")
            else:
                update_history(fp, None, error)
                failed.append(title)
                print(f"  ✗ 失敗: 「{title}」 {error}")

            if login_error:
                print("\n[push_note_drafts] ログインできないため、残りの記事は試さずに中止します")
                break
    finally:
        if browser_ctx:
            browser_ctx.__exit__(None, None, None)

    print(f"\n{'='*50}")
    print(f"[push_note_drafts] 完了: {success}/{len(targets)}件成功")
    if failed:
        print(f"失敗: {', '.join(failed)}")
    print(f"{'='*50}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
