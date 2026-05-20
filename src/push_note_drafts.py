"""
posts/note/articles/ にある下書き記事を note.com に一括アップロードするスクリプト

使い方:
  python src/push_note_drafts.py               # 全 draft をアップロード
  python src/push_note_drafts.py --dry-run     # 確認のみ（実際には投稿しない）
"""
import json
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from note_api_client import NoteAPIClient

ARTICLES_DIR = Path("posts/note/articles")
HISTORY_PATH = Path("posts/note/history.json")


# ── Frontmatter パーサー ──────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        meta = yaml.safe_load(parts[1])
        return meta or {}, parts[2].strip()
    except yaml.YAMLError:
        return {}, content


# ── 対象ファイル取得 ──────────────────────────────────────────────

def get_draft_articles() -> list[Path]:
    """note_status が 'draft' の記事ファイルを返す"""
    if not ARTICLES_DIR.exists():
        return []
    result = []
    for fp in sorted(ARTICLES_DIR.glob("*.md")):
        content = fp.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)
        if meta.get("note_status") == "draft":
            result.append(fp)
    return result


# ── ステータス更新 ────────────────────────────────────────────────

def mark_uploaded(filepath: Path, result: dict) -> None:
    """frontmatter の note_status と note_url を更新する"""
    content = filepath.read_text(encoding="utf-8")
    content = content.replace(
        'note_status: "draft"',
        'note_status: "uploaded_draft"',
    )
    content = content.replace(
        'note_url: ""',
        f'note_url: "{result.get("edit_url", result.get("url", ""))}"',
    )
    filepath.write_text(content, encoding="utf-8")


def update_history(filepath: Path, result: dict) -> None:
    """history.json の該当エントリに note URL を追記する"""
    if not HISTORY_PATH.exists():
        return
    with open(HISTORY_PATH, encoding="utf-8") as f:
        history = json.load(f)

    for entry in history:
        if Path(entry.get("filepath", "")).name == filepath.name:
            entry["note_url"] = result.get("edit_url", result.get("url", ""))
            entry["note_id"] = result.get("id")
            entry["note_key"] = result.get("key")
            break

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ── メイン ────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

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

    print(f"\n[push_note_drafts] {len(articles)}件の下書きをアップロードします")
    for fp in articles:
        content = fp.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)
        print(f"  - {meta.get('title', fp.stem)}")

    if dry_run:
        print("\n[push_note_drafts] --dry-run モード: 実際には投稿しません")
        return

    # ログイン（APIクライアント → ブラウザ自動化 の順で試行）
    use_browser = False
    client = NoteAPIClient()
    if session_token:
        client.login_with_session(session_token)
    else:
        print(f"\n[push_note_drafts] ログイン中: {email}")
        if not client.login(email, password):
            print("[push_note_drafts] API ログイン失敗 → ブラウザ自動化に切り替え")
            use_browser = True

    # アップロード
    success = 0
    failed = []

    for fp in articles:
        content = fp.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        title = meta.get("title", fp.stem)
        tags = meta.get("tags", [])

        print(f"\n→ アップロード中: 「{title}」")

        if use_browser:
            from note_browser_client import create_draft_via_browser
            result = create_draft_via_browser(email, password, title, body, tags)
        else:
            result = client.create_draft(title, body, tags)
            if result is None and email:
                print("  API 失敗 → ブラウザ自動化で再試行")
                from note_browser_client import create_draft_via_browser
                result = create_draft_via_browser(email, password, title, body, tags)

        if result:
            mark_uploaded(fp, result)
            update_history(fp, result)
            success += 1
            print(f"  ✓ 下書き保存完了: {result.get('edit_url', result.get('url', ''))}")
        else:
            failed.append(title)
            print(f"  ✗ 失敗: 「{title}」")

    print(f"\n{'='*50}")
    print(f"[push_note_drafts] 完了: {success}/{len(articles)}件成功")
    if failed:
        print(f"失敗: {', '.join(failed)}")
    print(f"{'='*50}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
