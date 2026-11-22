"""書き出し: カットの絵（または動画）にカメラの動きと字幕を付け、声と BGM を重ねて 1本の mp4 にする（ffmpeg）。

声は Mac の `say`（無料・端末内）。`say` が無い PC では声なしで書き出す（字幕は出る）。
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from . import art

FPS = 30
SHOT_TIMEOUT = 120


class RenderError(RuntimeError):
    pass


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # noqa: BLE001
        raise RenderError("ffmpeg が見つかりません。README の「準備」を見てください。") from e


def _run(args: list[str], timeout: float = SHOT_TIMEOUT) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RenderError("ffmpeg が時間内に終わりませんでした。") from e
    if p.returncode != 0:
        raise RenderError("ffmpeg でエラー: " + (p.stderr or "").strip()[-600:])
    return p


def media_duration(path: Path) -> float | None:
    """ffmpeg の出力から長さ（秒）を読む。"""
    try:
        p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, RenderError):
        return None
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", p.stderr or "")
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


# ── 声（Mac の say） ─────────────────────────────────────────

def say_available() -> bool:
    return shutil.which("say") is not None


def say_voices() -> list[str]:
    if not say_available():
        return []
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=10).stdout
    except (subprocess.TimeoutExpired, OSError):
        return []
    voices = []
    for line in out.splitlines():
        m = re.match(r"^(.+?)\s{2,}(\S+)\s+#", line)
        if m and m.group(2).startswith("ja"):
            voices.append(m.group(1).strip())
    return voices


def make_voice(text: str, voice: str, dest: Path, rate: int = 0) -> Path | None:
    """セリフを読み上げて wav にする。say が無ければ None。rate は1分あたりの語数（0 = ふつう）。"""
    if not text.strip() or not say_available():
        return None
    aiff = dest.with_suffix(".aiff")
    args = ["say", "-o", str(aiff)]
    if voice:
        args[1:1] = ["-v", voice]
    if rate:
        args[1:1] = ["-r", str(max(80, min(400, int(rate))))]
    try:
        subprocess.run([*args, text], check=True, capture_output=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        # 指定した声が無いときは既定の声でもう一度
        try:
            subprocess.run(["say", "-o", str(aiff), text], check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return None
    _run(["-i", str(aiff), "-ar", "44100", "-ac", "2", str(dest)])
    aiff.unlink(missing_ok=True)
    return dest


# ── 1カット ─────────────────────────────────────────────────

def _zoompan(camera: str, frames: int, w: int, h: int) -> str:
    n = max(1, frames - 1)
    center = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    expr = {
        "zoom_in": f"z='1+0.15*on/{n}':{center}",
        "zoom_out": f"z='1.15-0.15*on/{n}':{center}",
        "pan_right": f"z='1.15':x='(iw-iw/zoom)*on/{n}':y='ih/2-(ih/zoom/2)'",
        "pan_left": f"z='1.15':x='(iw-iw/zoom)*(1-on/{n})':y='ih/2-(ih/zoom/2)'",
    }.get(camera)
    if not expr:
        return f"scale={w}:{h},setsar=1"
    # 2倍に広げてから動かす（小数の位置でガタつかないように）
    return f"scale={w * 2}:{h * 2},zoompan={expr}:d={frames}:s={w}x{h}:fps={FPS},setsar=1"


def render_shot(shot: dict, size: tuple[int, int], work: Path, *, still: Path | None, video: Path | None,
                subtitle: Path | None) -> Path:
    w, h = size
    sec = float(shot["seconds"])
    frames = max(1, round(sec * FPS))
    out = work / f"shot_{shot['sort']:03d}.mp4"
    if video and video.exists():
        inputs = ["-stream_loop", "-1", "-i", str(video)]
        base = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},setsar=1[b]")
    elif still and still.exists():
        inputs = ["-loop", "1", "-framerate", str(FPS), "-i", str(still)]
        base = f"[0:v]{_zoompan(shot.get('camera', 'still'), frames, w, h)}[b]"
    else:
        raise RenderError(f"カット{shot['sort'] + 1}の絵がありません。")
    if subtitle and subtitle.exists():
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(subtitle)]
        graph = f"{base};[b][1:v]overlay=0:0:format=auto,format=yuv420p[v]"
    else:
        graph = f"{base};[b]format=yuv420p[v]"
    _run([*inputs, "-filter_complex", graph, "-map", "[v]", "-frames:v", str(frames), "-r", str(FPS),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(out)])
    return out


# ── 全体 ────────────────────────────────────────────────────

def render_project(shots: list[dict], size: tuple[int, int], work: Path, dest: Path, *,
                   stills: dict, videos: dict, voices: dict, bgm: Path | None, bgm_volume: float,
                   subtitles: bool, progress=None) -> list[str]:
    """全部のカットを書き出して dest に 1本の mp4 を作る。注意（警告）の一覧を返す。"""
    if not shots:
        raise RenderError("カットがありません。")
    work.mkdir(parents=True, exist_ok=True)
    warns: list[str] = []
    clips = []
    for i, s in enumerate(shots):
        sub = None
        if subtitles and (s.get("dialogue") or s.get("caption")):
            sub = work / f"sub_{s['sort']:03d}.png"
            spk = s.get("speaker", "") if s.get("speaker") not in ("", "ナレーション") else ""
            art.subtitle_png(size, s.get("dialogue", ""), speaker=spk, caption=s.get("caption", "")).save(sub)
        clips.append(render_shot(s, size, work, still=stills.get(s["id"]), video=videos.get(s["id"]), subtitle=sub))
        if progress:
            progress(i + 1, len(shots))
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    silent = work / "video.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)], timeout=300)

    total = sum(float(s["seconds"]) for s in shots)
    inputs, parts = ["-i", str(silent)], []
    t = 0.0
    idx = 1
    for s in shots:
        v = voices.get(s["id"])
        if v and v.exists():
            d = media_duration(v) or 0
            if d > float(s["seconds"]) + 0.3:
                warns.append(f"カット{s['sort'] + 1}: 声（{d:.1f}秒）がカット（{s['seconds']}秒）より長いので、次のカットにかかります")
            inputs += ["-i", str(v)]
            ms = int((t + 0.15) * 1000)
            parts.append(f"[{idx}:a]aresample=44100,adelay={ms}|{ms}[a{idx}]")
            idx += 1
        t += float(s["seconds"])
    labels = [f"[a{i}]" for i in range(1, idx)]
    if bgm and bgm.exists():
        inputs += ["-stream_loop", "-1", "-i", str(bgm)]
        vol = max(0.0, min(1.0, float(bgm_volume)))
        parts.append(f"[{idx}:a]aresample=44100,volume={vol:.2f},afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5[bg]")
        labels.append("[bg]")
        idx += 1
    if labels:
        mix = f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[mix]" if len(labels) > 1 else f"{labels[0]}anull[mix]"
        graph = ";".join(parts + [mix, f"[mix]atrim=0:{total:.3f},apad=whole_dur={total:.3f}[aout]"])
        _run([*inputs, "-filter_complex", graph, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
              "-t", f"{total:.3f}", "-movflags", "+faststart", str(dest)], timeout=300)
    else:
        # 音が何もないときも、無音の音声トラックを付けておく（SNS に上げるとき困らないように）
        _run(["-i", str(silent), "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(dest)], timeout=300)
    return warns


def poster(video: Path, dest: Path) -> Path | None:
    try:
        _run(["-ss", "0.5", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(dest)], timeout=30)
        return dest
    except RenderError:
        return None
