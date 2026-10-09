"""
動画用のオリジナル BGM をコードで合成する（外部の音源・API 不要・著作権の心配なし）

明るいエレクトロポップ／シンセウェイブ系。ドラム・ベース・パッド・アルペジオをその場で合成し、
動画の構成に合わせて「最初のインパクト」「盛り上げ（ビルド）」「最後の決め音」の位置を指定できる。

    python3 src/bgm_synth.py -o media/music/eternaldct_motion_pv_bgm.wav \\
        --duration 62 --bpm 118 --impact-bar 2 --build-bar 26 --drop-bar 28 --final-hit 60.0

必要: numpy, scipy（requirements-mcp.txt）
"""
import argparse
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
# Am - F - C - G（vi-IV-I-V）。パッドは声部の動きが小さくなる転回形
CHORDS = [[57, 60, 64], [57, 60, 65], [55, 60, 64], [55, 59, 62]]
BASS_ROOTS = [45, 41, 48, 43]


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _filter(x: np.ndarray, kind: str, cutoff, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def _saw(freq: float, n: int, phase: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    return 2.0 * ((freq * t + phase) % 1.0) - 1.0


def _env(n: int, attack: float, decay: float, sustain: float = 0.0, release: float = 0.01) -> np.ndarray:
    t = np.arange(n) / SR
    env = np.where(t < attack, t / max(attack, 1e-4),
                   sustain + (1 - sustain) * np.exp(-(t - attack) / max(decay, 1e-4)))
    r = int(release * SR)
    if 0 < r < n:
        env[-r:] *= np.linspace(1, 0, r)
    return env


class Track:
    def __init__(self, duration: float):
        self.n = int(duration * SR)
        self.buses = {name: np.zeros((self.n, 2)) for name in ("drums", "bass", "pad", "arp", "fx", "hit")}

    def add(self, bus: str, at: float, mono_or_stereo: np.ndarray, gain: float = 1.0, pan: float = 0.0):
        start = int(at * SR)
        if start >= self.n:
            return
        x = mono_or_stereo
        if x.ndim == 1:
            left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
            x = np.stack([x * left, x * right], axis=1) * np.sqrt(2)
        end = min(start + len(x), self.n)
        self.buses[bus][start:end] += x[:end - start] * gain


# ── 音色 ───────────────────────────────────────────────
def kick() -> np.ndarray:
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    freq = 48 + 110 * np.exp(-t * 28)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 6.5)
    click = np.random.default_rng(1).standard_normal(n) * np.exp(-t * 400) * 0.3
    return np.tanh(1.6 * (body + click))


def clap(rng) -> np.ndarray:
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    env = sum(np.where(t >= d, np.exp(-(t - d) / 0.008), 0) for d in (0, 0.011, 0.022))
    env = env + np.where(t >= 0.03, 0.6 * np.exp(-(t - 0.03) / 0.11), 0)
    return _filter(noise * env, "bandpass", [900, 6000]) * 0.9


def snare(rng, length: float = 0.18) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    noise = _filter(rng.standard_normal(n), "bandpass", [1500, 9000]) * np.exp(-t * 22)
    return 0.5 * tone + 0.8 * noise


def hat(rng, open_: bool = False) -> np.ndarray:
    n = int((0.22 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    noise = _filter(rng.standard_normal(n), "highpass", 7500, order=4)
    return noise * np.exp(-t / (0.07 if open_ else 0.012))


def crash(rng, length: float = 2.2) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    noise = _filter(rng.standard_normal((n, 2)), "bandpass", [3500, 14000])
    return noise * np.exp(-t / 0.7)[:, None]


def bass_note(midi: int, length: float) -> np.ndarray:
    n = int(length * SR)
    f = hz(midi)
    x = 0.6 * _saw(f, n) + 0.5 * np.sin(2 * np.pi * f * np.arange(n) / SR)
    x = _filter(x, "lowpass", 700)
    return x * _env(n, 0.004, 0.18, sustain=0.55, release=0.03)


def pad_chord(notes, length: float, cutoff: float) -> np.ndarray:
    n = int(length * SR)
    out = np.zeros((n, 2))
    for i, m in enumerate(notes):
        for ch, cents in ((0, -8), (1, 8)):
            f = hz(m) * 2 ** (cents / 1200)
            out[:, ch] += _saw(f, n, phase=0.13 * i + 0.4 * ch) + 0.5 * _saw(f * 2.003, n)
    out = _filter(out, "lowpass", cutoff, order=2)
    env = _env(n, 0.06, 10.0, sustain=1.0, release=0.06)
    return out * env[:, None] / 6


def pluck(midi: int, length: float, bright: float) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    x = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + 0.5 * _saw(f * 1.005, n)
    x = _filter(x, "lowpass", bright)
    return x * np.exp(-t / 0.09)


def riser(rng, length: float) -> np.ndarray:
    n = int(length * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    low = _filter(noise, "bandpass", [400, 1500])
    high = _filter(noise, "bandpass", [3000, 10000])
    sweep = np.sin(2 * np.pi * np.cumsum(220 + 900 * t ** 2) / SR) * 0.15
    return ((1 - t) * low + t * high) * t ** 2 * 0.6 + sweep * t


def impact(rng) -> np.ndarray:
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 4)) / SR) * np.exp(-t * 2.2)
    return np.tanh(1.5 * sub)


def stereo_reverb(x: np.ndarray, seconds: float = 2.2, wet: float = 0.22, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t * 6.9 / seconds)[:, None]
    ir = _filter(ir, "lowpass", 6000)
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    wet_sig = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], axis=1)
    return x + wet * wet_sig


def pingpong(x: np.ndarray, delay: float, feedback: float = 0.35, taps: int = 4) -> np.ndarray:
    out = x.copy()
    d = int(delay * SR)
    for k in range(1, taps + 1):
        ch = k % 2
        shifted = np.zeros(len(x))
        shifted[d * k:] = x[:len(x) - d * k, ch]
        out[:, 1 - ch] += shifted * feedback ** k
    return out


# ── 曲の組み立て ───────────────────────────────────────
def compose(duration: float, bpm: float, impact_bar: int, build_bar: int, drop_bar: int,
            final_hit: float, seed: int = 2026) -> np.ndarray:
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = beat * 4
    tr = Track(duration)
    k, cl = kick(), clap(rng)
    total_bars = int(np.ceil(final_hit / bar))

    for b in range(total_bars):
        t0 = b * bar
        if t0 >= final_hit:
            break
        chord, root = CHORDS[b % 4], BASS_ROOTS[b % 4]
        intro, building = b < impact_bar, build_bar <= b < drop_bar
        groove = not intro and not (building and b == build_bar)

        # パッド（イントロはフィルターを徐々に開く）
        cutoff = 600 + 1800 * (b + 1) / max(impact_bar, 1) if intro else 2600
        tr.add("pad", t0, pad_chord(chord, bar + 0.06, cutoff), gain=0.9)

        for s in range(16):  # 16分音符ごと
            ts = t0 + s * beat / 4
            if ts >= final_hit:
                break
            # アルペジオ
            notes = [m + 12 for m in chord] + [chord[0] + 24]
            bright = 1500 if intro else (2400 if b < drop_bar else 3000)
            tr.add("arp", ts, pluck(notes[s % 4], beat / 4 + 0.08, bright), gain=0.15 if intro else 0.18)
            if intro:
                continue
            if groove and s % 4 == 0:
                tr.add("drums", ts, k, gain=0.95)
            if groove and s in (4, 12):
                tr.add("drums", ts, cl, gain=0.55 * rng.uniform(0.9, 1.0))
            if groove and s % 2 == 0:
                vel = rng.uniform(0.75, 1.05) * (1.1 if s % 8 == 2 else 1.0)
                tr.add("drums", ts, hat(rng, open_=(s % 4 == 2 and b >= impact_bar + 8)),
                       gain=(0.13 if s % 4 == 2 else 0.11) * vel, pan=0.25)
            if groove and b >= impact_bar + 8 and s % 2 == 1:
                tr.add("drums", ts, hat(rng), gain=0.06 * rng.uniform(0.6, 1.0), pan=-0.25)
            if groove and s % 2 == 0:  # ベースは8分のオフビート寄り
                tr.add("bass", ts + (beat / 4 if s % 4 == 0 else 0), bass_note(root, beat / 2 - 0.03), gain=0.75)
            # 8小節ごとのフィル
            if (b - impact_bar) % 8 == 7 and s >= 12:
                tr.add("drums", ts, snare(rng), gain=0.22 + 0.04 * (s - 12))

        # ビルド：スネアロールが加速
        if building:
            for i, frac in enumerate(np.linspace(0, 1, 16 if b == build_bar else 32, endpoint=False)):
                tr.add("drums", t0 + frac * bar, snare(rng, 0.12), gain=0.12 + 0.3 * (frac if b > build_bar else 0))

    # FX：イントロとビルドのライザー、インパクト、クラッシュ
    tr.add("fx", 0.0, riser(rng, impact_bar * bar), gain=0.35)
    tr.add("fx", build_bar * bar, riser(rng, (drop_bar - build_bar) * bar), gain=0.45)
    for t_hit in (impact_bar * bar, drop_bar * bar):
        tr.add("fx", t_hit, impact(rng), gain=0.8)
        tr.add("fx", t_hit, crash(rng), gain=0.35)
        tr.add("drums", t_hit, k, gain=1.0)

    # 最後の決め音：コードのスタブ＋キック＋クラッシュ、リバーブの余韻で終わる
    stab = pad_chord([45, 57, 60, 64, 69, 72], 2.0, 5000) * _env(int(2.0 * SR), 0.005, 0.6)[:, None] * 5
    tr.add("hit", final_hit, stab, gain=0.7)
    tr.add("fx", final_hit - bar / 2, riser(rng, bar / 2), gain=0.3)
    tr.add("drums", final_hit, k, gain=1.0)
    tr.add("fx", final_hit, impact(rng), gain=0.9)
    tr.add("fx", final_hit, crash(rng, 2.0), gain=0.4)

    # キックに合わせてパッド・ベース・アルペジオを揺らす（ポンピング）
    pump = np.ones(tr.n)
    tt = np.arange(tr.n) / SR
    for b in range(impact_bar, total_bars):
        for q in range(4):
            tk = b * bar + q * beat
            if tk >= final_hit or (build_bar == b):
                continue
            idx = slice(int(tk * SR), min(int((tk + beat) * SR), tr.n))
            pump[idx] = np.minimum(pump[idx], 1 - 0.45 * np.exp(-(tt[idx] - tk) / 0.11))
    for name in ("pad", "bass", "arp"):
        tr.buses[name] *= pump[:, None]

    cut = int(final_hit * SR)
    fade_n = int(0.12 * SR)
    for name in ("pad", "bass", "arp"):
        tr.buses[name][cut:cut + fade_n] *= np.linspace(1, 0, min(fade_n, tr.n - cut))[:, None]
        tr.buses[name][cut + fade_n:] = 0

    arp = pingpong(tr.buses["arp"], beat * 0.75)
    music = tr.buses["pad"] + arp
    music = music - 0.35 * _filter(music, "bandpass", [1000, 3000])
    mix = (tr.buses["drums"] + tr.buses["bass"] + stereo_reverb(music, wet=0.3)
           + stereo_reverb(tr.buses["fx"] + tr.buses["hit"], 2.8, 0.25, seed=11))
    mix = _filter(mix, "highpass", 28)
    fade = int(0.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    mix = np.tanh(1.3 * mix / (np.abs(mix).max() + 1e-9))
    return mix / np.abs(mix).max() * 10 ** (-1 / 20)


def write_wav(path: Path, x: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="動画用のオリジナル BGM を合成する")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--duration", type=float, required=True, help="曲の長さ（秒）＝動画の長さ")
    p.add_argument("--bpm", type=float, default=118)
    p.add_argument("--impact-bar", type=int, default=2, help="イントロ明けのインパクトを入れる小節")
    p.add_argument("--build-bar", type=int, default=26, help="盛り上げ（スネアロール）を始める小節")
    p.add_argument("--drop-bar", type=int, default=28, help="盛り上げのあとの決め（クラッシュ）の小節")
    p.add_argument("--final-hit", type=float, help="最後の決め音の秒数（省略時は終わりの2秒前）")
    a = p.parse_args(argv)
    final_hit = a.final_hit if a.final_hit is not None else a.duration - 2.0
    x = compose(a.duration, a.bpm, a.impact_bar, a.build_bar, a.drop_bar, final_hit)
    write_wav(Path(a.output), x)
    print(a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
