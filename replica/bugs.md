# Bugs: 会議ノート

E2E を初めて流したとき・スクリーンショットを見たときに見つけたもの。すべて修正済み（同じ作業の中で直したのでコミットは1つ）。

### BUG-001: 録音中も「録音を開始」ボタンが表示されたまま

- Severity: S3
- Flow / case: F01 / F01-E1
- Screen: S02
- Browser / device: Chromium（Playwright）, 1280px

Steps
1. ＋新しい会議 →「録音する」
2. 「録音を開始」を押す

Expected: 「録音を開始」が隠れ、「一時停止」「停止」だけが出る
Actual: 3つとも出ていて、録音中にもう一度「録音を開始」を押せる
Evidence: replica/clone-screens/S02-recording.png（修正前）
Suspected cause: `.btn { display: inline-flex }` が `hidden` 属性より強い
Status: fixed（`[hidden] { display: none !important }`）。回帰テスト: F01-H1 の中の確認

### BUG-002: スマホ幅で上のメニューが縦に積み重なる

- Severity: S4
- Flow / case: UI-E1
- Screen: 全画面（topnav）
- Browser / device: Chromium, 390px

Steps
1. 390px 幅で任意の画面を開く

Expected: アプリ名と「＋新しい会議」が1行目、メニューが2行目に横並び
Actual: メニュー4項目が縦に並び、ヘッダーが高くなる
Evidence: replica/clone-screens/S03-mobile.png（修正前）
Status: fixed（640px 以下でメニューを2行目に回して横スクロール）

### BUG-003: faster-whisper が未インストールだと、録り終わった録音を保存できない

- Severity: S1（データ消失: 録り直せない会議の録音を失う）
- Flow / case: F01 / F01-E2
- Screen: S02

Steps
1. faster-whisper を入れずにアプリを起動
2. 会議を録音して「保存してノートを作る」

Expected: 録音は保存され、文字起こしは後でできる
Actual: 「faster-whisper が必要です」のエラーで保存されず、ページを閉じると録音が消える
Evidence: コードの確認（`POST /api/meetings` が保存前に断っていた）
Status: fixed（保存してから処理を「失敗＋理由」にし、導入後に「やり直す」で文字起こし）。回帰テスト: `WithoutWhisper.test_recording_is_kept_and_failed_with_reason`

### BUG-004: 横断質問で、日本語の質問から検索語を拾えない

- Severity: S3
- Flow / case: F05 / F05-H2
- Screen: S08

Steps
1. 「AIに聞く」で「渋谷の件」と質問

Expected: 「渋谷」を含む会議の文字起こしまで読んで答え、リンクが出る
Actual: 空白で区切っていたため「渋谷の件」1語で検索し、どの会議にも当たらない
Status: fixed（漢字・カタカナ・英数字の2文字以上の並びを言葉として拾う）。回帰テスト: `test_keyword_hits_splits_japanese`

## To check（再現していないもの・実機で確認すること）

- マイクを拒否したときの案内（F01-E3）、タブ音声つき録音（F01-E4）、2時間の録音（F01-E5）
- 本物の faster-whisper の日本語精度と速さ（REAL-1）、本物の Claude のノートの質と費用（REAL-2）
