# コマドリのコンポーネント仕様

トークンは `tokens.json`（CSS は `tools/anime_studio/static/tokens.css`）。生の色・px は部品の CSS に書かない。
アイコンは使わず、絵文字＋文字ラベルにする（元サービスのアイコン・イラストは使わない）。全部の部品は `/design` で一覧できる。

```
Button
  variants  primary（accent）, secondary（surface＋border）, ghost（文字だけ）, danger
  sizes     sm 32px, md 40px
  states    default, hover, active, focus-visible（2px accent のリング）, disabled, loading（ラベルの前に「…」、aria-busy）
  tokens    radius md, font sm/700
  a11y      本物の <button>。loading 中もラベルを残す
  used on   全画面

Stepper（段階のステッパー）
  items     1 脚本 / 2 キャラ / 3 場面 / 4 絵コンテ / 5 絵と動き / 6 音 / 7 書き出し
  states    todo（灰）, generating（橙の点が点滅・aria-live）, review（橙の枠「確認待ち」）, approved（緑の✓）, stale（黄「古い」）, failed（赤「失敗」）
  a11y      <nav aria-label="段階"> の中の <a>。今の段階に aria-current="step"。色だけでなく文字ラベルを必ず出す
  used on   S03

ChatLog（進行ログ＋指示欄）
  variants  役割の吹き出し（🎬監督 / ✍️脚本 / 🧑‍🎨キャラ / 🏞場面 / 🎞絵コンテ / 🖌作画 / 🎵音 / 🎚編集）、自分、システム
  states    empty（「指示を書くと、今の段階を作り直します」）, thinking（「考えています…」）, error
  a11y      ログは role="log" aria-live="polite"。入力は <textarea> と送信ボタン、⌘+Enter で送信
  used on   S03

ProjectCard（作品カード）
  content   サムネ（1カット目の絵 or 種類の色）、タイトル、種類・縦横比・尺、今の段階、更新日
  states    生成中バッジ, 失敗バッジ, 書き出し済みバッジ
  a11y      カード全体が1つの <a>
  used on   S01

CharacterCard / SceneCard
  content   画像（無ければ色の丸と頭文字）、名前、外見、性格（キャラ）、画像のアップロード、ライブラリに保存、削除
  states    画像なし, 画像あり, 保存済み（ライブラリ）
  used on   S05, S06, S11

ShotCard（カットカード）
  content   番号、縦横比どおりの絵、秒、カメラ、場面、登場キャラ、動き、話者＋セリフ（文字数/上限）、画面の文字、画像プロンプト、↑↓、画像の差し替え、削除
  states    絵なし, 仮の絵, 自分の画像, 生成画像, セリフが長すぎる（warning）
  a11y      並べ替えはドラッグではなく ↑↓ ボタン（キーボードで操作できる）
  used on   S07, S08

Chip（種類・スタイル・縦横比・カメラ）
  states    selected（accent-soft＋accent 文字）, default, focus-visible
  a11y      ラジオボタン（<input type=radio> を見た目だけチップに）
  used on   S02

Dropzone（画像・音のアップロード）
  states    idle, dragover（accent の点線）, uploading, done, error（形式・大きさ）
  a11y      中身は <label> ＋ <input type=file>。ドラッグできなくてもクリックで選べる
  used on   S05〜S07, S09

VideoPlayer
  <video controls playsinline>。縦横比どおりの枠。読み込み中は surface-2 の背景
  used on   S10

Banner（警告・お知らせ）
  variants  warning（古い段階がある・セリフが長い）, danger（失敗の理由と「やり直す」）, info
  a11y      role="status"（danger は role="alert"）
  used on   S03, S10

Toast
  画面下中央。info 3秒、error は閉じるまで。role="status"
  used on   全画面

Modal（確認）
  <dialog>。削除と作り直し（承認済みのものを上書きするとき）だけに使う。Esc で閉じる
  used on   S01, S03
```
