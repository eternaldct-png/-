# Circleback の口コミから: 不満・足りないもの・取り残された人、と直し方

## 集め方と限界（必ず読む）

- **集めた数: 22件（13の出典）。うち利用者本人の口コミ 14件、レビュー記事の「短所」欄 8件。星の付いた口コミは 5件。**
  目標の 100件には遠く、`reviews.py` も「30件未満は方向性の参考で、順位は当てにならない」と判定している。
- この作業環境のネットワーク設定で、App Store・Google Play・G2・Capterra・Trustpilot・Product Hunt・Reddit・Hacker News・circleback.ai
  がすべて遮断された（許可リストへの追加も環境のサービス側で拒否された）。そのためページを直接開けず、**ウェブ検索の結果に出た抜粋**だけを使った。
- そのため `reviews.csv` の本文は**原文と一字一句同じだとは確認できていない**（`verbatim` 列にそう書いた）。英語のまま残し、訳していない。
  作り話の口コミは1件も入れていない。リンク先で原文を確かめてから、外向けの資料に使うこと。
- G2 の Circleback には、同名の別製品（連絡先アプリ）のレビューが混ざっていると指摘されている。検索結果でそれと分かったものは除いた。
- 料金の話（無料プランの有無・$20〜25/月）は、出典どうしで食い違っている。

順位は `python3 .claude/skills/replica-entrepreneur/reviews.py replica/reviews.csv --themes replica/themes-meeting.json --out replica/feedback.md` の結果（星が低いほど・利用者本人の口コミほど重い）。

## 1. 不満（多い順）

| 順位 | 不満 | 件数 | 出典数 | 代表的な声（リンク） | 厚み |
| --- | --- | --- | --- | --- | --- |
| 1 | 高い・無料プランが無い・上位プラン限定の機能 | 5 | 5 | "The monthly plan can feel expensive if the user only needs occasional notes." [switchmytool](https://www.switchmytool.com/blog/circleback-ai-review) / "The app costs money for an account, which was not clearly disclosed." [App Store](https://apps.apple.com/us/app/circleback-ai-meeting-notes/id6738971048?see-all=reviews&platform=iphone) | 記事中心 |
| 2 | サポートに人がいない・返事が遅い | 5 | 3 | "No way to reach a human for support." [Trustpilot](https://www.trustpilot.com/review/circleback.ai) / "unable to talk to a human or open a support ticket" [G2](https://www.g2.com/products/circleback-ai-inc-circleback/reviews) | 利用者本人 |
| 3 | 話者の取り違え・会話が重なると崩れる | 4 | 4 | "Sometimes struggles when people talk over each other." [Tooliverse](https://tooliverse.ai/tools/circleback) / "one person's continuous speech was transcribed as two speakers" [tl;dv](https://tldv.io/blog/circleback-alternatives/) | 中 |
| 4 | 録音・ノートが取れていない／消えた | 3 | 3 | "circle back fails to take notes, which you only learn after the meeting." [Trustpilot](https://www.trustpilot.com/review/circleback.ai) / "The recording itself appeared successfully in the app, but was lost." [Google Play](https://play.google.com/store/apps/details?id=ai.circleback.app&hl=en) | 利用者本人・**いちばん深刻** |
| 5 | 権限・同意・記録の透明性 | 3 | 2 | "Consent tools are thin and there is no customer-facing audit log." [Tooliverse](https://tooliverse.ai/tools/circleback) | 薄い（記事のみ） |
| 6 | 聞き取り・要約の精度（小さい声・作り話のタスク） | 2 | 2 | "Words are not accurately recognized in softer audio." [G2](https://www.g2.com/products/circleback-ai-inc-circleback/reviews?qs=pros-and-cons) / "The AI summary sometimes hallucinates tasks that weren't actually agreed upon." [Tooliverse](https://tooliverse.ai/tools/circleback) | 薄い |
| 7 | 対面の会議に弱い | 2 | 2 | "Still needs work for in-person meetings" [G2](https://www.g2.com/products/circleback-ai-inc-circleback/reviews?qs=pros-and-cons) | 薄い |
| 8 | 処理中は次の会議を始められない | 1 | 1 | "You can't start a new meeting while another is still uploading or transcribing" [App Store](https://apps.apple.com/us/app/circleback-ai-meeting-notes/id6738971048?see-all=reviews&platform=iphone) | 薄い（1件） |
| 9 | 他社と比べて決め手が無い | 1 | 1 | "Circleback doesn't do anything that Granola or Fireflies doesn't already do better." [Medium](https://justtalkingtech.medium.com/best-ai-meeting-note-takers-in-2026-i-tested-14-over-90-days-heres-the-honest-ranking-a7ea13fb8b47) | 薄い（1人の意見） |

## 2. 足りないもの（名指しで求められている機能）

| 順位 | 求められていること | 件数 | 代表的な声 |
| --- | --- | --- | --- |
| 1 | スマホでもPC版と同じ機能を（PC版にしか無い機能がある） | 2（薄い） | "Some key functionalities are only available on desktop, it's frustrating." [Google Play](https://play.google.com/store/apps/details?id=ai.circleback.app&hl=en) |
| 2 | 話者の判定の改善 | 2 | "Reviewers suggest improvements in speaker detection." [Product Hunt](https://www.producthunt.com/products/circleback-3) |
| 3 | 人に問い合わせできる窓口 | 3 | 上の 2 と同じ |

## 3. 取り残されている人（ポジショニングの種）

- **たまにしか会議を録らない人** — 月額が割に合わない（不満1）。
- **録音を外部のサーバーに預けたくない人・同意をきちんと残したい人** — カレンダーや会議への権限を渡す必要があり、同意の記録・監査ログが薄い（不満5）。
- **対面の面談が中心の人** — 対面の会議に弱く、話者もずれる（不満3・7）。ライバーの面談・オーディションの面接はここに当たる。

## 4. 直したこと（会議ノート `tools/meeting_notes`）

| # | 不満 | 何をしたか | 大きさ | 確かめ方 |
| --- | --- | --- | --- | --- |
| 1 | 高い・分からない | 月額なし（自分のPCで動く）。AIの費用を1回ずつ記録し、会議ごと・月ごとに円で表示。**月の上限を超えたらAIを呼ばずに止める** | M | `test_fix1_*`、E2E FIX1-2-4 |
| 2 | サポートがいない | 「設定」に**動作チェック**（APIキー・Python・Whisper・モデル・空き容量・書き込み・DB・失敗した会議・処理待ち）を置き、✗/⚠ には直し方まで出す。README に症状別の対処表 | S | `test_fix2_*`、E2E FIX1-2-4 |
| 3 | 話者の取り違え | 文字起こしの**1行ずつ話者を直せる**。参加者の名前から**AIで話者を推定**（空の行だけ・参加者以外の名前は付けない・「推定」の印付き。人が直すと印が消える）。話者の無い行を1行ずつに分けて取り込む | M | `test_fix3_*`、E2E FIX3-H1 |
| 4 | 同意・透明性 | 録音の前に「相手に伝えた／自分だけのメモ」を**選ばないと録音できない**（会議に記録）。**操作の記録**（作成・編集・削除・書き出し・AIへの送信・失敗・設定変更）。**録音ファイルの保存日数**を決めると自動で削除（ノートは残す）。外に送るもの・送らないものを設定画面に明記 | M | `test_fix4_*`、E2E F01-H1 |
| 5 | 録音が消えた・後で気づく | 録音中、**10秒ごとに音声をPCへ保存**（送り直し・順番の確認つき）。ブラウザが落ちても**次に開いたとき「途中で止まった録音」から会議にできる**。途中保存が失敗しても手元の録音をまとめて送る。**20秒無音が続いたら警告**。処理が終わった・失敗したら**デスクトップ通知**。Whisper が無くても録音は保存（前回の BUG-003） | M | `test_fix5_*`、E2E FIX5-H1 |
| 6 | 精度・作り話のタスク | やることごとに**根拠の発言**をAIに書かせ、**文字起こしに本当にあるかを機械で確かめる**。無ければ「⚠ 要確認」、あれば時刻から聞き直せる。プロンプトで「合意・依頼・引き受けたものだけ」と指示。**よく出る言葉・固有名詞**を Whisper と AI に渡す。**小さい声を拾うモード**（無音カットを切る） | M | `test_fix6_*`、E2E FIX6-H1 |
| 7 | 対面に弱い | **マイクを選べる**（外付け・スピーカーフォン）。**会議室モード**（エコー除去・ノイズ除去・自動音量を切って、離れた声を消さない）。小さい声モード・AI話者推定と組み合わせる | S | E2E F01-H1 |
| 8 | 処理中は次を始められない | もともと処理はキューで、処理中も次の会議を入れられる。一覧に「処理中・処理待ち n件」を出す | S | `test_fix8_*`、E2E FIX8-H1 |

`features.csv` に `original=no` の行として追加した。

### 直さなかったもの（理由）

- **スマホのアプリ**（足りないもの1）: ブラウザのマイクは HTTPS か localhost でしか使えず、PCのアプリをスマホから安全に使うには証明書と認証が必要になる。自分専用の範囲を超えるので見送り。対面の会議はPCで録るか、スマホのボイスメモの録音ファイルを AirDrop でPCに送って「録音ファイルを入れる」から取り込む（README に記載）。
- **他社と比べた決め手**（不満9）: 機能ではなく位置づけの問題。下の「切り口」で扱う。
- **話者の自動判定そのもの（声で聞き分ける）**: Whisper 単体ではできない。pyannote などの話者分離は導入が重く（Hugging Face のトークン・数GBのモデル）、精度も対面・1本のマイクでは限られる。今回は「AIで推定＋人が1行ずつ直す」で代替。

## 5. 切り口（3案）

```
A. ライバー事務所・小さな会社の代表で、面談や商談の録音を外部サービスに預けたくない人へ。
   会議ノートは、録音をPCの外に出さず、同意と操作の記録を残しながら、要約とやることを作る。
   根拠: 不満5（3件・2出典、薄い）、不満4（3件・3出典）

B. たまにしか会議を録らないのに、月額を払いたくない人へ。
   会議ノートは月額なし、使った分のAI代（1時間の会議で数十円、推測）だけで、月の上限も決められる。
   根拠: 不満1（5件・5出典、記事中心）

C. AIの議事録に「言っていないタスク」が混ざるのが怖い人へ。
   会議ノートは、やることごとに根拠の発言を示し、文字起こしに無いものは「要確認」と出す。
   根拠: 不満6（2件、薄い）＋不満3（4件）
```

**おすすめ: A。** 自分の事業（ライバーの面談・オーディション、中小企業への AI 導入支援）にそのまま当てはまり、
「録音を外に出さない」は今回の作りの本質（ローカル処理）なので、真似されにくい。ただし根拠が薄い（記事の指摘が中心）ので、
外販するなら先に 100件規模で口コミを集め直すこと。

注意: 外向けの名前・広告・ストアの説明に Circleback の名前を出さない。比較ページを作るなら、事前に弁護士に確認する。
集めた口コミは調べもので、自社の宣伝文句（推薦の声）に使ってはいけない。
