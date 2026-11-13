# アマテラス MV（プログラムで描くミュージックビデオ）

楽曲「アマテラス」（4分26秒）のMVを、コードだけで描いて書き出すプロジェクト。
動画生成AI・有料素材・APIキーは使っていない。

- 完成品: `out/amaterasu_mv.mp4`（1920×1080 / 30fps / H.264 + AAC）
- 素材: `assets/`（音源 `song.mp3`、キャラ画像4枚、ロゴ）

## しくみ

| 層 | 技術 | 内容 |
|---|---|---|
| 背景 | WebGL2 フラグメントシェーダー | 太陽・コロナ・日食・天の岩戸・水平線の映り込み・白い朝 |
| レイヤー | Canvas 2D | 文字（縦書き/横書き・1字ずつの動き）、キャラ、向日葵、図形、粒子、簡易3Dカメラ |
| 仕上げ | WebGL2 | 合成、ブルーム、色収差、揺れ、粒状感、周辺減光、フラッシュ |
| 書き出し | Playwright（ヘッドレスChromium）→ ffmpeg | 1フレームずつ描いて4並列でエンコード、最後に音源と結合 |

すべての絵は「時刻 t の関数」なので、同じ t なら必ず同じ絵になる（途中から・並列で描ける）。

## 音との同期

`src/sync.py` が音源を解析して `assets/sync.json` を作る。

- テンポ: 177.78 BPM で一定（1拍 0.3375秒 / 1小節 1.35秒、最初の拍は 0.142秒）
- キック・スネア・全体のアタックの時刻と強さ
- 低域・中域・高域の音量の変化（60Hz）

シーンの切り替えは小節の頭（`B(小節番号)`）、文字の登場は歌詞の時刻、揺れや光はキックに合わせている。

## 使い方

```bash
npm install                     # フォント（Shippori Mincho B1 / Dela Gothic One / Cinzel）
pip install numpy scipy librosa pillow
python3 src/sync.py             # 音源を替えたとき（analysis/mono.wav を先に作る。下記）
python3 src/cutout.py           # キャラ画像を替えたとき（白背景を切り抜く）
node render.js --stills 16.6,80,214   # 指定した秒の静止画 → out/stills/
python3 sheet.py 名前                  # 静止画を1枚にまとめる → out/名前.jpg
node render.js --range 70 80 --name test   # 一部だけ書き出す（音つき）
node render.js --full                 # 全編を書き出す（4並列で30〜40分）
node render.js --serve                # ブラウザで音と一緒にプレビュー（?t=秒 で頭出し）
```

`analysis/mono.wav` の作り方:

```bash
ffmpeg -i assets/song.mp3 -ar 22050 -ac 1 analysis/mono.wav
```

## ファイル

| ファイル | 内容 |
|---|---|
| `src/engine.js` | 描画エンジン（シェーダー、文字組み、カメラ、画像の加工、1フレームの描画） |
| `src/scenes.js` | 0:00〜1:16（岩戸 / 題字 / Aメロ / 文字の回廊 / 瞳 / 夜の崩壊） |
| `src/scenes_b.js` | 1:16〜2:46（サビ1・向日葵 / Aメロ2 / ブレイク / サビ2） |
| `src/scenes_c.js` | 間奏と 2:46〜（文字の螺旋 / ブリッジ / ブレイクダウン / 向日葵の海 / 終幕・ロゴ） |
| `src/scenes_z.js` | タイムラインの組み立て |
| `render.js` | 書き出し |

## 直し方の例

- 歌詞の文言・タイミング: 各シーンの `LT('歌詞', …)` と、その後ろの秒数（例 `rise(t, 79.27, …)`）
- 色: `src/scenes.js` 冒頭の `C_WHITE` `C_GOLD` `C_VERM` など
- 太陽の大きさ・明るさ: 各 `bgSeg(...)` の `uSun`（位置と半径）と `uSunI`
- 新しい漢字を使うとき: `src/scenes.js` の `ALLTEXT` に足す（フォントの読み込み対象になる）
