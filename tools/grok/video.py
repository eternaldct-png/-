#!/usr/bin/env python3
"""
Grok で動画を作る — 数秒〜15秒のクリップを何本も生成し、ffmpeg でつないで 1〜2分の動画にする

使い方:
  # 1) テーマから絵コンテ（シーン割り）を作る
  python tools/grok/video.py plan "ライバー募集の1分PR動画" --seconds 60 --aspect 9:16 \\
      -o tools/grok/storyboards/recruit.yaml
  # 2) 絵コンテを確認・修正してから、クリップ生成 → 結合（API代がかかる。先に見積もりを表示）
  python tools/grok/video.py render tools/grok/storyboards/recruit.yaml
  python tools/grok/video.py render tools/grok/storyboards/recruit.yaml --dry-run   # 見積もりだけ
  # 3) BGM・つなぎ方だけ変えて結合し直す（API代はかからない）
  python tools/grok/video.py stitch tools/grok/storyboards/recruit.yaml

生成したクリップと状態は posts/videos/<絵コンテ名>/ に保存する。途中で止まっても、もう一度 render すれば
できているクリップは作り直さない（プロンプト等を変えたシーンだけ作り直す）。
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import grok_client  # noqa: E402
from grok_client import GrokError  # noqa: E402

ASPECTS = ("16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3")
RESOLUTIONS = ("480p", "720p", "1080p")
TRANSITIONS = ("fade", "none")
AUDIO_MODES = ("keep", "mute")
MAX_SCENES = 30
FPS = 24
# 料金の目安（USD/秒）。実際の単価は https://console.x.ai で確認し、違えば --price-per-sec で上書きする
DEFAULT_PRICE_PER_SEC = float(os.environ.get("GROK_VIDEO_PRICE_PER_SEC", "0.08"))
USD_JPY = 150
WORK_ROOT = ROOT / "posts" / "videos"

# YAML で "9:16" を "" で囲み忘れると 60進数の整数（556）になるので戻す
_SEXAGESIMAL = {int(a) * 60 + int(b): f"{a}:{b}" for a, b in (r.split(":") for r in ASPECTS)}


class StoryboardError(ValueError):
    pass


# ── 絵コンテ（YAML） ─────────────────────────────────────────

def _resolve_path(value, base: Path) -> Path:
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    for cand in (base / path, Path.cwd() / path, ROOT / path):
        if cand.exists():
            return cand
    return base / path


def load_storyboard(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise StoryboardError(f"絵コンテが見つかりません: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base = path.parent

    aspect = data.get("aspect_ratio", "16:9")
    if isinstance(aspect, int):
        aspect = _SEXAGESIMAL.get(aspect, aspect)
    aspect = str(aspect)
    if aspect not in ASPECTS:
        raise StoryboardError(f"aspect_ratio は {', '.join(ASPECTS)} のどれか（\"\" で囲む）: {aspect}")

    resolution = str(data.get("resolution", "720p"))
    if resolution not in RESOLUTIONS:
        raise StoryboardError(f"resolution は {', '.join(RESOLUTIONS)} のどれか: {resolution}")

    transition = str(data.get("transition", "fade"))
    if transition not in TRANSITIONS:
        raise StoryboardError(f"transition は fade / none のどちらか: {transition}")

    audio = str(data.get("audio", "keep"))
    if audio not in AUDIO_MODES:
        raise StoryboardError(f"audio は keep（クリップの音を使う）/ mute（消す）のどちらか: {audio}")

    bgm = data.get("bgm")
    bgm_path = _resolve_path(bgm, base) if bgm else None
    if bgm_path and not bgm_path.exists():
        raise StoryboardError(f"BGM ファイルが見つかりません: {bgm}")

    raw_scenes = data.get("scenes") or []
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise StoryboardError("scenes にシーンを1つ以上書いてください")
    if len(raw_scenes) > MAX_SCENES:
        raise StoryboardError(f"シーンは最大 {MAX_SCENES} 個までです（{len(raw_scenes)} 個）")

    scenes = []
    for i, sc in enumerate(raw_scenes, start=1):
        if not isinstance(sc, dict) or not str(sc.get("prompt", "")).strip():
            raise StoryboardError(f"シーン{i}: prompt が空です")
        try:
            duration = int(sc.get("duration", 8))
        except (TypeError, ValueError):
            raise StoryboardError(f"シーン{i}: duration は秒数（整数）で書いてください")
        if not 1 <= duration <= 15:
            raise StoryboardError(f"シーン{i}: duration は 1〜15 秒です（{duration}）")
        image = _resolve_path(sc["image"], base) if sc.get("image") else None
        if image and not image.exists():
            raise StoryboardError(f"シーン{i}: image が見つかりません: {sc['image']}")
        refs = [_resolve_path(r, base) for r in (sc.get("references") or data.get("references") or [])]
        for r in refs:
            if not r.exists():
                raise StoryboardError(f"シーン{i}: references の画像が見つかりません: {r}")
        cont = bool(sc.get("continue", False)) and i > 1
        if image and cont:
            raise StoryboardError(f"シーン{i}: image と continue は同時に使えません")
        if refs and (image or cont):
            raise StoryboardError(f"シーン{i}: references は image / continue と同時に使えません")
        scenes.append({
            "prompt": str(sc["prompt"]).strip(),
            "duration": duration,
            "image": image,
            "references": refs,
            "continue": cont,
            "note": str(sc.get("note", "")).strip(),
        })

    try:
        transition_seconds = float(data.get("transition_seconds", 0.5))
        bgm_volume = float(data.get("bgm_volume", 0.3))
    except (TypeError, ValueError):
        raise StoryboardError("transition_seconds / bgm_volume は数字で書いてください")

    return {
        "name": path.stem,
        "title": str(data.get("title", path.stem)),
        "aspect_ratio": aspect,
        "resolution": resolution,
        "model": str(data.get("model", "")).strip() or None,
        "style": str(data.get("style", "")).strip(),
        "generate_audio": data.get("generate_audio"),
        "transition": transition,
        "transition_seconds": max(0.0, transition_seconds),
        "audio": audio,
        "bgm": bgm_path,
        "bgm_volume": max(0.0, bgm_volume),
        "scenes": scenes,
    }


def full_prompt(sb: dict, scene: dict) -> str:
    return f"{scene['prompt']}\n{sb['style']}" if sb["style"] else scene["prompt"]


def _file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def scene_hashes(sb: dict) -> list[str]:
    """シーンの中身が変わったかを判定するハッシュ（continue のシーンは前のシーンにも依存）"""
    hashes = []
    for scene in sb["scenes"]:
        key = {
            "prompt": full_prompt(sb, scene),
            "duration": scene["duration"],
            "aspect": sb["aspect_ratio"],
            "resolution": sb["resolution"],
            "model": sb["model"],
            "generate_audio": sb["generate_audio"],
            "image": _file_hash(scene["image"]) if scene["image"] else None,
            "references": [_file_hash(r) for r in scene["references"]],
            "continue_from": hashes[-1] if scene["continue"] and hashes else None,
        }
        hashes.append(hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16])
    return hashes


# ── ffmpeg ──────────────────────────────────────────────────

def _require_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(f"{tool} が見つかりません。ffmpeg をインストールしてください（Mac: brew install ffmpeg）")


def _run(cmd: list[str]):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg が失敗しました:\n{' '.join(cmd)}\n{res.stderr[-2000:]}")


def probe(path: Path) -> dict:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(f"動画を読み込めません: {path}\n{res.stderr[-500:]}")
    info = json.loads(res.stdout)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError(f"映像が入っていません: {path}")
    duration = float(video.get("duration") or info.get("format", {}).get("duration") or 0)
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "duration": duration,
        "has_audio": any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
    }


def extract_last_frame(clip: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-sseof", "-0.3", "-i", str(clip),
          "-update", "1", "-q:v", "2", str(out)])
    if not out.exists():
        raise RuntimeError(f"最後のコマを取り出せませんでした: {clip}")
    return out


def normalize_clip(clip: Path, out: Path, width: int, height: int) -> float:
    """サイズ・fps・音声形式をそろえる（音のないクリップには無音を入れる）。長さ（秒）を返す"""
    info = probe(clip)
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = (f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS},format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(clip)]
    if info["has_audio"]:
        af = "[0:a]aresample=48000,aformat=channel_layouts=stereo,apad[a]"
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        af = "[1:a]aformat=channel_layouts=stereo[a]"
    cmd += ["-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{info['duration']:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(out)]
    _run(cmd)
    return probe(out)["duration"]


def build_stitch_command(clips: list[Path], durations: list[float], out: Path, transition: str = "fade",
                         transition_seconds: float = 0.5, keep_audio: bool = True,
                         bgm: Path = None, bgm_volume: float = 0.3) -> tuple[list[str], float]:
    """そろえたクリップをつなぐ ffmpeg コマンドと、できあがりの長さ（秒）を返す"""
    n = len(clips)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]
    parts = []

    t = min(transition_seconds, min(durations) / 2) if n > 1 else 0
    if transition == "fade" and t > 0:
        v_label, a_label = "[0:v]", "[0:a]"
        offset = 0.0
        for k in range(1, n):
            offset += durations[k - 1] - t
            parts.append(f"{v_label}[{k}:v]xfade=transition=fade:duration={t:.3f}:offset={offset:.3f}[v{k}]")
            v_label = f"[v{k}]"
            if keep_audio:
                parts.append(f"{a_label}[{k}:a]acrossfade=d={t:.3f}[a{k}]")
                a_label = f"[a{k}]"
        total = sum(durations) - t * (n - 1)
    else:
        streams = "".join(f"[{k}:v][{k}:a]" if keep_audio else f"[{k}:v]" for k in range(n))
        parts.append(f"{streams}concat=n={n}:v=1:a={1 if keep_audio else 0}[vc]" + ("[ac]" if keep_audio else ""))
        v_label, a_label = "[vc]", "[ac]"
        total = sum(durations)
    if not keep_audio:
        a_label = None

    if bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm)]
        fade = min(2.0, total / 4)
        parts.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                     f"aformat=channel_layouts=stereo,volume={bgm_volume},"
                     f"afade=t=out:st={total - fade:.3f}:d={fade:.3f}[bgm]")
        if a_label:
            parts.append(f"{a_label}[bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]")
            a_label = "[aout]"
        else:
            a_label = "[bgm]"

    cmd += ["-filter_complex", ";".join(parts), "-map", v_label]
    if a_label:
        cmd += ["-map", a_label, "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)]
    return cmd, total


# ── 作業フォルダと状態 ────────────────────────────────────────

def _rel(path: Path) -> str:
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def work_dir_for(sb: dict) -> Path:
    return WORK_ROOT / sb["name"]


def clip_path(work: Path, i: int) -> Path:
    return work / "clips" / f"scene_{i + 1:02d}.mp4"


def load_state(work: Path) -> dict:
    path = work / "state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"scenes": {}}


def save_state(work: Path, state: dict):
    work.mkdir(parents=True, exist_ok=True)
    (work / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def scene_done(work: Path, state: dict, i: int, h: str) -> bool:
    entry = state["scenes"].get(str(i + 1), {})
    return entry.get("hash") == h and entry.get("done") and clip_path(work, i).exists()


# ── コマンド: render ─────────────────────────────────────────

def render(sb: dict, yes: bool = False, dry_run: bool = False, price_per_sec: float = DEFAULT_PRICE_PER_SEC,
           max_seconds: int = None, out: Path = None, poll_interval: float = 5) -> Path | None:
    work = work_dir_for(sb)
    state = load_state(work)
    hashes = scene_hashes(sb)
    scenes = sb["scenes"]

    todo = [i for i in range(len(scenes)) if not scene_done(work, state, i, hashes[i])]
    # 依頼済み（request_id あり・内容同じ）のシーンは追加料金なしで受け取れる
    paid = [i for i in todo if state["scenes"].get(str(i + 1), {}).get("hash") != hashes[i]
            or not state["scenes"].get(str(i + 1), {}).get("request_id")]
    gen_seconds = sum(scenes[i]["duration"] for i in paid)
    total_seconds = sum(s["duration"] for s in scenes)
    cost = gen_seconds * price_per_sec

    print(f"🎬 {sb['title']}（{len(scenes)}シーン・合計 約{total_seconds}秒・{sb['aspect_ratio']}・{sb['resolution']}）")
    for i, scene in enumerate(scenes):
        mark = "✅ 作成済み" if i not in todo else ("⏳ 依頼済み" if i not in paid else "🆕 生成する")
        how = " ← 前のシーンの続き" if scene["continue"] else (" ← 画像から" if scene["image"] else "")
        print(f"  {i + 1:2d}. {scene['duration']:2d}秒 {mark}{how}  {scene['note'] or scene['prompt'][:50]}")
    print(f"💰 新しく生成する映像: {gen_seconds}秒 × ${price_per_sec}/秒 ≈ ${cost:.2f}"
          f"（約{round(cost * USD_JPY):,}円・目安）")

    if dry_run:
        print("（--dry-run のため生成しません）")
        return None
    if max_seconds is not None and gen_seconds > max_seconds:
        raise SystemExit(f"生成する秒数（{gen_seconds}秒）が上限 --max-seconds {max_seconds} を超えています。中止しました")
    if gen_seconds and not yes:
        if not sys.stdin.isatty():
            raise SystemExit("API代がかかるため、確認なしで進めるには --yes を付けてください")
        if input("この内容で生成しますか？ [y/N] ").strip().lower() not in ("y", "yes"):
            raise SystemExit("中止しました")

    if todo:
        if not grok_client.is_configured():
            raise SystemExit("XAI_API_KEY が設定されていません（https://console.x.ai で発行）")
        _require_ffmpeg()

    def submit(i: int, image: str = None) -> str:
        entry = state["scenes"].get(str(i + 1), {})
        if entry.get("hash") == hashes[i] and entry.get("request_id"):
            return entry["request_id"]
        scene = scenes[i]
        extra = {"generate_audio": bool(sb["generate_audio"])} if sb["generate_audio"] is not None else None
        request_id = grok_client.submit_video(
            full_prompt(sb, scene),
            duration=scene["duration"],
            aspect_ratio=sb["aspect_ratio"],
            resolution=sb["resolution"],
            image=image or (grok_client.image_to_data_uri(scene["image"]) if scene["image"] else None),
            reference_images=[grok_client.image_to_data_uri(r) for r in scene["references"]] or None,
            model=sb["model"],
            extra=extra,
        )
        state["scenes"][str(i + 1)] = {"hash": hashes[i], "request_id": request_id, "done": False}
        save_state(work, state)
        print(f"  → シーン{i + 1} を依頼しました（request_id={request_id}）")
        return request_id

    # 前のシーンに依存しないものは先にまとめて依頼しておく（xAI側で並行して作られる）
    for i in todo:
        if not scenes[i]["continue"]:
            try:
                submit(i)
            except GrokError as e:
                print(f"  ⚠ シーン{i + 1} の依頼に失敗（順番が来たらもう一度試します）: {e}")

    for i in todo:
        image = None
        if scenes[i]["continue"]:
            frame = extract_last_frame(clip_path(work, i - 1), work / "frames" / f"scene_{i:02d}_last.jpg")
            image = grok_client.image_to_data_uri(frame)
        request_id = submit(i, image=image)
        print(f"  … シーン{i + 1} の完成を待っています")
        try:
            url = grok_client.wait_video(request_id, poll_interval=poll_interval)
        except GrokError as e:
            state["scenes"].pop(str(i + 1), None)
            save_state(work, state)
            raise SystemExit(f"シーン{i + 1} の生成に失敗しました: {e}\n"
                             "もう一度 render すると作り直します（ポリシーで止められた場合はプロンプトを直してください）")
        grok_client.download(url, clip_path(work, i))
        state["scenes"][str(i + 1)]["done"] = True
        save_state(work, state)
        print(f"  ✅ シーン{i + 1} 完成: {_rel(clip_path(work, i))}")

    return stitch(sb, out=out)


# ── コマンド: stitch ─────────────────────────────────────────

def stitch(sb: dict, out: Path = None) -> Path:
    _require_ffmpeg()
    work = work_dir_for(sb)
    clips = [clip_path(work, i) for i in range(len(sb["scenes"]))]
    missing = [str(i + 1) for i, c in enumerate(clips) if not c.exists()]
    if missing:
        raise SystemExit(f"シーン {', '.join(missing)} のクリップがありません。先に render を実行してください")

    first = probe(clips[0])
    width, height = first["width"] // 2 * 2, first["height"] // 2 * 2
    norm_dir = work / "normalized"
    durations = [normalize_clip(c, norm_dir / c.name, width, height) for c in clips]
    norm_clips = [norm_dir / c.name for c in clips]

    out = Path(out) if out else work / f"{sb['name']}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd, total = build_stitch_command(
        norm_clips, durations, out,
        transition=sb["transition"],
        transition_seconds=sb["transition_seconds"],
        keep_audio=sb["audio"] == "keep",
        bgm=sb["bgm"],
        bgm_volume=sb["bgm_volume"],
    )
    _run(cmd)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"🎉 完成: {_rel(out)}（{total:.1f}秒・{width}x{height}・{size_mb:.1f}MB）")
    return out


# ── コマンド: plan ───────────────────────────────────────────

PLAN_SYSTEM = """あなたはショート動画の映像ディレクターです。AI動画生成（1シーン最大15秒）で作る動画の絵コンテを書きます。
- 各シーンの prompt は英語で、被写体・動き・カメラワーク・光・雰囲気を具体的に書く
- 画面内に文字・ロゴ・字幕を入れない（テロップは後で編集で入れる）
- 実在の有名人・他社のキャラクター・ブランドを出さない
- 前のシーンから映像が自然につながる場面は "continue": true にする（前のシーンの最後のコマから続きを作る）
- 出力はJSONのみ（説明文・コードブロック不要）"""


def plan(theme: str, seconds: int, aspect: str, scene_seconds: int, out: Path) -> Path:
    from generate import call_llm

    n = max(1, min(MAX_SCENES, round(seconds / scene_seconds)))
    per = max(1, min(15, round(seconds / n)))
    user = f"""テーマ: {theme}
動画の長さ: 約{seconds}秒（{n}シーン × 約{per}秒）
縦横比: {aspect}

次のJSON形式で返してください:
{{"title": "動画タイトル（日本語）",
  "style": "全シーン共通の映像スタイル（英語。色調・質感・照明など）",
  "scenes": [{{"note": "このシーンで何が映るか（日本語・40字以内）", "prompt": "English prompt", "duration": {per}, "continue": false}}]}}
"""
    provider = "grok" if grok_client.is_configured() else "claude"
    raw, used = call_llm(PLAN_SYSTEM, user, 4000, provider=provider)
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1])
        scenes = data["scenes"]
    except (ValueError, KeyError, TypeError):
        raise SystemExit(f"絵コンテを読み取れませんでした。もう一度実行してください:\n{raw[:500]}")

    storyboard = {
        "title": str(data.get("title") or theme),
        "aspect_ratio": aspect,
        "resolution": "720p",
        "style": str(data.get("style", "")),
        "transition": "fade",
        "transition_seconds": 0.5,
        "audio": "keep",
        "bgm": None,
        "bgm_volume": 0.3,
        "scenes": [
            {
                "note": str(sc.get("note", "")),
                "prompt": str(sc.get("prompt", "")),
                "duration": max(1, min(15, _int(sc.get("duration"), per))),
                "continue": bool(sc.get("continue")) and i > 0,
            }
            for i, sc in enumerate(scenes) if isinstance(sc, dict) and sc.get("prompt")
        ],
    }
    header = (
        f"# 絵コンテ（{used} が作成）。中身を確認・修正してから render してください\n"
        f"#   python tools/grok/video.py render {out}\n"
        "# 書き方: tools/grok/README.md\n"
    )
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + yaml.safe_dump(storyboard, allow_unicode=True, sort_keys=False, width=1000),
                   encoding="utf-8")
    total = sum(s["duration"] for s in storyboard["scenes"])
    print(f"📝 絵コンテを作成しました: {out}（{len(storyboard['scenes'])}シーン・約{total}秒）")
    return out


# ── CLI ─────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="Grok で動画クリップを生成し、つないで1本の動画にする")
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="テーマから絵コンテ（YAML）を作る")
    p_plan.add_argument("theme", help="動画のテーマ・内容")
    p_plan.add_argument("--seconds", type=int, default=60, help="動画の長さ（秒）。既定: 60")
    p_plan.add_argument("--aspect", default="9:16", choices=ASPECTS, help="縦横比。既定: 9:16")
    p_plan.add_argument("--scene-seconds", type=int, default=8, help="1シーンの長さの目安（秒）。既定: 8")
    p_plan.add_argument("-o", "--output", required=True, help="保存先の YAML")

    p_render = sub.add_parser("render", help="クリップを生成してつなぐ（API代がかかる）")
    p_render.add_argument("storyboard")
    p_render.add_argument("--yes", action="store_true", help="確認せずに生成する")
    p_render.add_argument("--dry-run", action="store_true", help="見積もりだけ表示して終わる")
    p_render.add_argument("--max-seconds", type=int, default=None, help="新しく生成する秒数の上限（超えたら中止）")
    p_render.add_argument("--price-per-sec", type=float, default=DEFAULT_PRICE_PER_SEC, help="見積もり用の単価（USD/秒）")
    p_render.add_argument("-o", "--output", help="完成動画の保存先（既定: posts/videos/<名前>/<名前>.mp4）")

    p_stitch = sub.add_parser("stitch", help="生成済みのクリップをつなぎ直す（API代はかからない）")
    p_stitch.add_argument("storyboard")
    p_stitch.add_argument("-o", "--output")

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            plan(args.theme, args.seconds, args.aspect, args.scene_seconds, Path(args.output))
        elif args.command == "render":
            render(load_storyboard(Path(args.storyboard)), yes=args.yes, dry_run=args.dry_run,
                   price_per_sec=args.price_per_sec, max_seconds=args.max_seconds,
                   out=Path(args.output) if args.output else None)
        else:
            stitch(load_storyboard(Path(args.storyboard)), out=Path(args.output) if args.output else None)
    except (StoryboardError, GrokError, RuntimeError) as e:
        raise SystemExit(f"エラー: {e}")


if __name__ == "__main__":
    main()
