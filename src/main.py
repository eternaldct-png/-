"""
X自動投稿 メインオーケストレーター
使い方:
  python src/main.py              # 実際に投稿
  python src/main.py --dry-run    # プレビューのみ（投稿しない）
  python src/main.py --generate   # 投稿文生成のみ表示
"""
import sys
import os
import yaml
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from research import build_research_context
from generate import generate_post
from post import post_to_x


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

    result = post_to_x(post_text, dry_run=dry_run)

    if not dry_run:
        print(f"[main] 完了！ tweet_id: {result.get('tweet_id')}")
    else:
        print("[main] ドライランが完了しました。")


if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    generate_only = "--generate" in args
    run(dry_run=dry_run, generate_only=generate_only)
