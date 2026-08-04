# CLAUDE.md — プロジェクト概要と定型作業

## このリポジトリの概要
eternaldct-png/- は ETERNAL d.c.t の投稿自動化 & グッズ販売サイト。
- Flask アプリ（`src/web_app.py`）を Render でホスト
- 本番URL: `https://kazuto-post-generator.onrender.com`
- ホームページ: `https://eternaldct.net`（WordPress、別管理）

---

## テスト

PR を出すと `.github/workflows/test.yml` が自動でテストを走らせる。
**赤くなったらマージしない**（Render に壊れたものがデプロイされる）。

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -m "not browser"   # 高速（数秒）。普段はこれで十分
playwright install chromium
pytest                    # ブラウザテスト込み
```

| ファイル | 守っているもの |
|---|---|
| `tests/test_diagnosis.py` | 診断設定の書き間違い、判定の偏り、生成文経由のXSS |
| `tests/test_payment_flow.py` | **未払いでレポートが出ないこと**、二重課金しないこと |
| `tests/test_promo.py` | 告知の頻度と文面のローテーション |
| `tests/test_main_integration.py` | 告知が投稿フローに正しく挟まること |
| `tests/test_browser.py` | 実ブラウザで12問答えて結果が出ること（JSの動作） |

**`diagnosis_config.yaml` に診断を足したら必ず `pytest` を通すこと。**
軸名の打ち間違いや、特定のタイプに回答が偏る設計をその場で検出できる。

**本番の依存（`requirements.txt`）は増やしていない。** テスト用は
`requirements-dev.txt` に分けてあるので、Render のデプロイには影響しない。

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

## /diagnosis ページ（AI診断・有料レポート販売）

12問に無料で答えるとタイプ判定が出て、**詳細レポートだけを有料（既定480円）で売る**自動収益ツール。
発送も在庫もサポートもなく、決済後の納品まで全自動で完結する。

**設定ファイル:** `persona/diagnosis_config.yaml`
**コード:** `src/diagnosis.py`（Blueprint。`src/web_app.py` に登録済み）

### 仕組み
1. `/diagnosis` で診断を選び、`/diagnosis/<quiz_id>` で12問に回答（無料・ログイン不要）
2. 回答を軸ごとに集計し、各タイプの `weights` との内積が最大のタイプを結果とする
3. 無料では「タイプ名＋短い要約」だけ表示し、詳細レポートを有料で案内
4. 購入すると Stripe Checkout に遷移。回答内容は Stripe の metadata に保存する
5. 決済完了後 `/diagnosis/report?session_id=...` に戻り、**支払い済みかを Stripe に問い合わせて確認してから** Claude API でその人専用のレポートを生成して表示

### 診断ジャンルを追加する（コード変更は不要）
`persona/diagnosis_config.yaml` の `quizzes` に1ブロック足すだけ。
1. `axes` に軸名を3〜4個決める
2. `questions` を12問、各4択で書く（`choices` の `scores` は `axes` のキーを使う）
3. `types` を5〜6個書く（`weights` は `axes` のキーを使う）
4. コミットして push すれば公開される

**タイプ設計のコツ:** 受け皿的な「バランス型」を作ると回答が偏ってそこに集中し、
結果がありきたりになって課金されなくなる。各タイプは軸の組み合わせが重ならないように散らす。

### 価格を変える
`persona/diagnosis_config.yaml` の `report.price` の1行だけ。

### 自動投稿での告知（`src/promo.py`）
X の自動投稿に診断ページの告知を混ぜて集客する。設定は同じ YAML の `promo` セクション。

- 既存の投稿文に URL を継ぎ足すと 140字前提の文章が壊れるので、**告知は独立した1投稿**にする
- 通常投稿を `every_n_posts` 件（既定6）出したら1回だけ告知に差し替わる。X は1日3回投稿なので約2日に1回
- 診断 × 文面の組み合わせを履歴で散らすため、同じ文面が続かない
- 告知回はトレンドリサーチも文章生成も走らないので、Claude API の費用がかからない
- 対象は X のみ。Instagram はキャプションのリンクが押せず、note / TikTok は記事・台本なので入れていない
- 止めたいときは `promo.enabled: false`

**カウンターは `posts/promo_state.json` に保存し、ワークフローでコミットしている。**
GitHub Actions は毎回クリーンに checkout するため、これをコミットしないと
カウンターが毎回0に戻って告知が永久に発火しない。投稿ワークフローの `git add` に
このファイルが含まれていることを確認すること。

### 注意
- **新しい環境変数は不要**。既存の `STRIPE_SECRET_KEY` と `ANTHROPIC_API_KEY` だけで動く。
- レポートは `posts/diagnosis_reports/` にキャッシュするが、これは高速化のためだけ。
  Render のファイルシステムは揮発するので、消えても Stripe の metadata から再生成される。
- レポート1件あたりの原価は Claude API 分の十数円程度。480円に対して十分小さい。
- `report.max_tokens` は「思考＋本文」の合計上限。減らしすぎるとレポートが途中で切れる。

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
