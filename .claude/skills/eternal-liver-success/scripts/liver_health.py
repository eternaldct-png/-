#!/usr/bin/env python3
"""所属ライバーの「状態スコア」と「更新前フォローの優先順」を出す（標準ライブラリだけで動く）。

使い方:
    python3 liver_health.py ライバー一覧.csv                # 表で出す
    python3 liver_health.py ライバー一覧.csv --format json  # JSONで出す
    python3 liver_health.py ライバー一覧.csv --today 2026-11-20 --target-days 20

CSV の列（1行目は見出し。スプレッドシートから「CSVでダウンロード」したものをそのまま使える）:
    活動名, 契約更新日, 今月配信日数, 先月配信日数, 今月配信時間, 先月配信時間,
    今月売上, 3か月平均売上, 最終連絡日, 面談欠席数, 備考
    - 日付は YYYY-MM-DD か YYYY/MM/DD。空欄の数値は 0 として扱う（その旨を warnings に出す）。
    - 売上は円・コイン・ダイヤのどれでもよい（全員同じ単位にそろえる）。

スコアは「声をかける順番を決めるための目安」で、ライバーの評価や報酬の判断には使わない。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

COLUMNS = [
    "活動名", "契約更新日", "今月配信日数", "先月配信日数", "今月配信時間", "先月配信時間",
    "今月売上", "3か月平均売上", "最終連絡日", "面談欠席数", "備考",
]
NUMERIC = ["今月配信日数", "先月配信日数", "今月配信時間", "先月配信時間",
           "今月売上", "3か月平均売上", "面談欠席数"]


@dataclass
class Result:
    name: str
    score: int                 # 0〜100（高いほど順調）
    activity: int              # 活動量 0〜40
    revenue: int               # 売上の推移 0〜30
    connection: int            # 事務所とのつながり 0〜30
    days_to_renewal: int | None
    priority: str              # 最優先 / 要フォロー / 様子見 / 順調
    flags: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    growth: bool = False       # 次の挑戦（イベント・グッズ・楽曲など）を相談する候補
    warnings: list[str] = field(default_factory=list)


def parse_date(text: str) -> date | None:
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def to_num(text: str) -> float | None:
    text = (text or "").replace(",", "").replace("円", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def ratio(now: float, before: float) -> float | None:
    """前と比べた割合（前が0なら比べられないので None）。"""
    if before <= 0:
        return None
    return now / before


def score_row(row: dict, today: date, target_days: int) -> Result:
    warnings: list[str] = []
    nums: dict[str, float] = {}
    for col in NUMERIC:
        value = to_num(row.get(col, ""))
        if value is None:
            if (row.get(col) or "").strip():
                warnings.append(f"{col}が数値として読めない（0として計算）")
            else:
                warnings.append(f"{col}が空欄（0として計算）")
            value = 0.0
        nums[col] = value

    flags: list[str] = []
    actions: list[str] = []

    # ── 活動量（40点）: 目標日数に対する配信日数 30点 + 先月からの落ち込み 10点
    days_rate = min(nums["今月配信日数"] / target_days, 1.0) if target_days > 0 else 0.0
    activity = round(days_rate * 30)
    days_trend = ratio(nums["今月配信日数"], nums["先月配信日数"])
    hours_trend = ratio(nums["今月配信時間"], nums["先月配信時間"])
    trend = min(t for t in (days_trend, hours_trend) if t is not None) if (
        days_trend is not None or hours_trend is not None) else 1.0
    activity += round(max(0.0, min(trend, 1.0)) * 10)
    if days_trend is not None and days_trend <= 0.5:
        flags.append(f"配信日数が先月の{days_trend:.0%}")
        actions.append("最近の生活の変化（本業・家庭・体調）を、責めずに聞く")
    elif hours_trend is not None and hours_trend <= 0.5:
        flags.append(f"配信時間が先月の{hours_trend:.0%}")
        actions.append("配信時間が減った理由を聞き、無理のない時間帯を一緒に考える")
    if nums["今月配信日数"] == 0:
        flags.append("今月まだ配信していない")

    # ── 売上の推移（30点）: 今月 ÷ 3か月平均
    rev_trend = ratio(nums["今月売上"], nums["3か月平均売上"])
    if rev_trend is None:
        revenue = 15  # 比べる材料がないので中間
        if nums["今月売上"] == 0:
            warnings.append("売上の比較材料がない（3か月平均が0）")
    else:
        revenue = round(max(0.0, min(rev_trend, 1.0)) * 30)
        if rev_trend <= 0.6:
            flags.append(f"売上が3か月平均の{rev_trend:.0%}")
            actions.append("リスナーとの関係や枠周りの状況を一緒に振り返る（ノルマとして伝えない）")

    # ── つながり（30点）: 最終連絡からの日数 20点 + 面談欠席 10点
    last = parse_date(row.get("最終連絡日", ""))
    if last is None:
        warnings.append("最終連絡日が読めない（連絡なし扱い）")
        since = None
        connection = 0
        flags.append("最終連絡日が不明")
    else:
        since = (today - last).days
        if since <= 7:
            connection = 20
        elif since >= 30:
            connection = 0
        else:
            connection = round(20 * (30 - since) / 23)
        if since >= 30:
            flags.append(f"事務所との連絡が{since}日ない")
            actions.append("用件なしの声かけ（最近の配信の良かった所を1つ具体的に伝える）")
    absences = int(nums["面談欠席数"])
    connection += max(0, 10 - absences * 5)
    if absences >= 2:
        flags.append(f"面談の欠席が{absences}回")
        actions.append("面談の時間・形式（通話／チャット）を本人の都合に合わせて選び直す")

    score = activity + revenue + connection

    # ── 契約更新日
    renewal = parse_date(row.get("契約更新日", ""))
    days_to_renewal = (renewal - today).days if renewal else None
    if renewal is None:
        warnings.append("契約更新日が読めない")
    elif 0 <= days_to_renewal <= 60:
        flags.append(f"契約更新まで{days_to_renewal}日")
        actions.append("更新前面談で、次の1年にやりたいことと続けにくい事情の両方を聞く")

    # ── 優先順
    near_renewal = days_to_renewal is not None and 0 <= days_to_renewal <= 60
    if score < 50 and near_renewal:
        priority = "最優先"
    elif score < 50 or (score < 70 and near_renewal):
        priority = "要フォロー"
    elif score < 80 or flags:
        priority = "様子見"
    else:
        priority = "順調"

    growth = score >= 80 and (rev_trend is None or rev_trend >= 1.0) and not flags
    if growth:
        actions.append("次の挑戦（イベント・グッズ・オリジナル曲など）に興味があるか聞く")
    if not actions:
        actions.append("いつも通りの声かけでよい")

    return Result(
        name=(row.get("活動名") or "").strip() or "（活動名なし）",
        score=score, activity=activity, revenue=revenue, connection=connection,
        days_to_renewal=days_to_renewal, priority=priority,
        flags=flags, actions=actions, growth=growth, warnings=warnings,
    )


ORDER = {"最優先": 0, "要フォロー": 1, "様子見": 2, "順調": 3}


def analyze(rows: list[dict], today: date, target_days: int) -> list[Result]:
    results = [score_row(r, today, target_days) for r in rows if any((v or "").strip() for v in r.values())]
    return sorted(results, key=lambda r: (ORDER[r.priority], r.score))


def read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or []) and c != "備考"]
        if missing:
            raise SystemExit(f"CSVに必要な列がない: {', '.join(missing)}")
        return list(reader)


def to_text(results: list[Result]) -> str:
    lines = []
    for r in results:
        renewal = f"更新まで{r.days_to_renewal}日" if r.days_to_renewal is not None else "更新日不明"
        lines.append(f"【{r.priority}】{r.name}  {r.score}点（活動{r.activity}/40・売上{r.revenue}/30・つながり{r.connection}/30）{renewal}")
        for fl in r.flags:
            lines.append(f"   ⚠ {fl}")
        for a in r.actions:
            lines.append(f"   → {a}")
        for w in r.warnings:
            lines.append(f"   ※ {w}")
    counts = {p: sum(1 for r in results if r.priority == p) for p in ORDER}
    lines.append("")
    lines.append("集計: " + " / ".join(f"{p} {n}人" for p, n in counts.items()))
    lines.append("※ スコアは声をかける順番の目安。評価・報酬・契約の判断には使わない。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="所属ライバーの状態スコアとフォローの優先順")
    parser.add_argument("csv_path")
    parser.add_argument("--today", help="基準日 YYYY-MM-DD（省略時は今日）")
    parser.add_argument("--target-days", type=int, default=20, help="月の目標配信日数（既定20）")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    today = parse_date(args.today) if args.today else date.today()
    if today is None:
        parser.error("--today は YYYY-MM-DD で指定する")
    results = analyze(read_csv(args.csv_path), today, args.target_days)
    if args.format == "json":
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))
    else:
        print(to_text(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
