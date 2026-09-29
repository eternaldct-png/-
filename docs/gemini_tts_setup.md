# Claude Code ⇔ Gemini TTS 連携セットアップ

Claude Code から Google の **Gemini 3.8 Flash TTS**（2026年9月23日公開）を API 経由で呼び出し、
テキストを音声ファイル（.wav / .mp3）にする仕組み。

```
Claude Code ──(MCP / stdio)──> src/mcp_gemini_tts.py ──> src/gemini_tts.py ──(HTTPS)──> Gemini API
                                                                          └─> media/tts_output/*.wav
```

## 1. APIキーを発行する（無料枠で使う）
1. https://aistudio.google.com/apikey で「APIキーを作成」
2. **課金（Billing）を設定していない Google Cloud プロジェクトのキーを使う** — これで無料枠（Free tier）になる。
   課金を有効にしたプロジェクトのキーは有料枠になり、使った分だけ請求される。
3. 自分の無料枠の上限（1分あたり・1日あたりの回数）は AI Studio の「Rate limits / 使用量」画面で確認する。
   Google は TTS の無料枠の具体的な回数を公表しておらず、アカウントや時期で変わる。

### 無料枠の上限に達したとき（自動処理）
| 状況 | 動き |
|---|---|
| 1分あたりの上限（HTTP 429） | API が指示する秒数（60秒以内）だけ待って1回だけ再試行 |
| 1日あたりの上限、または再試行でもダメ | `gemini-3.8-flash-lite-tts` に切り替えて作り直す（上限はモデルごとに別枠） |
| 両方とも上限 | エラー。1日の上限は太平洋時間の0時（日本時間16〜17時ごろ）にリセット |

- 切り替え先は `GEMINI_TTS_FALLBACK_MODELS`（カンマ区切り）で変更、`none` で無効化。
- Lite に切り替わった場合は、Claude Code の返答に「[model: gemini-3.8-flash-lite-tts]」と表示される（音質・表現力は Flash より下がる）。

### 無料枠の注意
- **無料枠では、送ったテキストと生成音声が Google のサービス改善に使われることがある。**
  応募者の氏名・住所など個人情報や、未発表の歌詞・台本を読み上げさせない。
- 無料枠は予告なく縮小されることがある（2026年4月に Pro 系モデルが無料枠から外れた前例あり）。
  業務で毎日必須になったら、有料枠（Flash-Lite で1分あたり約1円以下）への切り替えを検討する。

## 2. 自分のPCで準備する（初回のみ）
```bash
cd <このリポジトリ>
pip install -r requirements-mcp.txt

# APIキーを環境変数に（Mac/Linux: ~/.zshrc などに追記）
export GEMINI_API_KEY="取得したキー"
```
Windows (PowerShell): `setx GEMINI_API_KEY "取得したキー"` → ターミナルを開き直す。

## 3. Claude Code を起動する
リポジトリ直下で `claude` を起動すると `.mcp.json` の `gemini-tts` サーバーが読み込まれる
（初回は「このMCPサーバーを使いますか？」と聞かれるので承認）。`/mcp` で接続状態を確認できる。

あとは Claude Code にこう頼むだけ:
- 「『今夜21時から配信します！』を明るい女性の声で音声にして」
- 「kazuto と あまりん の掛け合いでオーディション告知の音声を作って。kazuto=Puck、あまりん=Kore」
- 「使える声の一覧を見せて」

## 使えるツール
| ツール | 内容 |
|---|---|
| `text_to_speech` | テキスト → 音声。`voice`（声）、`style`（読み方の指示）、`speakers`（2人の掛け合い）、`output_path`、`model` を指定可 |
| `list_voices` | プリセット音声30種の一覧 |

- 保存先のデフォルト: `media/tts_output/tts_日時.wav`（Git管理外）
- `.mp3` で保存するには ffmpeg が必要
- 文中に `<laugh>` `<sigh>` `<short pause>` などのタグを入れると笑い・ため息・間を表現できる

## モデルの切り替え
| モデル | 用途 |
|---|---|
| `gemini-3.8-flash-tts`（デフォルト） | 表現力重視（告知・ナレーション・キャラボイス） |
| `gemini-3.8-flash-lite-tts` | 低コスト・大量生成向け |

環境変数 `GEMINI_TTS_MODEL` で全体を切り替えるか、ツール呼び出し時に `model` を指定する。
新しいモデルが出たら同じ方法で差し替えられる（コード変更不要）。

## MCPを使わずにコマンドで使う
```bash
python3 src/gemini_tts.py "こんにちは" --voice Kore --style "明るく元気に"
python3 src/gemini_tts.py --file script.txt -o media/tts_output/intro.mp3
python3 src/gemini_tts.py "kazuto: やあ\nあまりん: こんにちは" --speakers "kazuto=Puck,あまりん=Kore"
python3 src/gemini_tts.py --list-voices
```

## 注意
- **Claude Code on the web（クラウド）で使う場合**: 環境のネットワーク設定で
  `generativelanguage.googleapis.com` への通信を許可し、環境変数に `GEMINI_API_KEY` を登録する必要がある。
- 未対応: Gemini 3.8 の「Voice design（自然文で声を作って ID で再利用）」機能。
  現状はプリセット音声 + `style` 指示で調整する。
- 生成音声を配信・販売物に使う場合は、Google の利用規約（生成物の商用利用条件、AI生成である旨の表示要否）を確認すること。
