# 元のアプリの口コミから: 不満・足りないもの・取り残された人、と直し方

## 集め方と限界（必ず読む）

- **数えた指摘: 14件（7つの出典）。星の付いた口コミ: 0件。利用者本人の声: 2件（1人のnote記事）。**
  目標の 100件にはまったく届かない。`reviews.py` も「30件未満は方向性の参考で、順位は当てにならない」と判定している。
- **そもそも利用者の口コミがほとんど見つからない。** App Store・Google Play にアプリが無く（Webのみ）、GetApp は「No reviews」（0件）、
  レビューサイトの stork.ai は「2026年11月3日時点で Trustpilot・Reddit・G2 に独立した利用者の口コミが無い」と書いている（検索結果より）。
- そのため集まったのは主に **レビュー記事の「短所」欄** で、**14件のうち6件は競合他社が書いた記事**（vmake / magiclight / anijam / nemovideo）。
  競合は元のアプリを悪く書く理由があるので、割り引いて読むこと（`reviews.csv` の `kind` 列に `competitor` と書いた）。
- この作業環境のネットワーク設定で、元のサイトもレビュー記事も直接開けなかった（DNS で遮断）。**ウェブ検索の結果に出た抜粋**だけを使った。
  本文は原文と一字一句同じだとは確認できていない（`verbatim` 列）。作り話の口コミは1件も入れていない。外向けの資料に使う前にリンク先で原文を確かめること。
- 出典のページを特定できなかった指摘は、数に入れずに下の「参考」に分けた。

順位は `python3 .claude/skills/replica-entrepreneur/reviews.py replica/anime/reviews.csv --themes replica/anime/themes-anime.json --out replica/anime/feedback.md`。

## 1. 不満（多い順）

| 順位 | 不満 | 件数 | 出典数 | 代表的な声（リンク） | 厚み |
| --- | --- | --- | --- | --- | --- |
| 1 | クレジット・料金（期限切れ・やり直しで減る・料金が不明・無料枠が狭い） | 7 | 4 | "Skip it if you dislike expiring, promo-driven credits." [stork.ai](https://www.stork.ai/en/oiioii) / 「動画生成中にエラーが発生することがある。再実行で対処できるが、その分のクレジットが消費される。」[metagri-labo](https://metagri-labo.com/ai-guide/oiioii-ai-intro/) | 記事のみ・**いちばん多い** |
| 2 | キャラ・場面がそろわない（人の手直しが要る） | 3 | 2 | "AI-generated animation still may need human intervention to achieve consistency and creativity." [vmake](https://vmake.ai/blog/oiioii-review) | 競合の記事のみ |
| 3 | 細かく直せない・決まった流れが指示より優先される | 3 | 3 | "the fixed flow has a higher priority than our instructions" [note（GENEL）](https://note.com/genel/n/n838e8c0b1867?hl=en) / "linear logic and lack of long-term creative memory can feel restrictive" [anijam](https://www.anijam.ai/blog/oiioii-ai-review/) | 利用者1人＋競合 |
| 4 | 短い動画しか作れない・物語の深さが出ない | 2 | 2 | "Some handle short clips well but fall apart the moment a project demands real narrative depth." [magiclight](https://magiclight.ai/academy/oiioii-ai-review/) | 薄い（競合のみ） |
| 5 | 使い始めるまでが面倒（招待制・同時に2カットまで） | 2 | 1 | 「招待コード制を採用しているため、利用開始にひと手間かかります」[metagri-labo](https://metagri-labo.com/ai-guide/oiioii-ai-intro/) | 薄い |
| 6 | 仕事に使えるか自分で確かめる必要がある（品質・権利・ライセンスが不明） | 2 | 1 | "Exact plan names, credit costs, and commercial license terms are missing." [nemovideo](https://www.nemovideo.com/model/oiioii-ai) | 薄い（競合のみ） |
| 7 | 生成中のエラー・不安定 | 1 | 1 | （1位の metagri-labo と同じ文） | 薄い（1件） |
| 8 | 似た動画・同じ言い回しばかりになる | 1 | 1 | "similar videos and the same phrases fill up the timeline" [note（GENEL）](https://note.com/genel/n/n838e8c0b1867?hl=en) | 薄い（1件。宣伝の仕方への指摘） |

### 参考（出典のページを特定できなかったので数に入れていない指摘）

検索の要約に「あるレビューでは」として出てきたが、どの記事か特定できなかったもの。直す対象には入れたが、件数には数えていない。

- 英語の読み上げ（TTS）がロボットのよう。声は自分で入れ直すのがおすすめ
- 無料版は透かし入り・月3本・15秒まで。1080p・透かしなしは有料
- 1回の生成は30〜60秒ほどの短い動画まで
- 細かい動き・ポーズの指定に限界がある（"Limited manual control over specific animation frames"）
- エージェントが多く、慣れるまで分かりにくい（"Steep learning curve"）
- ベータ版で不安定・ときどき失敗する
- 再生成を繰り返すとクレジットが減るので、最初はさっと承認して完成まで行くほうがよい（note の試用記事）

## 2. 足りないもの（名指しで求められている機能）

`reviews.py` の「求める声」の型には何も当たらなかった。短所の裏返しとして読めるもの:
- 1カット・1コマだけを細かく直す機能（不満3）
- 作品をまたいだ記憶（同じキャラ・設定を続きで使う）（不満3・4）
- 料金・ライセンスの分かりやすい表示（不満1・6）

## 3. 取り残された人（作業ごと無視されている）

- **細かく監督したい人**: 「初心者は迷わないが、中上級者には自由度が低い」（note・GENEL）。おまかせ一択の流れが合わない人
- **続き物・シリーズを作りたい人**: 「物語の深さ」「長期の記憶」が無い（競合の指摘）
- **仕事（クライアント案件）で使いたい人**: 品質・権利・ライセンスを自分で確かめる必要がある（競合の指摘）

## 4. 直したこと（全部コマドリに入れた）

元のアプリの中心の不満（クレジット・招待制・透かし・長さの上限）は、自分用のアプリでは**もともと無い**（無料・ローカル・透かしなし）。そのうえで、残る不満を次のように直した。
テストは `tests/test_anime_studio.py` の `test_fix_*`（11件）と E2E の `FX*`。

| # | 直したこと | どの不満 | 大きさ | テスト |
| --- | --- | --- | --- | --- |
| FX1 | **決まりごと**（作品ごと＋設定の「いつもの決まりごと」）を、どの段階でも毎回AIに最優先で渡す。決まり文句を使わないようAIに指示 | 3（指示より流れが優先・長期の記憶がない）、8 | S | `test_fix_rules_are_sent_to_ai_every_time` / E2E FX1 |
| FX2 | **1カットだけ直す**: 「この絵だけ作り直す」（変えたいことを書ける）、「このカットだけAIで直す」。ほかのカットは変えない | 3、1（やり直しで全部の費用がかかる） | M | `test_fix_rewrite_one_shot_only` / `test_fix_regenerate_one_image_only` / E2E FX2 |
| FX3 | **1カットの失敗で全部を止めない**。通信の失敗は1回だけ自動でやり直す。「絵が無い・失敗したカットだけ作る」で、できたカットの分は二度払わない | 7、1 | M | `test_fix_one_failed_shot_does_not_stop_others_and_retry_only_missing` |
| FX4 | **見た目をそろえる**: AI画像のプロンプトに毎回キャラの見た目と背景の説明を同じ言葉で入れ、作品ごとに同じ乱数の種を使う。画像も説明も無いキャラ・場面が「なし」のカットを警告 | 2 | S | `test_fix_consistency_prompt_and_seed` |
| FX5 | **押す前に見積もり**: 有料の設定のときは「全部で約○円・失敗したカットだけなら約○円・今月の合計」を出し、確認してから作る。無料の設定ならそう表示 | 1 | S | `test_fix_cost_estimate_shown_before_paid_generation` |
| FX6 | **続きを作る**: 同じキャラ（画像・声）・決まりごと・前の回のあらすじを引きついで次の回を作る。尺の上限を180秒→600秒に | 4、3 | M | `test_fix_sequel_keeps_characters_rules_and_story` / E2E FX6 |
| FX7 | 前の作品とアイデアがほぼ同じなら知らせる。仮の絵はカメラ（寄り・引き）に合わせて構図を変える | 8 | S | `test_fix_similar_idea_warning` |
| FX8 | **声の差し替え**: 読み上げが不自然なカットは、自分（やライバー本人）が録った声に替えられる。キャラごとに読み上げの速さを変えられる | 参考（TTS がロボット） | S | `test_fix_recorded_voice_replaces_tts` |
| FX9 | **書き出す前の確認**: 絵が全部ある・失敗なし・セリフが尺に収まる・全段階が終わっている を自動で確認し、BGMの権利・出演の了承は自分でチェック | 6 | S | `test_fix_preflight_checklist` / E2E FX9 |
| FX10 | **はじめての人向け**: 新規作成に3ステップの説明と「例を入れてみる」、各段階に「ここでやること」の一言 | 5、参考（慣れるまで分かりにくい） | S | E2E FX8 |

もとから無い（直す必要がない）もの: 招待制、同時に2カットまでの制限、透かし、クレジットの期限、月の本数の上限、30〜60秒の上限。

## 5. 売るときの切り口（参考。自分用なので今は使わない）

```
For 所属ライバー・推しキャラのショートアニメを続き物で作りたい事務所 who クレジットが消える・やり直すたびにお金が減るのが嫌な人,
コマドリ は 自分のPCで無料で動き、1カットだけ直せて、同じキャラで何話でも続きを作れる.
Evidence: クレジット・料金（7件・4出典）＋細かく直せない（3件・3出典）。どちらも記事中心で、利用者の口コミはほぼ無い
```

元のアプリの名前は、自分のアプリの名前・広告・説明に出さないこと。比較ページを作るなら、日本の法律（不正競争防止法・景品表示法）を弁護士に確認すること。
