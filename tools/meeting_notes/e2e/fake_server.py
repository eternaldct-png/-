"""E2E テスト用のサーバー。本物の Claude と Whisper の代わりに決まった答えを返す（お金がかからない・速い）。

    python3 tools/meeting_notes/e2e/fake_server.py --port 5099 --data /tmp/mn-e2e
"""
import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.meeting_notes.app import create_app  # noqa: E402


class FakeClaude:
    def __init__(self):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        time.sleep(0.3)
        user = kw["messages"][0]["content"]
        if "format" in kw["output_config"]:
            if "FAIL_AI" in user:
                return SimpleNamespace(stop_reason="refusal", content=[])
            owner = "山田" if "山田" in user else ""
            text = json.dumps({
                "title": "テスト会議のノート",
                "summary": "会場を渋谷に決め、見積もりを金曜までに送ることになった。",
                "sections": [{"heading": "会場", "bullets": ["渋谷の会場で決定", "定員は50人"]},
                             {"heading": "予算", "bullets": ["上限30万円"]}],
                "decisions": ["12月5日に開催する"],
                "action_items": [{"text": "見積もりを送る", "owner": owner, "due": "金曜"},
                                 {"text": "告知文を書く", "owner": "", "due": ""}],
            }, ensure_ascii=False)
        else:
            text = "記録では、会場は渋谷です。[00:05]"
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def fake_transcriber(path, *, model_size="small", language="ja", progress=None):
    for i in range(3):
        time.sleep(0.3)
        if progress:
            progress(i * 10.0, 30.0)
    return [{"speaker": "", "start": 0.0, "end": 4.0, "text": "会場は渋谷にしましょう。"},
            {"speaker": "", "start": 5.0, "end": 9.0, "text": "見積もりは金曜までに送ります。"}], 30.0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=5099)
    p.add_argument("--data", required=True)
    a = p.parse_args()
    app = create_app(a.data, transcriber=fake_transcriber, ai_client=FakeClaude())
    app.run(host="127.0.0.1", port=a.port, threaded=True)
