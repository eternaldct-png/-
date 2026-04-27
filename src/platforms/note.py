"""
note プラットフォームアダプター

note.com には公式 API がないため、生成した記事を Markdown ファイルとして保存し、
GitHub Issue で「公開リマインダー」を作成する。
手動でコピー&ペーストして投稿する運用を前提とする。
"""
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from platforms.base import PlatformAdapter

JST = ZoneInfo("Asia/Tokyo")
HISTORY_PATH = Path("posts/note/history.json")
ARTICLES_DIR = Path("posts/note/articles")


class NoteAdapter(PlatformAdapter):
    """note 記事生成アダプター（ファイル保存方式）"""

    def get_history_path(self) -> Path:
        return HISTORY_PATH

    def get_constraints(self) -> dict:
        return {
            "min_length": 1000,
            "max_length": 5000,
            "content_format": "markdown",
            "requires_media": False,
            "supports_media": False,
            "max_tokens_hint": 4096,
        }

    def is_duplicate(self, text: str) -> bool:
        """タイトルの先頭50文字で重複確認"""
        history = self._load_history()
        titles = {item.get("title", "")[:50] for item in history}
        key = text[:50]
        if key in titles:
            print(f"[note] 同タイトルの記事が履歴にあります: {key}...")
            return True
        return False

    def post(self, content: dict, dry_run: bool = False) -> dict:
        """
        note 記事を Markdown ファイルに保存する

        Args:
            content: {"title": ..., "body": ...(Markdown), "tags": [...]}
                     または generate_post() の戻り値 dict
            dry_run: Trueの場合はファイルを書き込まずプレビューのみ

        Returns:
            {platform_id, title, filepath, timestamp, status}
        """
        title = content.get("title", "無題")
        body = content.get("body", content.get("text", ""))
        tags = content.get("tags", [])

        timestamp = datetime.now(JST)
        slug = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{self._slugify(title)}"
        filepath = ARTICLES_DIR / f"{slug}.md"

        article_md = self._format_article(title, body, tags, timestamp)

        if dry_run:
            print(f"\n{'='*60}")
            print(f"[note][DRY RUN] 記事プレビュー")
            print(f"{'='*60}")
            print(f"タイトル: {title}")
            print(f"文字数: {len(body)}文字")
            print(f"タグ: {', '.join(tags)}")
            print(f"保存先: {filepath}")
            print(f"{'='*60}\n")
            print(article_md[:500] + "...\n")
            return {
                "platform_id": "dry_run",
                "title": title,
                "filepath": str(filepath),
                "timestamp": timestamp.isoformat(),
                "status": "dry_run",
            }

        ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(article_md)

        print(f"[note] 記事を保存しました: {filepath}")
        print(f"[note] 文字数: {len(body)}文字 | タグ: {', '.join(tags)}")
        print(f"[note] → note.com に手動でコピー&ペーストして公開してください")

        result = {
            "platform_id": slug,
            "title": title,
            "filepath": str(filepath),
            "timestamp": timestamp.isoformat(),
            "status": "saved",
        }
        self._save_history(result)
        return result

    # ── 内部メソッド ──────────────────────────────────────────

    @staticmethod
    def _slugify(text: str) -> str:
        """タイトルをファイル名に使えるslugに変換する"""
        # 日本語はそのまま残し、記号だけ除去
        slug = re.sub(r'[\\/:*?"<>|]', '', text)
        slug = slug.replace(' ', '_').replace('　', '_')
        return slug[:40]

    @staticmethod
    def _format_article(title: str, body: str, tags: list, timestamp: datetime) -> str:
        """Frontmatter + 本文の Markdown を生成する"""
        tags_yaml = "\n".join(f'  - "{t}"' for t in tags)
        return f"""---
title: "{title}"
date: "{timestamp.strftime('%Y-%m-%d')}"
tags:
{tags_yaml}
note_status: "draft"
note_url: ""
membership_only: false
---

{body}
"""

    def _load_history(self) -> list[dict]:
        path = self.get_history_path()
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _save_history(self, result: dict) -> None:
        path = self.get_history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        history = self._load_history()
        history.append(result)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def get_recent_posts(self, n: int = 5) -> list[str]:
        """直近n件の記事タイトルを返す（重複回避用）"""
        history = self._load_history()
        return [item.get("title", "") for item in history[-n:]]
