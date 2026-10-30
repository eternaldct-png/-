/* ============================================================
   所属ライバー＆動画データ
   ------------------------------------------------------------
   このファイルは admin.html（ライバー管理ページ）から書き出せます。
   手で編集してもOK：
   - LIVERS の並び順＝ページの表示順
   - VIDEOS の type は "youtube" か "tiktok"
     id は YouTube→watch?v=の後ろ ／ TikTok→動画IDの数字 または "@ユーザー名"
     thumb（任意）でサムネイル画像を指定可能
   ============================================================ */

const LIVERS = [
  {
    name: "梅ちゃん",
    en: "ume-chan",
    catch: "歌も、おしゃべりも、ときめきも。\nあなたの毎日に、小さな癒しとドキドキをお届けする桃色枠の梅ちゃんです。\nふらっと立ち寄って、心ゆくまで楽しんでいってください♡",
    genres: ["梅汁強酸性","枠主のみピンク可"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/梅ちゃん.jpg",
    color: "#7c5cff",
    links: [{ name: "X", url: "https://x.com/umechan_color" }, { name: "TikTok", url: "https://www.tiktok.com/@umechan.colorsing" }]
  },
  {
    name: "kazuto",
    en: "kazuto",
    catch: "歌ライバーイベント初回FRIDAY MUSIC SHOW本戦出場 初回GimmeTheMic出演MusicOnStageいいね数４位",
    genres: [],
    platforms: ["TikTok","Color Sing"],
    chips: ["フォロワー２７K","日間ライバー獲得","3.9万いいね！獲得"],
    photo: "assets/img/livers/ig_0965ad8060e67435016a30ea84a0d88191a9f8fa7d7f6c17f1.png",
    color: "#ff5f42",
    links: [{ name: "TikTok", url: "https://www.tiktok.com/@kazuto0223" }, { name: "YouTube", url: "https://www.youtube.com/@kazuto.singer" }, { name: "X", url: "https://x.com/NoiPhoneNoMusic" }, { name: "note", url: "https://note.com/eternal_d_c_t" }]
  },
  {
    name: "ゆきんこ",
    en: "yukinko",
    catch: "初めまして❣️ゆきんこ🌈💙です😊\n夢は大きく、鬼リーグ✨低音ハスキーボイスで歌う懐メロを是非聴きにきて下さいね😊\nお待ちしております🙇‍♀️🌈",
    genres: ["懐メロ"],
    platforms: [],
    chips: ["低音ハスキーボイス懐メロ好き","夢は大きく鬼リーグ"],
    photo: "assets/img/livers/line_oa_chat_260710_223022.jpg",
    color: "#00e5ff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=ba780456-2586-491e-8b7c-6614d3cb7ca6" }]
  },
  {
    name: "どらねこ🎺🐈‍⬛",
    en: "doraneko",
    catch: "『お知らせ』　8のつく日はリスナーさんセトリDAY♪\n\n🌙 疲れた夜に　大人の癒し枠\n🎺 トランペット生演奏 ＆ 歌配信\n\n🕰 毎日 20:30〜22:30\n\n⭐️ 推しマ【🎺🐈‍⬛】\n\nジャンル：\n邦楽｜洋楽｜昭和歌謡｜Disney｜ジブリ｜アニソン\n\n──────────\n【活動履歴】\n\nフリーとして開始\n1次審査合格 💮 2025/7/15\n初配信　　　  2025/8/8\n2次審査通過　  2025/8/16\n2025/10/14〜 さむふぁん！所属\n2026/11/1〜　ETERNALd.c.t所属\n\n──────────",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_6257.jpg",
    color: "#8495f5",
    links: []
  },
  {
    name: "⚖️Guilty⛓️",
    en: "Guilty",
    catch: "ギルティですよろしくお願いします😊\n推しマ➞⚖️⛓️※外さない覚悟がある人だけお願いいたします🙇‍♂️\n外した人は二度と付けさせません\nだからこそ\n単推し、推しマを付けることが\nどーゆー事なのか しっかり理解できてる方だけお願いいたします。\n\n🕊🌱🌿\n居心地のいい枠を目指します🍵\n投げて貰えるのは嬉しいけど…\n聴きに来てくれる事\n歌をきちんと聞いてくれる事が1番嬉しい✨️\n\n\n配信時間は\nプロフや名前の横にマメに書くようにします😊\n\n\n♪ .* 推し曲は基本的に歌っていません🙏\n（無理なギフト誘導や圧に繋げたくないので\n歌う時は コソッとみて サラッと歌う🥺）\nそれが一番スマート✨️\n\n♪̊̈‧͙ リクエストは、その日の状態と気持ちが合えばお応えします✨\nお気軽にどーぞ•*¨*•.¸¸\n\n♪̊̈‧͙ 歌唱中はギフトへのリアクションは基本 控えさせていただく場合が多いですが歌い終わってから1つ1つ大切に読み返しいたします🎁\n\n\n☮️〈枠について〉\n私自身は枠の管理人と思っております😊\n枠に遊びに来てくださる皆様こそ\n枠の主役であり\n1番楽しむべき存在\n私の歌やトークをBGM代わりに\n皆様が楽しい時間を過ごせてこそ\n私の枠は存在する意味を持ちます😊\nだからこそ\n枠の皆様が\n不快に思わぬよう\n我慢するような事がないよう\nしっかり管理させて頂きたいと思います😊\n無言入室\n明らかなミュート\n呼び掛けに全く応答がないなど\n誰かが不快に感じる可能性があると判断した場合\n雰囲気を守るために\n対応させていただく場合があります\nご理解の程よろしくお願いいたします🙇‍♀️\n\n歌うことは、私にとって本当に大切で楽しい時間であり。\n聴いてくださる皆様とのやり取りも私にとって\nかけがえのないものです😊\n「来てよかった」と思っていただける歌を届けていけたらと思っています🎶✨\n\n【画録について】\n画録は自由にして頂ければと思います😊\nもし 事前に言っていただければ\nその曲中はギフトや入室の反応などを極力控え\n枠のみんなで\n協力してひとつの動画を作るよーなイメージで\n歌わせて頂けたらと思っております🙇‍♀️\n\n\n- ̗̀⚠︎ ̖́-ライバーさんのフォローは行き来の無い方は\n定期的に整理させて頂いております🙏",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_6173.jpg",
    color: "#ff42ff",
    links: []
  },
  {
    name: "ラテ.latte",
    en: "latte",
    catch: "来てくれた方に少しでも楽しんでもらえたら嬉しい。つい笑顔になっちゃう配信を目指しています。\nラテはこんな人→クレイアーティストいつも明るい元気系、お淑やかさは…多分たまにある？",
    genres: [],
    platforms: ["Color Sing","Tik Tok"],
    chips: [],
    photo: "assets/img/livers/ラテ.png",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/1YfuCJTL8S7zgPtu6" }]
  },
  {
    name: "しー",
    en: "shi",
    catch: "はんなりやわらかな京都弁でお出迎え。 昭和歌謡を中心に色んな曲に挑戦しています。 自分の家のようにくつろげるあったかい枠を目指して配信中！ 歌によって変わる声色も楽しんでくださいね。",
    genres: ["昭和歌謡"],
    platforms: ["Smule","Color Sing"],
    chips: ["フォロワー1K"],
    photo: "assets/img/livers/しー.png",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/ik7zUsuZvfHgYdsd9" }]
  },
  {
    name: "keikei",
    en: "KEIKEI",
    catch: "はじめまして、keikeiです。 配信はゲリラ〜的にでご迷惑おかけします。 昼からが多いですが、夕方早朝の場合もよろしくお願いします。",
    genres: ["民謡"],
    platforms: [],
    chips: ["民謡でバタバタ。介護でバタバタ"],
    photo: "assets/img/livers/keikei.jpg",
    color: "#c86bff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=96aaae9f-b1d8-424b-b48e-46121e547c3a" }]
  },
  {
    name: "いちか!!",
    en: "ichika",
    catch: "いちか!!と申します！ 歌うことが好きで始めて見ました！ 色んな曲を歌いたいのでリクエストどんどんください！ 毎日配信頑張ります！",
    genres: [],
    platforms: [],
    chips: ["毎日配信がんばり中","リクエスト大歓迎"],
    photo: "assets/img/livers/liver27.jpeg",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=f6bda131-2b3e-4a0d-80f4-68290b642a7f" }]
  },
  {
    name: "KOUME",
    en: "KOUME",
    catch: "はじめまして✨koumeです✨ これからも笑える枠を基本的に変化球投げていきます❣️ よろしくお願いします。 歌うことが大好きで、男性曲・女性曲問わず、声色も変え、モノマネも混ぜながら楽しく歌います。",
    genres: [],
    platforms: [],
    chips: ["モノマネ×歌の変化球枠","男性曲も女性曲もOK","笑える配信がモットー"],
    photo: "assets/img/livers/KOUME.png",
    color: "#c86bff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=e92f7b41-75b0-488a-919b-ae098c7858f0" }]
  },
  {
    name: "なんでやねん！彩歌",
    en: "saika",
    catch: "なんでやねん！彩歌-ｻｲｶ-です！\n感謝の気持ちを忘れない！！！よろしくお願いします！\n笑いと歌で、少しでも元気になってもらえたら私は皆さんの元気を吸い取っていきます！",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_5700.jpg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=239abe84-f18b-4b7e-985f-51f440ca3f85" }]
  },
  {
    name: "こむたん",
    en: "komutan",
    catch: "初めましてこむたんです！2024年3月21日初配信 夢はオリソンGETする事（権利獲得済）生LIVEをする事 リーグ６６に戻す事！全日本に戻る事！新規リスナーをもっと増やす事！２周年を迎えて色々見えてくるモノがあったので試行錯誤しながら頑張ります！",
    genres: [],
    platforms: [],
    chips: ["オリソン権利獲得済","夢は生LIVE開催","毎日試行錯誤で挑戦中"],
    photo: "assets/img/livers/こむたん.jpg",
    color: "#2dffb4",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/rsKPB8GwqW1n6D9KA" }]
  },
  {
    name: "あまりん",
    en: "amarin",
    catch: "和製カレン・カーペンターを目指しLシンガーとして活躍中",
    genres: [],
    platforms: ["Smule","TikTok","Color Sing"],
    chips: ["フォロワー4.6K","動画投稿継続中","赤パール杯シルバー・敢闘賞"],
    photo: "assets/img/livers/liver07.jpeg",
    color: "#00e5ff",
    links: [{ name: "X", url: "https://x.com/amarinsinger" }, { name: "TikTok", url: "https://www.tiktok.com/@amarinsinger" }, { name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=a52afb82-8835-4745-a816-e8aa48889517" }]
  },
  {
    name: "あけまる",
    en: "akemaru",
    catch: "昭和歌謡が大好きで元ジャニーズのNEWSが好きな住民です！ 毎日１６時から１８時半頃まで配信してます！ お待ちしております！",
    genres: ["昭和歌謡"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/liver26.jpg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=49cb49d1-f7e9-4548-b0e7-9951e4e9a953" }]
  },
  {
    name: "ちぃぽん",
    en: "chiipon",
    catch: "『天城越え』皆様のおかげで敢闘賞を頂きました。ありがとうございます。 ちぃぽんと申します。歌を聴くこと&歌うこと、おしゃべりが好きです！",
    genres: [],
    platforms: [],
    chips: ["『天城越え』敢闘賞受賞","歌もおしゃべりも大好き"],
    photo: "assets/img/livers/liver12.jpg",
    color: "#c86bff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=678d743c-e2d9-4cde-873f-1a7d6f919882" }]
  },
  {
    name: "咲夏",
    en: "sana",
    catch: "仕事前の朝、お昼休みの時間を趣味も兼ねて有効活用できるので毎日楽しんでいます ライバーもリスナーも男女問わず楽しめる枠を目指しています",
    genres: [],
    platforms: ["Color Sing","TikTok"],
    chips: ["マネージャー","フル在宅ワークの傍らスキマ時間で配信中"],
    photo: "assets/img/livers/IMG_5550.jpg",
    color: "#ff4d9d",
    links: [{ name: "note", url: "https://note.com/sanamm0816" }, { name: "TikTok", url: "https://www.tiktok.com/@papayasab816" }, { name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=a5377007-fe8f-4b3d-a887-b26b783f06ec" }]
  },
  {
    name: "かっすー",
    en: "kassu",
    catch: "優里さん大好き🧡 歌うこと大好き🎤 癒し系大人を目指していましたが 素敵なリスナーさんたちのおかげで 笑いが絶えない配信ができています！笑",
    genres: [],
    platforms: [],
    chips: ["優里さんの曲が大好き","笑いの絶えない癒し枠"],
    photo: "assets/img/livers/かっすー.png",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=3298b81b-efe2-43dc-b8b2-ade6727c2485" }]
  },
  {
    name: "momoko",
    en: "MOMOKO",
    catch: "青パール集めたい！！音楽活動の宣伝にパールを使いたいのです。 生歌を聴いてほしい！ 平日7:00〜7:30、夜はまったりトーク多め",
    genres: [],
    platforms: [],
    chips: ["平日朝7:00〜の朝活配信","生歌にこだわり","夜はまったりトーク"],
    photo: "assets/img/livers/liver10.jpeg",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/tZ6Uy8AuzhAGf2826" }]
  },
  {
    name: "マックさん",
    en: "makkusan",
    catch: "親しみやすい関西弁と甘い歌声をお楽しみください 曲やアーティストに関するトークも必聴の価値ありです",
    genres: [],
    platforms: ["Smule","TikTok","Color Sing"],
    chips: ["フォローワー13K","動画投稿中","赤パール杯プラチナ３位"],
    photo: "assets/img/livers/IMG_5482.jpg",
    color: "#00e5ff",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/tfNj9ZQkhEeqWdsG9" }]
  },
  {
    name: "スタ",
    en: "suta",
    catch: "初めまして！スタと申します！ 歌う曲は男性曲が多めです！ 誰かの心に、少しでも響く歌をお届けできたらと思います。",
    genres: [],
    platforms: [],
    chips: ["男性曲多め","心に響く歌声をお届け"],
    photo: "assets/img/livers/スタ.png",
    color: "#7c5cff",
    links: [{ name: "X", url: "https://x.com/suta2566" }, { name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=0f034c4b-53e4-4eec-9524-0568015e8164" }, { name: "Yahoo!フリマ", url: "https://paypayfleamarket.yahoo.co.jp/user/p68809035" }]
  },
  {
    name: "Wolf🐺うるふ",
    en: "WOLF",
    catch: "アイドル・アニソン・平成〜最新曲まで幅広く歌います リクエスト募集中！ぜひコメントで応援してください",
    genres: ["アニソン"],
    platforms: ["Color Sing"],
    chips: ["褒められると伸びる！低音×高音シンガー"],
    photo: "assets/img/livers/liver09.png",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=9f1258d9-47cd-46cf-8a55-51bc47f768b3" }]
  },
  {
    name: "かぴのすけ♪",
    en: "kapinosuke",
    catch: "初めましてかぴのすけです♪お越しになられた際には”優しく”お出迎えさせて頂きます☺️名前も”〜タン”と呼ばせて頂きます☺️こちらは基本自由枠となっております☺️コイン回収⭕️潜り聞き⭕️ラジオ感覚聞き⭕️出入り自由⭕️※コメントで潜りますとくれる方＝気遣いプロ認定です！",
    genres: [],
    platforms: [],
    chips: ["基本自由枠・出入り自由","ラジオ感覚で聴ける","優しくお出迎え"],
    photo: "assets/img/livers/liver19.jpeg",
    color: "#00e5ff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=65651f94-5087-4573-8386-feeea2f68c58" }]
  },
  {
    name: "なっしーpart2",
    en: "nasshipart2",
    catch: "配信中梨汁飛ばしてますが化粧水だと思ってねっ 真面目かつ臨機応変にしてるけどバカが目立つ から悩んでる。毎日笑って楽しい配信がしたいだけなんです！",
    genres: [],
    platforms: [],
    chips: ["※ベタつく時もあるよぉ"],
    photo: "assets/img/livers/liver17.jpeg",
    color: "#2dffb4",
    links: [{ name: "X", url: "https://x.com/nassy_5367" }]
  },
  {
    name: "aRsa",
    en: "ARSA",
    catch: "aRsa『あしゃ』と読みます。 得意なものはヴィジュアル系・ロック系・昭和歌謡・POPS・ボカロ等。幅広く色々歌うただの歌好き🎵",
    genres: ["昭和歌謡","ボカロ","ロック"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/aRsh.png",
    color: "#2dffb4",
    links: [{ name: "X", url: "https://x.com/arsa24_11y069" }, { name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=4140faf1-142d-49d3-adf0-611062455aca" }]
  },
  {
    name: "Sugar",
    en: "SUGAR",
    catch: "聴いてくれる方に何か届けられると思います。 ボイトレ相談も対応できますのでお悩みも解決ベースでお話しします。 関わってくれた方々応援してくれた皆様感謝です。",
    genres: [],
    platforms: [],
    chips: ["ボイトレ相談OK","お悩み解決ベースのトーク"],
    photo: "assets/img/livers/シュガー.png",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=7338c0c6-2946-49a8-a963-dee557f1d6fc" }]
  },
  {
    name: "Yugo",
    en: "Yugo",
    catch: "昭和歌謡中心に、のんびり楽しく歌っていきます。\n懐かしい曲からちょっと意外な曲まで。\n歌いたい曲・リクエストも大歓迎！初見さんも大歓迎です。一緒に楽しい時間を過ごしましょう！",
    genres: ["昭和歌謡"],
    platforms: ["colorsing"],
    chips: [],
    photo: "assets/img/livers/IMG_5899.jpg",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=593d8be7-e98f-4da5-9a7e-cdd5208deada" }]
  },
  {
    name: "YUMIKO",
    en: "yumiko",
    catch: "ボーカリスト＆フルーティストのYUMIKOです。\n主にジャズでライブ活動をしています🎶\n\n歌えない曲も｢無茶ぶりリクエストタイム～🎤｣と言いながら頑張って歌いますw\n100%無理だと思ったら断念することもあり💦\nガイドしか追えない時はお経か、にゃーにゃー🐱になりますꉂ🤣w‪𐤔\n\nペンライト(青、黄色、ピンク、緑)フルコンボが出るとフルートを少しだけ吹いて感謝を伝えてます🎶🪈\n\nリスナーさんたちとワイワイ楽しく歌ったりフルート吹いたりしてます😆🎶\n笑いが絶えない枠かも😆\n\nたまーにフルートの時間をやります🪈\n反応できないかも知れません。\nどうかご了承くださいませ🙇‍♀️\n\n2026.02.26二次審査通過ε-(´∀｀*)ホッ\n初見さん大歓迎🔰\nコイン回収OK✨️\n\n来てくれるリスナーさん、ライバーさん\nいつもありがとうございます☺️\nフォロバは100%‼️😊\n誹謗中傷以外は自由です🙆‍♀️\n\n3月8日東京スタイルアワード出場決定💞✨️\nランウェイ歩いてきましたー✨️\n美意識上がりました✨️😆",
    genres: [],
    platforms: ["Color Sing","YouTube"],
    chips: [],
    photo: "assets/img/livers/IMG_6104.jpg",
    color: "#42bdff",
    links: [{ name: "YouTube", url: "youtube.com/@yumikokobari?si=0xzLiTTzlQ0n2_gT" }, { name: "Instagram", url: "x.gd/0IQk7" }]
  },
  {
    name: "なつっぺ",
    en: "natsuppe",
    catch: "童謡からPOPS、 K -pop、アニソン、ディズニー、洋楽、ロック、男性曲、歌謡曲、演歌、JAZZ、浅く広くなんでも歌います！",
    genres: ["アニソン","K-POP","演歌"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/なつっぺ.png",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=fb87ef92-8d98-4d40-a6bd-ef43e856b0d6" }]
  },
  {
    name: "みぃみん",
    en: "miimin",
    catch: "𝓢𝓲𝓵𝓮𝓷𝓽 𝓗𝓲𝓵𝓵(静岡県)は\n世界一小さな公園のある町より\nシンママ奮闘しながら\n歌とトークを🄳🄴🄻🄸🅅🄴🅁🅈ｴｯﾎ(🎤`˘´)🎀🩷ｴｯﾎ\nベースは心地いい低音ボイス\n低音〜高音の声域広め\n歌は浅く広く\n笑いのツボは浅めですꉂ🤣𐤔笑笑\n\n歌詞への感情移入…パないです(⸝⸝⸝ᵒ̴̶̷̥́ ⌑ ᵒ̴̶̷̣̥⸝⸝⸝)\nアレンジたまに入ります( ¯ﾉᵕ¯)＜大目に見てw\nオススメ歌、ぜひ教えてください(´｡•ㅅ•｡)",
    genres: [],
    platforms: [],
    chips: ["のんびりゆったり楽しく","お仕事中","家事中","寝落ち","寝起きetc…","恋愛","仕事","学業","友情等のご相談も","こんなボクで良ければ","いつでもどーぞ(◍ ´꒳ ◍)ᕷ*.°"],
    photo: "assets/img/livers/みいみん.jpg",
    color: "#2dffb4",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=b039f165-648c-4b7c-a0ce-a87474dc1db7" }]
  },
  {
    name: "ぴかぴか暴走マグマもちちゃん",
    en: "pikapika-bousou-magma-mochi-chan",
    catch: "初めまして🥰よろしくお願いします❤️\n昼間、午後配信多めです♡♫\n夜もできる時します⭐︎\n夜はちょっと声小さめです👾\nまだわからないことが多いですが色々教えてくれると嬉しいです☺️\nJ-POP、懐メロ、アニソン、インディーロック、パンク、UK/USロック\n\n嵐 perfume 菅田将暉 スーパービーバー GOGO7188 DISH// チャットモンチー ジュディマリ YUKI YUI チャランポランタン キノコホテル くるり アジカン レディオヘッド グリーンデイ Weezer ストロークス",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_5979.jpg",
    color: "#84f5c2",
    links: []
  },
  {
    name: "Chaco:Re",
    en: "CHACO:RE",
    catch: "チャコが名前です！ 邦楽、洋楽、ボカロ、アニソンなど歌うことがもちろん狂うほど好きですが聴くのも好きです。",
    genres: ["アニソン","ボカロ","洋楽"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/liver14.jpeg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=cb08613b-d6eb-407d-8d98-23b9a2f5a4e4" }]
  },
  {
    name: "ゆじを",
    en: "yujio",
    catch: "モノマネではなく、原曲重視の歌い回しやテクニックを寄せながら歌うスタイル サザンや、桑田さん90年代ヒット曲中心に歌ってます",
    genres: [],
    platforms: ["Smule","YouTube"],
    chips: ["Smuleフォローワー1.8K","YouTube動画投稿中"],
    photo: "assets/img/livers/liver08.jpeg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=55aaa1c8-33c0-4412-b4ea-9639a2428246" }]
  },
  {
    name: "ゆあ",
    en: "yua",
    catch: "ColorSing内で自称ゲラ子♡ 笑顔が絶えないライバーです。 でも歌唱は真面目！トークと歌唱のギャップ萌を楽しみに来てください。",
    genres: [],
    platforms: ["Color Sing"],
    chips: ["笑顔の絶えない枠","真面目歌唱×ゲラトークのギャップ萌え"],
    photo: "assets/img/livers/liver16.jpg",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=a9a18659-d734-4dc0-9c1e-b9c705cca08a" }]
  },
  {
    name: "AZU",
    en: "AZU",
    catch: "どうも！あずです。 コメント職人を目指してコメント欄で活動しておりましたが、ひょんなことから配信者として転生。 そこから始まる愉快痛快ライバーストーリー。 ゼッテェー来てくれよなッッ！！",
    genres: [],
    platforms: [],
    chips: ["元コメント職人","愉快痛快トーク枠"],
    photo: "assets/img/livers/liver21.jpeg",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=3557ebff-51ab-4117-9dc6-6f922894fcae" }]
  },
  {
    name: "とめこ",
    en: "tomeko",
    catch: "顔ありデビューするよ！ 色々な曲を覚えたいからリクエストしにきてくれたら嬉しい♡フォーク、昭和歌謡も好き",
    genres: ["昭和歌謡","フォーク"],
    platforms: [],
    chips: ["配信は楽しいものたくさんの笑顔を届けたい","ピアノ演奏も持ってる楽譜から"],
    photo: "assets/img/livers/liver23.jpeg",
    color: "#2dffb4",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=e6b4e43f-24ab-42c2-87ec-12e46974725d" }]
  },
  {
    name: "bijou",
    en: "BIJOU",
    catch: "「人の背中を押せる存在になりたい」を掲げて活動中",
    genres: ["ジャズ","歌謡曲"],
    platforms: ["Color Sing","TikTok"],
    chips: ["Rock/Blues/JAZZ/歌謡曲","TikTokで活動中"],
    photo: "assets/img/livers/liver25.jpeg",
    color: "#00e5ff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=0b2af8b7-75e8-417b-8809-5eca5eaa47b3" }]
  },
  {
    name: "うみよこ",
    en: "umiyoko",
    catch: "日常の雑務に追われる中大好きな音楽に心癒される日々を送っています。 私の歌のお聞きいただき何か、を感じていただければ幸いです。",
    genres: [],
    platforms: [],
    chips: ["私の名前は洋子"],
    photo: "assets/img/livers/liver30.jpg",
    color: "#c86bff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=09f50b68-84b7-4d5c-9063-fac794a0b6c8" }]
  },
  {
    name: "ココ",
    en: "koko",
    catch: "初めまして✨️沖縄育ちのココです！歌うと低音ボイスの、沖縄特有のまったりとした雰囲気でお話をします♩\nオールジャンルの雑食で色んな歌を歌います！\nまったりとした暖かい枠作りを目指しています✨️",
    genres: [],
    platforms: [],
    chips: ["ツボが浅くよく笑います☺️","歌はオールジャンルで色々な歌を歌います🎶"],
    photo: "assets/img/livers/ココ.png",
    color: "#00e5ff",
    links: [{ name: "X", url: "https://x.com/coco1005s" }]
  },
  {
    name: "すみっと🚬💀",
    en: "sumitto",
    catch: "元V系バンドマンがバンギャ、ギャ男の溜まり場という名の配信してます🤣\nご興味あるならゆっくりしてく？(。-∀-)ﾆﾔﾘ\n\n何を歌ってもV系になります。\n枠は21時くらいからマッタリやってます。\nV系多めなんでV系好き集まれー(˵ ͡° ͜ʖ ͡°˵)\n今なら古参ですw\n推しマ 🚬💀\nR8.4.25 2次審査通過",
    genres: [],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/IMG_6256.jpg",
    color: "#ff7b42",
    links: []
  },
  {
    name: "わんこ",
    en: "wanko",
    catch: "昭和歌謡メイン1970年代〜2010年くらいまでの歌をわかる範囲で歌おうと思っています 少しでも聴いている皆様に癒されますよう頑張りますので、どうか温かい目で応援していただけると嬉しいです！\nYouTube登録者まもなく１０００人！！",
    genres: ["昭和歌謡"],
    platforms: ["ColorSing","YouTube"],
    chips: ["はじめまして、わんこと申します"],
    photo: "assets/img/livers/liver39.jpeg",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=92fba68a-1fad-4500-81eb-dad83ef3bd14" }]
  },
  {
    name: "あじゃる",
    en: "ajaru",
    catch: "あじゃる@鹿児島弁♡平日🎤\n鹿児島より鹿児島弁で配信をお届けします！あじゃると申しますよろしくお願いします(^^)！！\n思ったことは何でもすぐ言っちゃう、降りてきたこともすぐ言っちゃう！しゃべくりがかしましい枠です𐤔𐤔𐤔𐤔\n歌は音高い系のバラード多め、ドラマチックな曲が好き♡昭和平成の懐メロ多めでやっております♫\nコイン回収からぜひぜひお気軽に遊びにいらして下さい⸜(˙꒳˙)⸝",
    genres: ["懐メロ"],
    platforms: [],
    chips: ["昭和〜平成の懐メロが多いです"],
    photo: "assets/img/livers/あじゃる１.png",
    color: "#2dffb4",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=e62de330-3717-4688-8ece-d510fadc1639" }]
  },
  {
    name: "Yun",
    en: "YUN",
    catch: "皆様初めましておはこんにちわ。 歌はクソ真面目？なはず。トークは超絶おバカ丸出し 自由気ままに配信をお届けしています♡",
    genres: [],
    platforms: [],
    chips: ["歌は真面目・トークはおバカ","自由気ままな配信"],
    photo: "assets/img/livers/Yun.png",
    color: "#c86bff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=a85f76b0-6cef-4a3f-ba69-fa094137065d" }]
  },
  {
    name: "ひすみや・ライバー.ド.ライバー",
    en: "hisumiya-raiba-do-raiba",
    catch: "金沢でタクシードライバーやってます。 昭和から平成前期の歌謡曲、ポップス、演歌を中心に歌います。特に安全地帯、CHAGE&ASUKA、中島みゆきさんの楽曲が大好きなおじさんです。",
    genres: ["演歌","歌謡曲"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/liver32.jpeg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=96732bc0-d4f5-4c91-9b59-04b214efa944" }]
  },
  {
    name: "chopper229",
    en: "CHOPPER229",
    catch: "歌には自信がないんです。半音下げのプロと言われています。癖なのか?改善する余地が見られないので、それは個性と言われ受け止めています。私のアピールポイント…何気ない笑、何気ない癒し、ゆったり昼下がりのあなたの FM 的な感じを目指しています。",
    genres: [],
    platforms: [],
    chips: ["自称・半音下げのプロ","昼下がりのFM風配信","何気ない癒しをお届け"],
    photo: "assets/img/livers/チョッパー.jpg",
    color: "#c86bff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=01cf9dfe-d462-4240-891f-fea9da54fad8" }]
  },
  {
    name: "しょーたいちょー",
    en: "shotaicho",
    catch: "ほぼMrs.GreenApple専門店です。 歌うことが好きなので、どんどんリクエスト貰えると嬉しいです！ 全く為になる情報をお届けしない歌メインのラジオみたいな配信をしていこうと思ってます。",
    genres: [],
    platforms: [],
    chips: ["ほぼミセス専門店","ミックスボイスが武器","ラジオ風歌配信"],
    photo: "assets/img/livers/line_oa_chat_260710_223626.JPG",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=9ae33ea2-a4e4-4acb-b365-6006503ca2e1" }]
  },
  {
    name: "ジャン",
    en: "jan",
    catch: "初めまして！ジャンと言います。お気軽にジャンジャン！とかジャンと呼んでください。みんな楽しく！実家感出して行きたいです！歌うことが好きで、唄わないと生活ができません",
    genres: [],
    platforms: [],
    chips: ["実家のような居心地","歌うことが生きがい","ジャンジャン呼んでね"],
    photo: "assets/img/livers/63414FEB-4F66-42BE-BAA0-E28DEAD041A3.png",
    color: "#00e5ff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=855142e2-590c-4500-bf4c-11d59ecd029c" }]
  },
  {
    name: "りぱこ",
    en: "ripako",
    catch: "目安・平日12:00～13:00\n「げらりひょんことりぱこです！\n伝説のお寿司レンチン術師！\nたくさん笑った！楽しかった！\nと思ってもらえるような\n枠を心がけています☆\n一緒にゲラゲラポーしましょ！」",
    genres: [],
    platforms: [],
    chips: ["配信できないor短時間の可能性大","基本的に夜・土日祝はお休み"],
    photo: "assets/img/livers/りぱこ.png",
    color: "#2dffb4",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=09c8013d-e15f-48fa-bbff-ca98ac924605" }]
  },
  {
    name: "Aii",
    en: "AII",
    catch: "皆さんこんにちは。 AIiiです。アイちゃんと呼んでくれて嬉しいです。Mrs.GreenApple、King Gnuなどを中心に歌っています。",
    genres: [],
    platforms: [],
    chips: ["ミセス・King Gnu中心","アイちゃんと呼んでね"],
    photo: "assets/img/livers/liver41.jpeg",
    color: "#2dffb4",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=cbadcb09-ed81-4418-8809-cbe4827d169c" }]
  },
  {
    name: "月影朱華",
    en: "tsukikage-shuka",
    catch: "ご機嫌麗しゅう 月影朱華（ツキカゲシュカ）です。 アニソン、ボカロを中心に、アイドルソングや昭和のヒット曲も歌うことができます。",
    genres: ["アニソン","ボカロ"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/liver44.jpeg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=427c16a0-54be-4a08-99e2-38bb2343f58a" }]
  },
  {
    name: "くるみん",
    en: "kurumin",
    catch: "昭和歌謡、懐メロ、アニソンを歌います！ 声真似も得意です！クレヨンしんちゃんの真似といえばココ！リクエストフリー レパートリーの中からリクエストしてね！ 仲良くしてくれたら嬉しいです！",
    genres: ["昭和歌謡","アニソン","懐メロ"],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/liver50.jpg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=236e430f-c597-4bb5-b31f-b92bbf2843f2" }]
  },
  {
    name: "いくら",
    en: "ikura",
    catch: "プロフィール見てくれてありがとう！よくフィリピンママのモノマネしてます！\nフィリピンママのモノマネ聞くならここだーよ！来てくれだと嬉しいだーよ！",
    genres: ["懐メロ","歌謡曲"],
    platforms: ["ClolerSing","TikTok"],
    chips: [],
    photo: "assets/img/livers/IMG_5432.jpg",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=4d1c8795-b489-4411-b5ec-c9029e2384a7" }]
  },
  {
    name: "リナ",
    en: "Rina",
    catch: "１６時以降配信予定！歌推し募集中！\n応援してくれるみんなに感謝感謝！配信に会いにきてくれたら喜び\nみんな待ってるよーん！",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_5702.jpg",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/ZrtpWyBBRAFLXW7G8" }]
  },
  {
    name: "やぶさん",
    en: "yabusan",
    catch: "ColorSingにて優しい歌声はあなたの心にも届くはず",
    genres: [],
    platforms: ["TikTok"],
    chips: ["TikTokフォローワー６.０K","２次審査合格しLシンガーへ"],
    photo: "assets/img/livers/liver38.png",
    color: "#ff4d9d",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/4JrBNb7c5MStZCeN7" }]
  },
  {
    name: "atsuuu",
    en: "ATSUUU",
    catch: "アツと申します。玉置浩二さんを崇拝しています。皆様がのんびり楽しんでくださる枠を目指して頑張ります！歌は気持ちで歌います。",
    genres: [],
    platforms: [],
    chips: ["玉置浩二さんを崇拝","気持ちで歌うスタイル","のんびり楽しめる枠"],
    photo: "assets/img/livers/liver33.jpg",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=1b267cf5-44c9-4e6f-bc07-b961b72cd71d" }]
  },
  {
    name: "沙夜",
    en: "sayo",
    catch: "リスナー様達と交流し楽しい配信を心掛けています 縛りもノルマもないのに手厚いサポート感謝です",
    genres: ["弾き語り"],
    platforms: [],
    chips: ["kotoyukiのボーカル沙夜","弾き語りで気持ちを込めて歌う"],
    photo: "assets/img/livers/liver40.jpeg",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://colorsing.page.link/5JDTbYkLv4f2JXzj6" }]
  },
  {
    name: "瑠琉",
    en: "ruru",
    catch: "ぎゃるる枠にいらっしゃいませ！ るるのあげ〜ぃにハマった？？ ねぇハマったよね？初めましてるると申します 歌うことだーいすき！ハイトーンだーいすき！ 黄色だーいすき！",
    genres: [],
    platforms: [],
    chips: ["ぎゃるる枠","ハイトーンだーいすき","るるのあげ〜ぃにハマってね"],
    photo: "assets/img/livers/liver45.jpeg",
    color: "#7c5cff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=caaeaee5-ad53-4d12-8cbc-48a58f7d97df" }]
  },
  {
    name: "柚華ゆずまる",
    en: "yuzuka-yuzumaru",
    catch: "プロフィール見て下さり\nありがとうございます┏○ﾍﾟｺｯ\n\n💠柚華（ゆずか）と申します💠\n\n気軽にゆずとかゆずまるとか呼んでくれたら嬉しいです✨\n1次審査通りましたヾ(o´∀｀o)ﾉﾜｧｰｨ♪\n予定としては10月からライバーでびぅします✨\n初配信17:00～予定です🎶\n是非応援お願い致します✧*｡٩(ˊωˋ*)و✧*｡\n\n話す声と、歌う声のギャップあります。\n音量気を付けたいと思いますが、歌声大きめですので大きすぎたりしたら教えてください(๑ｰㅅｰ๑)",
    genres: [],
    platforms: ["Color Sing","Smule","YouTube"],
    chips: [],
    photo: "assets/img/livers/IMG_5980.jpg",
    color: "#84f5ea",
    links: []
  },
  {
    name: "丘ちゃん",
    en: "okachan",
    catch: "・基本的に平日19時頃配信しますが、やらない時もあります。\n・土日祝日は基本的におやすみですが、たまにやる事もあります。\n・小さい声で歌うことができない奴なので配信場所がカラオケボックスとなり、時間になったら枠を閉じます🥹\n出席取れない場合は申し訳ございません🙇‍♂️\n\n・三度の飯より歌うことが好きだった。(今は同じくらい)\n・米米CLUBのトリビュートバンドでボーカルを担当してる丘ちゃんですがあまり米米の曲を知らないという🤣こんなわたくしですがよろしく✌️\n・リクエストは大歓迎❣️歌える曲は歌いますが歌えない曲は歌いません🙇‍♂️\n\n👇🏻リアルLIVE情報👇🏻\n✨10/11(日)19:00\n堺筋本町CLUBMERCURY\n(BOØWYカバー)\nぞーいVo.にて出演予定\n\n✨11/15(日)14:00\n神戸チキンジョージ\n(米米CLUBカバー)\nSHARI SHARI CLUB\nVO.にて出演予定\n\n✨12/19(土)\n心斎橋FootRock&Beers\nアマチュア界の紅白歌合戦\nVo.にて出場予定\n\n2027年\n\n✨2/28(日)\n心斎橋FootRock&Beers\n(T-BOLANカバー)\nTERU-BOLAN\nVo.にて出演予定",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_6105.jpg",
    color: "#42fff6",
    links: []
  },
  {
    name: "ひでなお",
    en: "hidenao",
    catch: "初めまして❣️\nYouTube公式アーティストやらせてもらってます。\n量子共鳴シンガー\nひでなおです(˶' ᵕ ' ˶)\n気軽に絡んで、歌やお話を楽しみましょう😊",
    genres: [],
    platforms: ["Color Sing","YouTube"],
    chips: [],
    photo: "assets/img/livers/IMG_6102.jpg",
    color: "#84cef5",
    links: [{ name: "YouTube", url: "" }]
  },
  {
    name: "ちゃんゆき！",
    en: "chanyuki!",
    catch: "10/21～お試し配信\n2次審査StaRt🍏\nとりあえず、配信めっちゃ楽しいです\"(∩>ω<∩)\"\n来て下さった方々ありがとうございます♡\n\n事務所の方々、カラーシングの先輩方色々とアドバイスありがとうございます！\n事務所(エターナル)の方々の配信、歌もうまいけど、おもしろい人多すぎて、笑いをありがとうございます\n(*･ω･)*_ _)ﾍﾟｺﾘ\n雑談うまくなれるよう参考にします(笑)\n同期の2次審査の方々も一緒にがんばりましょう♡\n\n平日は17時～19時\n土日祝は13時～15時、17時～19時に配信予定です！\n\n決まったアーティストじゃなくて好きな曲なら色々歌います。\nミセス🍏はむずかしいけど歌える曲増えるように練習頑張ってます。\n歌声は倖田來未に似てると言われます。浜崎あゆみも得意です。\n\n2次審査合格するために心をこめて歌います。\n応援よろしくお願いします♡\n\nあと、初配信で不慣れなため、ギフトやコメントの振り返りが十分にできません。ご了承ください。",
    genres: [],
    platforms: ["Color Sing"],
    chips: [],
    photo: "assets/img/livers/IMG_6107.jpg",
    color: "#427bff",
    links: []
  },
  {
    name: "🍅KOERI🍅",
    en: "koeri",
    catch: "11月1日から、お試し配信🍅\n2次審査11月4日から11月20日までに突破したいので、応援よろしくお願いします\n(*´︶`*)♡\n\n🍅お試し配信は、昼、夕🍅\n🍅2次審査は、朝、昼、夕🍅\n\nゲリラ配信、木金の時間はオープンチャットでお知らせします*´`*\nオプチャは、1Kから、もしくは\nメンシプにて入れます🍅ここから！",
    genres: [],
    platforms: [],
    chips: [],
    photo: "assets/img/livers/IMG_6255.jpg",
    color: "#f584d9",
    links: []
  },
  {
    name: "PAL",
    en: "PAL",
    catch: "歌える楽曲の多さは多数、素敵な歌声を楽しんでね！",
    genres: [],
    platforms: [],
    chips: ["２次審査を難なくクリア"],
    photo: "assets/img/livers/liver49.jpeg",
    color: "#00e5ff",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=a1aa0266-26c7-42db-b00d-6a005d18da73" }]
  },
  {
    name: "AKKI",
    en: "AKKI",
    catch: "ColorSing、Pocochaで活動中 関西でフルート演奏、フルート講師しています いつもの曲を聴いてみたら、また違う素敵に出逢えるかも♡歌も演奏もリクエストしてね！",
    genres: [],
    platforms: ["Color Sing","Pococha"],
    chips: ["フルート演奏＆講師","歌も演奏もリクエストOK"],
    photo: "assets/img/livers/liver46.jpg",
    color: "#ffb648",
    links: [{ name: "ColorSing", url: "https://web.colorsing.com/share/user?user_id=ea321711-0246-4838-b5b6-f890aed9a106" }]
  },
  {
    name: "しばみこ",
    en: "shibamiko",
    catch: "歌は懐メロ、バラード曲がメイン気軽に遊びに来てください",
    genres: ["バラード","懐メロ"],
    platforms: [],
    chips: ["作詞作曲を提供しています"],
    photo: "assets/img/livers/liver48.jpeg",
    color: "#c86bff",
    links: []
  }
];

const VIDEOS = [
  { type: "youtube", id: "DaH4kcJ-svA", title: "【Lシンガー10名で歌う】点描の唄 / Mrs. GREEN APPLE", liver: "kazuto" },
  { type: "youtube", id: "OtVMtPOzbaQ", title: "B'z「消えない虹」歌ってみた", liver: "kazuto" },
  { type: "youtube", id: "hXmE_lE5zag", title: "「70億にただ1つの奇跡」歌ってみた", liver: "kazuto" },
  { type: "youtube", id: "m5pPBdmcPTE", title: "歌ってみたcover", liver: "kazuto" },
  { type: "tiktok", id: "@kazuto0223", title: "kazuto 公式TikTok", liver: "kazuto" }
];
