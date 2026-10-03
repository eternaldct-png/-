# Grok（xAI）連携

Grok を4か所で使えるようにしています。**`XAI_API_KEY` を設定しない限り、今までの動き（Claude + DuckDuckGo）は何も変わりません。**

| 用途 | どこで | 動き |
|---|---|---|
| ネタ探し | 自動投稿（GitHub Actions）・投稿ジェネレーター | Grok の **X検索**で「直近3日にXで話題のこと」を集めて投稿文の材料にする。失敗したら DuckDuckGo に戻る |
| 投稿文の生成 | 同上 | `POST_LLM_PROVIDER=grok` で Grok が書く（既定は Claude）。片方が失敗したらもう片方で書く |
| 投稿文の比較 | 投稿ジェネレーター（`/`） | 「書くAI」で **比較** を選ぶと Claude と Grok が同じ条件で1件ずつ書いて並ぶ |
| 画像生成 | `tools/grok/image.py`・Actions「Grok Image」 | Codex / ChatGPT で作れないときの予備 |
| 動画生成 | `tools/grok/video.py`・Actions「Grok Video」 | 数秒〜15秒のクリップを何本も作り、ffmpeg でつないで 1〜2分の動画にする |

---

## 最初の設定

1. **APIキーを発行**: https://console.x.ai → API Keys で作成し、Billing でクレジットを購入（前払い）。
   使いすぎ防止に、Billing で月の上限（spending limit）を設定しておく。
2. **GitHub**: リポジトリの Settings → Secrets and variables → Actions
   - Secrets に `XAI_API_KEY` を追加（自動投稿のネタ探し・Grok Image / Grok Video で使う）
   - 投稿文も Grok に書かせたいときだけ、Variables に `POST_LLM_PROVIDER` = `grok` を追加
3. **Render**（投稿ジェネレーター `kazuto-post-generator`）: Environment に `XAI_API_KEY` を追加
   （「自動」で Grok を優先したいときは `POST_LLM_PROVIDER` = `grok` も）
4. **Mac で動画・画像ツールを使うとき**: ターミナルで `export XAI_API_KEY=xai-...` してから実行。ffmpeg も必要（`brew install ffmpeg`）

### 環境変数

| 変数 | 既定 | 内容 |
|---|---|---|
| `XAI_API_KEY` | なし | 必須。未設定なら Grok は一切使わない |
| `POST_LLM_PROVIDER` | `claude` | 投稿文を書くAI（`claude` / `grok`）。失敗時はもう片方に切り替え |
| `RESEARCH_PROVIDER` | `auto` | `ddg` にすると X検索を使わず DuckDuckGo だけにする（API代の節約） |
| `GROK_MODEL` | `grok-latest` | 文章のモデル。`grok-latest` は常に最新版を指すので、挙動を固定したいときは `grok-4.3` などを指定 |
| `GROK_RESEARCH_MODEL` | `GROK_MODEL` と同じ | ネタ探しだけ別モデルにしたいとき |
| `GROK_REASONING_EFFORT` | `low` | 考える深さ（`none` / `low` / `medium` / `high`）。上げると精度は上がるが遅く・高くなる |
| `GROK_IMAGE_MODEL` | `grok-imagine-image` | 画像のモデル（`--pro` で `grok-imagine-image-pro`） |
| `GROK_VIDEO_MODEL` | `grok-imagine-video` | 動画のモデル。1080p にしたいときは `grok-imagine-video-1.5` |
| `GROK_VIDEO_PRICE_PER_SEC` | `0.08` | 見積もり表示用の単価（USD/秒）。実際の単価に合わせて変える |

---

## 投稿文: Claude と Grok の比べ方

投稿ジェネレーター（`https://kazuto-post-generator.onrender.com/`）の「書くAI」:

- **自動** … `POST_LLM_PROVIDER` のAI → 失敗したらもう片方
- **Claude / Grok** … そのAIだけで書く（失敗しても切り替えない）
- **比較** … Claude と Grok で1件ずつ（件数3件なら3組・最大3組）。カードに「Claude」「Grok」と表示される。🔄 で書き直すと同じAIで書き直す

「どちらが精度が高いか」は、比較モードでしばらく並べて選んだ方を記録するのが確実です。自動投稿を Grok に切り替えるのは、その結果を見てからをおすすめします。

---

## 画像

```bash
python tools/grok/image.py "夜の配信部屋でマイクに向かって歌う青髪の青年、アニメ調" --aspect 4:5
# 所属キャラの見た目を保ちたいとき（参考画像。複数指定可）
python tools/grok/image.py "このキャラがマグカップを持って笑っている" --ref tools/motion_render/chars/c1.webp -n 2
```
- 保存先の既定は `posts/grok_images/`（コミットされない）。`-o src/static/goods/` のように直接保存もできる
- GitHub の Actions →「Grok Image」→ Run workflow でも作れる（スマホ可）。完成画像は実行結果ページの Artifacts から

---

## 動画（1〜2分）

AI動画は1本あたり最大15秒なので、**絵コンテ（YAML）でシーンを並べて、1本ずつ生成 → つなぐ**という流れです。

```bash
# 1) テーマから絵コンテを作る（Grok が書く。キーがなければ Claude）
python tools/grok/video.py plan "ライバー募集の1分PR動画" --seconds 60 --aspect 9:16 \
    -o tools/grok/storyboards/recruit.yaml
# 2) YAML を確認・修正。見積もりだけ見る
python tools/grok/video.py render tools/grok/storyboards/recruit.yaml --dry-run
# 3) 生成 → 結合（見積もりを出して確認してから始まる）
python tools/grok/video.py render tools/grok/storyboards/recruit.yaml
# 4) BGM やつなぎ方だけ変えたら、結合し直し（API代はかからない）
python tools/grok/video.py stitch tools/grok/storyboards/recruit.yaml
```

- できたクリップと完成動画は `posts/videos/<絵コンテ名>/`（コミットされない）
- 途中で失敗・中断しても、もう一度 `render` すれば**できているクリップは作り直さない**。
  プロンプトや秒数を変えたシーンだけ作り直す（`continue` のシーンは前のシーンが変わると作り直し）
- GitHub の Actions →「Grok Video」でも実行できる: `mode=plan` で絵コンテを作ってコミット →
  GitHub上で修正 → `mode=render` で生成。`max_seconds`（既定150秒）を超える生成は自動で中止

### 絵コンテの書き方（`storyboards/sample.yaml` が見本）

| 項目 | 例 | 説明 |
|---|---|---|
| `aspect_ratio` | `"9:16"` | **必ず `""` で囲む**。16:9 / 9:16 / 1:1 / 4:3 / 3:4 / 3:2 / 2:3 |
| `resolution` | `"720p"` | 480p（安い・速い）/ 720p / 1080p（`grok-imagine-video-1.5` のみ） |
| `style` | `"Anime-inspired..."` | 全シーンのプロンプトの後ろに付ける共通スタイル（色調・質感をそろえる） |
| `transition` | `fade` | `fade`（`transition_seconds` 秒重ねる）/ `none`（カット） |
| `audio` | `keep` | `keep`（Grok が付けた音を使う）/ `mute`（消す） |
| `bgm` | `"bgm/song.mp3"` | BGM（YAML からの相対パス）。動画の長さで切ってフェードアウト |
| `bgm_volume` | `0.3` | BGM の音量（`audio: keep` のときはクリップの音と重なる） |
| `references` | `["../../motion_render/chars/c1.webp"]` | 全シーン共通の参考画像（キャラ等。最大7枚）。プロンプトで `<IMAGE_1>` と書いて参照 |
| `scenes[].prompt` | | 何が映るか（英語の方が安定）。**文字・ロゴは入れない**（崩れるので、テロップは編集で） |
| `scenes[].duration` | `8` | 1〜15秒 |
| `scenes[].continue` | `true` | 前のシーンの最後のコマから続きを作る（映像が自然につながる） |
| `scenes[].image` | `"start.png"` | この画像を1コマ目にして動かす（`continue` と同時には使えない） |
| `scenes[].references` | | そのシーンだけの参考画像 |
| `scenes[].note` | | 自分用のメモ（生成には使わない） |

### 費用の目安（確信度: 低。必ず https://console.x.ai の料金表で確認）
- 動画: 1秒あたり 約$0.05〜0.08 → **1分で約450〜720円、2分で約900〜1,500円**（作り直した分は追加でかかる）
- 画像: 1枚 数円〜十数円
- ネタ探し（X検索）: 1回 数円程度 × 自動投稿の回数（現在1日10回前後）
- 実行前の見積もりは `GROK_VIDEO_PRICE_PER_SEC`（既定 $0.08/秒）で計算した目安です

### 注意
- 実在の人物（所属ライバー含む）の写真を `image` / `references` に使うときは本人の許可を取る。有名人・他社キャラは使わない
- 生成物の商用利用条件は xAI の利用規約を確認する。SNS（TikTok / Instagram / YouTube）に載せるときは各SNSの「AI生成コンテンツ」表示ルールに従う
- 自分の楽曲を BGM に使うのは問題ないが、他人の曲は使わない
