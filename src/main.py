"""
X自動投稿 メインオーケストレーター
使い方:
  python src/main.py              # 実際に投稿（キューがあればキューから、なければ生成）
  python src/main.py --dry-run    # プレビューのみ（投稿しない）
  python src/main.py --generate   # 投稿文生成のみ表示
"""
import sys
import os
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from research import build_research_context
from generate import generate_post
from post import post_to_x
from queue_manager import has_pending_posts, pop_next_post


def load_persona(config_path: str = "persona/config.yaml") -> dict:
    """ペルソナ設定を読み込む"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"ペルソナ設定が見つかりません: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(dry_run: bool = False, generate_only: bool = False) -> None:
    """メイン処理"""
    print("[main] ペルソナ設定を読み込み中...")
    persona = load_persona()
    print(f"[main] ペルソナ: {persona['name']}")

    # キューに投稿があればそちらを優先
    if has_pending_posts():
        print("[main] キューから次の投稿を取得します...")
        item = pop_next_post()
        post_text = item["text"]
        print(f"\n{'='*50}")
        print(f"キューからの投稿文 ({len(post_text)}文字):")
        print(f"{'='*50}")
        print(post_text)
        print(f"{'='*50}\n")
    else:
        print("[main] キューが空のため、投稿文をその場で生成します...")
        print("[main] トレンドリサーチ中...")
        research_context = build_research_context(persona.get("interests", []))
        print(f"[main] 季節コンテキスト: {research_context['seasonal_context']}")
        print(f"[main] 取得トピック数: {len(research_context['trending_topics'])}")

        print("[main] 投稿文を生成中...")
        post_text = generate_post(persona, research_context)

        print(f"\n{'='*50}")
        print(f"生成された投稿文 ({len(post_text)}文字):")
        print(f"{'='*50}")
        print(post_text)
        print(f"{'='*50}\n")

    if generate_only:
        print("[main] --generate モード: 投稿はスキップ")
        return

    # 重複の場合は最大3回まで再生成して投稿
    max_retries = 3
    for attempt in range(max_retries):
        result = post_to_x(post_text, dry_run=dry_run)
        if dry_run or result.get("tweet_id") != "skipped_duplicate":
            break
        if attempt < max_retries - 1:
            print(f"[main] 重複のため再生成します（{attempt + 2}/{max_retries}回目）...")
            research_context = build_research_context(persona.get("interests", []))
            post_text = generate_post(persona, research_context)
            print(f"[main] 再生成: {post_text}")
        else:
            print("[main] 再生成を3回試みましたがすべて重複でした。スキップします。")

    if not dry_run:
        tweet_id = result.get("tweet_id")
        if tweet_id and tweet_id not in ("skipped_duplicate",):
            print(f"[main] 完了！ tweet_id: {tweet_id}")
    else:
        print("[main] ドライランが完了しました。")


if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    generate_only = "--generate" in args
    run(dry_run=dry_run, generate_only=generate_only)
