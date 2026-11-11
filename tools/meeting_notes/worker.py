"""バックグラウンド処理（文字起こし → ノート生成）。

アプリ内のスレッド1本で、会議を1件ずつ順番に処理する。起動時に途中で止まった会議をキューに戻す。
"""
from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path

from . import ai, transcribe

log = logging.getLogger("meeting_notes.worker")


class Worker:
    def __init__(self, store, audio_dir: Path, *, transcriber=None, ai_client=None):
        self.store = store
        self.audio_dir = Path(audio_dir)
        self.transcriber = transcriber or transcribe.transcribe_audio
        self.ai_client = ai_client  # None なら本物の Claude
        self.q: queue.Queue[str] = queue.Queue()
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self.progress: dict[str, tuple[float, float]] = {}
        self._thread: threading.Thread | None = None

    # ── キュー ──────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        for mid in self.store.busy_meeting_ids():
            self.enqueue(mid)
        self._thread = threading.Thread(target=self._loop, name="meeting-notes-worker", daemon=True)
        self._thread.start()

    def enqueue(self, mid: str) -> bool:
        with self._lock:
            if mid in self._pending:
                return False
            self._pending.add(mid)
        self.q.put(mid)
        return True

    def is_pending(self, mid: str) -> bool:
        with self._lock:
            return mid in self._pending

    def purge_old_audio(self) -> int:
        """設定した日数より古い会議の録音ファイルを消す（ノート・文字起こしは残す）。"""
        days = int(float(self.store.settings().get("audio_retention_days") or 0))
        if days <= 0:
            return 0
        from datetime import datetime, timedelta, timezone
        before = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        n = 0
        for m in self.store.meetings_with_old_audio(before):
            (self.audio_dir / m["audio_path"]).unlink(missing_ok=True)
            self.store.update_meeting(m["id"], audio_path="")
            self.store.log("audio_purged", m["id"], f"保存期間（{days}日）を過ぎたので録音ファイルを削除")
            n += 1
        return n

    def _loop(self) -> None:
        import time
        last_purge = 0.0
        while True:
            if time.time() - last_purge > 3600:  # 1時間に1回、古い録音を消す
                try:
                    self.purge_old_audio()
                except Exception:
                    log.exception("録音の自動削除に失敗しました")
                last_purge = time.time()
            try:
                mid = self.q.get(timeout=600)
            except queue.Empty:
                continue
            try:
                self.process(mid)
            finally:
                with self._lock:
                    self._pending.discard(mid)
                self.progress.pop(mid, None)

    def drain(self) -> None:
        """テスト用: キューを今のスレッドで空にする。"""
        while not self.q.empty():
            mid = self.q.get()
            try:
                self.process(mid)
            finally:
                with self._lock:
                    self._pending.discard(mid)

    # ── 1件の処理 ────────────────────────────────────────

    def process(self, mid: str) -> None:
        m = self.store.get_meeting(mid)
        if not m:
            return
        settings = self.store.settings()
        try:
            if not m["transcript"]:
                if not m["audio_path"]:
                    raise ai.AIError("音声も文字起こしもありません。")
                self.store.update_meeting(mid, status="transcribing", error="")
                path = self.audio_dir / m["audio_path"]
                if not path.exists():
                    raise ai.AIError("録音ファイルが見つかりません（削除・移動された可能性があります）。")
                segs, total = self.transcriber(
                    str(path),
                    model_size=settings.get("whisper_model") or "small",
                    language=m.get("language") or settings.get("language") or "ja",
                    progress=lambda done, total: self.progress.__setitem__(mid, (done, total)),
                    vocabulary=ai.vocabulary(settings),
                    quiet=settings.get("quiet_mode") == "1",
                )
                if not segs:
                    raise ai.AIError("音声から言葉を聞き取れませんでした（無音・音量が小さい可能性があります）。")
                fields = {"transcript": segs}
                if total and not m.get("duration_sec"):
                    fields["duration_sec"] = round(total, 1)
                self.store.update_meeting(mid, **fields)
                m = self.store.get_meeting(mid)
            self.store.update_meeting(mid, status="summarizing", error="")
            meter = ai.Meter(self.store, settings, mid, "notes")
            notes = ai.generate_notes(m, settings, client=self.ai_client, meter=meter)
            self.store.log("ai_notes", mid, f"ノート作成のため文字起こし（{len(m['transcript'])}行）を Claude に送信")
            actions = notes.pop("action_items", [])
            fields = {"notes": notes, "notes_model": settings.get("model", ""), "status": "done", "error": ""}
            if not m["title"].strip() and notes.get("title"):
                fields["title"] = notes["title"][:60]
            self.store.replace_ai_actions(mid, actions)
            self.store.update_meeting(mid, **fields)
        except (ai.AIError, transcribe.TranscriptionUnavailable) as e:
            self.store.update_meeting(mid, status="failed", error=str(e))
            self.store.log("failed", mid, str(e))
        except Exception as e:  # 想定外のエラーも画面に理由を出す
            log.exception("処理に失敗しました: %s", mid)
            self.store.update_meeting(mid, status="failed", error=f"予期しないエラー: {type(e).__name__}: {e}")
            self.store.log("failed", mid, f"{type(e).__name__}: {e}")
