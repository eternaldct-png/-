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

    def _loop(self) -> None:
        while True:
            mid = self.q.get()
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
                )
                if not segs:
                    raise ai.AIError("音声から言葉を聞き取れませんでした（無音・音量が小さい可能性があります）。")
                fields = {"transcript": segs}
                if total and not m.get("duration_sec"):
                    fields["duration_sec"] = round(total, 1)
                self.store.update_meeting(mid, **fields)
                m = self.store.get_meeting(mid)
            self.store.update_meeting(mid, status="summarizing", error="")
            notes = ai.generate_notes(m, settings, client=self.ai_client)
            actions = notes.pop("action_items", [])
            fields = {"notes": notes, "notes_model": settings.get("model", ""), "status": "done", "error": ""}
            if not m["title"].strip() and notes.get("title"):
                fields["title"] = notes["title"][:60]
            self.store.replace_ai_actions(mid, actions)
            self.store.update_meeting(mid, **fields)
        except (ai.AIError, transcribe.TranscriptionUnavailable) as e:
            self.store.update_meeting(mid, status="failed", error=str(e))
        except Exception as e:  # 想定外のエラーも画面に理由を出す
            log.exception("処理に失敗しました: %s", mid)
            self.store.update_meeting(mid, status="failed", error=f"予期しないエラー: {type(e).__name__}: {e}")
