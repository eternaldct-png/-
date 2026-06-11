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
