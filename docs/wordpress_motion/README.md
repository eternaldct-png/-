# eternaldct.net に「動画制作（モーション作例集）」ページを追加する

`/motion`（Render）と同じ作例集を、ホームページ `https://eternaldct.net`（WordPress・SWELL）の
**固定ページとして HTML / CSS で直接作る**。Render の埋め込み（iframe）は使わない。

- 固定ページ `https://eternaldct.net/motion/`（タイトル「動画制作」）を作る
- 動画・ポスター画像は **WordPress のメディアライブラリにアップロード**して使う（Render が止まっていても表示される）
- トップページに入口のカード「こんな動画、つくれます。」を追加する
- 作例の中身は `persona/motion_config.yaml` から作る（`/motion` と同じ。制作中の枠は載せない）

作業は `src/wordpress_motion.py` が WordPress の REST API を使って自動で行う。GitHub Actions から実行する。

## ファイル

| ファイル | 役割 |
|---|---|
| `src/wordpress_motion.py` | ページの HTML/CSS/JS を作り、WordPress にアップロード・作成・更新する |
| `.github/workflows/publish_wordpress_motion.yml` | 上を GitHub Actions から実行する（手動 + 作例更新時に自動） |
| `docs/wordpress_motion/top_card.html` | トップページの入口カード（手で貼る場合もこれを使う） |
| `docs/wordpress_motion/eyecatch.jpg` | 固定ページのアイキャッチ（SNSでシェアされたときの画像にもなる） |
| `tests/test_wordpress_motion.py` | テスト |

---

## 初回のセットアップ（1回だけ）

### 1. WordPress でアプリケーションパスワードを発行
1. WordPress 管理画面 → **ユーザー → プロフィール**（管理者ユーザーで）
2. 下の方の **「アプリケーションパスワード」** に名前（例: `github-actions`）を入れて「新しいアプリケーションパスワードを追加」
3. 表示された `xxxx xxxx xxxx xxxx xxxx xxxx` を控える（ログインパスワードとは別物。あとから「取り消し」もできる）

### 2. GitHub に Secrets を登録
リポジトリの **Settings → Secrets and variables → Actions → New repository secret**

| Name | 値 |
|---|---|
| `WP_USER` | WordPress の管理者ユーザー名 |
| `WP_APP_PASSWORD` | 1 で発行したアプリケーションパスワード |
| `WP_URL` | （任意）`https://eternaldct.net` 以外にするときだけ |

### 3. 実行
GitHub の **Actions → 「ホームページに動画作例ページを反映」→ Run workflow**

| 項目 | 初回のおすすめ |
|---|---|
| status | `keep`（新規なら公開） ※先に下書きで確認したいなら `draft` |
| add_to_top | ✓（トップページに入口カードを追加） |
| prune | なし |

実行ログの最後に、作ったページのURLが出る。

### トップページへの追加のされ方
- **トップを固定ページで作っている**（設定 → 表示設定 →「ホームページ: 固定ページ」）→ その固定ページの**本文の最後**に
  カスタムHTMLブロックとして追加される。位置を変えたいときはブロックエディタでドラッグして移動する（移動後に再実行しても位置は保たれる）。
- **「最新の投稿」**（SWELL 標準のトップ）→ ウィジェット「トップページ上部」（なければ「トップページ下部」）に追加される。
- ページが下書きのときは、リンク切れを防ぐためトップへの追加はしない。
- 何度実行してもカードは1つだけ（既存のカードを更新する）。

## 作例を追加・変更したとき
`persona/motion_config.yaml` や `src/static/motion/` を変更して main にマージすると、ワークフローが自動で走り、
ホームページの固定ページも更新される（トップのカードには触らない。ページがまだない場合は何もしない）。
動画を作り直した場合は新しいファイル名でアップロードされる。古いファイルを消すときは手動実行で `prune` に✓。

## 手元で実行する場合
```bash
pip install flask pyyaml requests
WP_USER=... WP_APP_PASSWORD='xxxx xxxx ...' python src/wordpress_motion.py publish --add-to-top
python src/wordpress_motion.py build --out /tmp/motion_page.html   # HTMLだけ作って確認（接続しない）
```

---

## うまくいかないとき

| エラー | 原因と対処 |
|---|---|
| HTTP 401 | ユーザー名・アプリケーションパスワードの誤り。またはサーバーが認証ヘッダーを渡していない（レンタルサーバーの設定）。 |
| HTTP 403 | **国外IPアクセス制限**（エックスサーバー等の「WordPressセキュリティ設定」）で REST API が拒否されている可能性が高い。GitHub Actions は海外のサーバーから接続するため、実行する間だけ「REST API」の国外アクセス制限をOFFにする。セキュリティ系プラグイン（SiteGuard 等）の REST API 制限も確認。 |
| HTTP 404 / JSONではない応答 | REST API が無効化されている（プラグイン）。 |
| 「このスクリプトで作ったものではありません」 | すでに `motion` というスラッグのページがある。別スラッグにするか、上書きしてよければ `--force`。 |
| 「ウィジェットエリアが見つかりません」 | テーマのウィジェットエリア名が想定と違う。`top_card.html` をトップに手で貼る。 |

## 仕組みと注意点
- ページ本文は1つの「カスタムHTMLブロック」。CSS は `#edct-mw` の中だけに効くようにしてあり、テーマのデザインは崩さない。
  見出しやリンクにテーマの装飾がかからないように打ち消している。
- 動画は画面に入ったものだけ読み込んで無音ループ再生し、画面外で止める。タップで音ありの拡大表示。
- ブロックエディタで中身を手で直しても、次にワークフローが走ると上書きされる。文言の変更は `persona/motion_config.yaml` で行う。
- `persona/motion_config.yaml` の `page.contact_url` に公式LINEなどのURLを入れると、ページに「制作について相談する」ボタンが出る。
- キャッシュ系プラグイン（WP Rocket 等）を使っている場合、反映後にキャッシュを削除する。
