// 会議ノートの E2E テスト（Playwright。偽の Claude / Whisper を使う fake_server.py に対して動かす）
//
//   python3 tools/meeting_notes/e2e/fake_server.py --port 5099 --data /tmp/mn-e2e &
//   NODE_PATH=$(npm root -g) node tools/meeting_notes/e2e/flows.e2e.cjs http://127.0.0.1:5099 [スクショの保存先]
//
// どのテストも、ブラウザのコンソールエラーと 5xx 応答があれば失敗にする。
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2] || "http://127.0.0.1:5099";
const SHOTS = process.argv[3] || "";
const results = [];

function assert(cond, msg) { if (!cond) throw new Error(msg); }

async function shot(page, name) {
  if (!SHOTS) return;
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

async function waitDone(page) {
  // 処理中の表示が消える（＝ノートが出来上がる or 失敗する）まで待つ
  await page.waitForFunction(() => {
    const m = document.getElementById("meeting");
    return m && !["queued", "transcribing", "summarizing"].includes(m.dataset.status);
  }, null, { timeout: 30000 });
}

async function newMeeting(page, { title = "", participants = "", tags = "" } = {}) {
  await page.goto(`${BASE}/new`);
  if (title) await page.getByLabel("タイトル（空ならAIが付けます）").fill(title);
  if (participants) await page.getByLabel("参加者").fill(participants);
  if (tags) await page.getByLabel("タグ").fill(tags);
}

async function fromText(page, text, opts) {
  await newMeeting(page, opts);
  await page.getByRole("tab", { name: "📄 文字起こしを入れる" }).click();
  await page.getByLabel("または貼り付け").fill(text);
  await page.getByRole("button", { name: "取り込んでノートを作る" }).last().click();
  await page.waitForURL(/\/m\/[0-9a-f]{32}/);
  await waitDone(page);
}

const tests = {
  async "F03-H1 文字起こしを貼るとノートとやることができる"(page) {
    await fromText(page, "山田: 会場は渋谷にしましょう\n自分: 見積もりは金曜までに送ります", { tags: "営業" });
    await page.getByRole("heading", { name: "会場" }).waitFor();
    assert(await page.getByText("渋谷の会場で決定").isVisible(), "ノートの箇条書きが出ていない");
    assert(await page.getByRole("heading", { name: "テスト会議のノート" }).isVisible(), "AIのタイトルが付いていない");
    await shot(page, "S03-notes");
    await page.getByRole("tab", { name: /やること/ }).click();
    await page.getByRole("checkbox", { name: "見積もりを送る" }).check();
    await page.waitForTimeout(300);
    assert((await page.locator("#open-count").textContent()) === "1", "未完了の数が減っていない");
    await page.reload();
    await page.getByRole("tab", { name: /やること/ }).click();
    assert(await page.getByRole("checkbox", { name: "見積もりを送る" }).isChecked(), "完了が保存されていない");
    await shot(page, "S04-actions");
    await page.getByRole("tab", { name: "文字起こし" }).click();
    assert(await page.getByText("会場は渋谷にしましょう").isVisible(), "文字起こしが出ていない");
    assert(await page.locator(".tline .who", { hasText: "山田" }).count() === 1, "話者が付いていない");
    await shot(page, "S05-transcript");
  },

  async "F03-E1 空の文字起こしはエラーを出して進まない"(page) {
    await newMeeting(page);
    await page.getByRole("tab", { name: "📄 文字起こしを入れる" }).click();
    await page.getByRole("button", { name: "取り込んでノートを作る" }).last().click();
    await page.getByRole("alert").waitFor();
    assert(page.url().endsWith("/new"), "空なのに画面が進んだ");
  },

  async "F03-E2 vtt ファイル（Zoom 形式）を取り込むと話者と時刻が付く"(page) {
    const vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\n佐藤: 今日はよろしくお願いします\n\n2\n00:01:05.500 --> 00:01:09.000\n<v 鈴木>配信は週3回できます</v>\n";
    const file = path.join(require("os").tmpdir(), "mn-e2e-zoom.vtt");
    fs.writeFileSync(file, vtt);
    await newMeeting(page);
    await page.getByRole("tab", { name: "📄 文字起こしを入れる" }).click();
    await page.getByLabel(/文字起こしファイル/).setInputFiles(file);
    await page.getByRole("button", { name: "取り込んでノートを作る" }).last().click();
    await page.waitForURL(/\/m\//);
    await waitDone(page);
    await page.getByRole("tab", { name: "文字起こし" }).click();
    assert(await page.getByRole("button", { name: "01:05から再生" }).count() === 1, "時刻が読めていない");
    assert(await page.locator(".tline .who", { hasText: "鈴木" }).count() === 1, "<v> の話者が読めていない");
    assert((await page.locator(".meta").first().textContent()).includes("佐藤、鈴木"), "参加者が自動で入っていない");
  },

  async "F01-H1 ブラウザで録音して保存するとノートができる"(page) {
    await newMeeting(page, { title: "録音テスト", participants: "自分、山田" });
    await page.getByRole("tab", { name: "🎙 録音する" }).click();
    // 同意を選ばないと始まらない（不満への対応 #4）
    await page.getByRole("button", { name: "● 録音を開始" }).click();
    await page.getByRole("alert").filter({ hasText: "相手に伝えた" }).waitFor();
    await page.getByLabel("相手に「録音してノートを取る」と伝えた").check();
    await page.getByLabel(/会議室モード/).check();
    await page.getByRole("button", { name: "● 録音を開始" }).click();
    await page.waitForTimeout(2200);
    assert((await page.locator("#rec-time").textContent()) !== "00:00", "録音時間が進んでいない");
    assert(!(await page.getByRole("button", { name: "● 録音を開始" }).isVisible()), "録音中なのに「録音を開始」が見えている（B1）");
    await shot(page, "S02-recording");
    await page.getByRole("button", { name: "■ 停止" }).click();
    await page.getByRole("button", { name: "保存してノートを作る" }).click();
    await page.waitForURL(/\/m\//);
    assert(await page.getByRole("status").filter({ hasText: /順番待ち|文字起こし中|ノートを書いています/ }).count() >= 1, "処理中の表示が出ていない");
    await shot(page, "S03-processing");
    await waitDone(page);
    assert(await page.getByRole("heading", { name: "録音テスト" }).isVisible(), "自分で付けたタイトルが上書きされた");
    assert(await page.getByText("録音は相手に伝えた").isVisible(), "同意の記録が出ていない");
    assert(await page.getByText(/AI費用 約\d+円/).isVisible(), "AI費用が出ていない");
    assert(await page.locator("audio#player").count() === 1, "録音の再生バーが無い");
    await page.getByRole("tab", { name: "文字起こし" }).click();
    await page.getByRole("button", { name: "00:05から再生" }).click();
  },

  async "F02-H1 録音ファイルを入れるとノートができる"(page) {
    // 1秒の無音 wav を作る
    const sr = 8000, n = sr, buf = Buffer.alloc(44 + n * 2);
    buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 2, 4); buf.write("WAVEfmt ", 8); buf.writeUInt32LE(16, 16);
    buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22); buf.writeUInt32LE(sr, 24); buf.writeUInt32LE(sr * 2, 28);
    buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34); buf.write("data", 36); buf.writeUInt32LE(n * 2, 40);
    const file = path.join(require("os").tmpdir(), "mn-e2e.wav");
    fs.writeFileSync(file, buf);
    await newMeeting(page);
    await page.getByRole("tab", { name: "📁 録音ファイルを入れる" }).click();
    await page.getByLabel("録音・録画ファイル").setInputFiles(file);
    await page.getByRole("button", { name: "取り込んでノートを作る" }).first().click();
    await page.waitForURL(/\/m\//);
    await waitDone(page);
    assert(await page.getByText("渋谷の会場で決定").isVisible(), "ノートができていない");
  },

  async "F02-N1 対応していない形式はエラーになる"(page) {
    const file = path.join(require("os").tmpdir(), "mn-e2e.exe");
    fs.writeFileSync(file, "x");
    await newMeeting(page);
    await page.getByRole("tab", { name: "📁 録音ファイルを入れる" }).click();
    await page.getByLabel("録音・録画ファイル").setInputFiles(file);
    await page.getByRole("button", { name: "取り込んでノートを作る" }).first().click();
    await page.getByRole("alert").filter({ hasText: "対応していません" }).waitFor();
  },

  async "F01-N1 AIが失敗したら理由とやり直すボタンが出る"(page) {
    await fromText(page, "FAIL_AI これは失敗させるテスト");
    await page.getByText("うまく処理できませんでした").waitFor();
    assert(await page.getByRole("button", { name: "やり直す" }).isVisible(), "やり直すボタンが無い");
    await shot(page, "S03-failed");
    await page.goto(BASE + "/");
    assert(await page.locator(".badge-danger", { hasText: "失敗" }).count() >= 1, "一覧に失敗の印が無い");
  },

  async "F04-H1 やること一覧を担当者で絞って片付ける"(page) {
    await page.goto(`${BASE}/actions`);
    await shot(page, "S07-actions");
    await page.getByLabel("担当").selectOption("山田");
    await page.waitForURL(/owner=/);
    const rows = page.locator(".action-row");
    const before = await rows.count();
    assert(before >= 1, "山田さんのやることが無い");
    await rows.first().getByRole("checkbox").check();
    await page.waitForTimeout(900);
    assert(await rows.count() === before - 1, "完了にしたのに「まだ」の一覧から消えない");
  },

  async "F05-H1 キーワードで検索できる・0件の表示"(page) {
    await page.goto(`${BASE}/?q=渋谷`);
    assert(await page.locator(".meeting-card").count() >= 1, "検索で見つからない");
    await shot(page, "S01-search");
    await page.goto(`${BASE}/?q=存在しない言葉xyz`);
    await page.getByText("当てはまる会議はありませんでした").waitFor();
  },

  async "F05-H2 全会議にAIで質問できる"(page) {
    await page.goto(`${BASE}/ask`);
    await page.getByLabel("質問").fill("渋谷の会場の件はどうなった？");
    await page.getByRole("button", { name: "聞く" }).click();
    await page.locator(".msg-assistant", { hasText: "考えています…" }).waitFor({ state: "detached" });
    assert(await page.locator(".msg-assistant").last().textContent() === "記録では、会場は渋谷です。[00:05]", "答えが出ていない");
    assert(await page.locator("#sources a").count() >= 1, "読んだ会議へのリンクが無い");
    await shot(page, "S08-ask");
  },

  async "F06-H1 1つの会議に質問できる・履歴が残る"(page) {
    await page.goto(`${BASE}/`);
    await page.locator(".meeting-card").first().click();
    await page.getByRole("tab", { name: "AIに聞く" }).click();
    await page.getByLabel("質問").fill("会場は？");
    await page.getByRole("button", { name: "聞く" }).click();
    await page.getByText("記録では、会場は渋谷です。").waitFor();
    await page.reload();
    await page.getByRole("tab", { name: "AIに聞く" }).click();
    assert(await page.locator(".msg-user", { hasText: "会場は？" }).count() === 1, "質問の履歴が残っていない");
    await shot(page, "S06-ask-meeting");
  },

  async "F07-H1 編集・話者名の変更・やることの追加・削除"(page) {
    await fromText(page, "田中: 来週もう一度話しましょう");
    page.on("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "編集" }).click();
    await page.getByLabel("タイトル", { exact: true }).fill("😀 絵文字入り・とても長いタイトルの会議".repeat(3));
    await Promise.all([page.waitForEvent("load"), page.getByRole("button", { name: "保存", exact: true }).click()]);
    assert((await page.locator("#title-view").textContent()).startsWith("😀 絵文字入り"), "タイトルが変わっていない");
    await page.getByRole("tab", { name: "文字起こし" }).click();
    await page.getByText("話者の名前を直す").click();
    await page.getByLabel("新しい名前").fill("田中部長");
    await Promise.all([page.waitForEvent("load"), page.getByRole("button", { name: "変える", exact: true }).click()]);
    await page.locator(".tline .who", { hasText: "田中部長" }).waitFor();
    await page.getByRole("tab", { name: /やること/ }).click();
    await page.getByLabel("やること", { exact: true }).fill("議事録を共有する");
    await page.getByLabel("担当", { exact: true }).fill("自分");
    await Promise.all([page.waitForEvent("load"), page.getByRole("button", { name: "追加" }).click()]);
    await page.getByRole("checkbox", { name: "議事録を共有する" }).waitFor();
    // ノートを作り直しても、手で足したやることは残る
    await page.getByRole("tab", { name: "ノート" }).click();
    await page.getByRole("button", { name: "ノートを作り直す" }).click();
    await waitDone(page);
    await page.getByRole("tab", { name: /やること/ }).click();
    assert(await page.getByRole("checkbox", { name: "議事録を共有する" }).count() === 1, "作り直しで手入力のやることが消えた");
    // Markdown 書き出し
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Markdown保存" }).click()]);
    const md = fs.readFileSync(await dl.path(), "utf8");
    assert(md.includes("- [ ] 議事録を共有する（自分）"), "Markdown にやることが無い");
    // 削除
    const url = page.url();
    await page.getByRole("button", { name: "編集" }).click();
    await page.getByRole("button", { name: "この会議を削除" }).click();
    await page.waitForURL(BASE + "/");
    const res = await page.goto(url);
    assert(res.status() === 404, "削除したのに開ける");
  },


  async "FIX5-H1 録音中にブラウザが落ちても、次に開いたとき復旧できる"(page) {
    await newMeeting(page, { title: "途中で落ちた会議" });
    await page.getByRole("tab", { name: "🎙 録音する" }).click();
    await page.getByLabel("相手はいない（自分だけのメモ・独り言）").check();
    await page.getByRole("button", { name: "● 録音を開始" }).click();
    await page.getByText(/PCに保存済み/).waitFor({ timeout: 20000 });
    // 保存を押さずにタブを閉じる（＝ブラウザが落ちた）
    const ctx = page.context();
    await page.close({ runBeforeUnload: false });
    await new Promise((r) => setTimeout(r, 4000));
    const p2 = await ctx.newPage();
    await p2.goto(`${BASE}/`);
    await p2.getByText("途中で止まった録音があります").waitFor();
    await shot(p2, "FIX5-recover");
    await p2.getByRole("button", { name: "会議として保存" }).first().click();
    await p2.waitForURL(/\/m\//);
    await waitDone(p2);
    assert(await p2.getByRole("heading", { name: "途中で落ちた会議" }).isVisible(), "復旧した録音から会議ができていない");
    assert(await p2.getByText("自分だけのメモ").isVisible(), "同意の記録が引き継がれていない");
    return p2;
  },

  async "FIX6-H1 根拠が文字起こしに無いやることは「要確認」になり、確認できる"(page) {
    await fromText(page, "山田: 見積もりは金曜までに送ります\n自分: 了解です");
    await page.getByRole("tab", { name: /やること/ }).click();
    const bad = page.locator(".action-row", { hasText: "告知文を書く" });
    const good = page.locator(".action-row", { hasText: "見積もりを送る" });
    assert(await bad.getByText("⚠ 要確認").isVisible(), "根拠の無いやることに要確認が出ていない");
    assert(await good.getByText("根拠: 「見積もりは金曜までに送ります」").isVisible(), "根拠の発言が出ていない");
    assert(!(await good.getByText("要確認").isVisible()), "根拠のあるやることに要確認が出ている");
    await shot(page, "FIX6-evidence");
    await bad.getByRole("button", { name: "確認した" }).click();
    await page.getByRole("status").filter({ hasText: "確認済み" }).waitFor();
    await page.reload();
    await page.getByRole("tab", { name: /やること/ }).click();
    assert(!(await page.locator(".action-row", { hasText: "告知文を書く" }).getByText("要確認").isVisible()), "確認済みが保存されていない");
  },

  async "FIX3-H1 話者をAIで推定し、1行ずつ直せる"(page) {
    await fromText(page, "会場は渋谷にしましょう\n了解です", { participants: "山田、自分" });
    page.on("dialog", (d) => d.accept());
    await page.getByRole("tab", { name: "文字起こし" }).click();
    await page.getByRole("button", { name: "🤖 話者をAIで推定" }).click();
    await page.getByText("推定 1行").waitFor();
    await page.getByRole("tab", { name: "文字起こし" }).click();
    await shot(page, "FIX3-speakers");
    await page.getByRole("button", { name: /この行の話者を変える（今: なし）/ }).click();
    const input = page.getByLabel(/話者の名前/);
    await input.fill("自分");
    await input.press("Enter");
    await page.getByRole("status").filter({ hasText: "話者を直しました" }).waitFor();
    await page.reload();
    await page.getByRole("tab", { name: "文字起こし" }).click();
    assert(await page.getByRole("button", { name: /今: 自分/ }).count() === 1, "1行ずつの話者の変更が保存されていない");
  },

  async "FIX1-2-4 設定に動作チェック・AI費用・操作の記録が出て、上限を保存できる"(page) {
    await page.goto(`${BASE}/settings`);
    await page.getByRole("heading", { name: "動作チェック" }).waitFor();
    assert(await page.getByText("Claude の APIキー").isVisible(), "動作チェックが出ていない");
    assert((await page.locator("#month-cost").textContent()).match(/約\d+円/), "今月の費用が出ていない");
    assert(await page.locator(".log-table td", { hasText: "AIへ送信" }).count() >= 1, "AIへの送信が操作の記録に無い");
    await page.getByLabel("AI費用の月の上限（円）").fill("abc");
    await page.getByRole("button", { name: "保存" }).click();
    await page.getByRole("alert").filter({ hasText: "数字" }).waitFor();
    await page.getByLabel("AI費用の月の上限（円）").fill("3000");
    await page.getByLabel("よく出る言葉・固有名詞（カンマか改行で区切る）").fill("カラーシング、歌推し");
    await page.getByRole("button", { name: "保存" }).click();
    await page.getByRole("status").filter({ hasText: "保存しました" }).waitFor();
    await page.reload();
    assert((await page.getByLabel("AI費用の月の上限（円）").inputValue()) === "3000", "上限が保存されていない");
    await shot(page, "FIX-settings");
  },

  async "FIX8-H1 処理中でも次の会議を入れられる"(page) {
    await newMeeting(page);
    await page.getByRole("tab", { name: "📄 文字起こしを入れる" }).click();
    await page.getByLabel("または貼り付け").fill("一つ目の会議");
    await page.getByRole("button", { name: "取り込んでノートを作る" }).last().click();
    await page.waitForURL(/\/m\//);
    await newMeeting(page);
    await page.getByRole("tab", { name: "📄 文字起こしを入れる" }).click();
    await page.getByLabel("または貼り付け").fill("二つ目の会議");
    await page.getByRole("button", { name: "取り込んでノートを作る" }).last().click();
    await page.waitForURL(/\/m\//);
    await waitDone(page);
  },

  async "UI-E1 スマホ幅(390px)で横にはみ出さない"(page) {
    await page.setViewportSize({ width: 390, height: 844 });
    for (const p of ["/", "/new", "/actions", "/ask", "/settings"]) {
      await page.goto(BASE + p);
      const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert(over <= 0, `${p} が横に ${over}px はみ出している`);
    }
    await page.goto(`${BASE}/`);
    await page.locator(".meeting-card").first().click();
    const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert(over <= 0, `会議の詳細が横に ${over}px はみ出している`);
    await shot(page, "S03-mobile");
  },

  async "UI-E2 キーボードだけでタブを切り替えられる"(page) {
    await page.goto(`${BASE}/`);
    await page.locator(".meeting-card").first().click();
    await page.getByRole("tab", { name: "ノート" }).focus();
    await page.keyboard.press("ArrowRight");
    assert(await page.getByRole("tab", { name: /やること/ }).getAttribute("aria-selected") === "true", "→キーで次のタブに移らない");
  },

  async "UI-E3 設定を保存できる"(page) {
    await page.goto(`${BASE}/settings`);
    await page.getByLabel("ノートの書き方の指示・自分の前提").fill("金額は税込で書く");
    await page.getByRole("button", { name: "保存" }).click();
    await page.getByRole("status").filter({ hasText: "保存しました" }).waitFor();
    await page.reload();
    assert((await page.getByLabel("ノートの書き方の指示・自分の前提").inputValue()) === "金額は税込で書く", "設定が保存されていない");
    await shot(page, "S09-settings");
    await page.goto(`${BASE}/`);
    await shot(page, "S01-list");
    await page.goto(`${BASE}/new`);
    await shot(page, "S02-new");
  },
};

(async () => {
  const browser = await chromium.launch({
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", "--autoplay-policy=no-user-gesture-required"],
  });
  const only = process.env.ONLY;
  for (const [name, fn] of Object.entries(tests)) {
    if (only && !name.startsWith(only)) continue;
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true, permissions: ["microphone"] });
    const page = await context.newPage();
    const problems = [];
    page.on("console", (m) => { if (m.type() === "error" && !/status of (400|404|409|413|502)/.test(m.text())) problems.push("console: " + m.text()); });
    page.on("pageerror", (e) => problems.push("pageerror: " + e.message));
    page.on("response", (r) => { if (r.status() >= 500) problems.push(`5xx: ${r.status()} ${r.url()}`); });
    const t0 = Date.now();
    try {
      const replaced = await fn(page);
      if (replaced && replaced !== page) {
        replaced.on("console", (m) => { if (m.type() === "error" && !/status of (400|404|409|413|502)/.test(m.text())) problems.push("console: " + m.text()); });
      }
      if (problems.length) throw new Error(problems.join("\n"));
      results.push({ name, ok: true, ms: Date.now() - t0 });
      console.log(`✓ ${name} (${Date.now() - t0}ms)`);
    } catch (e) {
      results.push({ name, ok: false, error: e.message });
      console.log(`✗ ${name}\n    ${e.message.split("\n").join("\n    ")}`);
      await shot(page, "FAIL-" + name.split(" ")[0]).catch(() => {});
    }
    await context.close();
  }
  await browser.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})();
