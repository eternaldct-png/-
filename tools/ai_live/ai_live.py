"""AIキャラで TikTok LIVE を回す（B案の試作）。

使い方（配信するWindows PCで）:
    python ai_live.py                 # 本番: TikTok LIVE に接続
    python ai_live.py --demo          # 練習: TikTokにつながず、ダミーのコメント・ギフトで動かす
    python ai_live.py --demo --no-ai  # AIも使わず定型文だけ（AI代ゼロで画面・音声を確認）

起動中にこのウィンドウへ入力できるコマンド（＝オペレーター操作）:
    /say こんにちは       … キャラにそのまま言わせる
    /ai 新曲の告知をして  … AIに指示して言わせる
    /pause /resume        … 返事を一時停止・再開（荒れたとき用）
    /stats                … ここまでのAI代を表示
    /quit                 … 終了
  --demo のときだけ:
    c 名前 コメント       … ダミーのコメントを送る
    g 名前 ギフト名 ダイヤ … ダミーのギフトを送る（例: g たろう バラ 1）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_core import HERE, CostMeter, Task, TaskQueue, check_comment, gift_tier, load_config  # noqa: E402
from overlay import OverlayState, start_overlay  # noqa: E402
from voice import Voice, wav_seconds  # noqa: E402

log = logging.getLogger("ai_live")


class Show:
    """受け取ったイベントをキューに入れ、1つずつ「考える→しゃべる」を回す。"""

    def __init__(self, cfg: dict, use_ai: bool = True):
        self.cfg = cfg
        b = cfg["behavior"]
        self.queue = TaskQueue(b["comment_queue_max"], b["user_cooldown_sec"])
        self.meter = CostMeter(cfg["ai"])
        self.voice = Voice(cfg["voice"])
        img = cfg["character"].get("image")
        self.overlay = OverlayState(cfg["character"]["name"], (HERE / img).resolve() if img else None)
        self.brain = None
        if use_ai:
            from brain import Brain

            self.brain = Brain(cfg, self.meter)
        self.paused = False
        self.running = True
        self.last_activity = time.monotonic()
        self.skipped = 0
        log_dir = HERE / "logs"
        log_dir.mkdir(exist_ok=True)
        self.log_path = log_dir / f"{datetime.now():%Y%m%d_%H%M%S}.jsonl"

    # ---- イベントの受け取り（TikTok / デモ / オペレーター共通） ----
    def on_comment(self, user: str, text: str) -> None:
        reason = check_comment(text, self.cfg["safety"])
        if reason:
            self.skipped += 1
            log.info("スキップ（%s）: %s: %s", reason, user, text)
            return
        log.info("💬 %s: %s", user, text)
        self.queue.push("comment", user, text)
        self.last_activity = time.monotonic()

    def on_gift(self, user: str, gift: str, count: int, diamonds_each: int) -> None:
        total = max(count, 1) * max(diamonds_each, 0)
        tier = gift_tier(total, self.cfg["gifts"]["tiers"])
        log.info("🎁 %s: %s ×%d（%dダイヤ, %s）", user, gift, count, total, tier["name"])
        # 演出は待たせずにすぐ出す。お礼のセリフは順番に
        self.overlay.effect(tier.get("effect", "sparkle"), f"{user}さん {gift}×{count} ありがとう！")
        self.queue.push("gift", user, gift=gift, count=count, diamonds=total, tier=tier)
        self.last_activity = time.monotonic()

    def on_follow(self, user: str) -> None:
        if self.cfg["behavior"].get("greet_followers", True):
            self.overlay.effect("sparkle", f"{user}さん フォローありがとう！")
            self.queue.push("follow", user)

    def on_join(self, user: str) -> None:
        if self.cfg["behavior"].get("greet_joins", False):
            self.queue.push("join", user)

    # ---- しゃべる ----
    def _template(self, task: Task) -> str:
        if task.kind == "gift":
            return task.extra["tier"]["line"].format(user=task.user, gift=task.extra["gift"])
        if task.kind == "follow":
            return f"{task.user}さん、フォローありがとう！"
        if task.kind == "join":
            return f"{task.user}さん、いらっしゃい！"
        if task.kind == "idle":
            return f"ねえねえ、みんなの{task.text}って何？コメントで教えて！"
        if task.kind == "comment":
            return f"{task.user}さん、コメントありがとう！"
        return task.text

    def compose(self, task: Task) -> str:
        if task.kind == "operator" and task.extra.get("verbatim"):
            return task.text
        needs_ai = task.kind in ("comment", "idle", "operator") or (
            task.kind == "gift" and task.extra["tier"].get("use_ai")
        )
        if needs_ai and self.brain:
            text = self.brain.reply(task)
            if text:
                return text
        return self._template(task)

    def speak(self, task: Task, text: str) -> None:
        log.info("🗣  %s", text)
        wav = self.voice.synthesize(text)
        self.overlay.say(text, task.user if task.kind in ("comment", "gift", "follow") else "")
        if wav:
            self.voice.play(wav)
        else:
            time.sleep(min(2 + len(text) * 0.12, 10))  # 音声なしでも字幕を読める時間だけ待つ
        self.overlay.done()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": datetime.now().isoformat(timespec="seconds"), "kind": task.kind,
                                "user": task.user, "in": task.text, "out": text}, ensure_ascii=False) + "\n")

    async def run(self) -> None:
        b = self.cfg["behavior"]
        loop = asyncio.get_running_loop()
        topics = self.cfg["character"].get("idle_topics") or ["今日あったこと"]
        while self.running:
            if self.paused:
                await asyncio.sleep(0.5)
                continue
            task = self.queue.pop()
            if task is None and time.monotonic() - self.last_activity >= b["idle_after_sec"]:
                task = Task(5, 0, "idle", text=random.choice(topics))
                self.last_activity = time.monotonic()
            if task is None:
                await asyncio.sleep(0.3)
                continue
            text = await loop.run_in_executor(None, self.compose, task)
            await loop.run_in_executor(None, self.speak, task, text)
            await asyncio.sleep(b["reply_interval_sec"])

    # ---- オペレーター（人）の操作 ----
    def command(self, line: str, demo: bool) -> None:
        line = line.strip()
        if not line:
            return
        if line.startswith("/say "):
            self.queue.push("operator", text=line[5:], verbatim=True)
        elif line.startswith("/ai "):
            self.queue.push("operator", text=line[4:])
        elif line == "/pause":
            self.paused = True
            log.warning("⏸  返事を一時停止しました（/resume で再開）")
        elif line == "/resume":
            self.paused = False
            log.warning("▶  再開しました")
        elif line == "/stats":
            self.print_stats()
        elif line == "/quit":
            self.running = False
        elif demo and line.startswith("c "):
            parts = line.split(maxsplit=2)
            if len(parts) == 3:
                self.on_comment(parts[1], parts[2])
        elif demo and line.startswith("g "):
            parts = line.split()
            if len(parts) >= 3:
                diamonds = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
                self.on_gift(parts[1], parts[2], 1, diamonds)
        else:
            print("コマンド: /say /ai /pause /resume /stats /quit" + ("  （デモ: c 名前 コメント / g 名前 ギフト ダイヤ）" if demo else ""))

    def print_stats(self) -> None:
        print(f"📊 {self.meter.summary()} / 読まなかったコメント {self.skipped}件・溢れて捨てたコメント {self.queue.dropped}件")


def _read_console(show: Show, loop: asyncio.AbstractEventLoop, demo: bool) -> None:
    for line in sys.stdin:
        loop.call_soon_threadsafe(show.command, line, demo)
        if line.strip() == "/quit":
            break


# ---- TikTok LIVE（非公式ライブラリ TikTokLive）につなぐ ----
def _name(user) -> str:
    if user is None:
        return "だれか"
    return getattr(user, "nickname", None) or getattr(user, "nick_name", None) or getattr(user, "unique_id", None) or "だれか"


async def connect_tiktok(show: Show, unique_id: str) -> None:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent, FollowEvent, GiftEvent, JoinEvent

    client = TikTokLiveClient(unique_id=unique_id)

    @client.on(ConnectEvent)
    async def _connected(_event):
        log.info("✅ TikTok LIVE に接続しました（%s）", unique_id)

    @client.on(DisconnectEvent)
    async def _disconnected(_event):
        log.warning("⚠️  TikTok LIVE から切断されました")

    @client.on(CommentEvent)
    async def _comment(event):
        text = getattr(event, "content", None) or getattr(event, "comment", "")
        show.on_comment(_name(event.user), text)

    @client.on(GiftEvent)
    async def _gift(event):
        if getattr(event, "streaking", False):  # 連打中は最後にまとめてお礼する
            return
        gift = getattr(event, "gift", None) or getattr(event, "gift_details", None)
        name = getattr(gift, "name", None) or getattr(gift, "gift_name", None) or "ギフト"
        show.on_gift(_name(event.user), name, getattr(event, "repeat_count", 1) or 1, getattr(gift, "diamond_count", 0) or 0)

    @client.on(FollowEvent)
    async def _follow(event):
        show.on_follow(_name(event.user))

    @client.on(JoinEvent)
    async def _join(event):
        show.on_join(_name(event.user))

    if not os.environ.get("SIGN_API_KEY"):
        log.warning("SIGN_API_KEY が未設定です（無料枠・制限が厳しい）。安定させるなら Euler Stream のAPIキーを設定してください")
    # 配信開始前に起動しても、LIVEが始まるまで待ってつなぎ直す
    while show.running:
        try:
            await (await client.start())
        except Exception as e:  # 非公式ライブラリなので、どんな失敗でも止めずに再接続する
            log.warning("TikTok LIVE に接続できません（%s: %s）。30秒後に再接続します", type(e).__name__, e)
        await asyncio.sleep(30)


async def demo_feed(show: Show) -> None:
    """練習用: ダミーのコメント・ギフトをときどき流す。"""
    users = ["たろう", "はなこ", "みく", "けん", "ゆい"]
    comments = ["こんばんは！", "初見です", "好きな曲なに？", "声かわいい", "今日なに食べた？", "AIなの？", "歌って〜"]
    gifts = [("バラ", 1), ("TikTok", 1), ("ハート", 5), ("ドーナツ", 30), ("帽子", 99), ("ライオン", 29999)]
    while show.running:
        await asyncio.sleep(random.uniform(6, 14))
        r = random.random()
        if r < 0.7:
            show.on_comment(random.choice(users), random.choice(comments))
        elif r < 0.9:
            g, d = random.choice(gifts)
            show.on_gift(random.choice(users), g, random.choice([1, 1, 3]), d)
        else:
            show.on_follow(random.choice(users))


async def main_async(args) -> None:
    cfg = load_config(args.config)
    show = Show(cfg, use_ai=not args.no_ai)
    ov = cfg["overlay"]
    start_overlay(show.overlay, ov["host"], ov["port"])
    print(f"🖥  配信画面: http://{ov['host']}:{ov['port']}/ をブラウザで開いて、LIVE Studio でキャプチャしてください")
    if show.voice.check():
        print("🔊 VOICEVOX に接続しました")
    loop = asyncio.get_running_loop()
    threading.Thread(target=_read_console, args=(show, loop, args.demo), daemon=True).start()

    jobs = [asyncio.create_task(show.run())]
    if args.demo:
        print("🧪 デモモード: ダミーのコメント・ギフトが流れます（c / g コマンドで手動でも送れます）")
        jobs.append(asyncio.create_task(demo_feed(show)))
    else:
        jobs.append(asyncio.create_task(connect_tiktok(show, cfg["tiktok"]["unique_id"])))
    try:
        while show.running:
            done = [j for j in jobs if j.done()]
            for j in done:
                if j.exception():
                    raise j.exception()
            await asyncio.sleep(0.5)
    finally:
        for j in jobs:
            j.cancel()
        show.print_stats()
        print(f"📝 会話ログ: {show.log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIキャラ TikTok LIVE（試作）")
    parser.add_argument("--config", default=None, help="設定ファイル（既定: config.yaml）")
    parser.add_argument("--demo", action="store_true", help="TikTokにつながずダミーのイベントで動かす")
    parser.add_argument("--no-ai", action="store_true", help="AIを使わず定型文だけで動かす（AI代ゼロ）")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
