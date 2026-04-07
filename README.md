# X 自動投稿システム

ペルソナを定義して、Claude AIがリサーチ＆投稿文を自動生成し、GitHub Actionsで定期投稿するシステム。

## 構成

```
.
├── persona/
│   └── config.yaml          # ← ペルソナ設定（ここを編集する）
├── src/
│   ├── main.py              # メイン処理
│   ├── research.py          # トレンドリサーチ（DuckDuckGo）
│   ├── generate.py          # Claude APIで投稿文生成
│   └── post.py              # X APIで投稿
├── posts/
│   └── history.json         # 投稿履歴（自動生成）
├── .github/workflows/
│   └── auto_post.yml        # GitHub Actions スケジュール
├── .env.example             # 環境変数テンプレート
└── requirements.txt
```

## 投稿フロー

```
[GitHub Actions / cron]
       ↓
  ペルソナ設定読み込み (persona/config.yaml)
       ↓
  DuckDuckGo でトレンドリサーチ
       ↓
  Claude API で投稿文生成（ペルソナに合わせて）
       ↓
  X API で投稿
       ↓
  投稿履歴を posts/history.json に保存
```

---

## セットアップ

### 1. ペルソナをカスタマイズ

`persona/config.yaml` を編集して自分のキャラクターを定義する。

```yaml
name: "たろう"
bio: "普通のエンジニア。日常のこと、気になったこと、なんでもつぶやくよ。"
personality:
  - "話しかけやすい雰囲気"
  - "フォロワーの意見を聞くのが好き"
interests:
  - "テクノロジー・AI"
  - "グルメ・カフェ"
```

### 2. X API キーの取得手順

#### Step 1: X Developer Portal にアクセス

1. [https://developer.twitter.com/en/portal/dashboard](https://developer.twitter.com/en/portal/dashboard) を開く
2. Xアカウントでログインする

#### Step 2: アプリを作成する

1. 「+ Create Project」をクリック
2. プロジェクト名を入力（例: `auto-post-bot`）
3. ユースケースを選択（「Making a bot」が近い）
4. 説明を入力して「Next」

#### Step 3: アクセスレベルを設定する

1. 作成したアプリの「Settings」→「User authentication settings」
2. 「OAuth 1.0a」を有効化
3. **App permissions**: 「Read and write」を選択 ← **重要（書き込み権限が必要）**
4. **Callback URL**: `https://localhost` でOK
5. 保存する

#### Step 4: API キーを取得する

1. 「Keys and Tokens」タブを開く
2. 以下の4つをメモする：
   - **API Key** → `X_API_KEY`
   - **API Key Secret** → `X_API_SECRET`
   - **Access Token** → `X_ACCESS_TOKEN`
   - **Access Token Secret** → `X_ACCESS_SECRET`

> **注意**: Access Token は「Read and write」で再生成すること。「Read only」のままだと投稿できない。

#### Step 5: APIの利用制限について

| プラン | 月間ツイート数 | 料金 |
|--------|--------------|------|
| Free   | 500件        | 無料 |
| Basic  | 3,000件      | $100/月 |

1日3回 × 30日 = 90件なので **Free プランで十分**。

### 3. Claude API キーの取得

1. [https://console.anthropic.com](https://console.anthropic.com) にアクセス
2. アカウント作成 / ログイン
3. 「API Keys」→「Create Key」
4. キーをコピー（`sk-ant-...` で始まる文字列）

### 4. GitHub Secrets に登録

リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」で以下を追加：

| Secret名 | 値 |
|----------|---|
| `ANTHROPIC_API_KEY` | ClaudeのAPIキー |
| `X_API_KEY` | X API Key |
| `X_API_SECRET` | X API Key Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_SECRET` | Access Token Secret |

---

## ローカルで試す

```bash
# 依存関係をインストール
pip install -r requirements.txt

# .env ファイルを作成
cp .env.example .env
# .env を編集してAPIキーを入力

# 投稿文だけ生成（投稿しない）
python src/main.py --generate

# プレビュー（X APIへの投稿なし）
python src/main.py --dry-run

# 実際に投稿
python src/main.py
```

## 投稿スケジュール

| 時間 | タイミング |
|------|-----------|
| 8:00 JST | 朝の投稿 |
| 12:00 JST | 昼の投稿 |
| 20:00 JST | 夜の投稿 |

GitHub Actions の「Actions」タブから手動実行も可能。

## ペルソナのカスタマイズ Tips

### 口調を変える例

```yaml
# 丁寧系
personality:
  - "ですます調で話す"
  - "礼儀正しい"

# ギャル系
personality:
  - "ギャル語を使う（マジ、やば、神など）"
  - "テンション高め"

# 専門家系
personality:
  - "専門用語を適度に使う"
  - "根拠を示すのが好き"
```

### テーマを絞る例

```yaml
interests:
  - "投資・資産運用"
  - "筋トレ・フィットネス"
  - "子育て"
```
