# CLAUDE.md — プロジェクト概要と定型作業

## このリポジトリの概要
eternaldct-png/- は ETERNAL d.c.t の投稿自動化 & グッズ販売サイト。
- Flask アプリ（`src/web_app.py`）を Render でホスト
- 本番URL: `https://kazuto-post-generator.onrender.com`
- ホームページ: `https://eternaldct.net`（WordPress、別管理）

---

## /goods ページ（グッズ販売）のルーティン

### 商品を追加・編集する

**設定ファイル:** `persona/goods_config.yaml`  
**画像置き場:** `src/static/goods/`  
**コード変更は不要** — YAMLを編集してコミットするだけ。

#### 価格計算ルール
```
販売価格 = 本体価格（税込）+ 送料見積
送料見積 = 1,090円（郵便局ゆうパック サイズ60 全国平均）
```

#### シンプルな商品（バリアントなし）の追加
```yaml
- id: "商品ID（一度公開したら変更しない）"
  name: "商品名"
  price: 2190          # 税込・送料込みの整数（円）
  description: "説明文"
  image: "/static/goods/ファイル名.jpg"  # 任意
```

#### バリアントあり（サイズ/カラー/デザイン）の追加
```yaml
- id: "商品ID"
  name: "商品名"
  description: "説明文"
  variants:
    size:
      - label: "S"
        price: 4590    # サイズごとに価格を設定
      - label: "XL"
        price: 4590
      - label: "XXL"
        price: 5590    # XXLは高い場合も
    color:
      - label: "チャコール"
      - label: "ホワイト"
    design:            # 任意（不要なら削除）
      - label: "センター"
      - label: "スモール"
  images:              # 任意（color×designに対応した写真）
    - path: "/static/goods/ファイル名.webp"
      color: "チャコール"
      design: "センター"
```

#### 商品を追加するときに確認すること
1. 商品名
2. 本体価格（税込）
3. サイズ展開（S/M/L/XL/XXL など）& XXLだけ値段が違うか
4. カラー展開
5. デザイン展開（複数デザインがあるか）
6. 商品写真（添付してもらう → `src/static/goods/` に保存）

#### デプロイ手順（毎回同じ）
```bash
git add persona/goods_config.yaml src/static/goods/
git commit -m "商品名を追加"
git push -u origin claude/homepage-payment-spreadsheet-DD1ly
# → GitHub MCP で PR作成 → マージ → Render が自動デプロイ
```

---

## 現在の商品ラインナップ

| id | 商品名 | 価格 |
|---|---|---|
| chaco-mug-001 | chacoデザインマグカップ | 2,190円 |
| chaco-tshirt-001 | chacoデザインTシャツ 6.6oz | S〜XL: 4,590円 / XXL: 5,590円 |
| chaco-tshirt-56-001 | chacoデザインTシャツ 5.6oz | S〜XL均一: 3,590円 |

---

## Render 環境変数
| 変数名 | 用途 |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe本番キー（`sk_live_...`） |
| `WEB_PASSWORD` | `/goods/admin` ログインパスワード |
| `FLASK_SECRET_KEY` | セッション用秘密鍵 |
| `ANTHROPIC_API_KEY` | 投稿文生成 |

---

## 管理画面
- URL: `https://kazuto-post-generator.onrender.com/goods/admin`
- パスワード: Render の `WEB_PASSWORD` で設定した値
- 表示内容: 注文日時 / 商品名 / オプション（サイズ・カラー・デザイン）/ 金額 / 氏名 / 住所 / 連絡先

---

## /stickers ページ（LINEスタンプメーカー）

写真からLINEスタンプ（個別PNG・最大16枚）を作る無料ツール。OpenAI等の画像生成APIキーは使わない構成（従量課金を避けるため）。

### 仕組み
1. ユーザーがChatGPT Plus等（既存のサブスク）を使い、元写真1〜2枚から「ポーズ・表情違いを16種類、背景は無地の単色で」生成し、手元に16枚ダウンロードする（このapp外で行う手動ステップ）
2. `/stickers` にその16枚をアップロードし、各枚にセリフ（任意）を入力
3. `src/sticker_generator.py` が Pillow のみで以下を自動処理:
   - 背景透過（四隅の色を背景とみなし色距離でアルファ抜き）
   - 白ふち付与（アルファチャンネルの膨張差分）
   - セリフ合成（`media/fonts` のNoto Sans CJKを共有利用、`src/media/image_generator.py` と同じフォントDLロジック）
   - LINEスタンプ規定サイズ（最大370×320px）に縮小
4. 生成結果は一時ディレクトリ（OSの`tempfile`配下、2時間で自動削除）に保存し、個別PNGダウンロード or ZIP一括ダウンロード

### URL
- `/stickers` — アップロードフォーム
- `/stickers/generate` — POST、画像処理して結果ギャラリーを表示
- `/stickers/file/<job_id>/<NN>.png` `/stickers/zip/<job_id>` — ダウンロード

### 注意
- 元画像（ChatGPT生成画像）の背景が無地・単色だと背景透過の精度が高い。背景が複雑だと透過がうまくいかない場合がある。
- 新しい環境変数は不要（既存のRender環境変数だけで動く）。

---

## /audition ページ（ライバー・配信者オーディション応募）

Googleフォームの代わりに、サイト内に応募フォームを実装したもの。`persona/goods_config.yaml` のような
設定ファイルはなく、質問項目は `src/web_app.py` の `AUDITION_HTML` に直接埋め込み。

### 仕組み
- `/audition` — 応募フォーム（基本情報・活動について・アピール・確認事項の4セクション）
- `/api/audition/submit` — POST、`DATABASE_URL`（Postgres/Supabase）の `audition_applications` テーブルに保存
  （併せて `posts/audition_applications.json` にも控えを書き出す。DBが未設定・接続不可のときはファイルのみ）
- `/audition/admin` — `WEB_PASSWORD` でログインして応募一覧を確認（`/goods/admin` と同じパスワード）。
  カード／一覧表示の切り替え、応募者検索、確認ダイアログ付きの削除ができる。
- 応募があると、面談予約アプリ（`eternal-interview-booking`）と共有の `DATABASE_URL`（Postgres/Supabase）から
  `booking_line_links` テーブルの `person='admin'` で連携済みのLINEユーザーへ通知を送る
  （`kazuto-post-generator` 側にも同じ `DATABASE_URL` と `LINE_CHANNEL_ACCESS_TOKEN` の設定が必要。
  未設定なら通知は静かにスキップされ、応募自体は保存される）

### 注意
- **応募データの永続化には `DATABASE_URL` が必須**。Renderの無料プランはファイルが再デプロイ・スリープ復帰で
  消えるため、未設定だと応募が消える。`eternal-interview-booking` と同じ値を設定すればよい。
  設定した時点でファイルに残っている応募は、初回アクセス時に自動でDBへ移行される（`id` で重複スキップ）。
- `/audition/admin` の下部に保存先のステータス（DB保存中／ファイルのみ）が表示される。
  「⚠️ データベース未設定」と出ていたらRenderの環境変数を確認する。
- 管理画面のログインセッションを再起動後も保つには `FLASK_SECRET_KEY` の設定が必要
  （未設定だと起動ごとにランダム値になり、再起動のたびに再ログインが必要になる）。
- LINE通知を受け取るには、面談予約アプリの公式LINEアカウントで「連携 admin」を送っておく必要がある
  （手順: `docs/booking_line_setup.md`）。

---

## 面談予約アプリ（src/booking_app.py）

kazuto / あまりん / さな / しー / かぴのすけ の5人それぞれについて、外部ゲストが
ログイン不要で30分の面談を予約できるアプリ。Render では別サービス
`eternal-interview-booking` としてホスト（`render.yaml` 参照）。

**設定ファイル: `persona/booking_config.yaml`** — サイト名・アイコン・予約の呼び名
（面談/レッスン/施術など）・メンバー一覧（slug と表示名）・営業時間・表示日数・
リマインド時刻はすべてこの YAML で変更できる。コード変更なしで別事業者向けの
予約ツールとして外販デプロイ可能（手順: `docs/booking_line_setup.md` の「外販するとき」）。

### 仕組み
- `/availability`（空き時間登録）はパスワード保護（`AVAILABILITY_PASSWORD`、未設定時のデフォルト: `ETERNALLOVE`）。5人はログイン後、自分の名前を選んで空き時間（30分単位、9:00〜22:00）を登録する。
- `/book/<slug>`（外部ゲスト向け予約ページ）はログイン不要・一般公開。5人それぞれ独立したページ（`/book/kazuto` `/book/amarin` `/book/sana` `/book/shi` `/book/kapinosuke`）。
- 各予約ページには、**その人自身が空けている時間**（すでに予約済みの時間は除く）だけが表示される。他の人の空き時間と掛け合わせる（両方が空いている必要がある）ことはしない — 一人ひとり独立して予約を受け付ける。
- ゲストは名前だけ入力して予約。**先着順**で、同じ人・同じスロットは一度しか予約できない。予約枠は人ごとに独立しているため、同じ時間帯でも別の人になら予約できる。
- 予約が確定すると `eternal.d.c.t@gmail.com` の Google カレンダーに同期される（`GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_CALENDAR_ID` をそのカレンダーに合わせて設定し、サービスアカウントのメールアドレスをカレンダー共有に追加しておく必要あり）。
- `/availability` ページでは確定済みの予約枠に「編集」「削除」ボタンが表示され、ゲスト名の修正や予約取消（枠を再度空けてGoogleカレンダーのイベントも削除）ができる。
- 予約成功時は消えるトースト通知ではなく、閉じるまで表示され続けるポップアップで完了を知らせる。失敗時は従来通りトーストでエラーメッセージを表示。
- **LINE通知**: LINE公式アカウント（Messaging API）を連携すると、予約確定・キャンセル時に担当メンバーのLINEへ即時通知が届く。メンバーは公式アカウントに「連携 あまりん」のように送るだけで紐づく（「連携 admin」で全員分、「解除」で停止）。連携状況は `/availability` の「💬 LINE通知」カードに表示。環境変数: `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_CHANNEL_SECRET`。Webhook URL は `/line/webhook`。セットアップ手順: `docs/booking_line_setup.md`
- **LINEリマインド**: `/tasks/send-reminders?token=<REMINDER_SECRET>` を cron（cron-job.org 等）で1時間ごとに叩くと、開始24時間前（`booking_config.yaml` の `line.reminder_hours_before` で変更可）を過ぎた予約に1回だけリマインドを送る。
- ページ間の遷移（ホーム → 予約ページなど）では、タップした瞬間に「しばらくお待ちください…」のローディング表示を出し、遷移先ページの応答を待ってから実際に画面を切り替える（Render の低頻度アクセス時のコールドスタート対策）。

### URL
- `/` — メニュー（空き時間登録 + 5人分の予約リンク）
- `/availability` — 空き時間登録（5人共通、パスワード保護）
- `/book/kazuto` `/book/amarin` `/book/sana` `/book/shi` `/book/kapinosuke` — 各人との面談予約ページ（一般公開・ログイン不要）

### データ
- `posts/booking_availability.json` — 各人の空き時間（`DATABASE_URL` 設定時は Postgres の `booking_availability` テーブル）
- `posts/booking_reservations.json` — 確定した予約（同テーブル構成時は `interview_bookings` テーブル。予約の一意制約は `(member, slot)` の組み合わせ単位）
