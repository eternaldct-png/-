"""
決済〜レポート表示の経路

Stripe と Claude API はモックする。ここで守りたいのは
「払っていない人にレポートが出ないこと」と「払った人が確実に受け取れること」。
"""
import sys
from unittest import mock

import pytest

import diagnosis as D

ANSWERS = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
ANSWERS_CSV = "0,1,2,3,0,1,2,3,0,1,2,3"

FAKE_REPORT = """## あなたの回答から見えたこと
Q3とQ7の答えは**噛み合っていません**。

- 気になる点その1
- <script>alert('xss')</script>
"""


class FakeStripeObject(dict):
    """Stripe のオブジェクトは属性でも dict でも読めるので両方通す"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


@pytest.fixture
def expected_type():
    return D.judge(D.find_quiz("streamer-type"), ANSWERS)[0]


@pytest.fixture
def paid_metadata(expected_type):
    return {
        "kind": "diagnosis_report",
        "quiz_id": "streamer-type",
        "type_id": expected_type["id"],
        "answers": ANSWERS_CSV,
    }


@pytest.fixture
def fake_stripe(monkeypatch):
    stripe = mock.MagicMock()
    stripe.created_sessions = []

    def create(**kwargs):
        stripe.created_sessions.append(kwargs)
        return FakeStripeObject(url="https://checkout.stripe.test/cs_test_123")

    stripe.checkout.Session.create = create
    monkeypatch.setitem(sys.modules, "stripe", stripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    return stripe


def set_retrieve(stripe, payment_status, metadata):
    stripe.checkout.Session.retrieve = lambda session_id: FakeStripeObject(
        payment_status=payment_status, metadata=metadata
    )


@pytest.fixture
def fake_anthropic(monkeypatch):
    anthropic = mock.MagicMock()
    block = mock.MagicMock()
    block.type = "text"
    block.text = FAKE_REPORT
    message = mock.MagicMock()
    message.stop_reason = "end_turn"
    message.content = [block]
    anthropic.Anthropic.return_value.messages.create.return_value = message
    monkeypatch.setitem(sys.modules, "anthropic", anthropic)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-dummy")
    return anthropic


def calls(fake_anthropic):
    return fake_anthropic.Anthropic.return_value.messages.create.call_count


# ── 決済セッションの作成 ──────────────────────────────────────────

def test_回答12件がStripeのmetadataに収まる(client, fake_stripe, expected_type):
    res = client.post("/api/diagnosis/streamer-type/checkout", json={"answers": ANSWERS})
    assert res.status_code == 200

    metadata = fake_stripe.created_sessions[0]["metadata"]
    assert metadata["quiz_id"] == "streamer-type"
    assert metadata["type_id"] == expected_type["id"]
    assert metadata["answers"] == ANSWERS_CSV
    # Stripe の metadata は値ごとに500文字まで
    assert all(len(str(v)) <= 500 for v in metadata.values())


def test_金額と戻り先URLが正しい(client, fake_stripe):
    client.post("/api/diagnosis/streamer-type/checkout", json={"answers": ANSWERS})
    created = fake_stripe.created_sessions[0]

    assert created["line_items"][0]["price_data"]["unit_amount"] == D.report_price()
    assert created["line_items"][0]["price_data"]["currency"] == "jpy"
    # Stripe がセッションIDを埋め込むためのプレースホルダが必要
    assert "{CHECKOUT_SESSION_ID}" in created["success_url"]


def test_不正な回答では決済に進ませない(client, fake_stripe):
    res = client.post("/api/diagnosis/streamer-type/checkout", json={"answers": [0] * 3})
    assert res.status_code == 400
    assert not fake_stripe.created_sessions


# ── レポートの受け渡し ────────────────────────────────────────────

def test_未払いならレポートを生成すらしない(client, fake_stripe, fake_anthropic, paid_metadata, report_cache):
    set_retrieve(fake_stripe, "unpaid", paid_metadata)
    res = client.get("/diagnosis/report?session_id=cs_test_123")

    assert res.status_code == 402
    assert "あなたの回答から見えたこと" not in res.get_data(as_text=True)
    assert calls(fake_anthropic) == 0, "未払いなのに Claude API を呼んでいます（無駄な費用）"


def test_決済確認が取れないsession_idは弾く(client, fake_stripe, fake_anthropic, report_cache):
    def boom(session_id):
        raise Exception("No such checkout.session")

    fake_stripe.checkout.Session.retrieve = boom
    res = client.get("/diagnosis/report?session_id=cs_forged_999")

    assert res.status_code == 404
    assert calls(fake_anthropic) == 0


def test_支払い済みならレポートが表示される(
    client, fake_stripe, fake_anthropic, paid_metadata, expected_type, report_cache
):
    set_retrieve(fake_stripe, "paid", paid_metadata)
    res = client.get("/diagnosis/report?session_id=cs_test_123")
    body = res.get_data(as_text=True)

    assert res.status_code == 200
    assert expected_type["name"] in body
    assert "<h3>あなたの回答から見えたこと</h3>" in body
    assert "<strong>噛み合っていません</strong>" in body
    assert "__REPORT__" not in body and "__STYLE__" not in body


def test_生成文経由のスクリプトが混入しない(
    client, fake_stripe, fake_anthropic, paid_metadata, report_cache
):
    set_retrieve(fake_stripe, "paid", paid_metadata)
    body = client.get("/diagnosis/report?session_id=cs_test_123").get_data(as_text=True)

    assert "<script>alert" not in body
    assert "&lt;script&gt;" in body


def test_使ったモデル設定が意図通り(client, fake_stripe, fake_anthropic, paid_metadata, report_cache):
    set_retrieve(fake_stripe, "paid", paid_metadata)
    client.get("/diagnosis/report?session_id=cs_test_123")

    kwargs = fake_anthropic.Anthropic.return_value.messages.create.call_args.kwargs
    settings = D.load_config()["report"]
    assert kwargs["model"] == settings["model"]
    # Opus 5 では max_tokens が「思考＋本文」の合計上限になるため余裕が要る
    assert kwargs["max_tokens"] >= 4000
    # Opus 5 で 400 になるパラメータを送っていないこと
    assert "temperature" not in kwargs
    assert "top_p" not in kwargs


def test_再読み込みでは作り直さない(client, fake_stripe, fake_anthropic, paid_metadata, report_cache):
    set_retrieve(fake_stripe, "paid", paid_metadata)
    client.get("/diagnosis/report?session_id=cs_test_123")
    client.get("/diagnosis/report?session_id=cs_test_123")

    assert calls(fake_anthropic) == 1, "リロードのたびに課金されています"
    assert len(list(report_cache.glob("*.md"))) == 1


def test_キャッシュが消えても再生成できる(client, fake_stripe, fake_anthropic, paid_metadata, report_cache):
    """Render のファイルシステムは揮発するので、metadata から復元できる必要がある"""
    set_retrieve(fake_stripe, "paid", paid_metadata)
    client.get("/diagnosis/report?session_id=cs_test_123")

    for path in report_cache.glob("*.md"):
        path.unlink()

    res = client.get("/diagnosis/report?session_id=cs_test_123")
    assert res.status_code == 200
    assert calls(fake_anthropic) == 2


def test_生成に失敗しても支払い済みを握りつぶさない(
    client, fake_stripe, fake_anthropic, paid_metadata, report_cache
):
    set_retrieve(fake_stripe, "paid", paid_metadata)
    fake_anthropic.Anthropic.return_value.messages.create.side_effect = RuntimeError("API down")

    res = client.get("/diagnosis/report?session_id=cs_test_123")
    body = res.get_data(as_text=True)

    assert res.status_code == 500
    assert "お支払いは完了しています" in body
    assert "cs_test_123" in body, "問い合わせ用の番号が表示されていません"
