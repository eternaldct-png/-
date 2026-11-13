# Recon map: Circleback（Web / デスクトップ）

Scope: 会議の録音・文字起こし → AIノート（トピック別）＋アクションアイテム → 過去の会議の検索・質問。チーム共有・カレンダー連携ボット・外部ツール連携（Workflows）は対象外。
For: ETERNAL d.c.t 代表の自分専用（PCのブラウザで使う。ログイン・支払いなし）
Date: 2026-11-11

> この環境のネットワーク設定で circleback.ai 本体は開けなかった（DNS解決不可）。
> そのため、下の「出典」は検索結果・第三者のレビュー・ストア掲載からの情報。
> スクリーンショット（`replica/screens/`）は取得していない。画面の構成は公開情報からの推測を含む（各行に確信度を書く）。

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | 公式トップ | https://circleback.ai/ | 「AIノート・アクションアイテム・文字起こし・録音」が会議後数分で届く（検索結果の抜粋） |
| 2 | 公式 releases / workflows | https://circleback.ai/releases/workflows | Workflows = 会議後に Slack 投稿・Linear 起票・HubSpot 更新などを自動実行。タグ・参加者で条件指定 |
| 3 | 公式 How-to: アクションアイテム | https://circleback.ai/how-to/track-meeting-action-items | Action Items タブで「自分・チーム・過去の会議の相手」ごとに未完了タスクを確認 |
| 4 | 公式 llms.txt | https://circleback.ai/llms.txt | 連携先一覧（Notion, Attio, Zoho, monday.com, Webhook） |
| 5 | 公式 公開ノート例 | https://circleback.ai/view/m9vtzdx5fpzle2iypnm | 共有リンクで会議ノートを公開できる |
| 6 | App Store | https://apps.apple.com/app/id6738971048 | iOS アプリ。対面の会話も録音できる |
| 7 | SourceForge 掲載 | https://sourceforge.net/app/circleback/web-app/ | 要約・アクション抽出・話者付き文字起こし・100+言語・検索・Teams/Meet/Zoom/Slack |
| 8 | Y Combinator 企業ページ | https://www.ycombinator.com/companies/circleback | 会社概要 |
| 9 | 第三者レビュー | https://dupple.com/reviews/circleback | 料金（Free / Pro $15 などで出典ごとに食い違い）、Team プランで共有会議を横断AI検索 |
| 10 | Notion 連携ページ | https://www.notion.com/ja/connections/circleback | Notion へノートを送る連携 |

## Core loop

会議を録る（または録音・文字起こしを入れる）と、数分後にトピック別のノートと担当者付きのアクションアイテムが自動で出来上がり、あとから検索・質問できる。

## Screens

| ID | screen | route / how to reach | purpose | key components | states seen |
| --- | --- | --- | --- | --- | --- |
| S01 | 会議一覧 | トップ | 過去の会議を新しい順に並べ、開く | 検索ボックス、会議カード（タイトル・日時・参加者・タグ）、新規ボタン | empty, filled, 処理中バッジ, 失敗バッジ（確信度: 中） |
| S02 | 新しい会議 | 一覧の「新規」 | 録音する／音声・動画ファイルを入れる／文字起こしを貼る | タブ（録音・ファイル・テキスト）、録音ボタンとタイマー、ファイル選択、タイトル・日時・参加者・タグ入力 | idle, recording, uploading, error（マイク拒否・大きすぎるファイル）（確信度: 中。原典はボット参加・デスクトップアプリ録音） |
| S03 | 会議の詳細：ノート | 一覧のカード | トピック別ノートと要約を読む | 見出し付きノート、要約、参加者、タグ、再生バー、再生成・書き出し・削除 | processing, done, failed, 録音なし（確信度: 高） |
| S04 | 会議の詳細：アクションアイテム | S03 のタブ | この会議のタスクを確認・完了にする | チェックボックス付きリスト、担当者、期限 | empty, filled（確信度: 高） |
| S05 | 会議の詳細：文字起こし | S03 のタブ | 話者・時刻付きの全文を読む、話者名を直す | 発言行（話者・時刻・本文）、話者名の変更、本文内検索 | empty, filled（確信度: 高） |
| S06 | 会議の詳細：AIに質問 | S03 のパネル | この会議について追加で質問する | チャット欄、回答、出典の時刻 | empty, thinking, answered, error（確信度: 中） |
| S07 | アクションアイテム（横断） | 上部ナビ | 全会議のタスクを担当者・状態で絞って片付ける | 絞り込み（担当者・未完了/完了）、会議へのリンク付きリスト | empty, filled（確信度: 高。出典3） |
| S08 | 検索・横断質問 | 上部ナビ／一覧の検索 | キーワードで会議を探す、全会議に質問する | 検索結果（該当箇所の抜粋）、AI回答と出典会議 | no results, results, answer（確信度: 中） |
| S09 | 設定 | 上部ナビ | ノートの書き方の指示（自分の文脈）、言語、文字起こしの方式 | テキストエリア、セレクト、保存 | saved, error（確信度: 中。「your own context」の記述より） |

## Flows

```
F01 会議を録音してノートを得る（コアループ）
    S01 -> S02（録音タブ）-> 録音開始 -> 停止して保存 -> S03（処理中）-> S03（完了）
    happy path clicks: 4（新規 → 録音開始 → 停止 → 保存）
    edge: マイク許可を拒否、ブラウザが録音非対応、録音が長い（2時間超）、処理中にタブを閉じる、AI/文字起こしが失敗

F02 録音ファイルからノートを作る
    S01 -> S02（ファイルタブ）-> ファイル選択 -> 保存 -> S03
    happy path clicks: 3
    edge: 対応していない形式、ファイルが大きすぎる、無音

F03 文字起こし（Zoom/Meet の .vtt/.txt）からノートを作る
    S01 -> S02（テキストタブ）-> 貼り付け or ファイル -> 保存 -> S03
    happy path clicks: 3
    edge: 話者名のない書式、空のテキスト

F04 アクションアイテムを片付ける
    S07 -> 担当者で絞り込み -> チェック
    happy path clicks: 2
    edge: タスクが0件、担当者未定

F05 過去の会議を探して聞く
    S08 -> キーワード入力 -> 結果から S03 へ ／ 質問を入力 -> AI回答（出典会議つき）
    happy path clicks: 2
    edge: ヒット0件、会議が多すぎて全部はAIに渡せない

F06 1つの会議について追加で質問する
    S03 -> S06 に質問 -> 回答
    happy path clicks: 1
    edge: 文字起こしがまだ無い

F07 ノートを直す・書き出す
    S03 -> タイトル・参加者・タグの編集 / ノート再生成 / Markdown をコピー・保存 / 削除
```

## Components

| component | variants | states | used on |
| --- | --- | --- | --- |
| Button | primary, secondary, ghost, danger | default, hover, focus, disabled, loading | all |
| Input / Textarea / Select | text, search, date-time | default, focus, error, disabled | S02, S07, S08, S09 |
| Tabs | 下線タブ | active, hover, focus | S02, S03 |
| MeetingCard | 通常, 処理中, 失敗 | hover, focus | S01, S08 |
| StatusBadge | processing, done, failed | — | S01, S03 |
| Tag (chip) | default | — | S01, S03 |
| ActionItemRow | open, done | hover, focus | S04, S07 |
| TranscriptLine | 話者色 | highlight（検索一致） | S05 |
| RecorderPanel | idle, recording, paused | — | S02 |
| ChatPanel | 質問, 回答 | thinking, error | S06, S08 |
| Toast | success, error | — | all |
| EmptyState | — | — | S01, S04, S07, S08 |
| TopNav | — | active | all |

## Inferred data model

```
Meeting     id, title, started_at, duration_sec, participants[], tags[], source (record|upload|transcript),
            status (queued|transcribing|summarizing|done|failed), error, audio_path
            evidence: 出典1, 7（会議ごとにノート・文字起こし・録音）, 出典2（タグ・参加者で条件）
            confidence: high

Transcript  meeting_id, segments[{speaker, start_sec, end_sec, text}], language
            evidence: 出典7（話者付き文字起こし・100+言語）
            confidence: high

Notes       meeting_id, summary, sections[{heading, bullets[]}], generated_at, model
            evidence: 出典1（AIノート・トピック別）
            confidence: high

ActionItem  id, meeting_id, text, owner, due (任意), done, done_at
            evidence: 出典3（Action Items タブ、担当者で絞る）
            confidence: high

ChatMessage meeting_id (nullなら横断), role, content, created_at
            evidence: 出典1（AIアシスタントに追加で質問）
            confidence: medium

Settings    custom_context（ノートの書き方の指示）, language, transcriber
            evidence: 出典1（your own context to shape the notes）
            confidence: medium
```

Relationships: Meeting 1-1 Transcript, Meeting 1-1 Notes, Meeting 1-n ActionItem, Meeting 1-n ChatMessage

## Feature matrix

See `features.csv`. Must: 16, should: 9, could: 5, skip: 7.

## Out of scope (cannot or should not be cloned)

- 会議にボットを参加させる（Zoom/Meet/Teams の会議ボット基盤。各社の審査・常時稼働サーバーが必要）
- カレンダー連携による自動参加
- チーム共有・ワークスペース・権限（自分専用のため）
- Workflows（Slack/Linear/HubSpot/Notion への自動送信）と Webhook — 自分専用版では Markdown 書き出しで代替
- 公開共有リンク
- モバイルアプリ（PCのブラウザから録音で代替）
- Circleback のブランド（名前・ロゴ・配色・文言）

## Size

Screens 9, flows 7, entities 6. Hard parts: 文字起こし（ローカル Whisper の導入と処理時間）、話者分離（Whisper単体ではできない）、ブラウザでの会議音声の取り込み（相手の声＝タブ音声）。Size: M（コアは数日、話者分離などの精度は継続課題）。
