# Architecture: コマドリ（OiiOii のコアループを自分用に作り直したもの）

> 仮の名前は「コマドリ」（コマ撮り＋絵コンテのコマ）。元のサービス名はこの `replica/anime/` にだけ書き、アプリ本体・README には出さない。
> 自分専用・代表の Mac 1台で動かす。ログイン・支払いなし。**Render にはデプロイしない。**

## Stack

| layer | choice | why |
| --- | --- | --- |
| web app | Flask 3 + Jinja テンプレート + 素の JS | このリポジトリで使い慣れている（キキトメと同じ形）。ビルド不要 |
| styling | 素の CSS（`static/tokens.css` に replica-design のトークン） | Tailwind のビルドを入れない |
| database | SQLite（`~/Komadori/komadori.db`） | 1台・1人。サーバー不要、バックアップはフォルダごとコピー |
| files | `~/Komadori/projects/<作品id>/`（画像・音・書き出し） | リポジトリに入れない |
| jobs | アプリ内のスレッド1本（キュー） | 生成・書き出しを順番に処理。外部のジョブ基盤は不要 |
| 文章AI | `auto`（既定）/ `ollama`（端末内AI・無料）/ `simple`（AIなし・テンプレート）/ `claude`（明示して選んだときだけ） | キキトメと同じ方針。APIキーなしでも最後まで動く |
| 画像 | 既定: Pillow で描く「仮の絵」（色・構図・セリフ入り）＋自分の画像のアップロード。任意: fal.ai（`FAL_KEY`・従量） | 無料で全工程が通る。絵の質が要るときだけ課金 |
| 動き | 既定: ffmpeg のカメラワーク（寄り・引き・左右パン）。任意: fal.ai の image-to-video | 同上 |
| 声 | Mac の `say`（Kyoko など・無料・端末内）。無ければ声なし | APIキー不要 |
| 書き出し | ffmpeg（システムの ffmpeg か `imageio-ffmpeg` 同梱） | 字幕は Pillow で描いた透過PNGを重ねる（フォント設定に依存しない） |
| auth / payments / email | なし | ユーザーの指示。かわりに 127.0.0.1 だけで待ち受け＋独自ヘッダー必須 |

## Schema（`tools/anime_studio/schema.sql`）

SQLite なので uuid は Python で作った hex 文字列、時刻は UTC の ISO 文字列。持ち主の列は無い（1人用）。
アクセス制御は「127.0.0.1 だけ・Host 確認・書き換えは `X-Komadori: 1` ヘッダー必須」の1か所（`app.guard`）。

- `projects` 作品（種類・アイデア・スタイル・縦横比・尺・言語・雰囲気・脚本JSON・段階ごとの状態JSON・BGM・書き出し）
- `characters` キャラ（`project_id` が NULL ＝ 素材ライブラリ）
- `scenes` 場面（背景）
- `shots` カット（並び順・秒・場面・登場キャラ・カメラ・動き・セリフ・話者・画像プロンプト・画像・動画・声）
- `logs` 進行ログ（どの役割のエージェントが何をしたか。チャット欄に出す）
- `jobs` バックグラウンドの仕事（段階の生成・画像・書き出し）と状態
- `settings` 設定（key/value）

段階の状態（`projects.stages` JSON）: `todo` → `generating` → `review` → `approved`、失敗は `failed`、
前の段階を直したら後ろの `approved`/`review` は `stale`（古い）になる（F03）。

## API

全部 `127.0.0.1` だけ。POST/PATCH/DELETE は `X-Komadori: 1` 必須（他サイトからの送信を防ぐ）。

| method path | what | input | output | flow |
| --- | --- | --- | --- | --- |
| GET / | 作品一覧 S01 | — | HTML | F01 |
| GET /new | 新しい作品 S02 | — | HTML | F01 F02 |
| POST /api/projects | 作品を作る（おまかせなら全段階をキューへ） | JSON | {id} | F01 F02 |
| GET /p/<id> | ワークスペース S03（`?stage=` で段階） | — | HTML | F01 |
| GET /api/projects/<id> | 作品の全部（段階・キャラ・カット・ジョブ・ログ） | — | JSON | 全部（画面の更新用） |
| PATCH /api/projects/<id> | タイトル・設定・脚本の直接編集 | JSON | JSON | F03 |
| DELETE /api/projects/<id> | 作品とファイルを消す | — | ok | — |
| POST /api/projects/<id>/stages/<stage>/generate | 段階を（作り）直す。`instruction`＝「こう直して」 | JSON | {job} | F01 F03 |
| POST /api/projects/<id>/stages/<stage>/approve | 承認して次の段階へ（おまかせ中は自動） | — | JSON | F01 |
| POST /api/projects/<id>/characters | キャラ追加（ライブラリから `from_id` も可） | JSON | JSON | F05 |
| PATCH/DELETE /api/characters/<cid> | キャラの編集・削除・ライブラリ保存（`save_to_library`） | JSON | JSON | F05 |
| PATCH/DELETE /api/scenes/<sid> | 場面の編集・削除 | JSON | JSON | — |
| POST /api/projects/<id>/shots | カット追加 | JSON | JSON | F04 |
| PATCH/DELETE /api/shots/<sid> | カットの編集・削除 | JSON | JSON | F04 |
| POST /api/projects/<id>/shots/reorder | 並び順 | {ids:[]} | JSON | F04 |
| POST /api/upload/<kind>/<oid> | 画像（キャラ・場面・カット）/ BGM のアップロード | multipart | JSON | F06 F07 |
| POST /api/projects/<id>/render | 1本に書き出す（ジョブ） | — | {job} | F01 |
| GET /files/<id>/<name> | 作品フォルダのファイル配信（パス確認つき） | — | file | — |
| GET /library | 素材ライブラリ S11 | — | HTML | F05 |
| GET/POST /settings, /api/settings | 設定（文章AI・画像の作り方・声・FAL_KEYの有無表示） | JSON | JSON | — |

Background jobs: `generate:<stage>` / `render`。アプリ起動時に `running` のまま止まったジョブは `failed`（「やり直す」）に戻す。

## The parts that bite

- **AIの返事が壊れたJSON**: Claude は JSON スキーマで形を固定、Ollama も `format` でスキーマ指定。それでも壊れたら1回だけやり直し、だめなら `failed` と理由を出す。
- **尺とセリフ**: セリフが1カットの秒数×8文字を超えたら警告（`video_brief` と同じ考え方）。合計尺が目標から±20%外れたら警告。
- **書き出しの時間**: 30秒・6カット程度で数十秒。スレッドで回し、画面は2秒おきに状態を見る。ffmpeg は1カット60秒で打ち切る。
- **ファイル**: アップロードは画像（png/jpg/webp・20MB まで）と音（mp3/m4a/wav/aac・100MB まで）。拡張子と Pillow で中身を確認。配信は作品フォルダの中だけ（`..` を拒否）。
- **日本語の字幕フォント**: Mac はヒラギノ、Linux は Noto/WenQuanYi を順に探す。見つからなければ警告を出して英字フォント。
- **段階の古さ**: 前の段階を作り直したら後ろを `stale` にし、書き出し前に「古い段階があります」と出す（F03 の edge）。
- **費用**: fal.ai を使うときだけ従量課金。画像1枚・動画1本ごとに見積もりを出し、月の上限（設定）を超える前に止める。既定は使わない。
- **同時実行**: SQLite の接続は呼び出しごとに開閉。ジョブは1本のスレッドで順番に処理する。

## Build order

1. **Vertical slice**: S01 → S02 → S03（脚本→キャラ→絵コンテ→書き出し）を `simple` エンジン＋仮の絵で通す。テーブル: projects, characters, shots, jobs, logs。
2. **Must-haves**: 直接編集・「こう直して」・カットの並べ替え/追加/削除・画像アップロード・BGM・字幕・書き出しのダウンロード・古い表示・削除。
3. **Should-haves**: Ollama / Claude エンジン、場面（背景）、声（say）、おまかせ、素材ライブラリ、カメラワーク、fal.ai（任意）。
4. **Could**: 曲の長さに尺を合わせる MV モード。
