"""
マルチプラットフォーム自動投稿 メインオーケストレーター

使い方:
  python src/main.py                          # X に投稿（デフォルト）
  python src/main.py --platform instagram     # Instagram に投稿
  python src/main.py --platform note          # note 記事を生成
  python src/main.py --platform tiktok        # TikTok スクリプトを生成
  python src/main.py --dry-run                # プレビューのみ（投稿しない）
  python src/main.py --generate               # 生成のみ表示（投稿しない）
  python src/main.py --platform note --dry-run
"""
import sys
import os
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from research import build_research_context
from generate import generate_post
from queue_manager import has_pending_posts, pop_next_post

# プラットフォームアダプターの登録テーブル
def _get_platform_adapters():
    from platforms.x import XAdapter
    from platforms.note import NoteAdapter
    from platforms.instagram import InstagramAdapter
    from platforms.tiktok import TikTokAdapter
    return {
        "x": XAdapter,
        "note": NoteAdapter,
        "instagram": InstagramAdapter,
        "tiktok": TikTokAdapter,
    }


def load_persona(config_path: str = "persona/config.yaml") -> dict:
    """ペルソナ設定を読み込む"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"ペルソナ設定が見つかりません: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(dry_run: bool = False, generate_only: bool = False, platform: str = "x") -> None:
    """メイン処理"""
    print(f"[main] ペルソナ設定を読み込み中...")
    persona = load_persona()
    print(f"[main] ペルソナ: {persona['name']} | プラットフォーム: {platform.upper()}")

    adapters = _get_platform_adapters()
    if platform not in adapters:
        print(f"[main] エラー: 未対応のプラットフォーム '{platform}'。対応: {list(adapters.keys())}")
        sys.exit(1)

    adapter = adapters[platform]()
    constraints = adapter.get_constraints()

    # キューに該当プラットフォームの投稿があればそちらを優先
    # --generate モードは常に新規生成（キューへの追加が目的のため）
    item = None
    if not generate_only and has_pending_posts(platform=platform):
        print(f"[main] [{platform}] キューから次の投稿を取得します...")
        item = pop_next_post(platform=platform)

    if item is not None:
        content = {"text": item.get("text", ""), "platform": platform}
        if item.get("media_path"):
            content["media_path"] = item["media_path"]
        post_text = content["text"]
        print(f"\n{'='*50}")
        print(f"キューからの投稿文 ({len(post_text)}文字):")
        print(f"{'='*50}")
        print(post_text)
        print(f"{'='*50}\n")
    else:
        if generate_only:
            print(f"[main] [{platform}] --generate モード: 新規コンテンツを生成します...")
        else:
            print(f"[main] [{platform}] キューが空のため、コンテンツをその場で生成します...")
        print("[main] トレンドリサーチ中...")
        research_context = build_research_context(persona.get("interests", []))
        print(f"[main] 季節コンテキスト: {research_context['seasonal_context']}")
        print(f"[main] 取得トピック数: {len(research_context['trending_topics'])}")

        print("[main] コンテンツ生成中...")
        recent_posts = adapter.get_recent_posts(5)
        generated = generate_post(
            persona,
            research_context,
            platform=platform,
            constraints=constraints,
            recent_posts=recent_posts,
        )

        # X はstr、note/TikTok はdict を返す
        if isinstance(generated, dict):
            content = {**generated, "platform": platform}
            post_text = generated.get("text") or generated.get("title") or str(generated)[:80]
        else:
            content = {"text": generated, "platform": platform}
            post_text = generated

        print(f"\n{'='*50}")
        print(f"生成されたコンテンツ ({len(post_text)}文字 プレビュー):")
        print(f"{'='*50}")
        print(post_text)
        print(f"{'='*50}\n")

    if generate_only:
        # Instagram は --generate モードでも画像ファイルを生成・保存する
        # かつキャプションをキューに保存して Job2 が同じ内容で投稿できるようにする
        if platform == "instagram" and isinstance(content, dict):
            from media.image_generator import generate_instagram_image
            from queue_manager import load_queue, save_queue
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _ZI
            _jst = _ZI("Asia/Tokyo")
            now_jst = _dt.now(_jst)
            ts = now_jst.strftime("%Y%m%d_%H%M%S")
            media_path = Path(f"posts/media/{ts}_instagram.png")
            caption = content.get("caption", content.get("text", ""))
            hashtags = content.get("hashtags", [])
            generate_instagram_image(
                caption_text=caption,
                hashtags=hashtags[:8],
                output_path=media_path,
            )
            print(f"[main] 画像生成完了: {media_path}")

            # キャプション + 画像パスをキューに保存（Job2 がこれを使って投稿する）
            # 古い pending エントリは削除してから追加（重複防止）
            full_caption = caption + "\n\n" + " ".join(hashtags) if hashtags else caption
            queue = load_queue()
            queue = [q for q in queue if not (q.get("platform") == "instagram" and q.get("status") == "pending")]
            queue.append({
                "text": full_caption,
                "platform": "instagram",
                "scheduled_for": now_jst.isoformat(),
                "status": "pending",
                "created_at": now_jst.isoformat(),
                "posted_at": None,
                "media_path": str(media_path),
            })
            save_queue(queue)
            print(f"[main] キャプションをキューに保存しました: {media_path.name}")
        print("[main] --generate モード: 投稿はスキップ")
        return

    # 投稿実行（Xのみ重複再生成ロジックを適用）
    if platform == "x":
        max_retries = 3
        for attempt in range(max_retries):
            result = adapter.post(content, dry_run=dry_run)
            if dry_run or result.get("platform_id") not in ("skipped_duplicate",):
                break
            if attempt < max_retries - 1:
                print(f"[main] 重複のため再生成します（{attempt + 2}/{max_retries}回目）...")
                research_context = build_research_context(persona.get("interests", []))
                recent_posts = adapter.get_recent_posts(5)
                generated = generate_post(
                    persona, research_context,
                    platform=platform, constraints=constraints,
                    recent_posts=recent_posts,
                )
                content = {"text": generated, "platform": platform}
                print(f"[main] 再生成: {generated}")
            else:
                print("[main] 再生成を3回試みましたがすべて重複でした。スキップします。")
    else:
        result = adapter.post(content, dry_run=dry_run)

    if not dry_run:
        pid = result.get("platform_id")
        if pid and pid not in ("skipped_duplicate",):
            print(f"[main] 完了！ platform_id: {pid}")
    else:
        print("[main] ドライランが完了しました。")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="マルチプラットフォーム自動投稿")
    parser.add_argument(
        "--platform",
        choices=["x", "instagram", "note", "tiktok"],
        default="x",
        help="投稿先プラットフォーム（デフォルト: x）",
    )
    parser.add_argument("--dry-run", action="store_true", help="プレビューのみ（実際には投稿しない）")
    parser.add_argument("--generate", action="store_true", help="生成のみ表示（投稿しない）")
    args = parser.parse_args()

    run(dry_run=args.dry_run, generate_only=args.generate, platform=args.platform)
