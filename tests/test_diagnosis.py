"""診断の設定・判定ロジック・画面まわり"""
import random
from collections import Counter

import pytest

import diagnosis as D


# ── 設定ファイルの妥当性 ──────────────────────────────────────────
# diagnosis_config.yaml を手で編集したときの書き間違いをここで検出する

def test_診断が最低1本は公開されている():
    assert D.load_config()["quizzes"], "公開中の診断がありません"


@pytest.mark.parametrize("quiz", D.load_config()["quizzes"], ids=lambda q: q["id"])
def test_設問の軸がaxesに定義されている(quiz):
    for question in quiz["questions"]:
        assert len(question["choices"]) >= 2, f"選択肢が足りません: {question['text']}"
        for choice in question["choices"]:
            assert choice.get("label"), f"ラベルのない選択肢があります: {question['text']}"
            for axis in (choice.get("scores") or {}):
                assert axis in quiz["axes"], (
                    f"axes に無い軸 '{axis}' が使われています（{quiz['id']} / {question['text']}）"
                )


@pytest.mark.parametrize("quiz", D.load_config()["quizzes"], ids=lambda q: q["id"])
def test_タイプの重みがaxesに定義されている(quiz):
    assert len(quiz["types"]) >= 2, "タイプが2種類以上必要です"
    ids = [t["id"] for t in quiz["types"]]
    assert len(ids) == len(set(ids)), f"タイプIDが重複しています: {ids}"
    for type_ in quiz["types"]:
        assert type_.get("summary"), f"無料表示用の summary がありません: {type_['id']}"
        assert type_.get("weights"), f"weights がありません: {type_['id']}"
        for axis in type_["weights"]:
            assert axis in quiz["axes"], (
                f"axes に無い軸 '{axis}' が使われています（{quiz['id']} / {type_['id']}）"
            )


# ── 判定ロジック ──────────────────────────────────────────────────

@pytest.mark.parametrize("quiz", D.load_config()["quizzes"], ids=lambda q: q["id"])
def test_到達できないタイプがない(quiz):
    """
    どのタイプにも回答が振り分けられること。
    特定のタイプが出ないと、そのタイプの文章が死に設定になる。
    """
    random.seed(42)
    counter = Counter()
    for _ in range(3000):
        answers = [random.randrange(len(q["choices"])) for q in quiz["questions"]]
        type_, _ = D.judge(quiz, answers)
        counter[type_["id"]] += 1

    unreachable = {t["id"] for t in quiz["types"]} - set(counter)
    assert not unreachable, f"どう答えても出ないタイプがあります: {unreachable}"


@pytest.mark.parametrize("quiz", D.load_config()["quizzes"], ids=lambda q: q["id"])
def test_特定のタイプに偏りすぎない(quiz):
    """
    受け皿的なタイプを作ると回答がそこへ集中し、結果がありきたりになって
    課金されなくなる。1つのタイプが4割を超えたら設計を見直す。
    """
    random.seed(42)
    counter = Counter()
    trials = 3000
    for _ in range(trials):
        answers = [random.randrange(len(q["choices"])) for q in quiz["questions"]]
        type_, _ = D.judge(quiz, answers)
        counter[type_["id"]] += 1

    top_id, top_count = counter.most_common(1)[0]
    share = top_count / trials
    assert share <= 0.40, (
        f"'{top_id}' に {share:.0%} が集中しています。"
        "タイプの weights が他と重なっていないか確認してください"
    )


def test_極端な回答は狙い通りのタイプになる():
    """全問同じ選択肢を選んだら、その軸に対応する純粋なタイプが出る"""
    quiz = D.find_quiz("streamer-type")
    assert D.judge(quiz, [0] * 12)[0]["id"] == "leader"
    assert D.judge(quiz, [1] * 12)[0]["id"] == "healing"
    assert D.judge(quiz, [2] * 12)[0]["id"] == "talker"
    assert D.judge(quiz, [3] * 12)[0]["id"] == "creator"


# ── 回答のバリデーション ──────────────────────────────────────────

@pytest.mark.parametrize("bad", [None, [], "0,1,x", [0] * 11, [0] * 13, [0] * 11 + [99], [0] * 11 + [-1]])
def test_不正な回答を弾く(bad):
    quiz = D.find_quiz("streamer-type")
    with pytest.raises(ValueError):
        D.parse_answers(quiz, bad)


def test_カンマ区切り文字列を復元できる():
    """Stripe の metadata には文字列で入るので、そこから戻せる必要がある"""
    quiz = D.find_quiz("streamer-type")
    assert D.parse_answers(quiz, "0,1,2,3,0,1,2,3,0,1,2,3") == [0, 1, 2, 3] * 3


# ── モデル出力のHTML化 ────────────────────────────────────────────

def test_生成文のHTMLはエスケープされる():
    html = D.render_markdown("<script>alert(1)</script> と <img src=x onerror=alert(1)>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_見出しと太字と箇条書きだけ復元される():
    html = D.render_markdown("## 見出し\n本文**強調**です。\n\n- 一つ目\n- 二つ目")
    assert "<h3>見出し</h3>" in html
    assert "<strong>強調</strong>" in html
    assert html.count("<li>") == 2


# ── 画面 ─────────────────────────────────────────────────────────

def test_一覧ページが開ける(client):
    res = client.get("/diagnosis")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    for quiz in D.load_config()["quizzes"]:
        assert quiz["title"] in body


def test_診断ページにプレースホルダが残っていない(client):
    res = client.get("/diagnosis/streamer-type")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "__QUIZ_JSON__" not in body
    assert "__STYLE__" not in body
    assert "__PRICE__" not in body


def test_判定スコアをクライアントに渡さない(client):
    """スコアが見えると、狙ったタイプを出す方法が分かってしまう"""
    body = client.get("/diagnosis/streamer-type").get_data(as_text=True)
    assert "scores" not in body
    assert "weights" not in body


def test_存在しない診断は404(client):
    assert client.get("/diagnosis/存在しない").status_code == 404


def test_無料判定APIが結果を返す(client):
    res = client.post("/api/diagnosis/streamer-type/judge", json={"answers": [0] * 12})
    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] and data["summary"] and data["type_id"]


def test_回答が足りないと400(client):
    res = client.post("/api/diagnosis/streamer-type/judge", json={"answers": [0] * 5})
    assert res.status_code == 400
    assert res.get_json()["error"]


def test_session_idなしではレポートを出さない(client):
    assert client.get("/diagnosis/report").status_code == 400


# ── 有料レポートのプロンプト ──────────────────────────────────────

def test_プロンプトに本人の回答が全部入る():
    """一般論ではなく「その人の回答」に触れさせるのが有料の価値なので必須"""
    quiz = D.find_quiz("streamer-type")
    answers = [0, 1, 2, 3] * 3
    type_, _ = D.judge(quiz, answers)
    prompt = D.build_report_prompt(quiz, type_, answers)

    assert type_["name"] in prompt
    for index, question in enumerate(quiz["questions"]):
        assert question["choices"][answers[index]]["label"] in prompt
