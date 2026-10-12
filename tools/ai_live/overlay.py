"""配信画面（キャラ・字幕・ギフト演出）を出す小さなWebサーバー。

ブラウザで http://127.0.0.1:8765/ を開き、そのウィンドウを TikTok LIVE Studio の
「ウィンドウキャプチャ」で取り込む（または OBS のブラウザソースに URL を貼る）。
"""

from __future__ import annotations

import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


class OverlayState:
    def __init__(self, character_name: str, image_path: Path | None):
        self._lock = threading.Lock()
        self.character_name = character_name
        self.image_path = image_path
        self.subtitle = ""
        self.speaker_to = ""
        self.speaking = False
        self.effects: list[dict] = []
        self._effect_id = 0

    def say(self, text: str, to: str = "") -> None:
        with self._lock:
            self.subtitle, self.speaker_to, self.speaking = text, to, True

    def done(self) -> None:
        with self._lock:
            self.speaking = False

    def effect(self, name: str, label: str) -> None:
        with self._lock:
            self._effect_id += 1
            self.effects.append({"id": self._effect_id, "name": name, "label": label, "t": time.time()})
            self.effects = [e for e in self.effects if time.time() - e["t"] < 10]

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "name": self.character_name,
                "subtitle": self.subtitle,
                "to": self.speaker_to,
                "speaking": self.speaking,
                "effects": list(self.effects),
            }


def start_overlay(state: OverlayState, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.startswith("/state"):
                self._send(json.dumps(state.snapshot(), ensure_ascii=False).encode(), "application/json")
            elif self.path == "/character" and state.image_path and state.image_path.exists():
                ctype = mimetypes.guess_type(state.image_path.name)[0] or "image/png"
                self._send(state.image_path.read_bytes(), ctype)
            elif self.path in ("/", "/index.html"):
                self._send((HERE / "overlay.html").read_bytes(), "text/html; charset=utf-8")
            else:
                self.send_error(404)

        def _send(self, body: bytes, ctype: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # アクセスログは出さない
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
