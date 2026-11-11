# 部品の仕様（会議ノート）

トークン: `replica/design/tokens.json` → `tools/meeting_notes/static/tokens.css`。
部品の CSS: `tools/meeting_notes/static/app.css`。部品の見本ページ: `http://127.0.0.1:5055/design`。
アイコンは使わない（絵文字とテキストのみ。Circleback のアイコン・ロゴ・文言は使わない）。

```
Button (.btn)
  variants  primary (.btn-primary), secondary (既定), ghost (.btn-ghost), danger (.btn-danger)
  sizes     sm 32px (.btn-sm), md 40px
  states    default, hover, active, focus-visible (--focus-ring), disabled, loading (.is-loading: 文字は残し aria-busy)
  tokens    primary: bg accent / text on-accent、secondary: bg bg / border border-input / text text、radius md、font sm/600
  a11y      <button> か <a>。focus-visible で必ずリング
  used on   all

Input / Textarea / Select (.field)
  states    default, focus (--focus-ring), error (.field-error: border danger + 下にメッセージ), disabled
  tokens    border border-input, radius sm, font base, padding sp-2 sp-3
  a11y      <label for> 必須。エラー文は aria-describedby
  used on   S02, S03, S07, S08, S09

Tabs (.tabs / [role=tablist])
  states    active (下線 accent 3px・text)、inactive (text-muted)、hover、focus-visible
  a11y      role=tab / aria-selected / aria-controls、←→ キーで移動
  used on   S02, S03

MeetingCard (.card.meeting-card)
  content   タイトル（2行で省略）、日時、長さ、参加者、タグ、StatusBadge、要約の1行目
  states    hover (border accent)、focus-visible、処理中、失敗
  used on   S01, S08

StatusBadge (.badge)
  variants  processing (.badge-warn: warning on warning-soft), done (表示しない), failed (.badge-danger)
  used on   S01, S03

Tag (.chip)
  tokens    bg accent-soft, text accent, radius pill, font xs
  used on   S01, S03, S07

ActionItemRow (.action-row)
  content   チェックボックス、本文、担当者 chip、期限、会議名（横断一覧のみ）、削除
  states    open, done（本文に取り消し線・text-muted）、hover、focus
  a11y      本物の <input type=checkbox> + <label>
  used on   S03(アクション), S07

TranscriptLine (.tline)
  content   時刻ボタン（押すと録音のその位置から再生）、話者、本文
  states    検索一致 (<mark>)
  used on   S03(文字起こし)

RecorderPanel (.recorder)
  states    idle（「録音を開始」）、recording（経過時間・レベルメーター・「停止」）、stopped（再生プレビュー・「保存」「やり直す」）、error（マイク拒否）
  a11y      経過時間は aria-live=off、状態の変化は aria-live=polite で読み上げ
  used on   S02

ChatPanel (.chat)
  content   質問欄・送信、回答（Markdown を素朴に表示）、出典
  states    empty, thinking（.is-loading）, answered, error
  used on   S03(質問), S08

Toast (#toast)
  variants  success, error。3秒で消える（エラーは閉じるまで）。aria-live=polite
  used on   all

EmptyState (.empty)
  content   1行の説明と次の一手のボタン
  used on   S01, S03, S07, S08

TopNav (.topnav)
  content   アプリ名、会議／アクション／質問／設定、「＋ 新しい会議」
  states    現在のページは aria-current=page
  used on   all
```
