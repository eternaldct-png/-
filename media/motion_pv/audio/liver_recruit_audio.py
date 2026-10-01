"""
ライバー募集動画（liver_recruit.html）の音声を作る

- ナレーション: Open JTalk（pyopenjtalk-plus 同梱の HTS Voice "Mei"）で読み上げ
- BGM: numpy / scipy でゼロから合成したオリジナル曲（120BPM・王道進行。素材の権利問題なし）
- ナレーションが入る区間は BGM を自動で下げる（ダッキング）

使い方:
    pip install pyopenjtalk-plus numpy scipy
    python media/motion_pv/audio/liver_recruit_audio.py 出力.wav
    → render.js で書き出した映像と ffmpeg で合わせる（README 参照）

クレジット表記（CC BY 3.0）: HTS Voice "Mei" (c) 2009-2013 Nagoya Institute of Technology
"""
import json
import sys

import numpy as np
import pyopenjtalk
import scipy.io.wavfile as wavfile
import scipy.signal as ss

SR = 44100
DURATION = 60.0
BEAT = 0.5          # 120BPM
BAR = 4 * BEAT      # 1小節 = 2秒（映像のカットと同じグリッド）
N = int(SR * DURATION)
rng = np.random.default_rng(61)

# ── ナレーション（開始秒, 読み上げる文, この時刻までに言い終える） ──────────────
# 読み間違いを避けるため、一部はひらがなで書いている（例: はじめたいひと / 主夫のかた）
NARRATION = [
    (0.35, "歌うのが、好き。", 1.75),
    (1.8, "話すのが、好き。", 3.0),
    (3.1, "その「好き」を、配信してみませんか？", 5.95),
    (6.8, "エターナルディクト、ライバー募集中！", 9.5),
    (12.45, "所属ライバーは、61名。", 15.0),
    (15.45, "次は、あなたの番です。", 17.5),
    (20.15, "こんな人を、待っています。", 21.8),
    (21.95, "歌うことが、好きな人。", 23.65),
    (23.8, "話すのが、好きな人。", 25.6),
    (25.75, "副業で、はじめたいひと。", 27.45),
    (27.6, "主婦・主夫も歓迎。", 29.3),
    (29.45, "配信未経験でも、応募OK。", 31.6),
    (32.35, "エターナルディクトは、ライバー事務所。", 34.45),
    (34.6, "音楽制作や、グッズも手がけています。", 37.25),
    (37.45, "代表も、現役の配信者です。", 39.7),
    (40.25, "応募の流れです。", 41.3),
    (41.45, "応募フォームから応募して、", 42.85),
    (43.0, "審査結果は、メールでお知らせ。", 45.2),
    (45.4, "面談をへて、", 46.25),
    (46.4, "所属、配信スタート！", 48.2),
    (50.35, "あなたの「好き」を、配信で届けよう。", 53.6),
    (53.8, "エターナルディクト、ライバー募集中。", 56.2),
    (56.4, "応募は、プロフィールのリンクから！", 58.4),
]
BASE_SPEED = 1.15
MAX_SPEED = 1.45


def t_of(n):
    return np.arange(n) / SR


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(track, x, start):
    """track の start 秒の位置に x を足し込む（はみ出した分は捨てる）"""
    i0 = int(round(start * SR))
    if i0 >= len(track):
        return
    x = x[: len(track) - i0]
    track[i0:i0 + len(x)] += x


def lowpass(x, hz, order=2):
    b, a = ss.butter(order, hz / (SR / 2), "low")
    return ss.lfilter(b, a, x, axis=0)


def highpass(x, hz, order=2):
    b, a = ss.butter(order, hz / (SR / 2), "high")
    return ss.lfilter(b, a, x, axis=0)


def bandpass(x, lo, hi, order=2):
    b, a = ss.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return ss.lfilter(b, a, x, axis=0)


def saw(freq, n, phase=0.0):
    """折り返しノイズを抑えたノコギリ波（PolyBLEP）"""
    dt = freq / SR
    ph = (phase + freq * t_of(n)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt
    y[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt
    y[m] -= x * x + x + x + 1
    return y


# ── ナレーション ─────────────────────────────────────────────
def synth_line(text, max_len):
    speed = BASE_SPEED
    for _ in range(4):
        x, sr = pyopenjtalk.tts(text, speed=speed)
        x = x.astype(np.float64) / 32768.0
        a = np.abs(x)
        idx = np.where(a > a.max() * 0.02)[0]
        x = x[max(0, idx[0] - int(.01 * sr)): idx[-1] + int(.04 * sr)]
        if len(x) / sr <= max_len or speed >= MAX_SPEED:
            break
        speed = min(MAX_SPEED, speed * (len(x) / sr) / max_len * 1.02)
    x = ss.resample_poly(x, SR, sr)
    # 声の聞きやすさ: 低域カット・明瞭感を少し足す・軽く圧縮
    x = highpass(x, 90)
    x = x + 0.35 * bandpass(x, 2500, 6000)
    x = np.tanh(1.5 * x / np.max(np.abs(x))) / np.tanh(1.5)
    fade = int(.008 * SR)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x, speed


def build_narration():
    voice = np.zeros(N)
    timeline = []
    for start, text, end in NARRATION:
        x, speed = synth_line(text, end - start)
        place(voice, x, start)
        timeline.append({"start": start, "end": round(start + len(x) / SR, 2), "speed": round(speed, 2), "text": text})
    return voice, timeline


# ── BGM の楽器 ───────────────────────────────────────────────
def kick():
    n = int(SR * .45)
    t = t_of(n)
    f = 45 + 115 * np.exp(-t / .04)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .17)
    click = rng.standard_normal(n) * np.exp(-t / .003) * .25
    return np.tanh(1.6 * (body + click))


def clap():
    n = int(SR * .4)
    t = t_of(n)
    env = np.zeros(n)
    for off in (0, .011, .022):
        i0 = int(off * SR)
        env[i0:] += np.exp(-t[: n - i0] / .006)
    i0 = int(.022 * SR)
    env[i0:] += .7 * np.exp(-t[: n - i0] / .13)
    return bandpass(rng.standard_normal(n) * env, 900, 4000) * 1.6


def hat(open_=False):
    n = int(SR * (.25 if open_ else .06))
    t = t_of(n)
    return highpass(rng.standard_normal(n), 7000) * np.exp(-t / (.09 if open_ else .022))


def crash():
    n = int(SR * 2.2)
    t = t_of(n)
    return highpass(rng.standard_normal(n), 3500) * np.exp(-t / .7) * .6


def impact():
    n = int(SR * 1.6)
    t = t_of(n)
    f = 30 + 50 * np.exp(-t / .15)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .5)
    return np.tanh(1.4 * boom) + .4 * crash()[:n]


def riser(length):
    """ノイズのスイープ（盛り上げ）。少しずつ明るく・大きくなる"""
    n = int(SR * length)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    chunk = int(SR * .05)
    zi = None
    for i in range(0, n, chunk):
        k = i / n
        b, a = ss.butter(2, (400 + 7000 * k ** 2) / (SR / 2), "low")
        if zi is None:
            zi = ss.lfilter_zi(b, a) * 0
        seg, zi = ss.lfilter(b, a, noise[i:i + chunk], zi=zi)
        out[i:i + chunk] = seg
    t = t_of(n)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * (t / length) ** 2) / SR) * .15
    return (out * .9 + tone) * (t / length) ** 2


def pluck(m, length=.35, bright=1.0):
    n = int(SR * length)
    t = t_of(n)
    x = saw(midi_hz(m), n, rng.random()) * .6 + np.sin(2 * np.pi * midi_hz(m) * t) * .4
    return lowpass(x * np.exp(-t / (.09 * bright + .03)), 2600 + 2000 * bright) * np.minimum(1, t / .002)


def bell(m, length):
    """FM の鐘っぽい音（メロディ用）"""
    n = int(SR * (length + .6))
    t = t_of(n)
    f = midi_hz(m)
    mod = 1.8 * np.exp(-t / .25) * np.sin(2 * np.pi * f * 3.5 * t)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / .55)
    x += .25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / .3)
    return x * np.minimum(1, t / .003)


def pad_chord(notes, length, bright):
    """デチューンしたノコギリ波を重ねたパッド（左右に広げる）"""
    n = int(SR * (length + .25))
    t = t_of(n)
    left, right = np.zeros(n), np.zeros(n)
    for m in notes:
        for k, cents in enumerate((-14, -6, 0, 7, 15)):
            v = saw(midi_hz(m) * 2 ** (cents / 1200), n, rng.random()) / 5
            pan = (k - 2) / 2.5
            left += v * (1 - pan) / 2
            right += v * (1 + pan) / 2
    env = np.minimum(1, t / .03) * np.where(t < length, 1.0, np.exp(-(t - length) / .08))
    st = np.stack([left, right], axis=1) * env[:, None] / len(notes)
    return lowpass(st, 900 + 3600 * bright)


# ── 曲の構成 ────────────────────────────────────────────────
VOICING = {
    "F": [53, 57, 60, 65], "G": [55, 59, 62, 67], "Em": [52, 55, 59, 64], "Am": [57, 60, 64, 69],
    "Dm": [50, 53, 57, 62], "E": [52, 56, 59, 64], "C": [48, 52, 55, 60, 64],
}
ROOT = {"F": 41, "G": 43, "Em": 40, "Am": 45, "Dm": 38, "E": 40, "C": 36}
CYCLE = ["F", "G", "Em", "Am"]


def chords_of(bar):
    """小節（1始まり）→ [(拍, 長さ拍, コード)]。IV-V-iii-vi（王道進行）を基本に、サビ前で盛り上げる"""
    special = {1: "F", 2: "G", 3: "Am", 24: "Dm", 25: "E", 30: "C"}
    if bar == 28:
        return [(0, 2, "Em"), (2, 2, "Am")]
    if bar == 29:
        return [(0, 2, "F"), (2, 2, "G")]
    if bar in special:
        return [(0, 4, special[bar])]
    return [(0, 4, CYCLE[(bar - 4) % 4])]


def section_of(bar):
    if bar <= 3:
        return "intro"
    if bar <= 6 or 26 <= bar <= 29:
        return "drop"
    if bar <= 10 or 21 <= bar <= 24:
        return "main"
    if bar <= 16:
        return "groove"
    if bar <= 19:
        return "break"
    if bar in (20, 25):
        return "build"
    return "end"


MELODY = {
    "F": [(0, .5, 72), (.5, .5, 69), (1, .5, 72), (1.5, 1, 74), (2.5, .5, 72), (3, 1, 69)],
    "G": [(0, .5, 71), (.5, .5, 67), (1, .5, 71), (1.5, 1, 74), (2.5, .5, 76), (3, 1, 74)],
    "Em": [(0, 1, 76), (1, .5, 74), (1.5, .5, 71), (2, 1, 67), (3, 1, 71)],
    "Am": [(0, .5, 72), (.5, .5, 71), (1, 1.5, 69), (2.5, .5, 64), (3, 1, 69)],
}


def build_music():
    drums = np.zeros(N)
    bass = np.zeros(N)
    keys = np.zeros((N, 2))
    lead = np.zeros(N)
    fx = np.zeros(N)
    kick_times = []
    k, c, h, ho = kick(), clap(), hat(), hat(True)

    for bar in range(1, 31):
        b0 = (bar - 1) * BAR
        sec = section_of(bar)
        chords = chords_of(bar)

        # ドラム
        if sec in ("drop", "main", "groove"):
            for beat in range(4):
                place(drums, k, b0 + beat * BEAT)
                kick_times.append(b0 + beat * BEAT)
            for beat in (1, 3):
                place(drums, c * .8, b0 + beat * BEAT)
            for e in range(8):
                hh = ho if (sec == "drop" and e % 2 == 1 and e in (3, 7)) else h
                place(drums, hh * (.35 if e % 2 else .15), b0 + e * BEAT / 2)
            if sec == "drop":
                for s in range(16):
                    if s % 2:
                        place(drums, h * .07, b0 + s * BEAT / 4)
        elif sec == "break":
            place(drums, k * .7, b0)
            kick_times.append(b0)
            place(drums, k * .5, b0 + 2.5 * BEAT)
            for e in range(1, 8, 2):
                place(drums, h * .15, b0 + e * BEAT / 2)
        elif sec == "build":
            # スネアロール（だんだん細かく・大きく）
            hits = [(i * .5, .25) for i in range(4)] + [(2 + i * .25, .4) for i in range(4)] + [(3 + i * .125, .6) for i in range(8)]
            roll = .55 if bar == 20 else 1.0   # 20小節目はナレーション中なので控えめに
            for beat, vel in hits:
                place(drums, c * vel * roll, b0 + beat * BEAT)
            if bar == 25:
                for beat in range(2):
                    place(drums, k, b0 + beat * BEAT)
                    kick_times.append(b0 + beat * BEAT)
        if bar == 3:
            for i in range(8):
                place(drums, c * (.15 + .06 * i), b0 + (2 + i * .25) * BEAT)

        # 頭にインパクト（サビの入り・最後のキメ）
        if bar in (4, 26):
            place(fx, impact(), b0)
        if bar == 30:
            place(fx, impact() * .9, b0)
            place(drums, k, b0)
        if bar == 3:
            place(fx, riser(BAR) * .8, b0)
        if bar == 20:
            place(fx, riser(BAR) * .45, b0)
        if bar == 25:
            place(fx, riser(BAR) * .8, b0)

        for beat0, beats, name in chords:
            s = b0 + beat0 * BEAT
            length = beats * BEAT
            root = ROOT[name]
            # パッド（イントロはこもった音 → だんだん明るく）
            if sec == "intro":
                bright = .2 + .3 * (bar - 1) / 2
            elif sec in ("break", "build"):
                bright = .3
            elif sec == "end":
                bright = .6
            else:
                bright = .55 if sec == "groove" else .8
            vol = {"intro": 1.1, "break": .7, "build": .55, "groove": .45, "end": .9}.get(sec, .65)
            place(keys, pad_chord(VOICING[name], length if sec != "end" else 1.9, bright) * vol, s)

            # ベース
            if sec in ("drop", "main", "groove"):
                for e in range(int(beats * 2)):
                    n = int(SR * BEAT / 2 * .9)
                    t = t_of(n)
                    m = root + (12 if e % 4 == 3 else 0)
                    x = (saw(midi_hz(m), n) * .45 + np.sin(2 * np.pi * midi_hz(m) * t)) * np.minimum(1, t / .004) * np.exp(-t / .5)
                    place(bass, x, s + e * BEAT / 2)
            elif sec in ("break", "build", "intro") and bar > 1:
                n = int(SR * length)
                t = t_of(n)
                x = np.sin(2 * np.pi * midi_hz(root) * t) * np.minimum(1, t / .05) * np.minimum(1, (length - t) / .05)
                place(bass, x * (.5 if sec == "intro" else .7), s)
            elif sec == "end":
                n = int(SR * 1.9)
                t = t_of(n)
                place(bass, np.sin(2 * np.pi * midi_hz(root) * t) * np.exp(-t / .8), s)

            # アルペジオ（16分）
            if sec in ("intro", "main", "groove", "break", "build") and not (sec == "intro" and bar == 1):
                tones = [x + 12 for x in VOICING[name][:3]] + [VOICING[name][0] + 24]
                pattern = [0, 1, 2, 3, 2, 1, 2, 3]
                vel = {"intro": .22, "main": .3, "groove": .22, "break": .32, "build": .28}[sec]
                for i in range(int(beats * 4)):
                    note = pluck(tones[pattern[i % 8]], .3, bright=.6 if sec != "intro" else .3)
                    place(keys, np.stack([note * (.7 if i % 2 else .3), note * (.3 if i % 2 else .7)], axis=1) * vel, s + i * BEAT / 4)

            # メロディ（サビだけ）。半小節のコードはフレーズの前半だけ使う
            if sec == "drop":
                for beat, dur, m in MELODY[name]:
                    if beat < beats:
                        place(lead, bell(m, dur * BEAT), s + beat * BEAT)
        if bar == 30:
            for m in (72, 76, 79):
                place(lead, bell(m, 1.5) * .7, b0)

    # キックに合わせてパッドとベースを「ポンプ」させる（サイドチェイン）
    pump = np.ones(N)
    t = t_of(int(SR * BEAT))
    shape = 1 - .55 * np.exp(-t / .11)
    for kt in kick_times:
        i0 = int(kt * SR)
        seg = shape[: N - i0]
        pump[i0:i0 + len(seg)] = np.minimum(pump[i0:i0 + len(seg)], seg)

    bass = lowpass(bass, 700) * pump * .55
    keys = keys * pump[:, None]
    # 残響（合成したインパルス応答で畳み込み）
    ir_n = int(SR * 1.8)
    ir_t = t_of(ir_n)
    ir = rng.standard_normal((ir_n, 2)) * np.exp(-ir_t / .45)[:, None]
    ir[: int(.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2, axis=0))
    wet_src = np.stack([lead * .5, lead * .5], axis=1) + keys * .5
    wet = np.stack([ss.fftconvolve(wet_src[:, ch], ir[:, ch])[:N] for ch in range(2)], axis=1)

    mix = np.zeros((N, 2))
    mix += drums[:, None] * .55
    mix += bass[:, None]
    mix += keys * .55
    mix += np.stack([lead, lead], axis=1) * .22
    mix += fx[:, None] * .35
    mix += wet * .22
    return mix


def duck_curve(timeline, depth=0.38):
    """ナレーション中は BGM を下げる（入りは速く、戻りはゆっくり）"""
    g = np.ones(N)
    for seg in timeline:
        a, b = int((seg["start"] - .12) * SR), int((seg["end"] + .15) * SR)
        g[max(a, 0):min(b, N)] = depth
    smooth_attack = int(.08 * SR)
    smooth_release = int(.35 * SR)
    out = np.copy(g)
    for i in range(1, N):
        # 下げるときは速く・戻すときはゆっくり（1次の追従）
        coef = 1 / smooth_attack if g[i] < out[i - 1] else 1 / smooth_release
        out[i] = out[i - 1] + (g[i] - out[i - 1]) * coef
    return out


def main(out_path):
    voice, timeline = build_narration()
    music = build_music()
    music /= np.max(np.abs(music)) + 1e-9
    duck = duck_curve(timeline)
    mix = music * .75 * duck[:, None] + voice[:, None] * .8
    # 終わりは自然に消える
    fade = int(SR * .8)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    mix = np.tanh(1.2 * mix) / np.tanh(1.2)
    mix *= .89 / np.max(np.abs(mix))
    wavfile.write(out_path, SR, (mix * 32767).astype(np.int16))
    print(json.dumps(timeline, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "liver_recruit_audio.wav")
