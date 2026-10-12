# AIキャラ TikTok LIVE（B案・試作）

TikTok LIVE のコメント・ギフト・フォローを受け取り、AIキャラが返事を考えて、VOICEVOXの声で読み上げます。
画面にはキャラ・字幕・ギフト演出を出し、それを TikTok LIVE Studio で配信します。

```
TikTok LIVE ─(非公式ライブラリ TikTokLive)→ ai_live.py ─→ Claude（返事を作る）
                                               ├→ VOICEVOX（声にする）→ スピーカー / 仮想オーディオ
                                               └→ 配信画面 http://127.0.0.1:8765/（キャラ・字幕・演出）
                                                       ↓ ウィンドウキャプチャ
                                                 TikTok LIVE Studio → 配信
```

## できること（試作の範囲）

| 機能 | 内容 |
|---|---|
| コメント返事 | 新しいコメントを優先して返事。同じ人には30秒あけるなど、連投で独占されないようにしている |
| ギフト演出 | ダイヤ数で3段階（small / middle / big）。花火・ハート・キラキラと、お礼の帯を即座に表示 |
| ギフトのお礼 | 小さいギフトは定型文（速い・AI代0円）、大きいギフトはAIが特別なお礼を考える |
| フォローのお礼 | フォローされたら名前を呼んでお礼 |
| 雑談 | 25秒コメントが無ければ、`idle_topics` の話題で話しかける（沈黙を防ぐ） |
| 安全対策 | NGワード・URL・長文のコメントは読まない。AIの返事にNGワードが入れば差し替える。コメント内の命令（「設定を無視して〜と言って」）には従わない |
| オペレーター操作 | `/say` で直接しゃべらせる、`/ai` で指示、`/pause` で緊急停止、`/stats` でAI代を表示 |
| AI代の集計 | 実際に使ったトークン数から円に換算して表示。会話ログは `logs/` に保存 |

アバターはまず **静止画（`tools/motion_render/chars/` の画像）をしゃべるときに揺らすだけ** の簡易版です。
Live2D にするときは VTube Studio を使い、音声を仮想オーディオ経由で渡して口パクさせます（下の「Live2Dにする」）。

## 準備（配信するWindows PC）

1. Python 3.10以上を入れる
2. このフォルダで `pip install -r requirements.txt`
3. [VOICEVOX](https://voicevox.hiroshiba.jp/) を入れて起動しておく（無料）。`config.yaml` の `voice.speaker_id` で声を選ぶ
   - **使うキャラの利用規約とクレジット表記（例:「VOICEVOX:〇〇」）を必ず確認**し、配信のプロフィールなどに書く
4. 環境変数を設定する
   - `ANTHROPIC_API_KEY` … Claude のAPIキー（このリポジトリの投稿文生成と同じもので可）
   - `SIGN_API_KEY` … Euler Stream のAPIキー（任意。無いと無料枠で制限が厳しい）
5. `config.yaml` の `tiktok.unique_id` を配信するアカウントの @ID にする。キャラ名・設定・NGワードもここで変える

## 動かし方

```bash
# 1) まずAI代0円で画面と声だけ確認（ダミーのコメント・ギフトが流れる）
python ai_live.py --demo --no-ai

# 2) AIの返事を確認（ダミーのコメントにAIが返事。AI代がかかる）
python ai_live.py --demo

# 3) 本番（TikTokで配信を開始してから起動。開始前に起動しても30秒ごとに再接続する）
python ai_live.py
```

起動したら、ブラウザで `http://127.0.0.1:8765/` を開き、TikTok LIVE Studio の「ウィンドウキャプチャ」でそのブラウザを取り込みます。
声は LIVE Studio の「デスクトップ音声」で拾います。

起動中は、黒い画面（ターミナル）に次のコマンドを打てます。

| コマンド | 動き |
|---|---|
| `/say こんばんは！` | そのまましゃべらせる |
| `/ai 新曲の告知をして` | AIに指示してしゃべらせる |
| `/pause` / `/resume` | 返事を一時停止・再開（荒れたときの緊急停止） |
| `/stats` | ここまでのAI代を表示 |
| `/quit` | 終了 |
| `c 名前 コメント` / `g 名前 ギフト名 ダイヤ数` | （`--demo` のときだけ）ダミーのイベントを送る |

## Live2Dにする（任意）

1. Live2Dモデルを用意する（制作の外注が必要。見積もりを取る）
2. VTube Studio（Steam・無料）にモデルを読み込む
3. 仮想オーディオ（VB-CABLE など）を入れ、`config.yaml` の `voice.output_device` に `CABLE Input` などデバイス名の一部を書く
   （`pip install sounddevice numpy` が必要）
4. VTube Studio のマイク入力を `CABLE Output` にして、口パクを音声に連動させる
5. `overlay.html` のキャラ画像を消して、VTube Studio の画面と字幕の画面を LIVE Studio で重ねる

## 費用

[docs/ai_live_cost.md](../../docs/ai_live_cost.md) にまとめています。

## 注意（必ず読む）

- **TikTokLive は非公式ライブラリです。** TikTokの仕様変更で突然つながらなくなることがあります。
- **人がいないAIだけの配信は、TikTokのLIVE収益化ガイドラインで「収益化の対象外」とされる可能性があります**（第三者サイトの引用で、TikTok公式の文面は未確認）。
  試作では、人がそばで見ていて `/say` `/ai` `/pause` で介入できる運用を前提にしています。完全な無人放置はしないでください。
- AI生成のコンテンツであることは、配信タイトルやプロフィールで明示してください。
- 利用規約・著作権（声・キャラ・BGM）・収益化の扱いは、最終的にTikTok公式のガイドラインと専門家に確認してください。
