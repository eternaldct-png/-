// ツヅリの E2E。テスト計画: replica/anime/test-plan.md
// 失敗の条件: コンソールのエラー、5xx の応答、期待した表示が出ない
const { chromium } = require('playwright');
const path = require('path');
const BASE = process.env.BASE || 'http://127.0.0.1:5056';
const SHOTS = process.env.SHOTS; // スクリーンショットの保存先（任意）
const FIX = path.join(__dirname, 'fixtures');
const IDEA = 'あまりんは歌うのが大好き。でも人前だと緊張してしまう。あまりん「今日こそ、最後まで歌う！」配信を始めると、みんなのコメントが背中を押してくれた。さな：がんばれ！最後は笑顔で歌いきった。';

const results = [];
async function tcase(id, fn) {
  try { await fn(); results.push([id, 'pass']); console.log('PASS', id); }
  catch (e) { results.push([id, 'FAIL']); console.log('FAIL', id, process.env.DEBUG ? String(e).slice(0, 1200) : String(e).split('\n')[0]); }
}
function watch(page, errs) {
  // 4xx はわざと断らせるテストがあるので数えない（5xx は下の response で数える）
  page.on('console', m => { if (m.type() === 'error' && !/status of 4\d\d/.test(m.text())) errs.push('console: ' + m.text()); });
  page.on('pageerror', e => errs.push('pageerror: ' + e));
  page.on('response', r => { if (r.status() >= 500) errs.push(`5xx: ${r.status()} ${r.url()}`); });
}
const shot = async (page, name) => SHOTS && page.screenshot({ path: path.join(SHOTS, name + '.png'), fullPage: true });
const nextBtn = page => page.getByRole('button', { name: /OK・次へ/ });

(async () => {
  const browser = await chromium.launch();
  const errs = [];
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watch(page, errs);
  let projectUrl;

  await tcase('F01-E1 空のアイデアは止める', async () => {
    await page.goto(BASE + '/new');
    await page.getByRole('button', { name: '作りはじめる' }).click();
    await page.getByRole('alert').getByText('アイデアを書いてください').waitFor();
    if (!page.url().endsWith('/new')) throw new Error('移動してしまった');
  });

  await tcase('F01-H1 アイデア → 脚本 → … → 書き出し → ダウンロード', async () => {
    await page.getByLabel('アイデア・あらすじ・セリフ（必須）').fill(IDEA);
    await page.getByLabel(/^尺（秒/).fill('12');
    const submit = page.getByRole('button', { name: '作りはじめる' });
    await submit.dblclick(); // F01-E2 二度押ししても1本だけ
    await page.waitForURL(/\/p\//);
    projectUrl = page.url();
    await page.getByLabel('題名').waitFor();
    await shot(page, 'S04-script');
    for (const stage of ['脚本', 'キャラ', '場面', '絵コンテ', '絵と動き', '音']) {
      const b = nextBtn(page);
      await b.waitFor({ timeout: 30000 });
      await page.waitForFunction(() => { const x = [...document.querySelectorAll('button')].find(e => /OK・次へ/.test(e.textContent)); return x && !x.disabled; }, null, { timeout: 30000 });
      if (stage === 'キャラ') {
        await page.locator('input[type=file]').first().setInputFiles(path.join(FIX, 'chara.png'));
        await page.getByRole('img', { name: /の画像/ }).first().waitFor();
        await shot(page, 'S05-characters');
      }
      if (stage === '場面') {
        await page.locator('input[type=file]').first().setInputFiles(path.join(FIX, 'bg.png'));
        await page.getByRole('img', { name: /の画像/ }).first().waitFor();
      }
      if (stage === '絵コンテ') await shot(page, 'S07-storyboard');
      if (stage === '絵と動き') await shot(page, 'S08-art');
      await nextBtn(page).click();
      await page.waitForTimeout(400);
    }
    await page.locator('video').first().waitFor({ timeout: 120000 });
    await shot(page, 'S10-render');
    const href = await page.getByRole('link', { name: /ダウンロード/ }).getAttribute('href');
    const r = await page.request.get(BASE + href);
    if (r.status() !== 200 || !(r.headers()['content-type'] || '').includes('video/mp4')) throw new Error('ダウンロードできない');
  });

  await tcase('F01-E2 二度押しで作品が2本できない', async () => {
    await page.goto(BASE + '/');
    const n = await page.locator('a.pcard').count();
    if (n !== 1) throw new Error(`作品が ${n} 本`);
  });

  await tcase('F03-H1 脚本を直すと後ろの段階が「古い」になる', async () => {
    await page.goto(projectUrl + '?stage=script');
    const line = page.getByLabel('セリフ').first();
    await line.fill('書き換えたセリフ');
    await page.getByRole('button', { name: '脚本を保存' }).click();
    await page.getByRole('link', { name: /キャラ.*古い/ }).waitFor();
  });

  await tcase('F03-E1 リロードしても状態が残る', async () => {
    await page.reload();
    await page.getByRole('link', { name: /キャラ.*古い/ }).waitFor();
    if (await page.getByLabel('セリフ').first().inputValue() !== '書き換えたセリフ') throw new Error('消えた');
  });

  await tcase('F04-H1 カットを足す・並べ替える・消す', async () => {
    await page.goto(projectUrl + '?stage=storyboard');
    const before = await page.getByRole('heading', { name: /^カット \d+$/ }).count();
    await page.getByRole('button', { name: 'カット1の後ろに足す' }).click();
    await page.waitForFunction(n => document.querySelectorAll('[data-shot]').length === n + 1, before);
    await page.getByRole('button', { name: 'カット2を消す' }).click();
    await page.getByRole('dialog').getByRole('button', { name: '消す' }).click();
    await page.waitForFunction(n => document.querySelectorAll('[data-shot]').length === n, before);
    const first = await page.locator('[data-shot]').first().getAttribute('data-shot');
    await page.getByRole('button', { name: 'カット1を後ろへ' }).click();
    await page.waitForFunction(id => document.querySelectorAll('[data-shot]')[1]?.dataset.shot === id, first);
  });

  await tcase('F04-E1 長すぎるセリフに警告が出る', async () => {
    const ta = page.getByLabel('セリフ').first();
    await ta.fill('あ'.repeat(80));
    await ta.blur();
    await page.getByText(/セリフが長すぎます/).first().waitFor();
  });

  await tcase('F02-H1 おまかせで最後まで自動', async () => {
    await page.goto(BASE + '/new');
    await page.getByLabel('アイデア・あらすじ・セリフ（必須）').fill('ねこが窓の外を見ている。雨がやんで、虹が出た。');
    await page.getByLabel(/^尺（秒/).fill('6');
    await page.getByLabel(/おまかせ/).check();
    await page.getByRole('button', { name: '作りはじめる' }).click();
    await page.waitForURL(/\/p\//);
    await page.locator('video').first().waitFor({ timeout: 120000 });
  });

  await tcase('F05-H1 キャラ帳に保存して別の作品で使う', async () => {
    await page.goto(projectUrl + '?stage=characters');
    await page.getByRole('button', { name: 'キャラ帳に保存' }).first().click();
    await page.getByText('キャラ帳に保存しました').waitFor();
    await page.goto(BASE + '/library');
    await page.getByRole('img', { name: /の画像/ }).first().waitFor();
    await page.goto(BASE + '/new');
    await page.getByRole('group', { name: /キャラ帳から/ }).waitFor();
  });

  await tcase('F06-E1 画像でないファイルは断る', async () => {
    await page.goto(projectUrl + '?stage=art');
    await page.locator('input[type=file]').first().setInputFiles({ name: 'x.png', mimeType: 'image/png', buffer: Buffer.from('not an image') });
    await page.getByRole('alert').getByText('画像として読めませんでした').waitFor();
  });

  await tcase('F01-E3 スマホ幅（390px）で書き出しまで見える', async () => {
    const m = await browser.newPage({ viewport: { width: 390, height: 844 } });
    watch(m, errs);
    await m.goto(projectUrl + '?stage=render');
    await m.locator('video').first().waitFor();
    const over = await m.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    if (over) throw new Error('横にはみ出している');
    await shot(m, 'S03-mobile');
    await m.close();
  });

  await tcase('F01-E4 キーボードだけで次へ進める', async () => {
    await page.goto(BASE + '/');
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => document.activeElement && document.activeElement.textContent.trim());
    if (!focused) throw new Error('フォーカスが当たらない');
  });

  await tcase('F01-N1 他のサイトからの書き込みは断る', async () => {
    const r = await page.request.post(BASE + '/api/projects', { data: { idea: 'x' } });
    if (r.status() !== 403) throw new Error('ヘッダーなしの書き込みが通った: ' + r.status());
  });

  await tcase('FX1 作品の決まりごとを保存できる', async () => {
    await page.goto(projectUrl + '?stage=script');
    await page.getByText('📌 この作品の決まりごと').click();
    await page.getByLabel('この作品の決まりごと').fill('あまりんは関西弁');
    await page.getByRole('button', { name: '保存', exact: true }).click();
    await page.getByText('決まりごとを保存しました').waitFor();
    await page.reload();
    await page.getByText('（8文字）').waitFor();
  });

  await tcase('FX2 この絵だけ作り直す（ほかのカットはそのまま）', async () => {
    await page.goto(projectUrl + '?stage=art');
    const srcs = async () => page.locator('[data-shot] .frame img').evaluateAll(xs => xs.map(x => x.getAttribute('src').split('?')[0]));
    const before = await srcs();
    await page.getByLabel('カット2の絵をどう変えるか（任意）').fill('もっと明るく');
    await page.getByRole('button', { name: 'この絵だけ作り直す' }).nth(1).click();
    await page.waitForFunction(b => {
      const xs = [...document.querySelectorAll('[data-shot] .frame img')].map(x => x.getAttribute('src').split('?')[0]);
      return xs.length === b.length && xs[1] !== b[1];
    }, before, { timeout: 30000 });
    const after = await srcs();
    if (after.filter((x, i) => i !== 1 && x !== before[i]).length) throw new Error('ほかのカットまで変わった');
    await page.getByText('無料（仮の絵＋カメラの動き）').waitFor();
  });

  await tcase('FX9 書き出す前の確認にチェックを入れられる', async () => {
    await page.goto(projectUrl + '?stage=render');
    await page.getByRole('heading', { name: '書き出す前の確認' }).waitFor();
    const cb = page.getByLabel(/使ってよいと確認した/);
    await cb.check();
    await page.reload();
    if (!await page.getByLabel(/使ってよいと確認した/).isChecked()) throw new Error('保存されていない');
  });

  await tcase('FX6 同じキャラで続きを作る', async () => {
    await page.getByRole('link', { name: /続きを作る/ }).click();
    await page.getByRole('heading', { name: '続きを作る' }).waitFor();
    if (await page.getByLabel(/この作品の決まりごと/).inputValue() !== 'あまりんは関西弁') throw new Error('決まりごとが引きつがれていない');
    await page.getByLabel('アイデア・あらすじ・セリフ（必須）').fill('次の日、あまりんはステージに立った。');
    await page.getByRole('button', { name: '作りはじめる' }).click();
    await page.waitForURL(/\/p\//);
    await page.getByText(/の続き/).first().waitFor();
    await page.goto(page.url().split('?')[0] + '?stage=characters');
    await page.getByRole('img', { name: /の画像/ }).first().waitFor({ timeout: 20000 });
  });

  await tcase('FX8 はじめての人向けの例と説明', async () => {
    await page.goto(BASE + '/new');
    await page.getByRole('button', { name: '例を入れてみる' }).click();
    if (!(await page.getByLabel('アイデア・あらすじ・セリフ（必須）').inputValue()).includes('ミケ')) throw new Error('例が入らない');
    await page.goto(projectUrl + '?stage=storyboard');
    await page.getByText('1カットだけAIに直してもらうこともできます').waitFor();
  });

  await tcase('全体 コンソールエラー・5xx なし', async () => {
    if (errs.length) throw new Error(errs.join(' / '));
  });

  await browser.close();
  const failed = results.filter(r => r[1] !== 'pass');
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  process.exit(failed.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
