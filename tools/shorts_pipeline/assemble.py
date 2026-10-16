"""plan.yaml のカットをつないで、縦型ショート（1080x1920・30fps）の完成版を ffmpeg で作る。

使い方:
    python3 assemble.py work/<id>/plan.yaml

出力（work/<id>/out/）:
    final.mp4        … テロップ焼き込み・BGM・音量調整済み（このまま投稿できる版）
    segments/NN.mp4  … カットごとに切り出し・縦型に整えた素材（CapCut に読み込む用。テロップなし）
    captions.srt     … テロップ（CapCut の「字幕をインポート」で読み込める）
    captions.ass     … 焼き込みに使った字幕

テロップは TikTok / リール / ショートの UI（右側のボタン列・下部の説明文）に隠れない位置に置く。
フォントは tools/motion_render/fonts/（fetch_fonts.py で取得）の Noto Sans JP を使う。
Mac で別のフォントにしたいときは SHORTS_FONT="Hiragino Sans" のように指定する。
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

W, H, FPS = 1080, 1920, 30
HERE = Path(__file__).resolve().parent
FONT_DIR = HERE.parent / "motion_render" / "fonts"
FONT = os.environ.get("SHORTS_FONT", "Noto Sans JP")
HOOK_SECONDS = 2.2


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg 失敗: {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p


def probe(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", str(path)])
    info = json.loads(p.stdout)
    return float(info["format"]["duration"]), any(s["codec_type"] == "audio" for s in info["streams"])


def make_segment(src, dst, trim, keep_audio):
    """1カットを縦型 1080x1920・30fps・ステレオ音声つきに揃える（音が無ければ無音を足す）。"""
    src_dur, has_audio = probe(src)
    length = (min(trim[1], src_dur) - trim[0]) if trim else src_dur
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if trim:
        cmd += ["-ss", str(trim[0]), "-to", str(trim[1])]
    cmd += ["-i", str(src), "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"fps={FPS},setsar=1,format=yuv420p")
    audio = "0:a" if (keep_audio and has_audio) else "1:a"
    cmd += ["-filter_complex", f"[0:v]{vf}[v];[{audio}]aresample=48000,aformat=channel_layouts=stereo[a]",
            # 無音トラックは終わりが無いので、-shortest ではなく長さを明示して止める
            "-map", "[v]", "-map", "[a]", "-t", f"{length:.3f}",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", str(dst)]
    run(cmd)
    return probe(dst)[0]


def ts_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ts_ass(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_text(s):
    return s.strip().replace("{", "(").replace("}", ")").replace("\n", r"\N")


def write_captions(plan, timings, out_dir):
    """timings: [(start, end, caption)]。フックは冒頭 HOOK_SECONDS 秒、上寄せで大きく出す。"""
    srt, events = [], []
    hook = (plan.get("hook") or "").strip()
    if hook:
        events.append(f"Dialogue: 0,{ts_ass(0)},{ts_ass(HOOK_SECONDS)},Hook,,0,0,0,,{ass_text(hook)}")
    n = 0
    for start, end, cap in timings:
        if not cap or not cap.strip():
            continue
        # フックと重ならないように、最初のテロップはフックの後から出す
        s = max(start, HOOK_SECONDS) if hook and start < HOOK_SECONDS else start
        if s >= end - 0.3:
            continue
        n += 1
        srt.append(f"{n}\n{ts_srt(s)} --> {ts_srt(end)}\n{cap.strip()}\n")
        events.append(f"Dialogue: 0,{ts_ass(s)},{ts_ass(end)},Cap,,0,0,0,,{ass_text(cap)}")
    # 安全エリア: 右側 160px（いいね等のボタン列）、下 560px（説明文・音源表示）を避ける
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,{FONT},92,&H0000F0FF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,7,3,8,90,160,300,1
Style: Cap,{FONT},70,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,1,0,1,6,2,2,90,160,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"
    (out_dir / "captions.ass").write_text(ass, encoding="utf-8")
    (out_dir / "captions.srt").write_text("\n".join(srt), encoding="utf-8")


def assemble(plan_path):
    plan_path = Path(plan_path)
    base = plan_path.parent
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    out_dir = base / "out"
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    for old in seg_dir.glob("*.mp4"):
        old.unlink()

    keep_audio = plan.get("keep_clip_audio", True)
    timings, segs, t = [], [], 0.0
    for i, shot in enumerate(plan["shots"], 1):
        src = base / shot["video"]
        if not src.exists():
            sys.exit(f"{shot['id']}: 動画 {shot['video']} が無い（先に grok_video.py）")
        dst = seg_dir / f"{i:02d}_{shot['id']}.mp4"
        dur = make_segment(src, dst, shot.get("trim"), keep_audio)
        timings.append((t, t + dur, shot.get("caption", "")))
        segs.append(dst)
        t += dur
        print(f"segment {dst.name}: {dur:.2f}s")

    concat_list = out_dir / "concat.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
    joined = out_dir / "joined.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(joined)])

    write_captions(plan, timings, out_dir)
    ass = str((out_dir / "captions.ass").resolve()).replace("\\", "/").replace(":", r"\:")
    sub = f"subtitles=filename='{ass}'"
    if FONT_DIR.exists():
        sub += f":fontsdir='{FONT_DIR.as_posix()}'"

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(joined)]
    bgm = (plan.get("bgm") or "").strip()
    # 仕上げの音量はショート動画の目安 -14 LUFS / ピーク -1.5dB
    loud = "loudnorm=I=-14:TP=-1.5:LRA=11"
    if bgm:
        bgm_path = (base / bgm) if not Path(bgm).is_absolute() else Path(bgm)
        if not bgm_path.exists():
            bgm_path = HERE.parent.parent / bgm
        if not bgm_path.exists():
            sys.exit(f"BGM が無い: {bgm}")
        vol = plan.get("bgm_volume", 0.35) if keep_audio else 1.0
        fade_at = max(t - 1.0, 0)
        cmd += ["-stream_loop", "-1", "-i", str(bgm_path), "-filter_complex",
                f"[0:v]{sub}[v];[1:a]volume={vol},afade=t=out:st={fade_at}:d=1[b];"
                f"[0:a][b]amix=inputs=2:duration=first:normalize=0,{loud}[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", sub, "-af", loud]
    final = out_dir / "final.mp4"
    cmd += ["-t", f"{t:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "20", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(final)]
    run(cmd)
    joined.unlink()
    concat_list.unlink()
    print(f"final: {final} ({t:.2f}s)")
    return final


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    assemble(ap.parse_args().plan)
