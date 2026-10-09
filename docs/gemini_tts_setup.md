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
   **実測（2026年9月29日）: `gemini-3.8-flash-tts` の無料枠は1日10回**（Lite は別枠）。
   ナレーション台本は1セリフ＝1回なので、9セリフの動画1本でほぼ1日分を使う。

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

## 動画にナレーションを付ける（台本YAML → 完成動画）
```bash
python3 src/narration_builder.py media/narration/eternaldct_promo_60s.yaml --video ~/Downloads/eternaldct_promo_60s.mp4
```
1. 台本（`media/narration/*.yaml`）の各セリフを Gemini TTS で音声化
2. `at` 秒の位置に配置（`until` までに収まらなければ最大1.2倍速で詰め、それでも無理なら警告）
3. ナレーション中だけ元動画の BGM を `bgm_duck_db`（デフォルト9dB）下げて合成

出力先 `media/tts_output/<台本名>/`:
| ファイル | 用途 |
|---|---|
| `<動画名>_narrated.mp4` | 完成動画 |
| `narration.wav` | ナレーションだけの音声（CapCut などで細かく調整したいとき用） |
| `NN_xxxxxxxx.wav` | セリフごとの音声。セリフ・声・指示が同じなら次回は再利用（無料枠の節約） |

- セリフを直したら YAML を編集して同じコマンドを再実行 → 直した行だけ作り直される。
- 無料枠で1分あたりの上限に当たるときは `--pace 13` を付けると13秒間隔で呼び出す。
- Flash の1日上限を使い切ったら `GEMINI_TTS_MODEL=gemini-3.8-flash-lite-tts` を付けて実行（キャッシュはモデル別なので、翌日 Flash で作り直すこともできる）。
- 気に入らない声が出たら、その行の `NN_*.wav` を削除して再実行すると作り直せる（同じ文でも毎回少しずつ読み方が変わる）。
- ffmpeg は `requirements-mcp.txt` の `imageio-ffmpeg` に同梱されているので別途インストール不要。

## 音声のない動画に BGM も付ける
```bash
# 1) 動画の長さ・構成に合わせてオリジナル BGM を合成（外部音源・API 不要、著作権の心配なし）
python3 src/bgm_synth.py -o media/music/my_bgm.wav --duration 62 --bpm 118 \
    --impact-bar 2 --build-bar 26 --drop-bar 28 --final-hit 60.0
# 2) ナレーションと一緒に動画へ合成（ナレーション中だけ BGM が下がる）
python3 src/narration_builder.py media/narration/eternaldct_motion_pv.yaml \
    --video PV.mp4 --music media/music/my_bgm.wav --pace 13
```
- `--impact-bar` / `--build-bar` / `--drop-bar` は小節番号（1小節 = 240 / BPM 秒。118BPM なら約2.03秒）。
  映像の切り替わりに合わせて決め所を置く。`--final-hit` は最後の決め音の秒数。
- 市販の曲や Lyria で作った曲を使う場合も `--music` に渡せばよい（wav / mp3）。
- **Lyria（Google の音楽生成 API）は無料枠なし**（2026年10月時点、全 Lyria モデルの無料枠上限が 0）。
  使うには AI Studio で課金設定が必要。

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
