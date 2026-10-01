# motion_render — /motion 作例動画の制作ツール

`/motion` ページに載せている作例動画（`src/static/motion/*.mp4` と同名のポスター `.jpg`）は、
このフォルダのスクリプトから書き出しています。テキストや色を変えて作り直すときに使います。
**ページへの掲載・差し替えだけなら、このツールは不要**です（`persona/motion_config.yaml` を編集するだけ）。

## 仕組み
- `scenes/<作例id>.js` … 作例1本ぶんのアニメーション。時刻 `t`（秒）を受け取って1コマを Canvas に描く
- `lib.js` … 共通部品（キャラ表示・文字アニメ・パーティクル・吹き出しなど）
- `render.mjs` … ヘッドレス Chromium で1コマずつ描き、ffmpeg で 720p・30fps・音なしの H.264 mp4 に書き出す
- `chars/c1〜c5.webp` … キャラクター画像（背景透過済み）

## キャラクターの割り当て
各作例のメインキャラは、日付をシードにしたランダムなシャッフルで決めています（各キャラ3本ずつ）。

| キャラ | 作例 |
|---|---|
| c1（青髪・白Tシャツ） | lyric-motion / release-teaser / company-intro |
| c2（KDマスコット） | goods-promo / recruit / caption-edit |
| c3（ロングヘア・黒の衣装） | stream-alert / sns-ad / event-notice |
| c4（メガネ・ブラウス） | infographic / signage / tool-demo |
| c5（銀髪・黒Tシャツ） | stream-opening / liver-profile / logo-animation |

`recruit` と `company-intro` は後半で5人全員が登場します。

## 作り直す手順
```bash
cd tools/motion_render
python3 fetch_fonts.py                       # 初回のみ（Google Fonts を fonts/ に取得）
node render.mjs liver-profile stills 1,4,8   # 確認用のコマを review/ に出力
node render.mjs liver-profile video          # src/static/motion/ の mp4 とポスターを上書き
node render.mjs all video                    # 全作例を書き出し
```
- 必要なもの: Node.js、`playwright`（`npm i -g playwright` など）、ffmpeg、Python 3
- 1本 3MB を超えたら警告が出ます。`CRF=28 node render.mjs ...` のように CRF を上げると軽くなります。
- 店名・価格・日付・名前（「LIVER NAME」「20XX」「〇〇ライブホール」など）はサンプル表記です。
  実案件用に変えるときは各 `scenes/*.js` の文字列を書き換えてください。

## ホームページ（eternaldct.net）への反映
ホームページは静的サイト（`eternaldct-png/ETERNAL-` リポジトリの `eternaldct-new-site/`）。作例集は `motion.html`。
```bash
# 作例の一覧と動画・ポスターを motion.html / assets/motion/ に反映（このリポジトリのルートで）
python3 tools/motion_render/export_homepage.py <eternaldct-new-site のパス>
# SNS共有用の画像（1200×630・作例ポスター3枚を合成）
python3 tools/motion_render/make_eyecatch.py <eternaldct-new-site のパス>/assets/motion/ogp.jpg
```
その後、サイトの管理画面からいつもどおりサーバーに反映する。
