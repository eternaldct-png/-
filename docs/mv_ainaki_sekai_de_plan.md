# MV制作プラン「愛なき世界で」

- 曲の長さ: 5分23秒 / テンポ: 約68BPM(バラード。1小節 ≒ 3.5秒)※音の波形から推定
- 主演: 添付画像の女性(白いワンピース・お団子ヘア・ブラウンの髪)
- 動画生成: Seedance 2.5(Dreamina)で、1カット4〜8秒を生成 → 編集ソフト(CapCut等)で曲に合わせてつなぐ

---

## 1. コンセプト

**「色のない世界が、"君"を想うたびに色づいていく」**

| 要素 | 演出 |
|---|---|
| 愛を知らない「私」 | 彩度を落とした灰色の世界(曇り空・乾いた砂浜・無人の部屋) |
| 「君」 | **顔を映さない**(逆光のシルエット・手・背中・光の玉)。人物を2人そろえて生成するのは難しく、見る人が自分を重ねやすくなるため |
| 色づく世界 | サビのたびに色が戻る → 最後のサビで、添付画像そのままの青い海と白いワンピースになる |
| 光を知らぬ花 | 暗い場所で咲く白い花(月下美人のイメージ)。2番以降に何度も登場させる |

**色の流れ:** モノクロ → くすんだ色 → 1サビで部分的に色が戻る → 2番で夕暮れ → 2サビで夜の花 → 最後のサビで真昼の海(添付画像の色)

---

## 2. 曲の構成と時間 ※推定

音量の変化から区切りを推定しました。**歌詞が入るタイミングは実際に曲を聴いて直してください。**

| 時間 | パート | 歌詞 |
|---|---|---|
| 0:00–0:14 | イントロ | — |
| 0:14–0:42 | Aメロ1 | 愛を知らないまま〜世界が少しだけ色づいた |
| 0:42–1:10 | Aメロ2 | 名前を呼ぶ声が〜君が私を変えていく |
| 1:10–1:24 | Bメロ | 胸の奥が熱くなる〜息が乱れてしまう |
| 1:24–1:52 | サビ1 | 愛なき世界で〜もう止められない |
| 1:52–2:06 | 間奏 | — |
| 2:06–2:34 | Aメロ3 | 君の笑顔が〜君を失いたくないということ |
| 2:34–2:52 | Aメロ4 | もし世界が愛を持たなくても〜私を君へ導いていく |
| 2:52–3:40 | サビ2 | 愛なき世界で〜名前のない愛のまま |
| 3:40–3:46 | ブレイク | (音が薄くなる) |
| 3:46–4:28 | サビ3 | 愛なき世界で〜心はもう止められない |
| 4:28–5:04 | 最後のサビ | 愛なき世界で〜名前のない愛のまま |
| 5:04–5:23 | アウトロ | — |

---

## 3. 準備:主演の「キャラクターシート」を先に作る

添付画像1枚だけだと、カットごとに顔が変わりやすくなります。動画を作る前に、画像生成(ChatGPT・Dreaminaの画像生成など)で次の4枚を用意し、**全カットで参照画像として毎回指定**してください。

1. 正面のバストアップ(添付画像)
2. 横顔
3. 後ろ姿(お団子ヘアが見えるもの)
4. 全身(白いワンピース)

> 毎回プロンプトの最初に入れる共通の一文:
> `The same woman from the reference images: light-brown hair in a messy top bun with loose face-framing strands, soft brown eyes, white off-shoulder ruffled gauze dress.`

---

## 4. カット表とSeedance用プロンプト(26カット)

- 1カット4〜8秒。Seedanceに入れるプロンプトは英語で、最後に共通の画づくり指定を付けます。
  共通の画づくり指定: `cinematic, 35mm film look, shallow depth of field, soft natural light, 9:16 vertical` (横長で作るなら `16:9`)
- **縦長(9:16)をおすすめします。** TikTok/リールに切り出しやすく、添付画像も縦長のためです。

### イントロ 0:00–0:14

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 1 | 7 | 灰色の海辺。遠くに主人公の背中が小さく見える | `Desaturated, almost monochrome empty beach under overcast sky. Wide shot, the woman stands far away with her back to camera, wind moving her dress. Slow push-in. Melancholic, quiet.` |
| 2 | 7 | 乾いた砂に指で何かを書きかけて、やめる手元 | `Close-up of her fingertip drawing in dry grey sand, then stopping and pulling away. Muted colors, shallow depth of field.` |

### Aメロ1 0:14–0:42「愛を知らないまま〜」

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 3 | 7 | 無表情で窓辺に座る主人公(灰色の部屋) | `The woman sits by a window in a grey minimalist room, expressionless, looking outside. Desaturated tones, dust in the light. Static camera, subtle breathing.` |
| 4 | 7 | ひび割れたコップの水が乾いていく(心の比喩) | `Macro shot of a glass of water on a windowsill, the water slowly evaporating, cracks of dry light. Monochrome, time-lapse feel.` |
| 5 | 7 | 「君を見つけた」: 遠くに逆光のシルエットが現れる | `The woman on the grey beach turns her head; far away a backlit silhouette of a person appears, face not visible, glowing rim light. Slow rack focus from her to the silhouette.` |
| 6 | 7 | 「色づいた」: 彼女の頬と唇にだけ色が戻る | `Close-up of the woman's face in monochrome; color slowly blooms only on her cheeks and lips, pink warmth spreading. She blinks, surprised. Slow push-in.` |

### Aメロ2 0:42–1:10「名前を呼ぶ声が〜」

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 7 | 7 | 何かを言いかけて口をつぐむ | `Medium close-up, the woman parts her lips as if to call someone's name, then hesitates and looks down. Muted colors with a faint warm tint.` |
| 8 | 7 | ガラス越しに「君」の手と、彼女の手が重なりかける | `Two hands on opposite sides of a glass pane, almost touching, not quite. Backlit, soft bokeh. Her hand trembles slightly.` |
| 9 | 7 | 鏡の中で、髪をほどく・結ぶ | `The woman looks at herself in a mirror, ties her hair into a messy bun, her expression softening for the first time. Colors slightly warmer.` |
| 10 | 7 | 「変えていく」: 足元の灰色の砂に色が戻る | `Low angle, her bare feet step onto grey sand; with each step the sand turns warm beige and the sea behind turns faintly blue. Tracking shot.` |

### Bメロ 1:10–1:24「胸の奥が熱くなる〜」

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 11 | 7 | 胸に手を当て、息が浅くなる | `Close-up, the woman presses her hand to her chest, breathing faster, eyes glistening. Handheld camera, slight shake, warm light creeping in.` |
| 12 | 7 | 走り出す背中(浜辺) | `She suddenly runs along the shoreline away from camera, dress and loose hair flowing. Tracking shot from behind, colors intensifying.` |

### サビ1 1:24–1:52「愛なき世界で 君を想う〜」

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 13 | 7 | 海が一気に青くなる(1回目の色の爆発) | `Wide shot, the woman stops at the waterline; the whole grey ocean bursts into vivid turquoise from her feet outward. Sunlight breaks through clouds. Slow orbit camera.` |
| 14 | 7 | カメラを見つめて歌う(リップシンク風) | `Close-up, the woman looks into the camera and sings softly with emotion, wind in her hair, sparkling sea bokeh behind her.` |
| 15 | 7 | 光の粒が「君」の方へ伸びていく | `Particles of light rise from her open palm and drift toward a distant backlit silhouette across the water. Dreamy, slow motion.` |
| 16 | 7 | 「止められない」: 振り返って手を伸ばす | `The woman turns and reaches her hand toward the camera, longing expression, lens flare. Slow push-in, emotional peak.` |

### 間奏 1:52–2:06

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 17 | 7 | 夕暮れの海。色が少しくすむ(2番へ) | `Golden-hour beach, colors fading to a soft dusty orange. The woman sits on the sand hugging her knees, watching the sun set. Static wide shot.` |

### Aメロ3・4 2:06–2:52「君の笑顔が〜」「もし世界が〜」

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 18 | 7 | 「君」が笑う気配(口元だけ・逆光) | `Extreme close-up of a backlit person's smiling lips, face mostly in shadow, warm sunset rim light. Then cut focus to the woman watching, eyes tearing up.` |
| 19 | 7 | 涙が一筋、理由がわからない表情 | `Close-up, a single tear rolls down the woman's cheek; she touches it, confused, then smiles faintly. Sunset light.` |
| 20 | 7 | 夜、暗い路地で一輪だけ咲く白い花 | `Night, a single white flower blooming in a dark alley crack where no light reaches, petals glowing faintly on their own. Macro, slow bloom time-lapse.` |
| 21 | 7 | 「君を選んでしまう」: 暗闇の中、光の方へ歩き出す | `The woman in a dark empty street walks toward a single distant warm light, her white dress the only bright thing in frame. Tracking from behind.` |

### サビ2 2:52–3:40「光を知らぬ花のように〜」

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 22 | 8 | 夜の海、彼女の周りに白い花が次々と咲く | `Night beach under moonlight, white flowers bloom one after another in the sand around the woman as she spins slowly. Soft glow, overhead drone shot.` |
| 23 | 8 | 「君を照らす」: 胸元の光が「君」のシルエットを照らす | `A soft light glows from the woman's chest and illuminates a silhouette in front of her; we still don't see their face. Intimate, slow motion.` |

### ブレイク〜サビ3 3:40–4:28

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 24 | 6 | 一瞬だけ、すべてが灰色に戻る(「叶わない恋」) | `Sudden cut: the world drains back to monochrome, the silhouette dissolves into the wind like sand. The woman alone, stunned. Static.` |
| 25 | 8 | それでも笑って、サングラスを外す(添付画像のポーズ) | `Monochrome turns to full vivid color in one breath: bright blue sky, turquoise sea, the woman smiles and lowers her sunglasses, selfie angle, exactly like the reference image.` |

### 最後のサビ〜アウトロ 4:28–5:23

| # | 秒数 | 映像 | プロンプト |
|---|---|---|---|
| 26 | 8 | 真昼の海で、自撮りの角度のまま歌う → カメラが引いて空へ | `Selfie-angle shot of the woman singing joyfully on a sunlit tropical beach, then camera pulls back and rises into the blue sky with clouds. End on a single white flower petal floating in the air.` |

**秒数の配分:** 26カット ≒ 約190秒です。曲は323秒なので、残りは次の方法で埋めます。
- 歌っているカット(#14・#26)を角度・服の揺れを変えて**5〜8本追加で生成**し、サビで使い回す
- 同じカットのスロー再生・ズームで尺を延ばす(編集ソフトでできる)
- 最初は**1サビまでの1分52秒だけ**作って出来を確認するのがおすすめです

---

## 5. 費用の目安 ※料金は前回の調査の数字です

| 撮り直しの回数 | 生成する秒数 | API(720p・1秒0.231ドル) | Dreamina(1秒約26クレジット) |
|---|---|---|---|
| 少なめ(1.5倍) | 約480秒 | 約1.7万円 | 約12,600クレジット(Advancedの約1.5か月分) |
| ふつう(2.5倍) | 約810秒 | 約2.8万円 | 約21,000クレジット(約2.4か月分) |
| 多め(3倍) | 約970秒 | 約3.4万円 | 約25,200クレジット(約2.9か月分) |

→ 1曲まるごと作るなら、**前回調べた定額の無制限プラン(年額)か日数パスの方が安くなる可能性が高い**です。

---

## 6. リスク・確認事項

| 項目 | 内容 | 確信度 |
|---|---|---|
| 写真の人物の権利 | 添付画像がAIで作った人物ならOK。**実在の人(所属ライバーなど)の場合は、本人の書面での許可が必要**です | 高 |
| 実在の顔を参照に使う制限 | Seedanceは、実在の人物に見える顔写真を参照画像にすると生成を断ることがあるという報告があります。最初に1カット試してください | 低〜中(推測) |
| 顔の一貫性 | 26カットすべてで同じ顔に保つのは今のAIでは難しいです。後ろ姿・手元・遠景のカットを多めにして、顔が変わってもわかりにくくしています | 高 |
| 口の動きと歌のズレ | 歌に合わせた口の動きは完全にはそろいません。歌うカットは「口を少し動かす程度」にとどめるのが無難です | 中 |
| 商用利用 | YouTubeでの収益化や、ライバー・受託の作例として使うなら、Dreaminaの商用利用の規約を確認してください。**法務面は専門家への確認をおすすめします** | — |
| 曲の権利 | 自社で制作した曲なら問題ありません。外部の作家が関わっているなら、映像に使う許可を確認してください | — |
