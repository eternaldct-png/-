"""eternal-liver-success スキルの liver_health.py（ライバーの状態スコア）のテスト。"""
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "eternal-liver-success"
spec = importlib.util.spec_from_file_location("liver_health", SKILL / "scripts" / "liver_health.py")
lh = importlib.util.module_from_spec(spec)
sys.modules["liver_health"] = lh  # dataclass が自分のモジュールを引けるように登録してから読み込む
spec.loader.exec_module(lh)

TODAY = date(2026, 11, 20)


def row(**kw):
    base = {
        "活動名": "テスト", "契約更新日": "2027-06-01", "今月配信日数": "20", "先月配信日数": "20",
        "今月配信時間": "40", "先月配信時間": "40", "今月売上": "50000", "3か月平均売上": "50000",
        "最終連絡日": "2026-11-18", "面談欠席数": "0", "備考": "",
    }
    base.update(kw)
    return base


def test_healthy_liver_is_full_score_and_growth_candidate():
    r = lh.score_row(row(), TODAY, 20)
    assert r.score == 100
    assert r.priority == "順調"
    assert r.growth is True
    assert r.flags == []


def test_declining_liver_near_renewal_is_top_priority():
    r = lh.score_row(row(**{
        "契約更新日": "2027-01-05", "今月配信日数": "5", "先月配信日数": "20",
        "今月売上": "10000", "最終連絡日": "2026-10-01", "面談欠席数": "2",
    }), TODAY, 20)
    assert r.score < 50
    assert r.priority == "最優先"
    assert any("配信日数" in f for f in r.flags)
    assert any("連絡が50日" in f for f in r.flags)
    assert any("契約更新まで46日" in f for f in r.flags)
    assert r.growth is False


def test_blank_values_are_warned_not_guessed():
    r = lh.score_row(row(**{"今月売上": "", "最終連絡日": ""}), TODAY, 20)
    assert any("今月売上が空欄" in w for w in r.warnings)
    assert any("最終連絡日" in w for w in r.warnings)
    assert r.connection == 10  # 連絡なし扱い（0点）＋欠席0回（10点）


def test_no_previous_data_does_not_crash():
    r = lh.score_row(row(**{"先月配信日数": "0", "先月配信時間": "0", "3か月平均売上": "0"}), TODAY, 20)
    assert r.revenue == 15  # 比べる材料が無いときは中間
    assert 0 <= r.score <= 100


def test_actions_never_use_quota_wording():
    r = lh.score_row(row(**{"今月配信日数": "2", "今月売上": "1000"}), TODAY, 20)
    text = "".join(r.actions)
    assert "ノルマとして伝えない" in text
    assert "してください" not in text


def test_sample_csv_runs_and_sorts_by_priority(capsys):
    assert lh.main([str(SKILL / "assets" / "sample_livers.csv"), "--today", "2026-11-20", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    order = [d["priority"] for d in data]
    assert order == sorted(order, key=lambda p: lh.ORDER[p])
    assert data[0]["name"] == "サンプルA"
