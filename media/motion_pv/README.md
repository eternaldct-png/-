# モーション動画の元データ

HTML/CSS のアニメーションを1フレームずつ撮影して MP4 に書き出す。

| ファイル | 中身 |
|---|---|
| `pv.html` | 作例PV（MOTION WORKS）1920×1080 / 約62秒 / 14スタイルのダイジェスト |
| `liver_recruit.html` | ライバー募集動画 1080×1920（縦型）/ 60秒 / SNS向け |
| `motion.css` `motion.js` | 共通部品（シーンの表示区間・動きの種類・切り替えのワイプ・書き出し用の時刻制御） |
| `render.js` | 書き出しスクリプト（`--page` で対象を選ぶ） |

映像の出力は 30fps・H.264。ライバー募集動画は `audio/liver_recruit_audio.py` で作ったナレーションと BGM を後から合わせる（下記）。

## ライバー募集動画（liver_recruit.html）

カットはすべて 2秒単位（120BPM の1小節）なので、120BPM の BGM を頭からのせると拍に合う。

| 時間 | シーン |
|---|---|
| 0:00–0:06 | フック「歌うのが、好き。話すのが、好き。」→「その『好き』を、配信してみませんか？」 |
| 0:06–0:12 | LIVER AUDITION／ライバー募集中！ |
| 0:12–0:20 | 所属ライバー 61名（2026年10月時点）＋人アイコン61個、空き枠「YOU」→「次は、あなたの番。」 |
| 0:20–0:32 | こんな人を待っています（歌が好き／話すのが好き／副業で／主婦・主夫の方も／配信未経験でもOK） |
| 0:32–0:40 | ETERNAL d.c.t って？（ライバー事務所・音楽制作・グッズ制作販売／代表も現役の配信者） |
| 0:40–0:50 | 応募の流れ（応募フォーム → 審査結果をメール → 面談 → 所属・配信スタート）／未成年は保護者の同意が必要 |
| 0:50–1:00 | 「あなたの『好き』を、配信で届けよう。」／応募はプロフィールのリンクから |

- 所属ライバー数を更新するときは `data-count="61"`・`data-dots="61"`（人アイコンの数。`data-total` は空き枠を含む総数）・
  「所属ライバー61名」・「2026年10月時点」を書き換える。
- 文字は TikTok・リールの上下と右端のボタンに隠れにくいよう、中央の 約 840px 幅・上下 260〜1500px に収めている。
- 投稿前に Render の `AUDITION_STATUS` が `open` になっているか確認する（`closed` だと応募フォームが受付終了画面になる）。

### 音声（ナレーション＋BGM）

- ナレーション: Open JTalk（`pyopenjtalk-plus` に同梱の HTS Voice "Mei"）。読み上げる文と開始時刻は
  `audio/liver_recruit_audio.py` の `NARRATION`。読み間違える語はひらがなで書く（例: 「はじめたいひと」「主夫」）。
  文言や時刻を変えたら、`liver_recruit.html` の文字の出るタイミング（`--d`）もそろえる。
- BGM: 同じスクリプト内で numpy / scipy から合成したオリジナル曲（120BPM・IV–V–iii–vi の王道進行）。
  外部の音源は使っていないので権利表記は不要。ナレーション中は自動で音量を下げる。
- **クレジット表記が必要（CC BY 3.0）**: 投稿の説明文などに
  `ナレーション音声: HTS Voice "Mei" (c) 2009-2013 Nagoya Institute of Technology (CC BY 3.0)` を入れる。

```bash
pip install pyopenjtalk-plus numpy scipy
python media/motion_pv/audio/liver_recruit_audio.py audio.wav
node media/motion_pv/render.js video.mp4 --page liver_recruit.html
# 合成して SNS 向けの音量（-14 LUFS）にそろえる
ffmpeg -i video.mp4 -i audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000" -c:a aac -b:a 192k -movflags +faststart -shortest liver_recruit.mp4
```

## 作例PV（pv.html）

### シーン構成（120BPM・1小節=2秒のグリッドでカット）

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
# ライバー募集動画
FFMPEG=/path/to/ffmpeg node media/motion_pv/render.js liver_recruit.mp4 --page liver_recruit.html
# 一部だけ: --from 26 --to 30
```

書き出した MP4 はリポジトリにコミットしない（`.gitignore` 済み）。
`/motion` ページに載せる場合は YouTube（限定公開）にアップして `persona/motion_config.yaml` の `youtube:` に URL を貼る。

## 編集のしかた

- 文言: 各ページの `<section class="scene ...">` 内のテキストを書き換える。
- シーンの開始時刻・長さ: `data-s`（開始秒）と `data-len`（秒）。変えたら後ろのシーンもずらし、
  `#stage` の `data-duration`（全体の秒数）も合わせる。シーン切り替えのワイプは `data-s` から自動で入る。
- 要素ごとの動き: `class="fx fadeUp"` のように動きの種類を指定し、`--d`（シーン開始からの遅れ）と `--dur`（長さ）で調整。
  `--d` などは親から引き継がれるので、`.fx` の中に `.fx` を入れるときは子にも `--d` を書く。
