"""
AI診断アプリ — 無料診断 + 有料詳細レポート（Stripe決済）

無料で12問に答えるとタイプ判定と簡易結果が出る。
詳細レポートだけを有料（既定480円）で販売し、決済確認後に
Claude API でその人専用のレポートを生成する。

診断ジャンルの追加・編集は persona/diagnosis_config.yaml だけで完結する。

【設計メモ】
- 購入フローに DB を使わない。回答内容は Stripe の Checkout Session
  metadata に保存し、決済確認は stripe.checkout.Session.retrieve で行う。
- 生成済みレポートは posts/diagnosis_reports/ にキャッシュするが、
  これは高速化のためだけのもの。キャッシュが消えても metadata から
  再生成できる（Render のファイルシステムは揮発するため）。
"""
import json
import math
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request
from markupsafe import escape

diagnosis_bp = Blueprint("diagnosis", __name__)

CONFIG_PATH = Path("persona/diagnosis_config.yaml")
REPORT_CACHE_DIR = Path("posts/diagnosis_reports")

DEFAULT_PRICE = 480
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TOKENS = 8000
DEFAULT_EFFORT = "low"

_config_cache: dict = {"mtime": None, "data": None}


# ── 設定の読み込み ────────────────────────────────────────────────

def load_config() -> dict:
    """persona/diagnosis_config.yaml を読み込む（mtime が変わったときだけ再読込）"""
    import yaml

    if not CONFIG_PATH.exists():
        return {"report": {}, "quizzes": []}

    mtime = CONFIG_PATH.stat().st_mtime
    if _config_cache["mtime"] == mtime and _config_cache["data"] is not None:
        return _config_cache["data"]

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    data.setdefault("report", {})
    data["quizzes"] = [q for q in (data.get("quizzes") or []) if _is_valid_quiz(q)]

    _config_cache["mtime"] = mtime
    _config_cache["data"] = data
    return data


def _is_valid_quiz(quiz) -> bool:
    """最低限の項目が揃っている診断だけを公開する"""
    if not isinstance(quiz, dict):
        return False
    if not quiz.get("id") or not quiz.get("title"):
        return False
    questions = quiz.get("questions") or []
    types = quiz.get("types") or []
    if not questions or not types:
        return False
    return all((q.get("text") and q.get("choices")) for q in questions)


def find_quiz(quiz_id: str):
    return next((q for q in load_config().get("quizzes", []) if q["id"] == quiz_id), None)


def report_price() -> int:
    return int(load_config().get("report", {}).get("price", DEFAULT_PRICE))


# ── 判定ロジック ──────────────────────────────────────────────────

def judge(quiz: dict, answers: list) -> tuple:
    """
    回答からタイプを判定する。

    軸ごとにスコアを合計し、各タイプの weights との内積を
    weights のノルムで割った値（コサイン類似度に相当）が
    最大のタイプを結果とする。ノルムで割ることで、重みの
    合計が大きいタイプが常に勝つことを防いでいる。
    """
    axes = quiz.get("axes") or []
    totals = {axis: 0.0 for axis in axes}

    for index, question in enumerate(quiz["questions"]):
        choice = question["choices"][answers[index]]
        for axis, value in (choice.get("scores") or {}).items():
            if axis in totals:
                totals[axis] += float(value)

    best_type, best_score = None, None
    for type_ in quiz["types"]:
        weights = type_.get("weights") or {}
        magnitude = math.sqrt(sum(float(v) ** 2 for v in weights.values())) or 1.0
        score = sum(totals.get(a, 0.0) * float(weights.get(a, 0.0)) for a in axes) / magnitude
        if best_score is None or score > best_score:
            best_type, best_score = type_, score

    return best_type, totals


def parse_answers(quiz: dict, raw) -> list:
    """回答を検証して整数のリストに正規化する。不正なら ValueError"""
    if isinstance(raw, str):
        raw = [part for part in raw.split(",") if part != ""]
    if not isinstance(raw, list):
        raise ValueError("回答の形式が正しくありません")

    questions = quiz["questions"]
    if len(raw) != len(questions):
        raise ValueError("すべての質問に回答してください")

    answers = []
    for index, value in enumerate(raw):
        try:
            choice_index = int(value)
        except (TypeError, ValueError):
            raise ValueError("回答の形式が正しくありません")
        if not 0 <= choice_index < len(questions[index]["choices"]):
            raise ValueError("回答の形式が正しくありません")
        answers.append(choice_index)
    return answers


# ── レポート生成 ──────────────────────────────────────────────────

def _report_cache_path(session_id: str) -> Path:
    """session_id をそのままファイル名に使わないよう英数字だけに削る"""
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:120]
    return REPORT_CACHE_DIR / f"{safe}.md"


def build_report_prompt(quiz: dict, type_: dict, answers: list) -> str:
    """回答内容をそのまま渡して、その人専用のレポートを書かせる"""
    answer_lines = []
    for index, question in enumerate(quiz["questions"]):
        chosen = question["choices"][answers[index]]["label"]
        answer_lines.append(f"{index + 1}. {question['text']} → 「{chosen}」")
    answers_text = "\n".join(answer_lines)

    return f"""あなたは診断コンテンツのライターです。有料（{report_price()}円）の詳細レポートを日本語で書いてください。

# 診断
{quiz['title']}（{quiz.get('catch', '')}）

# 判定されたタイプ
{type_['name']}
タイプの特徴メモ: {type_.get('hint', '')}

# この人の実際の回答
{answers_text}

# 書き方の指示
- 全体で1800〜2200字程度。
- 必ず「この人の回答」に具体的に触れること。何番でどう答えたから、こう言える、という形で根拠を示す。一般論だけのレポートは絶対に書かない。
- 回答の中に矛盾や意外な組み合わせがあれば、そこを積極的に指摘する。そこが一番価値になる。
- 褒めるだけでは終わらせない。弱点や、放置すると起きる問題も具体的に書く。ただし人格否定はしない。
- 最後は明日から試せる具体的な行動で終える。抽象的な心がけではなく、行動として書く。
- 断定しすぎない。「〜の傾向があります」「〜になりやすいです」といった表現を使う。

# 出力フォーマット（この見出しをそのまま使う）
## あなたの回答から見えたこと
## 強みと、それが効く場面
## 気をつけたい癖
## 相性
## 明日からできること

見出しは「## 」で始め、本文は普通の文章で書く。箇条書きを使う場合は行頭に「- 」を付ける。
"""


def generate_report(quiz: dict, type_: dict, answers: list) -> str:
    """Claude API で詳細レポートを生成する"""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")

    settings = load_config().get("report", {})
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=settings.get("model", DEFAULT_MODEL),
        max_tokens=int(settings.get("max_tokens", DEFAULT_MAX_TOKENS)),
        output_config={"effort": settings.get("effort", DEFAULT_EFFORT)},
        messages=[{"role": "user", "content": build_report_prompt(quiz, type_, answers)}],
    )

    if message.stop_reason == "refusal":
        raise RuntimeError("生成が安全性フィルタで拒否されました")

    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if not text:
        raise RuntimeError(f"レポートが空でした（stop_reason={message.stop_reason}）")
    return text


def get_or_create_report(session_id: str, quiz: dict, type_: dict, answers: list) -> str:
    """キャッシュがあれば返し、なければ生成して保存する"""
    cache_path = _report_cache_path(session_id)
    if cache_path.exists():
        try:
            return cache_path.read_text(encoding="utf-8")
        except OSError:
            pass

    report = generate_report(quiz, type_, answers)

    try:
        REPORT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(report, encoding="utf-8")
    except OSError as e:
        # キャッシュはあくまで高速化用。失敗しても本文は返す
        print(f"[diagnosis] レポートのキャッシュ保存に失敗: {e}")

    return report


def render_markdown(text: str) -> str:
    """
    モデル出力を安全にHTML化する。

    先にすべてエスケープしてから、見出し・箇条書き・太字だけを
    復元する。エスケープ後に変換するので HTML の混入は起こらない。
    """
    html_parts = []
    list_items = []

    def flush_list():
        if list_items:
            html_parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for raw_line in text.split("\n"):
        line = str(escape(raw_line.strip()))
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)

        if not line:
            flush_list()
            continue
        if line.startswith("### "):
            flush_list()
            html_parts.append(f"<h4>{line[4:]}</h4>")
        elif line.startswith("## "):
            flush_list()
            html_parts.append(f"<h3>{line[3:]}</h3>")
        elif line.startswith("# "):
            flush_list()
            html_parts.append(f"<h3>{line[2:]}</h3>")
        elif line.startswith("- "):
            list_items.append(line[2:])
        else:
            flush_list()
            html_parts.append(f"<p>{line}</p>")

    flush_list()
    return "".join(html_parts)


# ── 画面 ─────────────────────────────────────────────────────────

BASE_STYLE = r"""
:root {
  --bg: #f7f7fb; --surface: #ffffff; --surface2: #f1f0fa;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent-text: #9333ea; --accent-glow: rgba(124,58,237,0.10);
  --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
body {
  margin: 0; padding: 0 16px 64px; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif;
  line-height: 1.75; font-size: 16px;
}
.wrap { max-width: 680px; margin: 0 auto; }
header { padding: 28px 0 20px; text-align: center; }
header h1 {
  margin: 0 0 6px; font-size: 24px; letter-spacing: .02em;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent;
}
header p { margin: 0; color: var(--muted); font-size: 14px; }
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
  padding: 20px; margin-bottom: 16px; box-shadow: var(--shadow);
}
.btn {
  display: block; width: 100%; padding: 15px 20px; border: 0; border-radius: 12px;
  background: var(--grad); color: #fff; font-size: 16px; font-weight: 700;
  cursor: pointer; text-align: center; text-decoration: none; font-family: inherit;
}
.btn:disabled { opacity: .5; cursor: default; }
.btn-sub {
  display: block; width: 100%; padding: 13px 20px; border: 1px solid var(--border);
  border-radius: 12px; background: var(--surface); color: var(--muted);
  font-size: 15px; text-align: center; text-decoration: none; cursor: pointer; font-family: inherit;
}
.muted { color: var(--muted); font-size: 13px; }
.error { color: #dc2626; font-size: 14px; margin: 12px 0 0; }
a { color: var(--accent-text); }
"""

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI診断 | ETERNALd.c.t</title>
<meta property="og:title" content="AI診断">
<meta property="og:description" content="12個の質問に答えるだけ。無料で診断できます。">
<style>__STYLE__
.quiz-link { display: block; text-decoration: none; color: inherit; }
.quiz-link .card { transition: transform .12s ease; }
.quiz-link:active .card { transform: scale(.99); }
.quiz-emoji { font-size: 34px; line-height: 1; }
.quiz-title { margin: 8px 0 4px; font-size: 19px; font-weight: 700; }
.quiz-catch { margin: 0 0 8px; color: var(--accent-text); font-size: 14px; font-weight: 600; }
.quiz-desc { margin: 0; color: var(--muted); font-size: 14px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>AI診断</h1>
    <p>12個の質問に答えるだけ・無料</p>
  </header>
  __QUIZZES__
  <p class="muted" style="text-align:center">詳細レポート（__PRICE__円）は診断のあとで選べます。</p>
</div>
</body>
</html>
"""

QUIZ_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ | AI診断</title>
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__CATCH__">
<style>__STYLE__
.progress { height: 6px; background: var(--surface2); border-radius: 999px; overflow: hidden; margin-bottom: 18px; }
.progress span { display: block; height: 100%; background: var(--grad); width: 0; transition: width .25s ease; }
.qnum { color: var(--accent-text); font-size: 13px; font-weight: 700; margin: 0 0 6px; }
.qtext { margin: 0 0 16px; font-size: 18px; font-weight: 700; line-height: 1.6; }
.choice {
  display: block; width: 100%; text-align: left; padding: 14px 16px; margin-bottom: 10px;
  border: 1px solid var(--border); border-radius: 12px; background: var(--surface2);
  font-size: 15px; font-family: inherit; color: inherit; cursor: pointer; line-height: 1.5;
}
.choice:active { background: var(--accent-glow); }
.back { margin-top: 4px; }
.result-emoji { font-size: 52px; text-align: center; line-height: 1; }
.result-name {
  text-align: center; font-size: 24px; font-weight: 700; margin: 10px 0 14px;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.result-summary { margin: 0 0 4px; }
.sell { background: var(--surface2); border: 1px dashed #d8d4ee; }
.sell h3 { margin: 0 0 8px; font-size: 16px; }
.sell ul { margin: 0 0 16px; padding-left: 20px; color: var(--muted); font-size: 14px; }
.price { text-align: center; font-size: 22px; font-weight: 700; margin: 0 0 12px; }
.hidden { display: none; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>__EMOJI__ __TITLE__</h1>
    <p>__CATCH__</p>
  </header>

  <div id="quizView">
    <div class="progress"><span id="bar"></span></div>
    <div class="card">
      <p class="qnum" id="qnum"></p>
      <p class="qtext" id="qtext"></p>
      <div id="choices"></div>
    </div>
    <button class="btn-sub back hidden" id="backBtn" type="button">← 前の質問へ</button>
  </div>

  <div id="resultView" class="hidden">
    <div class="card">
      <div class="result-emoji" id="rEmoji"></div>
      <div class="result-name" id="rName"></div>
      <p class="result-summary" id="rSummary"></p>
    </div>

    <div class="card sell">
      <h3>もっと詳しく知りたい方へ</h3>
      <ul>
        <li>あなたの<strong>実際の回答</strong>をもとにした個別レポート</li>
        <li>強みが効く場面と、気をつけたい癖</li>
        <li>相性の傾向</li>
        <li>明日から試せる具体的な行動</li>
      </ul>
      <p class="price">__PRICE__円</p>
      <button class="btn" id="buyBtn" type="button">詳細レポートを受け取る</button>
      <p class="error hidden" id="buyError"></p>
      <p class="muted" style="margin-top:12px">お支払いは安全な決済画面（Stripe）で行われます。決済後すぐに画面でレポートが表示されます。</p>
    </div>

    <button class="btn-sub" id="retryBtn" type="button">もう一度診断する</button>
    <p style="text-align:center;margin-top:16px"><a href="/diagnosis">ほかの診断を見る</a></p>
  </div>
</div>

<script>
const QUIZ = __QUIZ_JSON__;
const answers = [];
let index = 0;

const el = (id) => document.getElementById(id);

function renderQuestion() {
  const q = QUIZ.questions[index];
  el('qnum').textContent = `Q${index + 1} / ${QUIZ.questions.length}`;
  el('qtext').textContent = q.text;
  el('bar').style.width = `${(index / QUIZ.questions.length) * 100}%`;
  el('backBtn').classList.toggle('hidden', index === 0);

  const box = el('choices');
  box.textContent = '';
  q.choices.forEach((choice, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'choice';
    btn.textContent = choice;
    btn.onclick = () => pick(i);
    box.appendChild(btn);
  });
}

function pick(choiceIndex) {
  answers[index] = choiceIndex;
  if (index < QUIZ.questions.length - 1) {
    index += 1;
    renderQuestion();
    window.scrollTo(0, 0);
  } else {
    submit();
  }
}

el('backBtn').onclick = () => {
  if (index > 0) { index -= 1; renderQuestion(); window.scrollTo(0, 0); }
};

el('retryBtn').onclick = () => {
  answers.length = 0;
  index = 0;
  el('resultView').classList.add('hidden');
  el('quizView').classList.remove('hidden');
  renderQuestion();
  window.scrollTo(0, 0);
};

async function submit() {
  el('bar').style.width = '100%';
  try {
    const res = await fetch(`/api/diagnosis/${QUIZ.id}/judge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '判定に失敗しました');

    el('rEmoji').textContent = data.emoji || '✨';
    el('rName').textContent = data.name;
    el('rSummary').textContent = data.summary;
    el('quizView').classList.add('hidden');
    el('resultView').classList.remove('hidden');
    window.scrollTo(0, 0);
  } catch (e) {
    alert(e.message);
  }
}

el('buyBtn').onclick = async () => {
  const btn = el('buyBtn');
  const err = el('buyError');
  btn.disabled = true;
  btn.textContent = '決済画面を準備しています…';
  err.classList.add('hidden');
  try {
    const res = await fetch(`/api/diagnosis/${QUIZ.id}/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '決済の準備に失敗しました');
    window.location.href = data.url;
  } catch (e) {
    err.textContent = e.message;
    err.classList.remove('hidden');
    btn.disabled = false;
    btn.textContent = '詳細レポートを受け取る';
  }
};

renderQuestion();
</script>
</body>
</html>
"""

REPORT_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>詳細レポート | AI診断</title>
<meta name="robots" content="noindex">
<style>__STYLE__
.result-emoji { font-size: 52px; text-align: center; line-height: 1; }
.result-name {
  text-align: center; font-size: 24px; font-weight: 700; margin: 10px 0 0;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.report h3 {
  font-size: 17px; margin: 26px 0 8px; padding-left: 10px;
  border-left: 4px solid var(--accent-text); line-height: 1.4;
}
.report h3:first-child { margin-top: 0; }
.report h4 { font-size: 15px; margin: 18px 0 6px; }
.report p { margin: 0 0 12px; }
.report ul { margin: 0 0 12px; padding-left: 22px; }
.report li { margin-bottom: 6px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>__TITLE__</h1>
    <p>詳細レポート</p>
  </header>
  <div class="card">
    <div class="result-emoji">__EMOJI__</div>
    <div class="result-name">__NAME__</div>
  </div>
  <div class="card report">__REPORT__</div>
  <p class="muted" style="text-align:center">このページはブックマークすると後からでも開けます。<br>スクリーンショットでの保存もおすすめです。</p>
  <p style="text-align:center;margin-top:16px"><a href="/diagnosis">ほかの診断を見る</a></p>
</div>
</body>
</html>
"""

NOTICE_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ | AI診断</title>
<meta name="robots" content="noindex">
<style>__STYLE__</style>
</head>
<body>
<div class="wrap">
  <header><h1>__ICON__ __HEADLINE__</h1></header>
  <div class="card"><p style="margin:0">__MESSAGE__</p></div>
  <p style="text-align:center;margin-top:16px"><a href="/diagnosis">診断一覧に戻る</a></p>
</div>
</body>
</html>
"""


def _html(body: str):
    return body.replace("__STYLE__", BASE_STYLE), 200, {"Content-Type": "text/html; charset=utf-8"}


def _notice(title: str, icon: str, headline: str, message: str, status: int = 200):
    body = (NOTICE_HTML
            .replace("__STYLE__", BASE_STYLE)
            .replace("__TITLE__", str(escape(title)))
            .replace("__ICON__", icon)
            .replace("__HEADLINE__", str(escape(headline)))
            .replace("__MESSAGE__", message))
    return body, status, {"Content-Type": "text/html; charset=utf-8"}


# ── ルーティング ──────────────────────────────────────────────────

@diagnosis_bp.route("/diagnosis")
def diagnosis_index():
    quizzes = load_config().get("quizzes", [])
    if not quizzes:
        return _notice("準備中", "🛠", "準備中です",
                       "現在ご利用いただける診断がありません。もうしばらくお待ちください。")

    cards = []
    for quiz in quizzes:
        cards.append(
            f'<a class="quiz-link" href="/diagnosis/{escape(quiz["id"])}">'
            f'<div class="card">'
            f'<div class="quiz-emoji">{escape(quiz.get("emoji", "✨"))}</div>'
            f'<p class="quiz-title">{escape(quiz["title"])}</p>'
            f'<p class="quiz-catch">{escape(quiz.get("catch", ""))}</p>'
            f'<p class="quiz-desc">{escape(quiz.get("description", ""))}</p>'
            f'</div></a>'
        )

    return _html(INDEX_HTML
                 .replace("__QUIZZES__", "".join(cards))
                 .replace("__PRICE__", f"{report_price():,}"))


@diagnosis_bp.route("/diagnosis/<quiz_id>")
def diagnosis_quiz(quiz_id):
    quiz = find_quiz(quiz_id)
    if not quiz:
        return _notice("見つかりません", "🔍", "診断が見つかりません",
                       "URLが変更されたか、公開が終了した可能性があります。", status=404)

    # 判定用のスコアはクライアントに渡さない（設問文と選択肢ラベルだけ）
    payload = {
        "id": quiz["id"],
        "questions": [
            {"text": q["text"], "choices": [c["label"] for c in q["choices"]]}
            for q in quiz["questions"]
        ],
    }
    quiz_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    return _html(QUIZ_HTML
                 .replace("__QUIZ_JSON__", quiz_json)
                 .replace("__TITLE__", str(escape(quiz["title"])))
                 .replace("__CATCH__", str(escape(quiz.get("catch", ""))))
                 .replace("__EMOJI__", str(escape(quiz.get("emoji", "✨"))))
                 .replace("__PRICE__", f"{report_price():,}"))


@diagnosis_bp.route("/api/diagnosis/<quiz_id>/judge", methods=["POST"])
def api_diagnosis_judge(quiz_id):
    """無料の判定結果を返す"""
    quiz = find_quiz(quiz_id)
    if not quiz:
        return jsonify({"error": "診断が見つかりません"}), 404

    data = request.get_json(force=True, silent=True) or {}
    try:
        answers = parse_answers(quiz, data.get("answers"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    type_, _ = judge(quiz, answers)
    return jsonify({
        "type_id": type_["id"],
        "name": type_["name"],
        "emoji": type_.get("emoji", "✨"),
        "summary": type_.get("summary", ""),
    })


@diagnosis_bp.route("/api/diagnosis/<quiz_id>/checkout", methods=["POST"])
def api_diagnosis_checkout(quiz_id):
    """詳細レポート購入用の Stripe Checkout セッションを作る"""
    import stripe

    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return jsonify({"error": "決済機能が設定されていません（管理者にお問い合わせください）"}), 500
    stripe.api_key = secret_key

    quiz = find_quiz(quiz_id)
    if not quiz:
        return jsonify({"error": "診断が見つかりません"}), 404

    data = request.get_json(force=True, silent=True) or {}
    try:
        answers = parse_answers(quiz, data.get("answers"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    type_, _ = judge(quiz, answers)
    base_url = request.url_root.rstrip("/")

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {"name": f"{quiz['title']} 詳細レポート（{type_['name']}）"},
                    "unit_amount": report_price(),
                },
                "quantity": 1,
            }],
            metadata={
                "kind": "diagnosis_report",
                "quiz_id": quiz["id"],
                "type_id": type_["id"],
                "answers": ",".join(str(a) for a in answers),
            },
            success_url=f"{base_url}/diagnosis/report?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/diagnosis/{quiz['id']}",
        )
        return jsonify({"ok": True, "url": checkout_session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@diagnosis_bp.route("/diagnosis/report")
def diagnosis_report():
    """決済完了後のレポート表示。支払い済みであることを Stripe で必ず確認する"""
    import stripe

    session_id = request.args.get("session_id", "")
    if not session_id:
        return _notice("エラー", "⚠️", "レポートを表示できません",
                       "URLが正しくありません。決済完了後に表示されたページを開いてください。", status=400)

    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return _notice("エラー", "⚠️", "レポートを表示できません",
                       "決済機能が設定されていません。", status=500)
    stripe.api_key = secret_key

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        return _notice("エラー", "⚠️", "レポートを表示できません",
                       "決済情報が確認できませんでした。お手数ですが、もう一度お試しください。", status=404)

    if checkout_session.get("payment_status") != "paid":
        return _notice("お支払い未完了", "⏳", "お支払いが確認できていません",
                       "決済が完了するまでレポートは表示されません。"
                       "完了済みの場合は、少し時間をおいてからこのページを再読み込みしてください。", status=402)

    metadata = checkout_session.get("metadata") or {}
    quiz = find_quiz(metadata.get("quiz_id", ""))
    if not quiz:
        return _notice("エラー", "⚠️", "レポートを表示できません",
                       "診断データが見つかりませんでした。お手数ですがお問い合わせください。", status=404)

    try:
        answers = parse_answers(quiz, metadata.get("answers", ""))
    except ValueError:
        return _notice("エラー", "⚠️", "レポートを表示できません",
                       "回答データが読み取れませんでした。お手数ですがお問い合わせください。", status=500)

    type_ = next((t for t in quiz["types"] if t["id"] == metadata.get("type_id")), None)
    if not type_:
        type_, _ = judge(quiz, answers)

    try:
        report = get_or_create_report(session_id, quiz, type_, answers)
    except Exception as e:
        print(f"[diagnosis] レポート生成に失敗: {e}")
        # 決済は完了しているので、再読み込みで必ず作り直せることを伝える
        return _notice(
            "生成中にエラー", "⚠️", "レポートの生成に失敗しました",
            "お支払いは完了しています。このページを再読み込みすると、もう一度生成を試みます。<br>"
            "何度も失敗する場合は、下記の番号を添えてお問い合わせください。<br>"
            f'<span class="muted">{escape(session_id)}</span>',
            status=500,
        )

    body = (REPORT_HTML
            .replace("__STYLE__", BASE_STYLE)
            .replace("__TITLE__", str(escape(quiz["title"])))
            .replace("__EMOJI__", str(escape(type_.get("emoji", "✨"))))
            .replace("__NAME__", str(escape(type_["name"])))
            .replace("__REPORT__", render_markdown(report)))
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}
