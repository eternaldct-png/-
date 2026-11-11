"""動作チェック（不満: サポートに人がいない・困ったときに聞く相手がいない）。

自分専用アプリなので「問い合わせ先」の代わりに、よくある原因をアプリ自身が調べて、直し方まで出す。
AI を呼ぶチェックはしない（お金がかからない）。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import transcribe


def _whisper_model_cached(size: str) -> bool:
    """faster-whisper のモデルがダウンロード済みか（Hugging Face のキャッシュを見る）。"""
    hub = Path(os.environ.get("HF_HUB_CACHE") or os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    if hub.name != "hub":
        hub = hub / "hub"
    repo = {"turbo": "mobiuslabsgmbh--faster-whisper-large-v3-turbo"}.get(size, f"Systran--faster-whisper-{size}")
    snap = hub / f"models--{repo}" / "snapshots"
    return snap.exists() and any(snap.iterdir())


def run_checks(data_dir: Path, store, worker, testing: bool = False) -> list[dict]:
    """[{name, ok: True/False/None(注意), detail, fix}] を返す。"""
    settings = store.settings()
    out = []

    def add(name, ok, detail, fix=""):
        out.append({"name": name, "ok": ok, "detail": detail, "fix": fix})

    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if key or testing:
        add("Claude の APIキー", True, "設定されています" + (f"（…{key[-4:]}）" if key else ""))
    else:
        add("Claude の APIキー", False, "設定されていません。ノート作成とAIへの質問が動きません。",
            "~/MeetingNotes/.env に ANTHROPIC_API_KEY=… を書いて、アプリを起動し直す（README「準備」）")

    py = sys.version_info
    add("Python", py >= (3, 10), f"{py.major}.{py.minor}.{py.micro}",
        "" if py >= (3, 10) else "python.org から 3.10 以上を入れて、start.command を起動し直す")

    if transcribe.whisper_available() or testing:
        add("文字起こし（faster-whisper）", True, "インストール済み")
        size = settings.get("whisper_model") or "small"
        if testing:
            pass
        elif _whisper_model_cached(size):
            add(f"Whisper のモデル（{size}）", True, "ダウンロード済み")
        else:
            add(f"Whisper のモデル（{size}）", None, "まだダウンロードされていません。最初の文字起こしのときに自動でダウンロードします（small で約500MB）。",
                "インターネットにつながった状態で最初の録音を処理する")
    else:
        add("文字起こし（faster-whisper）", False, "インストールされていません。録音は保存されますが、文字にできません。",
            "ターミナルで tools/meeting_notes/.venv/bin/pip install faster-whisper → 起動し直す → 会議の画面で「やり直す」")

    try:
        free = shutil.disk_usage(data_dir).free
        gb = free / 1024 ** 3
        add("空き容量", gb >= 2, f"{gb:.1f} GB", "" if gb >= 2 else "1時間の録音で約30MB。不要なファイルを消すか、「設定」で録音の保存期間を決める")
    except OSError as e:
        add("空き容量", None, f"調べられませんでした（{e}）")

    try:
        probe = Path(data_dir) / ".write-test"
        probe.write_text("ok")
        probe.unlink()
        add("保存先に書き込めるか", True, str(data_dir))
    except OSError as e:
        add("保存先に書き込めるか", False, f"{data_dir}（{e}）", "フォルダの権限を確かめるか、--data で別の場所を指定する")

    try:
        with store.conn() as c:
            res = c.execute("PRAGMA quick_check").fetchone()[0]
        add("データベース", res == "ok", "正常" if res == "ok" else res,
            "" if res == "ok" else "「設定」の JSON 書き出しでバックアップを取ってから、~/MeetingNotes/meeting_notes.db を調べる")
    except Exception as e:  # noqa: BLE001
        add("データベース", False, str(e))

    failed = [m for m in store.list_meetings() if m["status"] == "failed"]
    if failed:
        add("失敗した会議", None, f"{len(failed)}件あります（最新: {failed[0]['error'][:80]}）",
            "会議の画面で理由を読み、「やり直す」を押す")
    else:
        add("失敗した会議", True, "ありません")

    pending = worker.q.qsize()
    add("処理待ち", True, f"{pending}件" if pending else "ありません")
    return out
