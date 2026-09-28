# Claude Code ⇔ Gemini TTS 連携セットアップ

Claude Code から Google の **Gemini 3.8 Flash TTS**（2026年9月23日公開）を API 経由で呼び出し、
テキストを音声ファイル（.wav / .mp3）にする仕組み。

```
Claude Code ──(MCP / stdio)──> src/mcp_gemini_tts.py ──> src/gemini_tts.py ──(HTTPS)──> Gemini API
                                                                          └─> media/tts_output/*.wav
```

## 1. APIキーを発行する
1. https://aistudio.google.com/apikey で「APIキーを作成」
2. 課金設定を確認（TTS は従量課金。料金は Google の公式料金ページで確認すること）

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
