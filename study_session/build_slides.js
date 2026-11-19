const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("/root/.claude/skills/synced/4c2b9332-9a55-4edb-8e07-db9531131cc1_2ee5d1b5-8835-4bee-a270-317af0634841/pptx/scripts/apply_theme.js");

const OUT = process.argv[2] || "deck.pptx";
const FONT = "Yu Gothic";

const THEME = {
  name: "ETERNAL AI Study",
  headFontFace: FONT,
  bodyFontFace: FONT,
  colors: {
    dk1: "1F1B2E", lt1: "FFFFFF", dk2: "241A4F", lt2: "F1EEFA",
    accent1: "FF5C7A", accent2: "13A58F", accent3: "F2A516", accent4: "6C5CE7",
    accent5: "77738C", accent6: "3D3560", hlink: "6C5CE7", folHlink: "77738C",
  },
};
const HEX = THEME.colors;

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = "はじめてのAI勉強会 ChatGPT・Codex";
  pres.author = "ETERNAL d.c.t";
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  const C = pres.SchemeColor;
  const W = 13.333;

  const footer = { text: { text: "ETERNAL d.c.t ｜ はじめてのAI勉強会", options: { x: 0.6, y: 6.95, w: 6, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } };

  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: HEX.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", align: "left", x: 0.8, y: 2.1, w: 11.7, h: 1.4, fontSize: 48, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", align: "left", x: 0.8, y: 3.6, w: 11.7, h: 0.8, fontSize: 24, color: C.background2, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "SECTION_DARK",
    background: { color: HEX.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", align: "left", x: 3.2, y: 2.75, w: 9.3, h: 1.2, fontSize: 40, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", align: "left", x: 3.2, y: 3.95, w: 9.3, h: 0.8, fontSize: 20, color: C.background2, valign: "top", margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 12.3, y: 6.95, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: HEX.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", align: "left", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 34, bold: true, color: C.text2, valign: "middle", margin: 0 }, text: "" } },
      footer,
    ],
    slideNumber: { x: 12.3, y: 6.95, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
  });

  const shadow = () => ({ type: "outer", color: "3D3560", opacity: 0.12, blur: 8, offset: 2, angle: 90 });
  const card = (s, name, x, y, w, h, fill = C.background2, withShadow = false) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: name, x, y, w, h, rectRadius: 0.15, fill: { color: fill }, line: { type: "none" }, ...(withShadow ? { shadow: shadow() } : {}) });
  const circleIcon = async (s, name, Comp, x, y, d, fill, iconColor = "FFFFFF") => {
    s.addShape(pres.shapes.OVAL, { objectName: name + " circle", x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" } });
    const pad = d * 0.25;
    s.addImage({ data: await icon(Comp, iconColor), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name });
  };
  const text = (s, name, t, o) => s.addText(t, { objectName: name, isTextBox: true, fontSize: 16, color: C.text1, margin: 0, valign: "top", ...o });
  const content = (title, section) => { const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section }); s.addText(title, { placeholder: "title" }); return s; };
  const sectionSlide = async (num, title, sub, section, Comp) => {
    const s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: section });
    s.addShape(pres.shapes.OVAL, { objectName: "section number circle", x: 0.8, y: 2.55, w: 1.9, h: 1.9, fill: { color: C.accent1 }, line: { type: "none" } });
    text(s, "section number", num, { x: 0.8, y: 2.55, w: 1.9, h: 1.9, fontSize: 48, bold: true, color: C.background1, align: "center", valign: "middle" });
    s.addText(title, { placeholder: "title" });
    s.addText(sub, { placeholder: "body" });
    return s;
  };

  // ===== 1. Title =====
  pres.addSection({ title: "はじめに" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "はじめに" });
  s.addText("はじめてのAI勉強会", { placeholder: "title" });
  s.addText("ChatGPT と Codex を、今日から自分の味方に", { placeholder: "body" });
  await circleIcon(s, "AI icon", fa.FaRobot, 10.9, 0.7, 1.5, C.accent1);
  text(s, "organizer", "ETERNAL d.c.t", { x: 0.8, y: 5.9, w: 6, h: 0.5, fontSize: 18, bold: true, color: C.accent3 });
  s.addNotes("【0〜3分】あいさつと自己紹介。今日は90分、半分以上は手を動かす時間だと伝える。PCとChatGPTのログインができているか、チャットで「OK」と書いてもらう。（サポート担当：出席を記録）");

  // ===== 2. Goals =====
  s = content("今日のゴール", "はじめに");
  const goals = [
    [fa.FaComments, "ChatGPTに上手に頼める", "「聞き方の型」を覚えて、ほしい答えを引き出す", C.accent4],
    [fa.FaMagic, "自分の作業を1つAIに任せる", "家事・歌や配信・仕事、どれでもOK", C.accent1],
    [fa.FaTools, "Codexで道具ができるのを体験", "プログラミングの知識はいりません", C.accent2],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, `goal card ${i + 1}`, x, 1.75, 3.8, 4.6, C.background2);
    await circleIcon(s, `goal icon ${i + 1}`, goals[i][0], x + 0.4, 2.15, 1.2, goals[i][3]);
    text(s, `goal number ${i + 1}`, `0${i + 1}`, { x: x + 2.5, y: 2.2, w: 1.0, h: 0.6, fontSize: 28, bold: true, color: goals[i][3], align: "right" });
    text(s, `goal title ${i + 1}`, goals[i][1], { x: x + 0.4, y: 3.65, w: 3.0, h: 1.1, fontSize: 22, bold: true, color: C.text2 });
    text(s, `goal desc ${i + 1}`, goals[i][2], { x: x + 0.4, y: 4.85, w: 3.0, h: 1.2, fontSize: 16, color: C.text1 });
  }
  s.addNotes("【3〜5分】3つのゴールを読み上げる。終わるころには、全員が1つは自分の作業をAIに任せられている状態を目指すと伝える。");

  // ===== 3. Agenda =====
  s = content("今日の流れ（90分）", "はじめに");
  const agenda = [
    ["0分", "はじめに", "代表の使い方を見る"],
    ["10分", "つきあい方", "得意・苦手と約束"],
    ["20分", "ハンズオン①", "聞き方の型"],
    ["45分", "ハンズオン②", "自分の作業を任せる"],
    ["65分", "Codex体験", "道具を作ってみる"],
    ["80分", "まとめ", "次の一歩"],
  ];
  const ax0 = 1.2, aStep = 2.1, ay = 3.1;
  s.addShape(pres.shapes.LINE, { objectName: "timeline line", x: ax0 + 0.35, y: ay + 0.35, w: aStep * 5, h: 0, line: { color: C.background2, width: 4 } });
  agenda.forEach(([t, h, d], i) => {
    const x = ax0 + i * aStep;
    const hands = i === 2 || i === 3 || i === 4;
    s.addShape(pres.shapes.OVAL, { objectName: `timeline dot ${i + 1}`, x, y: ay, w: 0.7, h: 0.7, fill: { color: hands ? C.accent1 : C.text2 }, line: { color: C.background1, width: 3 } });
    text(s, `timeline time ${i + 1}`, t, { x: x - 0.65, y: ay - 0.75, w: 2.0, h: 0.45, fontSize: 18, bold: true, color: C.accent5, align: "center" });
    text(s, `timeline head ${i + 1}`, h, { x: x - 0.65, y: ay + 0.95, w: 2.0, h: 0.5, fontSize: 18, bold: true, color: C.text2, align: "center" });
    text(s, `timeline desc ${i + 1}`, d, { x: x - 0.65, y: ay + 1.5, w: 2.0, h: 0.9, fontSize: 14, color: C.text1, align: "center" });
  });
  s.addShape(pres.shapes.OVAL, { objectName: "legend dot", x: 0.9, y: 6.1, w: 0.25, h: 0.25, fill: { color: C.accent1 }, line: { type: "none" } });
  text(s, "legend", "＝ 手を動かす時間", { x: 1.25, y: 6.05, w: 4, h: 0.35, fontSize: 14, color: C.accent5, valign: "middle" });
  s.addNotes("【5〜7分】流れを説明。ピンクの3つが手を動かす時間。質問はいつでもチャットにどうぞと伝える。");

  // ===== 4. Demo =====
  s = content("わたしは、こんなふうに使っています", "はじめに");
  const demos = [
    [fa.FaPenNib, "SNSの投稿文", "下書きをAIに出してもらい、自分の言葉に直して投稿"],
    [fa.FaVideo, "リールの台本", "テーマを伝えて構成とセリフの案をもらい、話しやすく整える"],
    [fa.FaClipboardList, "仕事の管理ツール", "AIと一緒に、予約や応募の管理画面を作った"],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 1.7 + i * 1.65;
    card(s, `demo card ${i + 1}`, 0.6, y, 12.1, 1.4, C.background2);
    await circleIcon(s, `demo icon ${i + 1}`, demos[i][0], 0.95, y + 0.25, 0.9, C.text2);
    text(s, `demo title ${i + 1}`, demos[i][1], { x: 2.2, y: y + 0.2, w: 3.6, h: 1.0, fontSize: 22, bold: true, color: C.text2, valign: "middle" });
    text(s, `demo desc ${i + 1}`, demos[i][2], { x: 5.9, y: y + 0.2, w: 6.5, h: 1.0, fontSize: 16, valign: "middle" });
  }
  s.addNotes("【7〜10分】実際の画面を見せる（投稿文の下書き、台本、管理ツール）。ポイントは「AIに全部任せる」ではなく「下書きを出してもらって自分で仕上げる」こと。");

  // ===== 5. Can / Can't =====
  pres.addSection({ title: "AIとのつきあい方" });
  s = content("AIの得意なこと・苦手なこと", "AIとのつきあい方");
  card(s, "good card", 0.6, 1.7, 5.9, 4.8, C.background2);
  card(s, "bad card", 6.85, 1.7, 5.9, 4.8, C.background2);
  await circleIcon(s, "good icon", fa.FaThumbsUp, 0.95, 2.0, 0.9, C.accent2);
  await circleIcon(s, "bad icon", fa.FaExclamation, 7.2, 2.0, 0.9, C.accent1);
  text(s, "good head", "得意なこと", { x: 2.05, y: 2.0, w: 4, h: 0.9, fontSize: 24, bold: true, color: C.text2, valign: "middle" });
  text(s, "bad head", "苦手なこと", { x: 8.3, y: 2.0, w: 4, h: 0.9, fontSize: 24, bold: true, color: C.text2, valign: "middle" });
  const bl = (arr) => arr.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < arr.length - 1, paraSpaceAfter: 10 } }));
  text(s, "good list", bl(["文章の下書き・言いかえ", "長い文の要約・整理", "アイデアをたくさん出す", "手順やプログラムを書く"]), { x: 1.0, y: 3.2, w: 5.2, h: 3.0, fontSize: 18 });
  text(s, "bad list", bl(["最新の出来事や正確な数字（まちがえることがある）", "あなたの事情（伝えないとわからない）", "最後に決めること（決めるのはあなた）"]), { x: 7.25, y: 3.2, w: 5.2, h: 3.0, fontSize: 18 });
  s.addNotes("【10〜15分】AIは「物知りで仕事が速い新人さん」。事情を伝えるほど良い答えが返ってくるが、まちがえることもあるので最後は自分で確認する、と説明。");

  // ===== 6. Rules =====
  s = content("使うときの3つの約束", "AIとのつきあい方");
  const rules = [
    [fa.FaUserShield, "個人情報は入れない", "住所・電話番号・他の人の名前など"],
    [fa.FaLock, "秘密は入れない", "会社の秘密、パスワード、お客さんの情報"],
    [fa.FaSearch, "答えは確認してから使う", "数字や事実は、自分で調べてから使う"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    await circleIcon(s, `rule icon ${i + 1}`, rules[i][0], x + 1.15, 1.9, 1.5, C.accent1);
    text(s, `rule title ${i + 1}`, rules[i][1], { x, y: 3.7, w: 3.8, h: 0.7, fontSize: 24, bold: true, color: C.text2, align: "center" });
    text(s, `rule desc ${i + 1}`, rules[i][2], { x: x + 0.3, y: 4.5, w: 3.2, h: 1.2, fontSize: 16, align: "center" });
  }
  s.addNotes("【15〜20分】この3つだけは必ず守る。このあとのハンズオンでも、実名や住所は入れずに「Aさん」などに置きかえてもらう。");

  // ===== 7. Section 01 =====
  pres.addSection({ title: "ハンズオン①" });
  s = await sectionSlide("01", "ハンズオン①　聞き方の型", "20分〜45分｜4つの要素で頼むと、答えが変わる", "ハンズオン①");
  s.addNotes("ここから手を動かす時間。ChatGPTの画面を開いてもらう。");

  // ===== 8. Four parts =====
  s = content("聞き方の型は、この4つ", "ハンズオン①");
  const parts = [
    ["役割", "AIに何者になってほしいか", "あなたは歌配信者のSNS担当です", C.accent4],
    ["目的", "何のためにやりたいか", "明日の歌枠に来てほしい", C.accent1],
    ["条件", "守ってほしいこと", "100文字以内・絵文字は2つまで", C.accent2],
    ["出力形式", "どんな形でほしいか", "3パターンを箇条書きで", C.accent3],
  ];
  parts.forEach(([h, d, ex, col], i) => {
    const x = 0.6 + i * 3.08;
    card(s, `part card ${i + 1}`, x, 1.7, 2.85, 4.9, C.background2);
    s.addShape(pres.shapes.OVAL, { objectName: `part number circle ${i + 1}`, x: x + 0.3, y: 2.0, w: 0.8, h: 0.8, fill: { color: col }, line: { type: "none" } });
    text(s, `part number ${i + 1}`, String(i + 1), { x: x + 0.3, y: 2.0, w: 0.8, h: 0.8, fontSize: 24, bold: true, color: C.background1, align: "center", valign: "middle" });
    text(s, `part head ${i + 1}`, h, { x: x + 0.3, y: 3.0, w: 2.3, h: 0.6, fontSize: 26, bold: true, color: C.text2 });
    text(s, `part desc ${i + 1}`, d, { x: x + 0.3, y: 3.65, w: 2.3, h: 0.9, fontSize: 16 });
    text(s, `part example label ${i + 1}`, "例", { x: x + 0.3, y: 4.65, w: 2.3, h: 0.35, fontSize: 12, bold: true, color: C.accent5 });
    text(s, `part example ${i + 1}`, ex, { x: x + 0.3, y: 5.0, w: 2.3, h: 1.4, fontSize: 15, color: C.text2, italic: true });
  });
  s.addNotes("【20〜27分】4つを1つずつ説明。全部そろわなくてもいい、2つ入れるだけでも答えが変わると伝える。");

  // ===== 9. Before / After =====
  s = content("型を使うと、こう変わる", "ハンズオン①");
  card(s, "before card", 0.6, 1.7, 4.6, 4.8, C.background2);
  card(s, "after card", 6.0, 1.7, 6.7, 4.8, C.background2, true);
  text(s, "before label", "Before", { x: 1.0, y: 2.0, w: 3.8, h: 0.5, fontSize: 18, bold: true, color: C.accent5 });
  text(s, "before prompt", "「配信の告知文を書いて」", { x: 1.0, y: 2.7, w: 3.8, h: 1.2, fontSize: 22, bold: true, color: C.text2 });
  text(s, "before result", "→ だれにでも当てはまる、ふつうの文が出てくる", { x: 1.0, y: 4.4, w: 3.8, h: 1.5, fontSize: 16, color: C.accent5 });
  await circleIcon(s, "arrow", fa.FaArrowRight, 5.27, 3.75, 0.66, C.accent1);
  text(s, "after label", "After", { x: 6.4, y: 2.0, w: 3, h: 0.5, fontSize: 18, bold: true, color: C.accent1 });
  text(s, "after prompt", [
    { text: "【役割】", options: { bold: true, color: C.accent4 } }, { text: "あなたは歌配信者のSNS担当です。", options: { breakLine: true } },
    { text: "【目的】", options: { bold: true, color: C.accent1 } }, { text: "明日21時からの歌枠に来てほしいので、告知文を作ってください。", options: { breakLine: true } },
    { text: "【条件】", options: { bold: true, color: C.accent2 } }, { text: "100文字以内、親しみやすい口調、絵文字は2つまで。", options: { breakLine: true } },
    { text: "【出力形式】", options: { bold: true, color: C.accent3 } }, { text: "3パターンを箇条書きで出してください。" },
  ], { x: 6.4, y: 2.6, w: 5.9, h: 3.6, fontSize: 17, paraSpaceAfter: 8 });
  s.addNotes("【27〜30分】実際に両方をChatGPTに入れて、結果の違いを画面で見せる。");

  // ===== 10. Hands-on 1 =====
  s = content("やってみよう：題材を1つ選んで、型で頼む", "ハンズオン①");
  const topics = [
    [fa.FaHome, "家事", ["今週の献立を考える", "LINEの返信を考える"], C.accent2],
    [fa.FaMusic, "歌・配信", ["練習メニューを作る", "配信の告知文を作る"], C.accent1],
    [fa.FaBriefcase, "仕事", ["メールの文面を作る", "会議メモを要約する"], C.accent4],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, `topic card ${i + 1}`, x, 1.7, 3.8, 3.9, C.background2);
    await circleIcon(s, `topic icon ${i + 1}`, topics[i][0], x + 0.4, 2.0, 1.0, topics[i][3]);
    text(s, `topic head ${i + 1}`, topics[i][1], { x: x + 1.6, y: 2.0, w: 2.0, h: 1.0, fontSize: 26, bold: true, color: C.text2, valign: "middle" });
    text(s, `topic list ${i + 1}`, bl(topics[i][2]), { x: x + 0.45, y: 3.35, w: 3.1, h: 1.9, fontSize: 18 });
  }
  card(s, "done note", 0.6, 5.85, 12.1, 0.8, C.text2);
  text(s, "done text", "できたら、チャットに「できた」と書いてください（選んだ題材も一緒に）", { x: 0.9, y: 5.85, w: 11.5, h: 0.8, fontSize: 18, bold: true, color: C.background1, valign: "middle" });
  s.addNotes("【30〜45分】15分ほど作業。サポート担当は、だれがどの題材を選んだかを記録する（あとで案内を分けるため）。困っている人には個別に声をかける。最後に2〜3人に結果を共有してもらう。");

  // ===== 11. Section 02 =====
  pres.addSection({ title: "ハンズオン②" });
  s = await sectionSlide("02", "ハンズオン②　自分の作業を任せる", "45分〜65分｜いつもの作業を、1つAIに渡してみる", "ハンズオン②");
  s.addNotes("休憩が必要なら、ここで3分とる。");

  // ===== 12. 3 steps =====
  s = content("3ステップで、作業を1つ任せる", "ハンズオン②");
  const steps = [
    [fa.FaListUl, "書き出す", "毎日・毎週くり返している作業を1つ思い出す"],
    [fa.FaKeyboard, "型で頼む", "役割・目的・条件・出力形式で頼む"],
    [fa.FaPaperPlane, "提出する", "結果をフォームで送る（うまくいかなくてもOK）"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, `step card ${i + 1}`, x, 1.7, 3.8, 3.3, C.background2);
    await circleIcon(s, `step icon ${i + 1}`, steps[i][0], x + 0.4, 2.0, 1.0, C.accent1);
    text(s, `step number ${i + 1}`, `STEP ${i + 1}`, { x: x + 1.6, y: 2.0, w: 2.0, h: 0.45, fontSize: 14, bold: true, color: C.accent5 });
    text(s, `step head ${i + 1}`, steps[i][1], { x: x + 1.6, y: 2.4, w: 2.0, h: 0.6, fontSize: 26, bold: true, color: C.text2 });
    text(s, `step desc ${i + 1}`, steps[i][2], { x: x + 0.4, y: 3.3, w: 3.0, h: 1.5, fontSize: 17 });
  }
  card(s, "tip card", 0.6, 5.3, 12.1, 1.3, C.background2);
  await circleIcon(s, "tip icon", fa.FaLightbulb, 0.9, 5.5, 0.9, C.accent3);
  text(s, "tip text", [
    { text: "うまくいかないときは、続けて頼み直せばOK", options: { bold: true, color: C.text2, breakLine: true } },
    { text: "「もっと短く」「主婦向けに」「表にして」など、一言足すだけで変わります" },
  ], { x: 2.1, y: 5.45, w: 10.3, h: 1.0, fontSize: 17, valign: "middle" });
  s.addNotes("【45〜65分】作業は15分。提出フォームのURLをチャットに貼る。提出内容（どんな作業を任せたか）を記録する。仕事の作業を出してくれた人は、最後の個別相談の案内を個別にする候補。");

  // ===== 13. Section 03 =====
  pres.addSection({ title: "Codex体験" });
  s = await sectionSlide("03", "Codex体験", "65分〜80分｜話しかけるだけで、道具ができる", "Codex体験");
  s.addNotes("ここは見るだけでもOK。操作したい人は一緒に。");

  // ===== 14. What is Codex =====
  s = content("Codexってなに？", "Codex体験");
  text(s, "codex lead", "ChatGPTに入っている、「道具を作ってくれるAI」です", { x: 0.6, y: 1.6, w: 12.1, h: 0.7, fontSize: 22, bold: true, color: C.accent1 });
  const flow = [
    [fa.FaComments, "話しかける", "やりたいことを日本語で伝える"],
    [fa.FaCode, "Codexが作る", "中身のプログラムをAIが書く"],
    [fa.FaCheckCircle, "道具ができる", "そのまま使える。直したい所も言葉で伝える"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.3;
    card(s, `flow card ${i + 1}`, x, 2.6, 3.6, 3.2, C.background2);
    await circleIcon(s, `flow icon ${i + 1}`, flow[i][0], x + 1.2, 2.9, 1.2, C.text2);
    text(s, `flow head ${i + 1}`, flow[i][1], { x: x + 0.2, y: 4.25, w: 3.2, h: 0.6, fontSize: 22, bold: true, color: C.text2, align: "center" });
    text(s, `flow desc ${i + 1}`, flow[i][2], { x: x + 0.3, y: 4.85, w: 3.0, h: 0.9, fontSize: 15, align: "center" });
    if (i < 2) await circleIcon(s, `flow arrow ${i + 1}`, fa.FaArrowRight, x + 3.72, 3.88, 0.46, C.accent1);
  }
  text(s, "codex note", "※ ChatGPTのプランに含まれています。使える回数はプランによって違います", { x: 0.6, y: 6.15, w: 12.1, h: 0.4, fontSize: 12, color: C.accent5 });
  s.addNotes("【65〜68分】プログラミングの知識はいらないことを強調。開催前に、無料プランでどこまで使えるかを公式ページで確認しておくこと。");

  // ===== 15. Demo =====
  s = content("デモ：歌の練習記録表を作ってもらう", "Codex体験");
  card(s, "prompt card", 0.6, 1.7, 6.6, 4.9, C.text2);
  text(s, "prompt label", "Codexへの頼み方（例）", { x: 1.0, y: 2.0, w: 5.8, h: 0.5, fontSize: 16, bold: true, color: C.accent3 });
  text(s, "prompt body", "「歌の練習記録表を作ってください。日付・練習した曲・時間・ひとことメモを入れられて、1週間の合計時間が見られるようにしてください。」", { x: 1.0, y: 2.7, w: 5.8, h: 3.5, fontSize: 20, color: C.background1 });
  text(s, "points head", "見てほしいポイント", { x: 7.7, y: 1.8, w: 5, h: 0.6, fontSize: 22, bold: true, color: C.text2 });
  const pts = [
    [fa.FaComments, "日本語で頼むだけ"],
    [fa.FaRedo, "直したい所も、言葉で伝えて直せる"],
    [fa.FaGift, "できた道具は、自分のものとして使える"],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 2.65 + i * 1.15;
    await circleIcon(s, `point icon ${i + 1}`, pts[i][0], 7.7, y, 0.8, C.accent2);
    text(s, `point text ${i + 1}`, pts[i][1], { x: 8.75, y, w: 4.0, h: 0.8, fontSize: 18, valign: "middle" });
  }
  text(s, "try note", "操作してみたい人は一緒に。見るだけでもOKです", { x: 7.7, y: 6.1, w: 5.0, h: 0.45, fontSize: 14, color: C.accent5 });
  s.addNotes("【68〜80分】画面共有でデモ。うまく動かないときに備えて、録画した予備の動画を用意しておく。最後に「自分でも何か作ってみたい人は手を挙げて（チャットで）」と聞き、手を挙げた人を記録する。");

  // ===== 16. Summary =====
  pres.addSection({ title: "まとめ" });
  s = content("今日できるようになったこと", "まとめ");
  const done = ["ChatGPTに、聞き方の型で頼める", "自分の作業を1つ、AIに任せられた", "Codexで「話すだけで道具ができる」を見た"];
  for (let i = 0; i < 3; i++) {
    const y = 1.8 + i * 1.2;
    card(s, `done card ${i + 1}`, 0.6, y, 8.0, 1.0, C.background2);
    s.addImage({ data: await icon(fa.FaCheckCircle, HEX.accent2), x: 0.9, y: y + 0.2, w: 0.6, h: 0.6, altText: "check" });
    text(s, `done text ${i + 1}`, done[i], { x: 1.75, y, w: 6.7, h: 1.0, fontSize: 20, bold: true, color: C.text2, valign: "middle" });
  }
  card(s, "habit card", 9.0, 1.8, 3.7, 3.4, C.accent1);
  text(s, "habit head", "続けるコツ", { x: 9.3, y: 2.05, w: 3.1, h: 0.6, fontSize: 20, bold: true, color: C.background1 });
  text(s, "habit body", "1日1回、なにか1つAIに頼んでみる", { x: 9.3, y: 2.8, w: 3.1, h: 2.1, fontSize: 22, bold: true, color: C.background1 });
  s.addNotes("【80〜84分】今日の3つを振り返る。明日から1日1回使ってみることをすすめる。");

  // ===== 17. Next step =====
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "まとめ" });
  text(s, "next title", "次の一歩", { x: 0.8, y: 0.6, w: 11.7, h: 0.9, fontSize: 40, bold: true, color: C.background1 });
  const nexts = [
    [fa.FaBookOpen, "もっと使いこなしたい人", "聞き方テンプレ集・道具の作り方の手順書（note）", "公式LINEでご案内します", C.accent3],
    [fa.FaHandshake, "仕事に取り入れたい人", "個別相談（無料・30分）", "あなたの仕事に合わせて一緒に考えます", C.accent2],
  ];
  for (let i = 0; i < 2; i++) {
    const x = 0.8 + i * 6.0;
    card(s, `next card ${i + 1}`, x, 1.8, 5.7, 3.7, C.background1);
    await circleIcon(s, `next icon ${i + 1}`, nexts[i][0], x + 0.4, 2.1, 1.0, nexts[i][4]);
    text(s, `next head ${i + 1}`, nexts[i][1], { x: x + 1.6, y: 2.1, w: 3.8, h: 1.0, fontSize: 22, bold: true, color: C.text2, valign: "middle" });
    text(s, `next item ${i + 1}`, nexts[i][2], { x: x + 0.4, y: 3.4, w: 4.9, h: 1.0, fontSize: 20, bold: true, color: C.text1 });
    text(s, `next desc ${i + 1}`, nexts[i][3], { x: x + 0.4, y: 4.5, w: 4.9, h: 0.6, fontSize: 16, color: C.accent5 });
  }
  text(s, "survey", "最後に、アンケートへのご協力をお願いします（2分で終わります）", { x: 0.8, y: 5.95, w: 11.7, h: 0.6, fontSize: 20, bold: true, color: C.accent3 });
  s.addNotes("【84〜90分】2つの出口を案内。オプチャ内では有料noteを直接案内せず、公式LINEに誘導する。アンケートのURLを貼り、回答時間をとる。個別相談の候補（仕事の作業を提出した人・経営者・個人事業主）には、あとで公式LINEから個別に案内する。");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
