"""完成動画の機械チェック + 目視レビュー用のコマ一覧を作る。

使い方:
    python3 qc.py work/<id>/out/final.mp4          # 合格なら終了コード 0、不合格なら 1

出力（動画と同じフォルダの qc/）:
    report.json   … 各チェックの結果
    contact.jpg   … 0.5秒ごとのコマを並べた一覧（AI が見て破綻・読みにくさを採点する用）
    hook_*.jpg    … 冒頭 0 / 1 / 2 秒のコマ（つかみの確認用）

チェック内容:
    - 解像度 1080x1920・縦型 / 尺 9〜60秒 / 30fps / 音声あり
    - 真っ黒なコマが 0.3 秒以上続いていないか
    - 映像が 1 秒以上止まっていないか（AI 動画でよくある固まり）
    - 音量が -14 LUFS ±2 / ピークが -1 dBTP 以下
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def check(path, min_sec=9.0, max_sec=60.0):
    path = Path(path)
    qc_dir = path.parent / "qc"
    qc_dir.mkdir(exist_ok=True)
    results = []

    def add(name, ok, detail):
        results.append({"check": name, "ok": bool(ok), "detail": detail})

    info = json.loads(sh(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate",
                          "-of", "json", str(path)]).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    dur = float(info["format"]["duration"])
    num, den = v["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    add("resolution", (v["width"], v["height"]) == (1080, 1920), f"{v['width']}x{v['height']}")
    add("duration", min_sec <= dur <= max_sec, f"{dur:.2f}s（{min_sec:g}〜{max_sec:g}s）")
    add("fps", abs(fps - 30) < 0.5, f"{fps:.2f}")
    add("audio", any(s["codec_type"] == "audio" for s in info["streams"]), "音声トラック")

    err = sh(["ffmpeg", "-v", "info", "-i", str(path), "-vf",
              "blackdetect=d=0.3:pix_th=0.08,freezedetect=n=0.002:d=1.0",
              "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
    add("black_frames", not blacks, [f"{float(a):.1f}-{float(b):.1f}s" for a, b in blacks] or "なし")
    freezes = re.findall(r"freeze_start: ([\d.]+)", err)
    add("frozen_video", not freezes, [f"{float(a):.1f}s〜" for a in freezes] or "なし")
    m_i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    m_p = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", err)
    lufs = float(m_i[-1]) if m_i else None
    peak = float(m_p[-1]) if m_p and m_p[-1] != "-inf" else None
    add("loudness", lufs is not None and -16 <= lufs <= -12, f"{lufs} LUFS（目標 -14）")
    add("true_peak", peak is not None and peak <= -1.0, f"{peak} dBTP（-1.0 以下）")

    sh(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vf",
        "fps=2,scale=216:384,tile=8x4:padding=4:color=white", "-frames:v", "1", str(qc_dir / "contact.jpg")])
    for sec in (0, 1, 2):
        sh(["ffmpeg", "-y", "-v", "error", "-ss", str(sec), "-i", str(path), "-frames:v", "1",
            "-q:v", "3", str(qc_dir / f"hook_{sec}s.jpg")])

    passed = all(r["ok"] for r in results)
    report = {"file": str(path), "passed": passed, "checks": results}
    (qc_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--min", type=float, default=9.0)
    ap.add_argument("--max", type=float, default=60.0)
    a = ap.parse_args()
    rep = check(a.video, a.min, a.max)
    for r in rep["checks"]:
        print(("OK  " if r["ok"] else "NG  ") + f"{r['check']}: {r['detail']}")
    print("PASSED" if rep["passed"] else "FAILED")
    sys.exit(0 if rep["passed"] else 1)
