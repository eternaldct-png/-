# AIキャラ TikTok LIVE（B案）の費用まとめ

調査日: 2026-10-12。為替は **1ドル=160円で仮置き**（2026年4月の実勢 159.64円〔FRB/FRED〕をもとにした仮の値。10月の実勢は未確認）。
「推定」と書いた数字は、前提を置いた計算で、実際の配信で `/stats` を見て確かめる必要がある。

## 結論

| 構成 | 初期費用 | 月額（1日3時間×30日＝90時間配信） |
|---|---|---|
| **最小構成**（静止画アバター＋VOICEVOX＋Claude Haiku） | **0円** | **約1,500円**（AI代 約1,100円＋電気代 約400円） |
| 標準構成（＋Claude Opus＝返事が賢い＋接続を安定させる有料キー） | 0円 | 約5万円（AI代 約42,000円＋Euler Stream 約8,000円＋電気代） |
| Live2D構成（上のどちらか＋Live2Dモデル） | **モデル制作費（要見積もり）**＋VTube Studio 0〜約2,400円 | 上と同じ |

**いちばん効くのはAIモデルの選び方**（Opus と Haiku で約40倍の差）。まず Haiku で品質を確かめ、物足りなければ Sonnet → Opus と上げるのがよい。

## 1. AI代（Claude API）— 使った分だけ

公式の料金（USD / 100万トークン。Anthropic のモデル一覧、2026-10-06時点）:

| モデル | 入力 | 出力 | 特徴 |
|---|---|---|---|
| Claude Opus 5.5（試作の既定） | $4.00 | $20.00 | いちばん自然で賢い。考える時間のぶん少し遅い |
| Claude Sonnet 5.5 | $2.00 | $10.00 | 中間 |
| Claude Haiku 5.5 | $0.10 | $0.50 | 速くて安い。短い返事向き |

**計算の前提（推定）**: 1回の返事＝入力 約1,700トークン（キャラ設定＋直近8往復＋コメント）＋出力 約150トークン。
1時間に約300回返事（1回あたり 考える2秒＋しゃべる5秒＋間2秒）。

| モデル | 1返事 | 1時間 | 月90時間 |
|---|---|---|---|
| Opus 5.5 | 約1.6円 | 約470円 | **約42,300円** |
| Sonnet 5.5 | 約0.8円 | 約235円 | 約21,200円 |
| Haiku 5.5 | 約0.04円 | 約12円 | **約1,100円** |

- 小さいギフトのお礼・フォローのお礼は定型文なので、AI代はかからない。
- コメントが多くても、返事の回数は「しゃべる速さ」で上限が決まる（1時間300回前後）。視聴者が増えてもAI代は青天井にはならない。
- 切り替えは `config.yaml` の `ai.model` を1行変えるだけ。

## 2. TikTokからコメント・ギフトを受け取る部分

| 項目 | 費用 | 補足 |
|---|---|---|
| TikTokLive（Pythonライブラリ） | 0円 | 非公式。仕様変更で止まることがある |
| Euler Stream（署名サーバー）無料枠 | 0円 | 1日2,500リクエストなど。制限が厳しいとの報告あり |
| Euler Stream Business | $50/月（約8,000円） | 安定させたいとき。48時間の無料お試しあり |

## 3. 声（読み上げ）

| 項目 | 費用 | 補足 |
|---|---|---|
| VOICEVOX | **0円** | キャラごとに利用規約が違う。多くは「VOICEVOX:キャラ名」のクレジット表記で商用可。**企業が使う場合は事前確認が必要なキャラもある**（例: 青山龍星）。クレジットなしで使う場合は有料契約になる例もある（Voiceger版ずんだもん: 1キャラ40万円＋税） |
| ElevenLabs（任意・より自然な声やオリジナル声） | Starter $5〜6/月（約1,000円）、Creator $22/月（約3,500円） | 無料プランは商用不可。オリジナル声のクローンは Creator 以上。価格は第三者サイトの情報で、公式未確認 |

## 4. 見た目（アバター）

| 項目 | 費用 | 補足 |
|---|---|---|
| 静止画アバター（試作の方式） | 0円 | 所属キャラ画像をしゃべるときに揺らす |
| VTube Studio | 0円（Steam） | Webカメラで顔を動かす場合のみ、透かし削除DLC $14.99（約2,400円・買い切り）。AIキャラは顔を動かさないので不要なことが多い |
| Live2D Cubism Editor | 個人・年商1,000万円未満の事業者は無料との情報あり | 第三者ブログの情報で公式未確認。モデルを自社で作る場合のみ必要 |
| Live2Dモデルの制作（外注） | **わかりません（要見積もり）** | イラスト＋モデリングの外注費は依頼先と仕様で大きく変わる |

## 5. 演出ツール（任意）

| 項目 | 費用 | 補足 |
|---|---|---|
| TikFinity | 無料版あり / Pro 約$19/月（約3,000円） | 試作では演出を自前の画面で作ったので**不要**。Pro価格は第三者情報 |

## 6. 配信環境

| 項目 | 費用 | 補足 |
|---|---|---|
| Windows PC | 既存PCを使う前提で0円 | TikTok LIVE Studio は Windows のみとの情報（2026年5月時点、第三者） |
| 電気代 | 約420円/月（推定） | 150W × 90時間 × 31円/kWh（目安単価）で計算 |
| TikTok LIVE Studio | 0円 | **PC配信にはフォロワー1,000人以上などの条件があるとの情報**（第三者・公式未確認） |

## お金のリスク（費用以上に大事）

| リスク | 内容 | 確信度 |
|---|---|---|
| 収益化の対象外になる | TikTokのLIVE収益化ガイドラインは「人が実質的に関わらず、主に自動のシステムで運営されるLIVE」を収益化の対象外とする、と第三者サイトが引用している。**ギフト収入がゼロ扱いになれば、B案は収益モデルごと崩れる** | 中（公式文面は未確認） |
| 接続が止まる | 非公式ライブラリなので、TikTok側の変更で受信が止まる。止まっている間はただの静止画配信になる | 高 |
| 費用の読み違い | AI代は返事の長さ・会話履歴の量・モデルで大きく変わる。最初の数回は `/stats` で実測すること | 高 |
| TikTok Shop の配信には使えない | TikTok Shop（米国）は、AI音声・録音音声で商品を紹介するLIVEを禁止している | 高（TikTok Shop公式の販売者向けページ） |

利用規約・収益化・声や画像の権利は、TikTok公式のヘルプと専門家（弁護士など）に最終確認すること。

## 出典

- Claude API の料金: Anthropic 公式のモデル一覧（2026-10-06時点）
- [FRED: 円/ドルのスポットレート](https://fred.stlouisfed.org/series/EXJPUS)
- [Euler Stream SDK（GitHub）](https://github.com/eulerstream/euler-api-sdk) / [TikTokLive（PyPI）](https://pypi.org/project/TikTokLive/)
- [VOICEVOX の商用利用（crystal-method）](https://crystal-method.com/blog/voicevox-commercial/) / [VOICEVOX の使い方と商用利用（Hakky）](https://book.st-hakky.com/data-science/voicevox-usage-and-commercial-use)
- [ElevenLabs の料金（smallest.ai）](https://smallest.ai/blog/elevenlabs-pricing-plans-cost-what-you-get-in-2026) / [ElevenLabs の料金（magichour）](https://magichour.ai/blog/elevenlabs-pricing)
- [VTube Studio（DekuDeals）](https://www.dekudeals.com/items/vtube-studio) / [透かし削除DLC（DekuDeals）](https://www.dekudeals.com/items/vtube-studio-remove-watermark) / [VTuberソフト比較（Eklipse）](https://blog.eklipse.gg/reviews/best-vtuber-software.html)
- [TikFinity（AlternativeTo）](https://alternativeto.net/software/tikfinity/about/) / [TikFinity Mobile の無料版とPro版（公式ブログ）](https://blog.tikfinity.com/how-to-set-up-tikfinity-mobile/)
- [TikTok Shop: 高品質な動画とLIVEの要件](https://seller-us.tiktok.com/university/essay?knowledge_id=4581457528243969&lang=en) / [Livecade: LIVE制限の解除](https://livecade.io/docs/fix-live-restrictions/) / [TikTokのAI音声ルール（aituber.app）](https://aituber.app/blog/tiktok-ai-voice-rules/)
- [TikTok LIVE の配信条件（assist-all）](https://lifestyle.assist-all.co.jp/tiktok-live-requirements-beginners-guide/) / [TikTok LIVE Studio の設定ガイド（Eklipse）](https://blog.eklipse.gg/beginner-guide-2/tiktok-live-studio-setup-guide.html)
