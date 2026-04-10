"""
投稿キュー生成スクリプト
次のN件分の投稿を事前生成してキューに保存する
投稿予定日の曜日・日付を使って生成するため、曜日がずれない

使い方:
  python src/generate_queue.py          # デフォルト3件生成
  python src/generate_queue.py --count 6  # 6件生成
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import load_persona
from research import build_research_context
from generate import generate_post
from queue_manager import add_to_queue, get_next_scheduled_datetimes, print_queue_preview


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3, help="生成する投稿数（デフォルト:3）")
    args = parser.parse_args()

    print(f"[generate_queue] {args.count}件の投稿を生成します...")
    persona = load_persona()
    preferred_hours = persona.get("posting_schedule", {}).get("preferred_hours", [8, 12, 20])

    # 投稿予定日時を先に計算する
    scheduled_times = get_next_scheduled_datetimes(args.count, preferred_hours)

    posts = []
    for i, target_dt in enumerate(scheduled_times):
        print(f"[generate_queue] {i+1}/{args.count}件目を生成中... (予定: {target_dt.strftime('%m/%d %H時 %A')})")
        research_context = build_research_context(persona.get("interests", []))
        # ← 投稿予定日時を渡すことで、その日の曜日で生成される
        text = generate_post(persona, research_context, target_dt=target_dt)
        posts.append(text)

    add_to_queue(posts, preferred_hours)
    print_queue_preview()


if __name__ == "__main__":
    main()
