# Recon map: OiiOii（Web）

Scope: アイデア（文章・画像）→ 脚本 → キャラ設定 → シーン設定 → 絵コンテ（カット）→ 各カットの映像 → 音（BGM・セリフ）→ 1本の動画に書き出す、までのコアループ。
コミュニティ・ギャラリー公開・テンプレート配布・ログイン・課金（クレジット）は対象外。
For: ETERNAL d.c.t 代表の自分専用（PCのブラウザで使う。ログイン・支払いなし）。所属ライバーのショートアニメ・MV・リール素材づくり。
Date: 2026-11-21

> この環境のネットワーク設定で oiioii.ai 本体と第三者レビュー記事は開けなかった（DNS解決不可）。
> 下の情報は **検索結果の要約（第三者のレビュー・ツール紹介サイト）からの二次情報**。料金はサイトごとに食い違う。
> スクリーンショット（`screens/`）は取得していない。画面の構成は推測を含む（各行に確信度を書く）。

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | 公式トップ（日本語） | https://www.oiioii.ai/ja/ | 開けず。英語・日本語・簡体字に対応（検索結果） |
| 2 | 公式 Story Anime ページ | https://www.oiioii.ai/en/story-anime | 物語アニメ生成のランディング（検索結果のタイトルのみ） |
| 3 | Product Hunt | https://www.producthunt.com/products/oiioii/launches | ローンチ情報 |
| 4 | 第三者レビュー（pollo.ai 日本語） | https://pollo.ai/ja/hub/oiioii-review | 「7エージェント動画制作チーム」 |
| 5 | 第三者レビュー（gaga.art） | https://gaga.art/blog/oiioii/ | ワークフロー・料金 |
| 6 | 第三者レビュー（vmake） | https://vmake.ai/blog/oiioii-review | 料金・長所短所 |
| 7 | 第三者レビュー（kingy.ai） | https://kingy.ai/news/oiioii-oiioii-ai-a-deep-dive-review-the-ai-animation-studio-that-wants-to-replace-your-entire-production-team/ | クレジットの有効期限（サブスク31日・追加365日・ログボ3日） |
| 8 | 第三者レビュー（media.io） | https://www.media.io/comparison/oiioii-review.html | 「animation-first workspace」、複数カット・シリーズ・繰り返し出るキャラ向け |
| 9 | 第三者レビュー（anijam・競合） | https://www.anijam.ai/blog/oiioii-ai-review/ | 「直線的な工程で長期の創作メモリがない」（競合による評価） |
| 10 | dataconomy | https://dataconomy.com/2026/06/24/oiioii-ai-makes-animation-feel-like-directing-not-prompt-engineering/ | 「プロンプトでなく監督する感覚」 |
| 11 | aiagent-navi（日本語） | https://aiagent-navi.com/ai-agent/oiioii-ai-animation-agent/ | 日本語の紹介 |
| 12 | ai-deck | https://ai-deck.app/blog/oiioii/ | 「脚本から美術・音楽まで分業」 |
| 13 | toolmage（日本語） | https://www.toolmage.com/ja/tool/oiioii/ | ツール紹介 |

## 公開情報から分かったこと（事実・二次情報）

- 7つのAIエージェントが分業: アートディレクター／シーンデザイナー／脚本家／IPデザイナー／キャラクターデザイナー／絵コンテ作家／サウンドディレクター（出典 4, 5 ほか）
- 作品の種類: クイック動画／ショートMV／ストーリー動画／アニメMV、マンガ→動画、IP（キャラ）作成（出典: 検索要約）
- 始め方: 物語の説明を書く or 脚本を入れる（画像も貼れる）→ スタイル・尺・縦横比・セリフの言語・感情を選ぶ（出典 5, 6）
- 脚本・キャラ・シーン・絵コンテを **生成 → 確認・編集 → 次へ** の順で進める。脚本は直接編集もプロンプトでの修正もできる（出典 5）
- キャラ設定画（リファレンスシート）を先に承認してから絵コンテ作家が各カットを作る（出典 5）
- 絵コンテのコマは並べ替え・プロンプトの修正・参照画像の差し替えができる（出典 5）
- チャットで指示を出しながら進める／ワンクリックのおまかせモードもある（出典: 検索要約）
- 作ったキャラ・シーンは素材ライブラリに保存して使い回せる。スタイルライブラリがある（出典 4, 13）
- 縦横比: 16:9 / 9:16 / 1:1（出典 5）
- 楽曲からMVを作る機能（出典: 検索要約）
- 料金: フリーミアム。無料は透かし入り・月3本・15秒という記述、有料は $17〜$29/月と食い違い。1080p・透かしなしは有料（出典 5, 6, 7）
- 弱点として挙がっていること: 1時間の長編は無理、生成後の細かい部分修正に制限、シーンの一貫性にばらつき、直線的な工程（出典 9, 4）

## Core loop

アイデアを書く → AIが脚本・キャラ・シーン・カット割りを順に出し、各段階で自分が確認・修正する → 全カットの絵と動きと音がそろったら1本の動画に書き出す。

## Screens

| ID | screen | route / how to reach | purpose | key components | states seen |
| --- | --- | --- | --- | --- | --- |
| S01 | ホーム（作品一覧） | トップ | 作品を新しい順に並べて開く、新しく作る | 新規ボタン、作品カード（サムネ・タイトル・段階・更新日）、種類のチップ | empty, filled, 生成中バッジ（確信度: 中） |
| S02 | 新しい作品 | ホームの「新規」 | アイデア・脚本・画像を入れて、種類・スタイル・尺・縦横比・言語・感情を選ぶ | 大きな入力欄、画像ドロップ、種類チップ、スタイル選択、尺・縦横比セレクト、おまかせ/1段ずつの切り替え | idle, 入力不足エラー（確信度: 高） |
| S03 | 制作ワークスペース | 作品を開く | 左にチャット（エージェントの発言）、右に今の段階の成果物。段階のステッパー | ステッパー（脚本→キャラ→シーン→絵コンテ→映像→音→書き出し）、チャット欄、成果物パネル、承認ボタン | 生成中, 確認待ち, 承認済み, 失敗（確信度: 中） |
| S04 | 脚本 | S03 の段階1 | あらすじ・シーン構成・セリフを読む・直す | タイトル、ログライン、シーンごとのセリフ表、直接編集、「こう直して」入力 | generating, review, edited（確信度: 高） |
| S05 | キャラクター | S03 の段階2 | キャラごとの設定画（三面図）と説明を確認・差し替え | キャラカード（名前・見た目の説明・画像）、参照画像アップロード、作り直し、ライブラリに保存 | empty, generating, review（確信度: 高） |
| S06 | シーン（背景） | S03 の段階3 | 場面ごとの背景画を確認・差し替え | シーンカード、作り直し、保存 | 同上（確信度: 中） |
| S07 | 絵コンテ | S03 の段階4 | カットごとの絵・秒数・カメラ・セリフ・プロンプト | カットのグリッド、並べ替え、プロンプト修正、参照画像差し替え、カット追加・削除 | generating, review, 1カットだけ失敗（確信度: 高） |
| S08 | 映像（カットの動き） | S03 の段階5 | 各カットを静止画から動く映像にする | カットごとのプレビュー、作り直し | generating, done, failed（確信度: 中） |
| S09 | 音 | S03 の段階6 | BGM・セリフの声・効果音 | BGM選択/アップロード、声の割り当て、音量（確信度: 低） |
| S10 | 書き出し | S03 の段階7 | 1本にまとめてプレビュー・ダウンロード | プレビュープレイヤー、解像度、ダウンロード | rendering, done, failed（確信度: 中） |
| S11 | 素材ライブラリ | 上部ナビ | 保存したキャラ・シーンを見る・別の作品で使う | 種類タブ、素材カード、削除（確信度: 中） |
| S12 | スタイルライブラリ | S02 のスタイル選択から | 絵柄を選ぶ | スタイルカード（見本・名前）（確信度: 中） |
| S13 | 料金・クレジット | 上部ナビ | 残りクレジット・プラン | skip（今回は作らない） |
| S14 | ログイン | 初回 | アカウント | skip（今回は作らない） |

## Flows

```
F01 アイデアから1本作る（コアループ・1段ずつ確認）
    S01 -> S02 -> S03/S04 脚本を承認 -> S05 キャラを承認 -> S06 シーンを承認 -> S07 絵コンテを承認
        -> S08 映像 -> S09 音 -> S10 書き出し -> ダウンロード
    happy path clicks: 約10（新規・作る・承認×6・書き出し・ダウンロード）
    edge: AIが失敗、1カットだけ失敗、途中でタブを閉じる、セリフが尺に収まらない、画像が無いカット

F02 おまかせ（ワンクリック）で1本作る
    S01 -> S02（おまかせ ON）-> S03（全段階が自動で進む）-> S10
    happy path clicks: 3
    edge: 途中の段階で失敗したらそこで止まる

F03 途中の段階を直す
    S04〜S07 のどこかで「こう直して」or 直接編集 -> その段階だけ作り直し -> 後ろの段階は「古い」表示
    edge: 前の段階を直したのに後ろが古いまま書き出してしまう

F04 絵コンテのカットを並べ替える・足す・消す
    S07 -> ドラッグ（or ↑↓）-> 秒数が合計に反映
    edge: 0カット、尺の合計がおかしい

F05 キャラを素材ライブラリに保存して別作品で使う
    S05 -> 保存 -> S11 -> 新しい作品の S02/S05 で選ぶ
    edge: 同じ名前のキャラ

F06 自分の画像を入れる（ChatGPT 等で作った絵・所属キャラの絵）
    S05/S06/S07 -> アップロード -> そのコマの絵になる
    edge: 大きすぎる、画像以外、縦横比が違う

F07 曲・BGMからMVを作る
    S02（MV） -> 曲をアップロード -> 尺を曲に合わせる -> S10
    edge: 曲が長すぎる、形式が違う
```

## Components

| name | variants | states | used on |
| --- | --- | --- | --- |
| ボタン | primary / secondary / ghost / danger | default, hover, disabled, loading | 全画面 |
| ステッパー | 7段階 | 未着手, 生成中, 確認待ち, 承認済み, 古い, 失敗 | S03 |
| チャット吹き出し | エージェント（役割アイコン付き）/ 自分 / システム | 通常, 考え中 | S03 |
| 作品カード | — | 生成中, 完了 | S01 |
| キャラカード / シーンカード | — | 画像なし, 生成中, 画像あり | S05, S06, S11 |
| カットカード | — | 画像なし, 画像あり, 動画あり, 失敗 | S07, S08 |
| チップ（種類・スタイル・縦横比） | 選択/未選択 | — | S02 |
| 画像ドロップ | — | idle, dragover, uploaded, error | S02, S05〜S07 |
| 動画プレイヤー | — | loading, ready | S08, S10 |
| トースト | info / error | — | 全画面 |
| モーダル（確認） | — | — | 削除・作り直し |

## Inferred data model

```
Project   id, title, kind (story|mv|quick|manga), idea, style, aspect (16:9|9:16|1:1),
          duration_sec, language, mood, stage, created_at, updated_at
          evidence: S02 の入力項目（出典5）  confidence: high
Script    project_id, logline, scenes[{no, place, summary, lines[{speaker, text}]}], version
          evidence: 出典5「脚本を直接編集・プロンプトで修正」  confidence: medium
Character id, project_id (nullable=ライブラリ), name, look (外見の説明), personality, image_path, saved_to_library
          evidence: キャラ設定画を先に承認（出典5）、素材ライブラリ（出典4）  confidence: high
Scene     id, project_id, name, description, image_path  confidence: medium
Shot      id, project_id, order, seconds, scene_id, characters[], camera, action, dialogue, image_prompt,
          image_path, video_path, status
          evidence: 絵コンテの並べ替え・プロンプト修正・参照画像（出典5）  confidence: high
Audio     project_id, bgm_path, voice per line（推測）  confidence: low
Render    project_id, path, created_at, status  confidence: medium
Credit    （skip: 課金）
```

## What cannot be cloned（skip）

| item | reason |
| --- | --- |
| 自社の画像・動画生成モデル（キャラ一貫性エンジン等） | モデルそのものは持ち出せない。自分用は **外部の生成サービス（fal.ai・任意・従量）か、自分で用意した画像（ChatGPT Plus 等・既存サブスク）** で代わりにする |
| スタイルライブラリの見本画像 | 先方の著作物。自分で作ったスタイル名と説明文だけにする |
| 作品の公開・コミュニティ | 自分専用なので不要 |
| ログイン・クレジット課金 | ユーザーの指示で不要 |

## Size

- Screens: 12（S13・S14 は skip）／ Flows: 7 ／ Entities: 6
- Hard parts:
  1. 画像・動画の生成をどうするか（無料で動く既定と、任意の有料生成の切り替え）
  2. カットを1本の動画にまとめる書き出し（ffmpeg・カメラの動き・字幕・BGM）
  3. 段階ごとの「承認 → 後ろの段階が古くなる」状態管理と、AIの失敗時の扱い
- Size: **M**（自分用・1台のPCに絞るなら、骨組みは数日。仕上げに数週間）
