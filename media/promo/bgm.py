"""プロモ映像用 BGM（60秒 / 120BPM）を numpy だけで合成する。

著作権フリーにするため外部音源は使わず、すべてシンセで生成する。
コード進行は王道進行（IV - V - iii - vi = F - G - Em - Am）、1小節 = 2秒。
映像側（promo.html）のシーン切り替えと同じ時刻に展開が変わる:
  0-4s   イントロ（パッド + ライザー）
  4s     インパクト（ロゴ登場）
  4-12s  キック + ベース
  12-18s キネティック・タイポ（毎秒スタブ + クラップ + ハット）
  18-46s フルグルーヴ（アルペジオ追加）
  46-52s ブレイク → ビルドアップ
  52s    インパクト（エンドカード）
  52-60s グルーヴ → フェードアウト
出力: media/promo/out/bgm.wav（44.1kHz / 16bit / ステレオ）
"""
from pathlib import Path
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
DUR = 60.0
BEAT = 0.5
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(3)
OUT = Path(__file__).resolve().parent / "out" / "bgm.wav"


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def env_adsr(n, a, d, s, r, sus_len):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, int(sus_len * SR) - a_n - d_n)
    e = np.concatenate([
        np.linspace(0, 1, a_n, endpoint=False),
        np.linspace(1, s, d_n, endpoint=False),
        np.full(s_n, s),
        np.linspace(s, 0, r_n),
    ])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def place(buf, sig, start):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


# 王道進行（F - G - Em - Am）
CHORDS = [
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 67],  # G
    [52, 55, 59, 62],  # Em7
    [57, 60, 64, 67],  # Am7
]
ROOTS = [41, 43, 40, 45]  # F2 G2 E2 A2


def chord_at(bar):
    return CHORDS[bar % 4], ROOTS[bar % 4]


def drums_on(tt):
    return (4 <= tt < 46) or (52 <= tt < 58)


# ---------- 各パート ----------
pad = np.zeros(N)
bass = np.zeros(N)
arp = np.zeros(N)
drums = np.zeros(N)
fx = np.zeros(N)
stabs = np.zeros(N)

# パッド（デチューンしたノコギリ波を重ねてローパス）
for bar in range(30):
    notes, _ = chord_at(bar)
    start = bar * 2.0
    n = int(2.4 * SR)
    tt = np.arange(n) / SR
    sig = np.zeros(n)
    for m in notes:
        for det in (-0.08, 0.0, 0.08):
            sig += saw(midi(m + det), tt + rng.random())
    sig = lp(sig, 1800 if 18 <= start < 46 else 1100) / 12
    place(pad, sig * env_adsr(n, 0.35, 0.3, 0.8, 0.5, 2.0), start)

# ベース（8分で刻む。サイン + 少しだけ倍音）
for bar in range(2, 30):
    start = bar * 2.0
    if 46 <= start < 50:
        continue
    _, root = chord_at(bar)
    f = midi(root)
    for k in range(8):
        s = start + k * 0.25
        if not drums_on(s):
            continue
        n = int(0.24 * SR)
        tt = np.arange(n) / SR
        note = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt) + 0.1 * saw(f, tt)
        place(bass, note * env_adsr(n, 0.005, 0.08, 0.6, 0.05, 0.2) * 0.55, s)

# アルペジオ（16分・プラック）
for bar in range(9, 23):  # 18s - 46s
    start = bar * 2.0
    notes, _ = chord_at(bar)
    seq = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[3] + 12, notes[2] + 12, notes[1] + 12, notes[3] + 12, notes[0] + 24]
    for k in range(16):
        s = start + k * 0.125
        f = midi(seq[k % 8])
        n = int(0.3 * SR)
        tt = np.arange(n) / SR
        tone = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 3 * f * tt)) * np.exp(-tt * 14)
        place(arp, tone * (0.22 if k % 4 == 0 else 0.14), s)

# ドラム
def kick_sample():
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    f = 45 + 110 * np.exp(-tt * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-tt * 9) + 0.3 * np.sin(ph) * np.exp(-tt * 60)


def clap_sample():
    n = int(0.25 * SR)
    tt = np.arange(n) / SR
    nz = bp(rng.standard_normal(n), 900, 5000)
    e = np.exp(-tt * 22)
    for d in (0.0, 0.012, 0.024):  # 手拍子っぽい多重アタック
        e = e + 0.6 * np.exp(-np.maximum(tt - d, 0) * 120) * (tt >= d)
    return nz * e * 0.35


def hat_sample(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    tt = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-tt * (18 if open_ else 80)) * 0.18


K, CL, HH, OH = kick_sample(), clap_sample(), hat_sample(), hat_sample(True)
steps = np.arange(0, DUR, 0.125)
for s in steps:
    if not drums_on(s):
        continue
    beat_pos = round((s % 2.0) / 0.125)  # 1小節内の16分位置
    if beat_pos % 4 == 0:
        place(drums, K * 0.9, s)
    if s >= 12 and beat_pos in (4, 12):
        place(drums, CL, s)
    if s >= 12 and beat_pos % 4 == 2:
        place(drums, OH if s >= 18 else HH, s)
    if s >= 18 and beat_pos % 2 == 1:
        place(drums, HH * 0.6, s)

# サイドチェイン（キックでパッドとベースを沈ませる）
duck = np.ones(N)
for s in np.arange(0, DUR, BEAT):
    if drums_on(s):
        n = int(0.45 * SR)
        tt = np.arange(n) / SR
        i = int(s * SR)
        j = min(N, i + n)
        duck[i:j] = np.minimum(duck[i:j], (1 - 0.6 * np.exp(-tt * 9))[: j - i])

# キネティック・タイポ（12-18s）の毎秒スタブ
for k in range(6):
    s = 12 + k
    notes, _ = chord_at(int(s // 2))
    n = int(0.5 * SR)
    tt = np.arange(n) / SR
    sig = sum(saw(midi(m + 12), tt) for m in notes)
    sig = lp(sig, 3500) * np.exp(-tt * 7) * 0.12
    place(stabs, sig, s)

# FX: ライザー（ノイズを徐々に明るく）とインパクト
def riser(start, dur, gain=0.35):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    nz = rng.standard_normal(n)
    out = np.zeros(n)
    seg = int(0.05 * SR)
    for i in range(0, n, seg):  # 区間ごとにカットオフを上げる
        fc = 300 + 7000 * (i / n) ** 2
        out[i:i + seg] = bp(nz[max(0, i - 2048):i + seg], fc * 0.6, min(fc * 1.6, 18000))[-len(nz[i:i + seg]):]
    place(fx, out * (tt / dur) ** 2 * gain, start)


def impact(at):
    n = int(2.5 * SR)
    tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (38 + 60 * np.exp(-tt * 8)) * tt) * np.exp(-tt * 2.2)
    crash = hp(rng.standard_normal(n), 4000) * np.exp(-tt * 1.8) * 0.25
    place(fx, (boom * 0.9 + crash), at)


riser(0.5, 3.5)
impact(4.0)
riser(49.0, 3.0, 0.4)
impact(52.0)
# 46-52 のブレイクでスネアロールで盛り上げる
for i, s in enumerate(np.arange(50.0, 52.0, 0.0625)):
    place(drums, CL * (0.2 + 0.8 * i / 32), s)

# ---------- ミックス ----------
dry_music = pad * 0.55 * duck + bass * duck + arp * 0.8 + stabs
send = pad * 0.5 + arp * 0.6 + stabs * 0.8

# 簡易リバーブ（減衰ノイズのインパルス応答を FFT 畳み込み）
ir_n = int(2.2 * SR)
ir_t = np.arange(ir_n) / SR
ir_l = rng.standard_normal(ir_n) * np.exp(-ir_t * 3.2)
ir_r = rng.standard_normal(ir_n) * np.exp(-ir_t * 3.2)
ir_l, ir_r = lp(ir_l, 6000), lp(ir_r, 6000)


def conv(x, ir):
    L = len(x) + len(ir)
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return y / np.max(np.abs(ir)) * 0.02


rev_l, rev_r = conv(send, ir_l), conv(send, ir_r)
# アルペジオは左右に少し揺らす
pan = 0.5 + 0.25 * np.sin(2 * np.pi * t_all / 4)
left = dry_music + drums + fx + rev_l + arp * 0.3 * (1 - pan)
right = dry_music + drums + fx + rev_r + arp * 0.3 * pan
mix = np.stack([left, right], axis=1)

# マスター: ソフトクリップ → ノーマライズ → フェード
mix = np.tanh(mix * 1.15)
mix /= np.max(np.abs(mix)) / 0.89
fade_in = np.clip(t_all / 0.3, 0, 1)
fade_out = np.clip((60 - t_all) / 2.5, 0, 1)
mix *= (fade_in * fade_out)[:, None]

OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("written", OUT)
