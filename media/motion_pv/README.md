# モーション動画 作例PV（MOTION WORKS）

「こんな動画がつくれます」を約1分で見せるプロモーションビデオの元データ。
HTML/CSS のアニメーションを1フレームずつ撮影して MP4 に書き出す。

- 出力: 1920×1080 / 30fps / 約62秒 / H.264（音声なし）
- `pv.html` … 映像の中身（テキスト・色・タイミングはすべてここ）
- `render.js` … 書き出しスクリプト

## シーン構成（120BPM・1小節=2秒のグリッドでカット）

BGM を 120BPM の曲にして頭をそろえると、カットが拍に合う。

| 時間 | No | シーン | 縦横比 |
|---|---|---|---|
| 0:00–0:04 | – | イントロ（MOTION WORKS） | 16:9 |
| 0:04–0:07.5 | 01 | ロゴアニメーション | 16:9 |
| 0:07.5–0:11.5 | 02 | 配信オープニング・待機画面 | 16:9 |
| 0:11.5–0:14.5 | 03 | ギフト・フォロー演出 | 1:1 |
| 0:14.5–0:18.5 | 04 | ライバー紹介プロフィール | 9:16 |
| 0:18.5–0:22.5 | 05 | リリックモーション（歌詞動画） | 16:9 |
| 0:22.5–0:26 | 06 | 新曲リリース告知 | 16:9 |
| 0:26–0:30 | 07 | SNS縦型広告 | 9:16 |
| 0:30–0:34 | 08 | グッズ・商品プロモーション | 4:5 |
| 0:34–0:37.5 | 09 | イベント・キャンペーン告知 | 16:9 |
| 0:37.5–0:41.5 | 10 | 求人・オーディション募集 | 16:9 |
| 0:41.5–0:45 | 11 | テロップ・字幕アニメーション | 16:9 |
| 0:45–0:49 | 12 | サービス紹介（インフォグラフィック） | 16:9 |
| 0:49–0:52.5 | 13 | 店頭サイネージ・メニュー | 16:9 |
| 0:52.5–0:56.5 | 14 | ツール操作デモ | 16:9 |
| 0:56.5–1:02 | – | アウトロ（一覧 → ロゴ・お問い合わせ） | 16:9 |

作中の人名・店名・曲名・日付・数値（HIKARI、LUMINA、ソラノオト、70% など）はすべて架空のサンプル。

## 準備（初回のみ）

フォント（`media/fonts/` に置く。リポジトリには含めない）:

```bash
cd media/fonts
for w in Black Bold Medium; do
  curl -sSLO https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/Japanese/NotoSansCJKjp-$w.otf
done
curl -sSL -o Montserrat.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
```

- Playwright（`npm i -g playwright` など）と ffmpeg（libx264 入り）が必要。
  ffmpeg がない環境では `pip install imageio-ffmpeg` で入る静的バイナリを `FFMPEG` に指定すればよい。

## プレビュー・書き出し

```bash
# ブラウザで再生（フォント読み込みのため Chromium は --allow-file-access-from-files 付きで開く）
#   pv.html?t=30 … 30秒地点で停止した状態を表示

# 静止画だけ確認
node media/motion_pv/render.js check.png --stills 5,20,45

# 全編を書き出し（数分かかる）
FFMPEG=/path/to/ffmpeg node media/motion_pv/render.js motion_pv.mp4
# 一部だけ: --from 26 --to 30
```

書き出した MP4 はリポジトリにコミットしない（`.gitignore` 済み）。
`/motion` ページに載せる場合は YouTube（限定公開）にアップして `persona/motion_config.yaml` の `youtube:` に URL を貼る。

## 編集のしかた

- 文言: `pv.html` の各 `<section class="scene ...">` 内のテキストを書き換える。
- シーンの開始時刻・長さ: `data-s`（開始秒）と `data-len`（秒）。変えたら後ろのシーンもずらし、
  `DURATION`（全体の秒数）も合わせる。シーン切り替えのワイプは `data-s` から自動で入る。
- 要素ごとの動き: `class="fx fadeUp"` のように動きの種類を指定し、`--d`（シーン開始からの遅れ）と `--dur`（長さ）で調整。
