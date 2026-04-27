"""
投稿キュー管理モジュール
投稿を事前に生成・保存・確認・編集できる仕組みを提供する
platform フィールドで X / Instagram / note / TikTok を区別する
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

QUEUE_PATH = Path("posts/queue.json")
JST = ZoneInfo("Asia/Tokyo")


def load_queue() -> list[dict]:
    """キューを読み込む"""
    if not QUEUE_PATH.exists():
        return []
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_queue(queue: list[dict]) -> None:
    """キューを保存する"""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def get_next_scheduled_times(count: int, preferred_hours: list[int]) -> list[str]:
    """次のcount件分のスケジュール時刻を返す（JST）"""
    now = datetime.now(JST)
    times = []
    check = now

    while len(times) < count:
        for hour in sorted(preferred_hours):
            candidate = check.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > now:
                times.append(candidate.isoformat())
            if len(times) >= count:
                break
        check = (check + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    return times[:count]


def pop_next_post(platform: str = None) -> dict | None:
    """
    キューから次の投稿を取り出す（statusがpendingの最初の1件）

    Args:
        platform: 対象プラットフォーム（None で全プラットフォーム対象）

    Returns:
        投稿アイテム、または None（キューが空の場合）
    """
    queue = load_queue()
    now = datetime.now(JST)
    changed = False

    for item in queue:
        if item.get("status") != "pending":
            continue

        # platformフィルタ（指定がある場合のみ）
        item_platform = item.get("platform", "x")
        if platform and item_platform != platform:
            continue

        # 予定時刻が2時間以上過去ならexpiredにしてスキップ
        scheduled_str = item.get("scheduled_for", "")
        if scheduled_str:
            try:
                scheduled = datetime.fromisoformat(scheduled_str)
                if scheduled.tzinfo is None:
                    scheduled = scheduled.replace(tzinfo=JST)
                if scheduled < now - timedelta(hours=2):
                    item["status"] = "expired"
                    changed = True
                    print(f"[queue] 期限切れのためスキップ: {item['text'][:40]}...")
                    continue
            except Exception:
                pass

        item["status"] = "posted"
        item["posted_at"] = now.isoformat()
        save_queue(queue)
        return item

    if changed:
        save_queue(queue)
    return None


def has_pending_posts(platform: str = None) -> bool:
    """
    pendingな投稿があるかどうか

    Args:
        platform: 対象プラットフォーム（None で全プラットフォーム対象）
    """
    for item in load_queue():
        if item.get("status") != "pending":
            continue
        item_platform = item.get("platform", "x")
        if platform is None or item_platform == platform:
            return True
    return False


def get_next_scheduled_datetimes(count: int, preferred_hours: list[int]) -> list[datetime]:
    """次のcount件分のスケジュール時刻をdatetimeで返す（JST）"""
    now = datetime.now(JST)
    times = []
    check = now

    while len(times) < count:
        for hour in sorted(preferred_hours):
            candidate = check.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > now:
                times.append(candidate)
            if len(times) >= count:
                break
        check = (check + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    return times[:count]


def add_to_queue(
    posts: list[str],
    preferred_hours: list[int],
    platform: str = "x",
    media_paths: list[str] = None,
) -> None:
    """
    生成した投稿文をキューに追加する

    Args:
        posts: 投稿テキストのリスト
        preferred_hours: 投稿希望時間リスト（例: [8, 12, 20]）
        platform: 投稿先プラットフォーム（"x" | "instagram" | "note" | "tiktok"）
        media_paths: 画像/動画パスのリスト（Instagramなど、optional）
    """
    queue = load_queue()
    pending_count = sum(1 for item in queue if item.get("status") == "pending")
    times = get_next_scheduled_datetimes(len(posts), preferred_hours)

    media_paths = media_paths or [None] * len(posts)

    for text, scheduled_for, media_path in zip(posts, times, media_paths):
        entry = {
            "text": text,
            "platform": platform,
            "scheduled_for": scheduled_for.isoformat(),
            "status": "pending",
            "created_at": datetime.now(JST).isoformat(),
            "posted_at": None,
        }
        if media_path:
            entry["media_path"] = media_path
        queue.append(entry)

    save_queue(queue)
    print(f"[queue] {len(posts)}件を{platform}キューに追加しました（合計pending: {pending_count + len(posts)}件）")


def print_queue_preview() -> None:
    """キューの中身を見やすく表示する"""
    queue = load_queue()
    pending = [item for item in queue if item.get("status") == "pending"]

    if not pending:
        print("キューにpendingな投稿はありません。")
        return

    print(f"\n{'='*60}")
    print(f"投稿プレビュー（{len(pending)}件）")
    print(f"{'='*60}")
    for i, item in enumerate(pending, 1):
        scheduled = item.get("scheduled_for", "未設定")
        platform = item.get("platform", "x")
        text = item.get("text", "")
        print(f"\n【{i}件目】[{platform.upper()}] 予定: {scheduled}")
        print(f"{'-'*40}")
        print(text)
        print(f"（{len(text)}文字）")
    print(f"\n{'='*60}")
    print(f"※ posts/queue.json を直接編集して内容を変更できます")
