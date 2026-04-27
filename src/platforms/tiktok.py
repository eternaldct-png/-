"""
TikTok プラットフォームアダプター（Phase 3: スクリプト生成のみ）

TikTok Content Posting API は審査が必要なため、
まず動画スクリプトを JSON + Markdown ファイルとして保存する。
GitHub Issue で「撮影・投稿リマインダー」を作成する。

Phase 3.5（将来）: ffmpeg での動画自動生成 + API 投稿
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from platforms.base import PlatformAdapter

JST = ZoneInfo("Asia/Tokyo")
HISTORY_PATH = Path("posts/tiktok/history.json")
SCRIPTS_DIR = Path("posts/tiktok/scripts")


class TikTokAdapter(PlatformAdapter):
    """TikTok スクリプト生成アダプター"""

    def get_history_path(self) -> Path:
        return HISTORY_PATH

    def get_constraints(self) -> dict:
        return {
            "duration_seconds": 60,
            "content_format": "video_script",
            "requires_media": False,
            "supports_media": False,
            "max_tokens_hint": 800,
        }

    def is_duplicate(self, text: str) -> bool:
        """フックの先頭50文字で重複確認"""
        history = self._load_history()
        hooks = {item.get("hook", "")[:50] for item in history}
        key = text[:50]
        if key in hooks:
            print(f"[tiktok] 同一フックのスクリプトが履歴にあります: {key}...")
            return True
        return False

    def post(self, content: dict, dry_run: bool = False) -> dict:
        """
        TikTok スクリプトをファイルに保存する

        Args:
            content: generate_post() の dict 戻り値
                     {"hook", "body", "cta", "on_screen_text", "hashtags",
                      "duration_estimate_sec", "bgm_suggestion"}
            dry_run: Trueの場合はファイル保存しない

        Returns:
            {platform_id, hook, filepath, timestamp, status}
        """
        hook = content.get("hook", "")
        body = content.get("body", content.get("text", ""))
        cta = content.get("cta", "")
        on_screen = content.get("on_screen_text", [])
        hashtags = content.get("hashtags", [])
        duration = content.get("duration_estimate_sec", 60)
        bgm = content.get("bgm_suggestion", "")

        timestamp = datetime.now(JST)
        slug = timestamp.strftime("%Y%m%d_%H%M%S")
        json_path = SCRIPTS_DIR / f"{slug}_tiktok_script.json"
        md_path = SCRIPTS_DIR / f"{slug}_tiktok_script.md"

        script_data = {
            "hook": hook,
            "body": body,
            "cta": cta,
            "on_screen_text": on_screen,
            "hashtags": hashtags,
            "duration_estimate_sec": duration,
            "bgm_suggestion": bgm,
            "created_at": timestamp.isoformat(),
            "status": "draft",
        }

        if dry_run:
            print(f"\n{'='*60}")
            print(f"[TikTok][DRY RUN] スクリプトプレビュー")
            print(f"{'='*60}")
            print(f"フック: {hook}")
            print(f"本題: {body[:150]}...")
            print(f"CTA: {cta}")
            print(f"推定時間: {duration}秒")
            print(f"ハッシュタグ: {' '.join(hashtags)}")
            print(f"{'='*60}\n")
            return {
                "platform_id": "dry_run",
                "hook": hook,
                "filepath": str(md_path),
                "timestamp": timestamp.isoformat(),
                "status": "dry_run",
            }

        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

        # JSON（将来の動画自動生成用）
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        # Markdown（人間が読む撮影台本）
        md_content = self._format_script_md(script_data)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"[tiktok] スクリプトを保存しました: {md_path}")
        print(f"[tiktok] → 動画を撮影して TikTok にアップロードしてください")

        result = {
            "platform_id": slug,
            "hook": hook,
            "filepath": str(md_path),
            "timestamp": timestamp.isoformat(),
            "status": "saved",
        }
        self._save_history(result)
        return result

    # ── 内部メソッド ──────────────────────────────────────────

    @staticmethod
    def _format_script_md(script: dict) -> str:
        """人間が読みやすい撮影台本 Markdown を生成する"""
        on_screen = "\n".join(f"- {t}" for t in script.get("on_screen_text", []))
        hashtags = " ".join(script.get("hashtags", []))
        return f"""# TikTok 撮影台本

**作成日**: {script.get('created_at', '')}
**推定時間**: {script.get('duration_estimate_sec', 60)}秒
**BGM提案**: {script.get('bgm_suggestion', '')}

---

## 🎬 フック（最初の3秒）

> {script.get('hook', '')}

---

## 📢 本題（40秒）

{script.get('body', '')}

---

## 💬 CTA（最後17秒）

> {script.get('cta', '')}

---

## 📱 テロップテキスト

{on_screen}

---

## #ハッシュタグ

{hashtags}

---

## ✅ 投稿チェックリスト

- [ ] 動画を撮影
- [ ] テロップを追加
- [ ] BGM を設定
- [ ] ハッシュタグをコピー
- [ ] TikTok にアップロード
- [ ] `status: "posted"` に更新（JSONファイル）
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
        """直近n件のフックを返す（重複回避用）"""
        history = self._load_history()
        return [item.get("hook", "") for item in history[-n:]]
