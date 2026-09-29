"""
動画にナレーションを付ける（Gemini TTS で音声生成 → 秒数どおりに配置 → BGM を自動で下げて合成）

    python3 src/narration_builder.py media/narration/eternaldct_promo_60s.yaml --video promo.mp4
    python3 src/narration_builder.py media/narration/eternaldct_promo_60s.yaml   # 動画なし: ナレーション音声だけ

出力（media/tts_output/<YAML名>/）:
    NN_xxxxxxxx.wav      セリフごとの音声（テキスト・声・指示が同じなら次回は再利用＝無料枠の節約）
    narration.wav        ナレーションだけの音声トラック（CapCut などの編集ソフトに載せる用）
    <動画名>_narrated.mp4 BGM を下げてナレーションを重ねた完成動画（--video 指定時）

セリフが区間（at〜until）より長い場合は最大 1.2 倍速まで詰め、それでも入らなければ警告を出す。
"""
import argparse
import array
import hashlib
import math
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_tts  # noqa: E402

MAX_SPEEDUP = 1.2
TARGET_SPEECH_DB = -18.0   # 発話部分の平均音量の目標（dBFS）
EDGE_FADE_IN = 0.01
EDGE_FADE_OUT = 0.03


def load_cues(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cues = config.get("cues") or []
    if not cues:
        raise gemini_tts.GeminiTTSError(f"{path} に cues がありません")
    last_end = 0.0
    for i, cue in enumerate(cues, 1):
        if not str(cue.get("text", "")).strip():
            raise gemini_tts.GeminiTTSError(f"{i}番目のセリフ（text）が空です")
        at, until = float(cue["at"]), float(cue.get("until", cue["at"] + 30))
        if until <= at:
            raise gemini_tts.GeminiTTSError(f"{i}番目: until（{until}）が at（{at}）以前です")
        if at < last_end:
            raise gemini_tts.GeminiTTSError(f"{i}番目: 前のセリフの区間（〜{last_end}秒）と重なっています")
        cue["at"], cue["until"] = at, until
        last_end = until
    return config


def clip_path(out_dir: Path, index: int, text: str, voice: str, style: str, model: str = "") -> Path:
    key = hashlib.sha1(f"{model}\n{voice}\n{style}\n{text}".encode()).hexdigest()[:8]
    return out_dir / f"{index:02d}_{key}.wav"


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as wf:
        return wf.getnframes() / wf.getframerate()


def speech_gain_db(path: Path, target_db: float = TARGET_SPEECH_DB) -> float:
    """発話部分（20ms ごとに -45dBFS 以上の区間）の平均音量を target_db にそろえるゲイン"""
    with wave.open(str(path)) as wf:
        rate, width = wf.getframerate(), wf.getsampwidth()
        samples = array.array("h", wf.readframes(wf.getnframes())) if width == 2 else array.array("h")
    step = max(rate // 50, 1)
    loud = []
    for i in range(0, len(samples) - step + 1, step):
        power = sum(v * v for v in samples[i:i + step]) / step / 32768 ** 2
        if power > 10 ** (-45 / 10):
            loud.append(power)
    if not loud:
        return 0.0
    level_db = 10 * math.log10(sum(loud) / len(loud))
    return max(min(target_db - level_db, 12.0), -12.0)


def speed_for(duration: float, slot: float) -> float:
    """区間に収めるための再生速度（1.0 = 等速、上限 MAX_SPEEDUP）"""
    return min(max(duration / slot, 1.0), MAX_SPEEDUP)


def generate_clips(config: dict, out_dir: Path, pace: float = 0.0) -> list[dict]:
    """各セリフを音声化（キャッシュがあれば再利用）して、配置情報のリストを返す"""
    out_dir.mkdir(parents=True, exist_ok=True)
    voice = config.get("voice", gemini_tts.DEFAULT_VOICE)
    model = gemini_tts._model_chain(None)[0]
    placed = []
    last_call = 0.0
    for i, cue in enumerate(config["cues"], 1):
        style = cue.get("style", config.get("style", ""))
        path = clip_path(out_dir, i, cue["text"], voice, style, model)
        if path.exists():
            print(f"[{i:02d}] キャッシュを使用: {path.name}")
        else:
            # 無料枠は1分あたりの回数も少ないので、指定秒数ぶん間隔を空けて呼ぶ
            wait = pace - (time.monotonic() - last_call)
            if last_call and wait > 0:
                time.sleep(wait)
            print(f"[{i:02d}] 生成中: {cue['text']}")
            last_call = time.monotonic()
            _, used_model = gemini_tts.text_to_speech(cue["text"], output=path, voice=voice, style=style)
            if used_model != gemini_tts._model_chain(None)[0]:
                print(f"      ※ 無料枠の上限のため {used_model} で作成")

        duration = wav_duration(path)
        slot = cue["until"] - cue["at"]
        speed = speed_for(duration, slot)
        fitted = duration / speed
        status = "OK"
        if speed > 1.0:
            status = f"{speed:.2f}倍速で調整"
        if fitted > slot + 0.05:
            status = f"⚠ {fitted - slot:.1f}秒はみ出し（セリフを短くしてください）"
        print(f"      {cue['at']:5.1f}〜{cue['until']:5.1f}秒 枠{slot:.1f}秒 / 音声{duration:.1f}秒 → {status}")
        placed.append({"path": path, "at": cue["at"], "end": cue["at"] + fitted, "speed": speed,
                       "gain_db": speech_gain_db(path)})
    return placed


def _narration_filters(placed: list[dict], first_input: int) -> tuple[list[str], str]:
    """各クリップを速度調整・音量をそろえて at 秒に配置し、1本に混ぜるフィルタ"""
    filters, labels = [], []
    for n, clip in enumerate(placed):
        chain = ["aformat=sample_rates=48000:channel_layouts=stereo"]
        if clip["speed"] > 1.0:
            chain.append(f"atempo={clip['speed']:.3f}")
        delay = int(round(clip["at"] * 1000))
        # 音量は固定ゲインでそろえる（loudnorm の動的処理は無音部の雑音まで持ち上げるため使わない）。
        # 先頭・末尾に短いフェードを付けて、切れ目の「プツッ」を防ぐ
        fade_out_at = max(clip["end"] - clip["at"] - EDGE_FADE_OUT, 0)
        # deesser: TTS 音声の「ス・ツ・ズ」の刺さる高音を和らげる
        chain += ["deesser=i=0.5:m=0.5:f=0.5", f"volume={clip['gain_db']:.1f}dB",
                  f"afade=t=in:d={EDGE_FADE_IN}", f"afade=t=out:st={fade_out_at:.3f}:d={EDGE_FADE_OUT}",
                  f"adelay={delay}|{delay}"]
        filters.append(f"[{first_input + n}:a]{','.join(chain)}[c{n}]")
        labels.append(f"[c{n}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest[narr]")
    return filters, "[narr]"


def ducking_expression(placed: list[dict], duck_db: float, fade_in: float = 0.25,
                       fade_out: float = 0.5) -> str:
    """ナレーションが鳴っている間だけ BGM を duck_db 下げる音量式（前後はフェード）"""
    gain = 10 ** (-duck_db / 20)
    envs = [
        f"clip(min((t-{c['at'] - fade_in:.3f})/{fade_in},({c['end'] + fade_out:.3f}-t)/{fade_out}),0,1)"
        for c in placed
    ]
    env = envs[0]
    for e in envs[1:]:
        env = f"max({env},{e})"
    return f"1-{1 - gain:.4f}*{env}"


def has_audio(ffmpeg: str, video: Path) -> bool:
    info = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True).stderr
    return bool(re.search(r"Stream #\d+:\d+.*: Audio:", info))


def build(config: dict, placed: list[dict], out_dir: Path, video: Path | None) -> list[Path]:
    ffmpeg = gemini_tts.ffmpeg_exe()
    if not ffmpeg:
        raise gemini_tts.GeminiTTSError("ffmpeg が見つかりません。pip install -r requirements-mcp.txt を実行してください")
    clip_inputs = [arg for c in placed for arg in ("-i", str(c["path"]))]
    outputs = []

    # ナレーションだけのトラック
    narration = out_dir / "narration.wav"
    filters, narr = _narration_filters(placed, 0)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", *clip_inputs,
                    "-filter_complex", ";".join(filters), "-map", narr, str(narration)], check=True)
    outputs.append(narration)
    if not video:
        return outputs

    # 動画に合成（元の音声がある場合はナレーション中だけ BGM を下げる）
    result = out_dir / f"{video.stem}_narrated.mp4"
    filters, narr = _narration_filters(placed, 1)
    if has_audio(ffmpeg, video):
        duck = ducking_expression(placed, float(config.get("bgm_duck_db", 9)))
        filters += [
            f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume='{duck}':eval=frame[bgm]",
            f"[bgm]{narr}amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[out]",
        ]
    else:
        filters.append(f"{narr}alimiter=limit=0.95[out]")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), *clip_inputs,
                    "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[out]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(result)], check=True)
    outputs.append(result)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="動画にナレーションを付ける（Gemini TTS）")
    parser.add_argument("cues", help="ナレーション台本の YAML（media/narration/*.yaml）")
    parser.add_argument("--video", help="ナレーションを重ねる動画（省略時はナレーション音声だけ作る）")
    parser.add_argument("-o", "--out-dir", help="出力先フォルダ（省略時 media/tts_output/<YAML名>/）")
    parser.add_argument("--pace", type=float, default=0.0,
                        help="API 呼び出しの最小間隔（秒）。無料枠の1分あたり上限に当たるときは 13 など")
    args = parser.parse_args(argv)

    cue_file = Path(args.cues)
    out_dir = Path(args.out_dir) if args.out_dir else gemini_tts.DEFAULT_OUTPUT_DIR / cue_file.stem
    video = Path(args.video) if args.video else None
    if video and not video.exists():
        print(f"エラー: 動画が見つかりません: {video}", file=sys.stderr)
        return 1
    try:
        config = load_cues(cue_file)
        placed = generate_clips(config, out_dir, pace=args.pace)
        outputs = build(config, placed, out_dir, video)
    except (gemini_tts.GeminiTTSError, subprocess.CalledProcessError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print("\n完成:")
    for path in outputs:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
