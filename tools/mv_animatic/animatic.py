"""MV「愛なき世界で」確認用の絵コンテ動画(添付画像1枚 + 曲)を書き出す。"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

IMG, AUDIO, OUT, SRT = sys.argv[1:5]
W, H, FPS, DUR = 540, 960, 24, 323.16
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
f_big = ImageFont.truetype(FONT, 34)
f_mid = ImageFont.truetype(FONT, 22)
f_sm = ImageFont.truetype(FONT, 17)
f_title = ImageFont.truetype(FONT, 54)

src = Image.open(IMG).convert("RGB")  # 908x2000
SW, SH = src.size
WIN_H = SW * 16 / 9  # 9:16 の窓(ズーム1のとき)

# 画像内の注目点
FACE, WIDE, SKY, HAND, DRESS, SEA, SAND = (440, 700), (454, 1000), (454, 330), (660, 1080), (454, 1500), (760, 620), (700, 1800)

# 色: (彩度開始, 彩度終了, 色味RGB倍率, 明るさ)
MONO = (0.0, 0.0, (0.95, 1.0, 1.05), 0.85)
MUTE = (0.25, 0.35, (0.97, 1.0, 1.03), 0.9)
BLOOM = (0.0, 1.0, (1.0, 1.0, 1.0), 1.0)
WARMUP = (0.35, 0.7, (1.04, 1.0, 0.95), 0.95)
BURST = (0.2, 1.25, (1.0, 1.0, 1.0), 1.05)
FULL = (1.15, 1.2, (1.0, 1.0, 1.0), 1.05)
SUNSET = (0.75, 0.7, (1.18, 0.95, 0.72), 0.92)
NIGHT = (0.35, 0.4, (0.7, 0.82, 1.15), 0.55)
DRAIN = (1.1, 0.0, (1.0, 1.0, 1.0), 0.9)
REVIVE = (0.0, 1.25, (1.0, 1.0, 1.0), 1.05)

# (開始秒, 終了秒, パート, カット名, 内容, 注目点開始, 注目点終了, ズーム開始, ズーム終了, 色)
C = [
    (0, 7, "イントロ", "#1", "灰色の海辺・遠くに後ろ姿", SKY, WIDE, 1.0, 1.08, MONO),
    (7, 14, "イントロ", "#2", "乾いた砂に指で書きかけてやめる", SAND, SAND, 1.6, 1.8, MONO),
    (14, 21, "Aメロ1", "#3", "灰色の部屋・窓辺で無表情", WIDE, FACE, 1.05, 1.3, MONO),
    (21, 28, "Aメロ1", "#4", "コップの水が乾いていく(心の比喩)", HAND, HAND, 2.0, 2.3, MONO),
    (28, 35, "Aメロ1", "#5", "遠くに逆光のシルエット(=君)が現れる", SEA, SEA, 1.5, 1.7, MUTE),
    (35, 42, "Aメロ1", "#6", "頬と唇にだけ色が戻る", FACE, FACE, 1.8, 2.1, BLOOM),
    (42, 49, "Aメロ2", "#7", "名前を呼びかけて口をつぐむ", FACE, FACE, 1.6, 1.75, MUTE),
    (49, 56, "Aメロ2", "#8", "ガラス越しに手が重なりかける", HAND, HAND, 1.9, 2.1, MUTE),
    (56, 63, "Aメロ2", "#9", "鏡の前で髪を結ぶ・表情がゆるむ", SKY, FACE, 1.4, 1.6, WARMUP),
    (63, 70, "Aメロ2", "#10", "歩くたびに砂と海に色が戻る", SAND, WIDE, 1.5, 1.1, WARMUP),
    (70, 77, "Bメロ", "#11", "胸に手を当て、息が浅くなる", DRESS, FACE, 1.5, 1.7, WARMUP),
    (77, 84, "Bメロ", "#12", "波打ち際を走り出す背中", WIDE, SEA, 1.0, 1.3, (0.7, 0.95, (1, 1, 1), 1.0)),
    (84, 91, "サビ1", "#13", "海が一気に青くなる(色の爆発1回目)", SEA, WIDE, 1.4, 1.0, BURST),
    (91, 98, "サビ1", "#14", "カメラを見つめて歌う", FACE, FACE, 1.5, 1.7, FULL),
    (98, 105, "サビ1", "#15", "手のひらから光の粒が君へ伸びる", HAND, SEA, 1.8, 1.5, FULL),
    (105, 112, "サビ1", "#16", "振り返って手を伸ばす", WIDE, FACE, 1.1, 1.5, FULL),
    (112, 119, "間奏", "#17", "夕暮れ・膝を抱えて座る", SKY, WIDE, 1.2, 1.0, SUNSET),
    (119, 126, "間奏", "追加", "夕日の波・砂浜の足あと", SAND, SAND, 1.5, 1.7, SUNSET),
    (126, 133, "Aメロ3", "#18", "逆光の君の口元が笑う → 見つめる彼女", FACE, FACE, 2.2, 1.9, SUNSET),
    (133, 140, "Aメロ3", "追加", "歌唱カット(夕日・横顔)", FACE, FACE, 1.5, 1.6, SUNSET),
    (140, 147, "Aメロ3", "#19", "涙が一筋、理由がわからない表情", FACE, FACE, 2.0, 2.3, SUNSET),
    (147, 154, "Aメロ3", "追加", "歌唱カット(夕日・引き)", WIDE, WIDE, 1.0, 1.1, SUNSET),
    (154, 163, "Aメロ4", "#20", "夜の路地、光のない場所で咲く白い花", DRESS, DRESS, 1.8, 2.1, NIGHT),
    (163, 172, "Aメロ4", "#21", "暗闇の中、遠い光へ歩き出す", WIDE, SKY, 1.0, 1.2, NIGHT),
    (172, 180, "サビ2", "#22", "夜の浜辺・周りに白い花が咲いていく", WIDE, WIDE, 1.15, 1.0, NIGHT),
    (180, 188, "サビ2", "追加", "歌唱カット(月明かり・正面)", FACE, FACE, 1.5, 1.7, NIGHT),
    (188, 196, "サビ2", "#23", "胸元の光が君のシルエットを照らす", DRESS, FACE, 1.6, 1.6, (0.4, 0.75, (0.85, 0.9, 1.08), 0.75)),
    (196, 204, "サビ2", "追加", "歌唱カット(夜・手元)", HAND, HAND, 1.8, 2.0, NIGHT),
    (204, 212, "サビ2", "追加", "花びらが舞う・ゆっくり回る", SKY, WIDE, 1.3, 1.1, NIGHT),
    (212, 220, "サビ2", "追加", "歌唱カット(夜・アップ)", FACE, FACE, 1.9, 2.1, NIGHT),
    (220, 226, "ブレイク", "#24", "世界が灰色に戻る・君が砂になって消える", WIDE, WIDE, 1.0, 1.05, DRAIN),
    (226, 234, "サビ3", "#25", "一気に色が戻る・サングラスを外して笑う", HAND, FACE, 1.3, 1.5, REVIVE),
    (234, 241, "サビ3", "追加", "歌唱カット(真昼・正面)", FACE, FACE, 1.5, 1.7, FULL),
    (241, 248, "サビ3", "追加", "波しぶき・光の反射", SEA, SEA, 1.6, 1.9, FULL),
    (248, 255, "サビ3", "追加", "歌唱カット(全身・回る)", WIDE, WIDE, 1.0, 1.12, FULL),
    (255, 262, "サビ3", "追加", "手を空へ伸ばす", HAND, SKY, 1.6, 1.3, FULL),
    (262, 268, "サビ3", "追加", "歌唱カット(アップ)", FACE, FACE, 1.9, 2.1, FULL),
    (268, 275, "最後のサビ", "#26", "自撮りの角度のまま歌う", FACE, FACE, 1.4, 1.6, FULL),
    (275, 282, "最後のサビ", "追加", "白い花が昼の浜辺に咲いている", SAND, DRESS, 1.6, 1.4, FULL),
    (282, 289, "最後のサビ", "追加", "歌唱カット(海を背に)", WIDE, FACE, 1.05, 1.4, FULL),
    (289, 296, "最後のサビ", "追加", "光の中のシルエット(君)へ微笑む", SEA, SEA, 1.5, 1.6, FULL),
    (296, 304, "最後のサビ", "追加", "歌唱カット(ラスト・アップ)", FACE, FACE, 1.7, 2.0, FULL),
    (304, 314, "アウトロ", "#26続き", "カメラが引いて空へ上がる", FACE, SKY, 1.6, 1.0, FULL),
    (314, DUR, "アウトロ", "エンド", "花びら1枚が空を漂う → タイトル", SKY, SKY, 1.0, 1.0, (1.1, 0.9, (1, 1, 1), 1.05)),
]

LYR = {
    (14, 42): "愛を知らないまま生きてきた/心はいつも静かで乾いていた/君を見つけたその瞬間に/世界が少しだけ色づいた",
    (42, 70): "名前を呼ぶ声が欲しくなる/触れられない距離が苦しくなる/こんな気持ち　知らなかった/君が私を変えていく",
    (70, 84): "胸の奥が熱くなる/理由なんていらない/ただ君がいるだけで/息が乱れてしまう",
    (84, 112): "愛なき世界で　君を想う/知らない感情に戸惑いながら/それでも君を求めてしまう/光よりも強い衝動で/君へ伸びていく心は/もう止められない",
    (126, 154): "君の笑顔が胸を締めつける/涙の意味もわからないまま/ただ一つだけ確かなこと/君を失いたくないということ",
    (154, 172): "もし世界が愛を持たなくても/私は君を選んでしまう/初めて知ったこの痛みが/私を君へ導いていく",
    (172, 220): "愛なき世界で　君を想う/叶わない恋でも離れられない/光を知らぬ花のように/君だけを求めて 咲き続ける/この想いは 君を照らす/名前のない愛のまま",
    (226, 268): "愛なき世界で　君を想う/知らない感情に戸惑いながら/それでも君を求めてしまう/光よりも強い衝動で/君へ伸びていく/心はもう止められない",
    (268, 304): "愛なき世界で　君を想う/叶わない恋でも離れられない/光を知らぬ花のように/君だけを求めて咲き続ける/この想いは 君を照らす/名前のない愛のまま",
}
lyrics = []
for (a, b), text in LYR.items():
    lines = text.split("/")
    step = (b - a) / len(lines)
    for i, ln in enumerate(lines):
        lyrics.append((a + i * step, a + (i + 1) * step - 0.3, ln))


def fmt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


with open(SRT, "w", encoding="utf-8") as f:
    for i, (a, b, ln) in enumerate(lyrics, 1):
        f.write(f"{i}\n{fmt(a)} --> {fmt(b)}\n{ln}\n\n")


def text_layer(draw_fn):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    shadow = im.split()[3].filter(ImageFilter.GaussianBlur(3))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(shadow.point(lambda v: min(255, v * 2)))
    return Image.alpha_composite(sh, im)


def header(c):
    a, b, part, cut, desc = c[:5]

    def d(dr):
        dr.rectangle((0, 0, W, 92), fill=(0, 0, 0, 120))
        dr.text((16, 12), f"{cut}  {part}  {int(a)//60}:{int(a)%60:02d}–{int(b)//60}:{int(b)%60:02d}", font=f_mid, fill=(255, 255, 255, 255))
        dr.text((16, 48), desc, font=f_mid, fill=(255, 230, 160, 255))
        dr.text((16, H - 30), "確認用の絵コンテ動画 / 歌詞の位置は推定", font=f_sm, fill=(255, 255, 255, 170))
    return np.asarray(text_layer(d)).astype(np.float32) / 255


def lyric_img(ln):
    def d(dr):
        tw = dr.textlength(ln, font=f_big)
        dr.text(((W - tw) / 2, H - 150), ln, font=f_big, fill=(255, 255, 255, 255))
    return np.asarray(text_layer(d)).astype(np.float32) / 255


def title_img():
    def d(dr):
        t = "愛なき世界で"
        tw = dr.textlength(t, font=f_title)
        dr.text(((W - tw) / 2, H * 0.42), t, font=f_title, fill=(255, 255, 255, 255))
    return np.asarray(text_layer(d)).astype(np.float32) / 255


headers = [header(c) for c in C]
lyr_imgs = [lyric_img(l[2]) for l in lyrics]
TITLE = title_img()
src_np = src


def ease(x):
    return x * x * (3 - 2 * x)


def render_base(c, t):
    a, b = c[0], c[1]
    p = ease(min(1, max(0, (t - a) / (b - a))))
    (x0, y0), (x1, y1), z0, z1, grade = c[5], c[6], c[7], c[8], c[9]
    z = z0 + (z1 - z0) * p
    cx, cy = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    wh, ww = WIN_H / z, SW / z
    cx = min(max(cx, ww / 2), SW - ww / 2)
    cy = min(max(cy, wh / 2), SH - wh / 2)
    box = (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2)
    fr = np.asarray(src_np.resize((W, H), Image.BILINEAR, box=box)).astype(np.float32) / 255
    s0, s1, tint, br = grade
    s = s0 + (s1 - s0) * p
    gray = fr @ np.array([0.299, 0.587, 0.114], np.float32)
    fr = gray[..., None] + (fr - gray[..., None]) * s
    fr = fr * np.array(tint, np.float32) * br
    return np.clip(fr, 0, 1)


def over(fr, layer, alpha=1.0):
    a = layer[..., 3:4] * alpha
    return fr * (1 - a) + layer[..., :3] * a


XF = 0.35
ff = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-i", AUDIO, "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT],
    stdin=subprocess.PIPE)

n = int(DUR * FPS)
ci = 0
for k in range(n):
    t = k / FPS
    while ci < len(C) - 1 and t >= C[ci][1]:
        ci += 1
    c = C[ci]
    fr = render_base(c, t)
    if ci > 0 and t < c[0] + XF:  # 前のカットからのクロスフェード
        w = (t - c[0]) / XF
        fr = render_base(C[ci - 1], t) * (1 - w) + fr * w
    if t < 1.0:
        fr = fr * t
    if t > DUR - 2:
        fr = fr * max(0, (DUR - t) / 2)
    fr = over(fr, headers[ci])
    for (a, b, _), li in zip(lyrics, lyr_imgs):
        if a <= t < b:
            fade = min(1, (t - a) / 0.3, (b - t) / 0.3)
            fr = over(fr, li, fade)
            break
    if t < 6:
        fr = over(fr, TITLE, min(1, (t - 1) / 1.0, (6 - t) / 1.0) if t > 1 else 0)
    if t > 314:
        fr = over(fr, TITLE, min(1, (t - 314) / 1.5))
    ff.stdin.write((fr * 255).astype(np.uint8).tobytes())
    if k % 1200 == 0:
        print(f"{t:.0f}s", flush=True)
ff.stdin.close()
ff.wait()
print("done", ff.returncode)
