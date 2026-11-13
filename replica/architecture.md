# Architecture: 会議ノート（Circleback のコア機能を自分用に作り直したもの）

置き場所: `tools/meeting_notes/`（このリポジトリ。Render の本番アプリ `src/web_app.py` とは別物で、デプロイしない）
動かし方: Mac で `python3 tools/meeting_notes/app.py` → ブラウザで `http://127.0.0.1:5055`

## Stack

| layer | choice | why |
| --- | --- | --- |
| web | Flask 3 + Jinja テンプレート + 素の JavaScript | このリポジトリが Flask。ビルド工程なしで `python3 app.py` だけで動く |
| styling | 素の CSS（`static/tokens.css` のカスタムプロパティ） | Tailwind はビルドが要るので使わない。トークン名は replica-design と同じ |
| database | SQLite（`~/MeetingNotes/meeting_notes.db`） | 1人・1台なのでサーバー不要。ファイル1つでバックアップできる |
| 文字起こし | faster-whisper（ローカル、無料）。未導入なら「文字起こしを貼る」だけ使える | 従量課金を避ける方針（/stickers と同じ）。音声を外部に送らない |
| AIノート・質問 | Claude API（`ANTHROPIC_API_KEY`、`claude-opus-5-5`、構造化出力） | 既存の環境変数をそのまま使う。`src/video_brief.py` と同じ呼び方 |
| auth | なし。`127.0.0.1` だけで待ち受ける | 自分専用。LAN の他の端末からは開けない |
| payments / email | なし | 不要 |
| jobs | アプリ内のバックグラウンドスレッド 1本（キュー） | 文字起こし・AI処理で画面を止めない。Celery などは過剰 |
| files | `~/MeetingNotes/audio/` | 録音はリポジトリに置かない（個人情報・容量） |
| hosting | 自分の Mac | 会議の音声を外に出さない |

## Schema

Tables: 4（meetings / action_items / chat_messages / settings）。Access rules: なし（ローカル専用、127.0.0.1 のみ）。
SQL は `replica/schema.sql`（アプリは `tools/meeting_notes/schema.sql` を読む。同じ内容）。

- 文字起こし・ノートは meetings の JSON 列に入れる（1会議1つしかなく、単独で検索しないため別テーブルにしない）
- アクションアイテムは横断一覧・絞り込み・完了の切り替えがあるので別テーブル
- アクションアイテムの `manual=1` は手で足した行。ノート再生成で AI 抽出分だけ入れ替え、手入力分と完了状態は残す（同じ文言の行は完了状態を引き継ぐ）

## API

| method path | does | who | input | output | flow |
| --- | --- | --- | --- | --- | --- |
| GET / | 会議一覧（`?q=` 検索、`?tag=` 絞り込み） | 自分 | q, tag | HTML | F05 |
| GET /new | 新しい会議の画面 | 自分 | — | HTML | F01–F03 |
| POST /api/meetings | 会議を作る（音声 or 文字起こし）→ キューへ | 自分 | multipart: title, started_at, participants, tags, audio / transcript_text / transcript_file | {id} | F01–F03 |
| GET /m/<id> | 会議の詳細（ノート・アクション・文字起こし・質問） | 自分 | — | HTML | F06, F07 |
| GET /api/meetings/<id>/status | 処理状況（ポーリング用） | 自分 | — | {status, error} | F01 |
| PATCH /api/meetings/<id> | タイトル・日時・参加者・タグの更新 | 自分 | JSON | {ok} | F07 |
| POST /api/meetings/<id>/regenerate | ノートを作り直す（文字起こしは再利用） | 自分 | — | {ok} | F07 |
| POST /api/meetings/<id>/retry | 失敗した処理をやり直す | 自分 | — | {ok} | F01 |
| POST /api/meetings/<id>/speakers | 話者名の付け替え | 自分 | {from, to} | {ok} | F07 |
| DELETE /api/meetings/<id> | 会議と録音ファイルを削除 | 自分 | — | {ok} | F07 |
| GET /m/<id>/audio | 録音の再生（Range 対応） | 自分 | — | audio | F07 |
| GET /m/<id>/export.md | Markdown 書き出し | 自分 | — | text/markdown | F07 |
| POST /api/meetings/<id>/ask | この会議に質問 | 自分 | {question} | {answer} | F06 |
| GET /actions | アクションアイテム横断（`?owner=` `?state=open|done|all`） | 自分 | — | HTML | F04 |
| POST /api/actions | 手動で追加 | 自分 | {meeting_id, text, owner, due} | {id} | F04 |
| PATCH /api/actions/<id> | 完了の切り替え・編集 | 自分 | JSON | {ok} | F04 |
| DELETE /api/actions/<id> | 削除 | 自分 | — | {ok} | F04 |
| GET /ask | 全会議への横断質問の画面 | 自分 | — | HTML | F05 |
| POST /api/ask | 全会議に質問 | 自分 | {question} | {answer, sources[]} | F05 |
| GET/POST /settings | ノートの指示・言語・Whisper モデル | 自分 | form | HTML | — |
| GET /api/backup | DB を JSON で書き出し | 自分 | — | JSON | — |

Webhooks in/out: なし。
Jobs: `worker` スレッド（常駐）。キューの会議を「文字起こし → ノート生成」の順に処理。起動時に queued / transcribing / summarizing のまま残った会議をキューに戻す。

## The parts that bite

- **時刻**: DB は UTC。会議の開始日時の入力はブラウザのローカル時刻 → JS で UTC に直して送る。表示も JS でローカルに直す。
- **二重処理**: キュー投入は会議IDで重複排除。処理中の会議に「再生成」を押しても受け付けない（409）。
- **長い会議**: 2時間の会議 ≒ 日本語で 4〜6万字。Claude の入力（1M トークン）には収まるが、横断質問では全文を渡さない（ノートの要約を渡し、キーワードが当たった会議だけ全文を足す。上限 `ask_max_chars`）。
- **文字起こしの時間**: faster-whisper の `small` モデルは Apple Silicon の CPU で実時間の 1/3〜1/5 程度（推測。マシン次第）。画面には進捗（何分まで処理したか）を出す。
- **ファイルサイズ**: アップロード上限 1GB（`MAX_CONTENT_LENGTH`）。動画は音声だけ使う（faster-whisper が内部で ffmpeg 相当のデコードをする — PyAV 同梱）。
- **話者分離**: Whisper だけでは誰が話したか分からない。vtt の話者名（Zoom/Meet/Teams の書き出し）は取り込む。録音からの場合は「話者」1人扱いで、AI のノート側で文脈から担当者を推定する。
- **AIの失敗**: refusal・接続失敗・JSON不正は status=failed と理由を残し、「やり直す」で再実行。
- **プライバシー**: 音声は外部に送らない（ローカル Whisper）。Claude には文字起こしテキストだけを送る。

## Build order

1. Vertical slice: S02（テキスト貼り付け）→ キュー → Claude でノート → S03 表示。tables: meetings, action_items。routes: POST /api/meetings, GET /m/<id>, status
2. Must-haves: S01 一覧・検索、S02 録音・ファイル、文字起こし、S04/S05 タブ、S07 アクション横断、編集・削除・再試行、再生、S06 会議への質問
3. Should-haves: S08 横断質問、S09 設定（ノートの指示）、再生成、Markdown、話者名付け替え、タブ音声の同時録音、タグ絞り込み、手動アクション、時刻クリックで再生
4. Fixes from replica-entrepreneur: 未実施
