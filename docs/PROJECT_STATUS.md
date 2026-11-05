# プロジェクト全体の棚卸し（2026-11-05 時点）

Claude Code でこれまでに作ったもの・途中のもの・新しいセッションの準備をまとめたもの。
各機能の詳しい使い方は `CLAUDE.md` を見る。

---

## 1. 動いているもの（main に入っていて本番に出ている）

| 区分 | 機能 | URL / 場所 | 使い方の説明 |
|---|---|---|---|
| 販売 | グッズ販売（Stripe決済） | `/goods`・`/goods/admin` | CLAUDE.md「/goods」 |
| 集客 | モーション動画の作例集（15本） | `/motion`（ホームページの `motion.html` にも掲載） | CLAUDE.md「/motion」 |
| 集客 | LINEスタンプメーカー | `/stickers` | CLAUDE.md「/stickers」 |
| 採用 | オーディション応募フォーム＋管理画面＋スライド表示 | `/audition`・`/audition/admin` | CLAUDE.md「/audition」 |
| ライバー支援 | 枠周り記録・歌推しチェック | `/waku` | CLAUDE.md「/waku」 |
| 営業 | X営業リスト・DM下書き・自動返信 | `/leads/admin` | `docs/sales_leads_setup.md` |
| 制作 | AI動画の制作指示書＋下書き生成（fal.ai）＋つなぎ＋字幕 | `/video-brief` | CLAUDE.md「/video-brief」 |
| 社内 | 面談予約（5人分・LINE通知・Googleカレンダー同期） | 別サービス `eternal-interview-booking` | `docs/booking_line_setup.md` |
| 自動投稿 | X / Instagram / note / TikTok台本の自動生成 | `.github/workflows/`（12本） | README.md |

> GitHub Actions が毎日 `chore: note記事生成` などを main に直接コミットしている。履歴の大半はこれ。

---

## 2. 途中のまま main に入っていない作業（29ブランチ）

### 2-1. main に同じ機能がすでに入っている → 消してよい候補（確信度：中）

ファイルの比較と CLAUDE.md の記述から判断した。消す前に念のため中身を見ること。

| ブランチ | 内容 | 判断の根拠 |
|---|---|---|
| `claude/gallant-cerf-c1a5fu` | video-brief：AI歌手MVのジャンル | 同じ内容がPR #212で main に入っている |
| `claude/kind-hypatia-6tut7e` | オーディション未確認者のスライド表示 | `/audition/admin/slides` が main にある |
| `claude/modest-franklin-85leqf` | /waku の歌推し判定を月間1Kに | main の /waku が月間1K判定になっている |
| `claude/music-streamer-posting-workflow-dsPj2` | GitHub保存・デプロイ設定 | 追加ファイル9/9が main にある |
| `claude/social-revenue-automation-snpsK` | マルチプラットフォーム自動投稿 | 追加ファイル21/21が main にある |
| `claude/schedule-calendar-google-sync-3ab7ul` | イベントカレンダー（**PR #72 が開いたまま**） | 追加ファイル3/3が main にある |
| `codex/audition-admin-view-delete` | オーディション管理画面の削除機能 | v2 のブランチが main に入っている |

### 2-2. main に入っていない作業 → 「入れる／捨てる」を決める必要がある

| テーマ | ブランチ | 内容 | 最終更新 |
|---|---|---|---|
| 動画 | `claude/shorts-pipeline` | AIショート動画の制作パイプライン | 10/16 |
| 動画 | `claude/loving-cannon-8xo7t6` | AIキャラ TikTok LIVE の試作と費用まとめ | 10/12 |
| 動画 | `claude/cool-franklin-0qlx0w` | MV「愛なき世界で」の確認用動画・歌詞字幕 | 10/11 |
| 動画 | `claude/affectionate-bohr-04lo4e` | MOTION WORKS PV のナレーション・BGM（Gemini TTS の MCP 設定を含む） | 10/09 |
| 動画 | `claude/festive-feynman-lkd1h3` | 縦型リリック動画「灯」 | 10/09 |
| 動画 | `claude/confident-lamport-ksdf2r` | ライバー募集動画のナレーション（Gemini TTS） | 10/01 |
| 動画 | `claude/quirky-hopper-outf6j` | プロモーション映像（60秒CM） | 9/28 |
| ホームページ | `claude/nice-knuth-6ev9ts` | 所属ライバー数・活動率の更新スクリプト | 10/30 |
| ホームページ | `claude/nifty-galileo-9f3t1l` | `apply_motion.py` の不具合修正 | 10/01 |
| ホームページ | `claude/3dcg-homepage-design-qjr5df` | 事業画像の生成プロンプト集（ファイル42個） | 9/05 |
| 投稿・営業 | `claude/zealous-cray-kx9usz` | /leads の送り主を公式アカウント（担当: kazuto）に | 10/09 |
| 投稿・営業 | `claude/determined-sagan-qfjlb8` | 投稿文を自分の声で読み上げる🔊ボタン | 10/09 |
| 投稿・営業 | `claude/wizardly-newton-5dc5za` | Grok（xAI）でネタ探し・投稿文・画像・動画 | 10/03 |
| 投稿・営業 | `claude/tender-davinci-6db695` | note下書きの状態表示と自動アップロードの修正 | 9/25 |
| 投稿・営業 | `claude/auto-revenue-tool-udutuf` | AI診断アプリ `/diagnosis`＋テストのCI（**PR #118 が開いたまま**） | 7/25 |
| 投稿・営業 | `claude/kazuto-note-articles-BWEAX` | note APIクライアントの強化（一部は main にある） | 5/20 |
| 資料・小物 | `claude/organize-and-update-model-09q9vk` | Claude API のモデル指定の整理 | 7/26 |
| 資料・小物 | `claude/add-membership-metrics-colorsing-i13zdn` | ColorSing月次タブにメンバーシップ6列を足す Apps Script | 7/22 |
| 資料・小物 | `claude/icon-maker-improvements-vsgtef` | アイコンメーカーの改善 | 7/21 |
| 資料・小物 | `claude/discord-event-manual-42wz2h` | Discordイベント作成マニュアル | 7/13 |
| 資料・小物 | `claude/manga-homepage-social-2oxvk4` | マンガ画像生成プロンプト集 | 7/13 |
| 資料・小物 | `claude/add-ai-skills-docs-dmo3o` | 秘書・マーケ・ライター・エンジニアのスキル（**PR #1 が開いたまま**） | 3/28 |

### 2-3. main に入り済みのブランチ（16本）→ 消しても何も失わない

`adoring-feynman` `automate-x-posts-persona` `disable-same-day-booking` `dreamy-dirac`
`google-dashboard-browser-start` `google-form-audition-application` `homepage-payment-spreadsheet`
`inspiring-keller` `interview-booking-30min-slots` `line-sticker-generator` `music-streamer-posting-GXS5E`
`niche-automation-tool` `scheduling-paired-slots` `sleepy-goldberg`（以上 `claude/`）、`codex/audition-admin-edit` `codex/audition-admin-view-delete-v2`

---

## 3. 新しいセッションで「使えない・つながらない」を防ぐ

### 3-1. 何が起きているか（2026-11-05 のセッションで確認）

| 症状 | 原因 | 直し方（ユーザーが設定画面で行う） |
|---|---|---|
| テストやアプリが動かない（`flask` などが入っていない） | クラウドのコンテナは毎回まっさらで、パッケージが入っていない | 下の 3-2 のセットアップスクリプトを環境に登録する |
| デザイン・マーケ・Zoom プラグインのツール（Asana / Atlassian / Notion / HubSpot / Linear / Intercom / Ahrefs / Amplitude / Klaviyo / Similarweb / Zoom）が「403」で失敗 | 環境の**ネットワーク制限**で、そのサーバーへの通信が止められている | 3-3 のドメインを許可する。使わないプラグインは外す |
| Notion / Stripe / Circleback が使えない | claude.ai でのサインインがまだ | claude.ai の「設定 → コネクタ」でサインインする |
| パソコンの画面操作（コンピュータユース）や Mac のフォルダが使えない | クラウドのセッションは**クラウド上のコンテナ**で動いていて、パソコンにはつながっていない | パソコンの作業は Claude デスクトップアプリで行う。または Remote Control でフォルダを共有する（3-4） |
| 別のリポジトリ（`ETERNAL-` や `salon-tools`）が見えない | セッション開始時に付けたリポジトリしか入っていない | セッションを作るときに一緒に選ぶ。途中でも Claude に頼めば追加できる |

普通に使えていたもの：GitHub（このリポジトリ）、Gmail、Googleカレンダー、Googleドライブ、Slack、Canva、Figma、Supermetrics、Claude Docs、ffmpeg、Node.js、Chromium（画面のスクリーンショット確認用）。

### 3-2. セットアップスクリプト（環境の設定に1回登録するだけ）

場所：セッション上部のクラウド環境メニュー → 編集 → **Setup script**

```bash
cd ./- && pip install --ignore-installed blinker -r requirements.txt pytest
```

- スクリプトはリポジトリの1つ上のフォルダで始まる。リポジトリ名が `-` なので `cd -`（「前のフォルダに戻る」という別の意味になる）ではなく `cd ./-` と書く。
- `--ignore-installed blinker` がないと、OS にもともと入っている blinker とぶつかってインストールが失敗する。
- 2026-11-05 にこのコマンドで入れた後、テスト97件がすべて通った（約15秒）。

### 3-3. ネットワークで許可するドメイン（使うプラグインの分だけ）

場所：クラウド環境メニュー → 編集 → **Network access** → Allowed domains（「Allow package managers」はオンのまま）

| プラグイン | ドメイン |
|---|---|
| Notion（design） | `mcp.notion.com` |
| Asana | `mcp.asana.com` |
| Atlassian（Jira / Confluence） | `mcp.atlassian.com` |
| Linear | `mcp.linear.app` |
| Intercom | `mcp.intercom.com` |
| HubSpot | `mcp.hubspot.com` |
| Klaviyo | `mcp.klaviyo.com` |
| Ahrefs | `api.ahrefs.com` |
| Amplitude | `mcp.amplitude.com` / `mcp.eu.amplitude.com` |
| Similarweb | `mcp.similarweb.com` |
| Zoom | `mcp.zoom.us` / `mcp-us.zoom.us` |

手順の公式ページ：https://code.claude.com/docs/en/cloud-environments#network-access

### 3-4. パソコンでしかできない作業

- 例：Mac の `ETERNALライバー事務所/` フォルダの編集、FTPS での Xserver への反映、ブラウザの手作業。
- やり方：(1) Claude デスクトップアプリでセッションを開く、または (2) パソコンのターミナルでそのフォルダに移動して `claude remote-control` を実行し、Claude アプリからそのセッションにつなぐ。
- クラウドのセッションからパソコンのフォルダを使う機能は、まだ全員には開放されていない（デスクトップアプリの 設定 → Claude Code → Remote Control で共有するフォルダを選ぶ）。

---

## 4. 次にやること（おすすめ順）

1. 3-2 のセットアップスクリプトを登録する（5分。毎回の「動かない」がなくなる）。
2. 使うプラグインだけ 3-3 のドメインを許可し、使わないプラグインは外す（起動時のエラー表示が減る）。
3. 2-2 の表で「入れる」ものを決める。動画系の7本は似た内容が多いので、まとめて判断するとよい。
4. 2-1 と 2-3 のブランチを消す（消してよいと言ってもらえれば Claude がまとめて消す）。
