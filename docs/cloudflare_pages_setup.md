# 3DCGホームページ（site/）の公開手順 — Cloudflare Pages

`site/` 配下は **ビルド不要の静的サイト**。three.js は `site/vendor/` に同梱しているので外部CDNに依存しない。

## 構成

| ファイル | 役割 |
|---|---|
| `site/index.html` + `js/main.js` | トップ（案②）。黒背景にガラス状オブジェクト。スクロールで事業ごとに形と差し色が変わる |
| `site/stage.html` + `js/stage.js` | 下層（案①）。ライバー50人を光の球で表示。音に反応するパーティクル |
| `site/showroom.html` + `js/showroom.js` | 下層（案③）。グッズを3Dで回して色・デザインを切替 → 既存 `/goods` へ |
| `site/css/style.css` | 共通デザイン（色・フォントは `:root` の変数で一括変更） |
| `site/js/common.js` | 端末判定・ローダー・ページ遷移・仮画像生成・既存サービスのURL |
| `site/data/livers.json` | ステージに載せるライバー一覧（表示名 / ジャンル / 配信URL） |
| `site/data/products.json` | `persona/goods_config.yaml` の写し。`python3 scripts/sync_products.py` で再生成 |
| `site/_redirects` | `/goods` `/audition` `/book` を Render の既存サービスへ転送 |
| `site/_headers` | キャッシュとセキュリティヘッダ |

## Cloudflare Pages に載せる（初回のみ・約10分）

1. Cloudflare ダッシュボード → **Workers & Pages → Create → Pages → Connect to Git**
2. GitHub の `eternaldct-png/-` を選択
3. ビルド設定
   - Production branch: `main`（このPRをマージ後）
   - Framework preset: **None**
   - Build command: **空欄**
   - Build output directory: **`site`**
4. Save and Deploy → `https://<project>.pages.dev` で確認
5. **Custom domains** → `eternaldct.net` または `3d.eternaldct.net` を追加
   - eternaldct.net の DNS が Cloudflare 管理なら自動で CNAME が入る
   - 他社DNSなら、案内された CNAME レコードを追加する
   - **注意**: `eternaldct.net` そのものを向けると WordPress（SWELL）が見えなくなる。
     まずは `3d.eternaldct.net` のようなサブドメインで公開し、反応を見てから切り替えるのが安全

以後は `main` に push するたびに自動デプロイされる（PRごとにプレビューURLも発行される）。

## ローカルで確認

```bash
cd site && python3 -m http.server 8765
# → http://localhost:8765/
```

## 素材を差し替える場所

| 素材 | 置き場所 / 変更箇所 |
|---|---|
| キャッチコピー・事業説明文 | `site/index.html` の各 section（`<!-- ▼ 仮 -->` コメントの箇所） |
| 事業ごとの写真 | `index.html` の `.gl-img` に `data-src="assets/img/xxx.jpg"` を指定（`data-placeholder` を削除） |
| ロゴ | 現状は文字ロゴ。SVGが用意できたら `nav .logo` を `<img>` に差し替え、3D化は `main.js` の `core` を置換 |
| ライバー一覧 | `site/data/livers.json`（掲載許諾を取った人のみ） |
| ステージの音楽 | `site/assets/audio/theme.mp3` を置くだけ（無ければ生成音のデモが鳴る） |
| 商品の3Dモデル | `site/assets/models/<商品id>.glb` を置くだけ（無ければ簡易モデル） |
| 商品追加 | `persona/goods_config.yaml` を編集 → `python3 scripts/sync_products.py` → 写真を `site/assets/img/` にコピー |
| ブランドカラー・フォント | `site/css/style.css` の `:root` |
| 事業ごとの差し色・揺らぎ | `site/js/main.js` の `STATES` 配列 |

## 端末ごとの挙動

- スマホ・低性能端末: ポリゴン数とパーティクル数を落とし、ガラス（透過）を金属質に切替（`common.js` の `caps.quality`）
- `prefers-reduced-motion` が有効な端末: 常時アニメーションを止め、スクロール時だけ更新
- WebGL 非対応: 3Dを出さず、静止グラデーション + 通常の画像で表示（`html.no-webgl`）
