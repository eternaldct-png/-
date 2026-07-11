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

## 面談予約アプリ（src/booking_app.py）

kazuto / あまりん / さな / しー / かぴのすけ の5人それぞれについて、外部ゲストが
ログイン不要で1時間の面談を予約できるアプリ。Render では別サービス
`eternal-interview-booking` としてホスト（`render.yaml` 参照）。

### 仕組み
- `/availability`（空き時間登録）はパスワード保護（`AVAILABILITY_PASSWORD`、未設定時のデフォルト: `ETERNALLOVE`）。5人はログイン後、自分の名前を選んで空き時間（1時間単位、9:00〜22:00）を登録する。
- `/book/<slug>`（外部ゲスト向け予約ページ）はログイン不要・一般公開。5人それぞれ独立したページ（`/book/kazuto` `/book/amarin` `/book/sana` `/book/shi` `/book/kapinosuke`）。
- 各予約ページには、**その人自身が空けている時間**（すでに予約済みの時間は除く）だけが表示される。他の人の空き時間と掛け合わせる（両方が空いている必要がある）ことはしない — 一人ひとり独立して予約を受け付ける。
- ゲストは名前だけ入力して予約。**先着順**で、同じ人・同じスロットは一度しか予約できない。予約枠は人ごとに独立しているため、同じ時間帯でも別の人になら予約できる。
- 予約が確定すると `eternal.d.c.t@gmail.com` の Google カレンダーに同期される（`GOOGLE_SERVICE_ACCOUNT_JSON` / `GOOGLE_CALENDAR_ID` をそのカレンダーに合わせて設定し、サービスアカウントのメールアドレスをカレンダー共有に追加しておく必要あり）。
- `/availability` ページでは確定済みの予約枠に「編集」「削除」ボタンが表示され、ゲスト名の修正や予約取消（枠を再度空けてGoogleカレンダーのイベントも削除）ができる。
- 予約成功時は消えるトースト通知ではなく、閉じるまで表示され続けるポップアップで完了を知らせる。失敗時は従来通りトーストでエラーメッセージを表示。
- ページ間の遷移（ホーム → 予約ページなど）では、タップした瞬間に「しばらくお待ちください…」のローディング表示を出し、遷移先ページの応答を待ってから実際に画面を切り替える（Render の低頻度アクセス時のコールドスタート対策）。

### URL
- `/` — メニュー（空き時間登録 + 5人分の予約リンク）
- `/availability` — 空き時間登録（5人共通、パスワード保護）
- `/book/kazuto` `/book/amarin` `/book/sana` `/book/shi` `/book/kapinosuke` — 各人との面談予約ページ（一般公開・ログイン不要）

### データ
- `posts/booking_availability.json` — 各人の空き時間（`DATABASE_URL` 設定時は Postgres の `booking_availability` テーブル）
- `posts/booking_reservations.json` — 確定した予約（同テーブル構成時は `interview_bookings` テーブル。予約の一意制約は `(member, slot)` の組み合わせ単位）
