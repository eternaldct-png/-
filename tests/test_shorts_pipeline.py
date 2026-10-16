"""tools/shorts_pipeline の編集（assemble.py）と検証（qc.py）を、ダミー動画で通しで確かめる。"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "shorts_pipeline"))

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg が無い")


def _clip(path, seconds, audio=True):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s=720x1280:r=24:d={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=f=440:d={seconds}", "-shortest", "-c:a", "aac"]
    subprocess.run(cmd + ["-c:v", "libx264", str(path)], check=True)


def test_assemble_and_qc(tmp_path):
    import assemble
    import qc

    (tmp_path / "clips").mkdir()
    _clip(tmp_path / "clips" / "s1.mp4", 5)
    _clip(tmp_path / "clips" / "s2.mp4", 6, audio=False)  # 音の無いクリップにも無音が足される
    plan = {
        "id": "t", "hook": "最後まで見て", "keep_clip_audio": True, "bgm": "",
        "shots": [
            {"id": "s1", "video": "clips/s1.mp4", "caption": "一言目"},
            {"id": "s2", "video": "clips/s2.mp4", "trim": [0.5, 5.5], "caption": "二言目"},
        ],
    }
    (tmp_path / "plan.yaml").write_text(yaml.safe_dump(plan, allow_unicode=True), encoding="utf-8")

    final = assemble.assemble(tmp_path / "plan.yaml")
    assert final.exists()
    assert len(list((tmp_path / "out" / "segments").glob("*.mp4"))) == 2
    srt = (tmp_path / "out" / "captions.srt").read_text(encoding="utf-8")
    # 最初のテロップはフック（2.2秒）の後から出る
    assert "00:00:02,200 --> 00:00:05,000\n一言目" in srt
    assert "二言目" in srt

    report = qc.check(final)
    checks = {c["check"]: c for c in report["checks"]}
    assert checks["resolution"]["ok"]
    assert checks["fps"]["ok"]
    assert checks["audio"]["ok"]
    assert abs(float(checks["duration"]["detail"].split("s")[0]) - 10.0) < 0.2
    assert (tmp_path / "out" / "qc" / "contact.jpg").exists()


def test_qc_rejects_landscape_and_short(tmp_path):
    import qc

    path = tmp_path / "wide.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=3",
                    "-c:v", "libx264", str(path)], check=True)
    report = qc.check(path)
    failed = {c["check"] for c in report["checks"] if not c["ok"]}
    assert not report["passed"]
    assert {"resolution", "duration", "audio"} <= failed


def test_grok_payload_is_vertical_and_embeds_image(tmp_path):
    import grok_video

    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "s1.png").write_bytes(b"\x89PNG fake")
    shot = {"id": "s1", "image": "images/s1.png", "video_prompt": " slow push in ", "duration": 7}
    p = grok_video.build_payload(shot, tmp_path)
    assert p["aspect_ratio"] == "9:16"
    assert p["duration"] == 7
    assert p["prompt"] == "slow push in"
    assert p["image"]["url"].startswith("data:image/png;base64,")
    assert grok_video.find_video_url({"status": "done", "video": {"url": "https://x/v.mp4"}}) == "https://x/v.mp4"
    assert grok_video.find_video_url({"status": "pending"}) is None
