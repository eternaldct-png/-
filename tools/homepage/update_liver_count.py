#!/usr/bin/env python3
"""ホームページの「所属ライバー数」「活動率」を最新の数字に直す（Mac で実行する1回きりのスクリプト）。

使い方:
    python3 update_liver_count.py <ETERNALライバー事務所 のパス>          # 確認だけ（何も書き換えない）
    python3 update_liver_count.py <ETERNALライバー事務所 のパス> --apply  # 書き換える（*.bak-日時 を作る）

変更内容（2026-10）:
  所属ライバー 58名 → 67名 / 一覧ページの 60+ → 67+
  活動率 86.2% → 83.5%（期間の表記は「2026年10月現在の事務所管理データ」）
  「2026年7月現在」「2026年7月時点」→「2026年10月現在」「2026年10月時点」
  （合格率100%はそのまま。初月の実例など「2026年6〜7月の事務所管理データ」は活動率の直後以外は残す）
対象は、所属人数・活動率・合格率のどれかが書かれているテキストファイルだけ。
「所属ライバー11人」（機材アンケート）や「55名分」（紹介ページ数）は変えない。
"""
import datetime
import re
import shutil
import sys
from pathlib import Path

EXTS = {".html", ".htm", ".md", ".js", ".json", ".yaml", ".yml", ".py", ".txt", ".csv", ".xml", ".toml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv"}
TARGET = re.compile(r"(?<!\d)58名|<b>58<|86\.2%|活動率86-2|合格率100|data-count=\"60\"")

RULES = [
    ("活動率の期間", re.compile(r"86\.2%（2026年(?:6〜7月|7月現在)の事務所管理データ"), "83.5%（2026年10月現在の事務所管理データ"),
    ("活動率", re.compile(r"(?<![\d.])86\.2(?!\d)"), "83.5"),
    ("活動率（見出しのリンク名）", re.compile(r"活動率86-2"), "活動率83-5"),
    ("所属人数", re.compile(r"(?<!\d)58名"), "67名"),
    ("所属人数（大きい数字）", re.compile(r"<b>58(?=</b>名|<span>名)"), "<b>67"),
    ("一覧ページ 60+", re.compile(r'data-count="60"(?=[^\n]{0,160}所属ライバー)'), 'data-count="67"'),
    ("時点", re.compile(r"2026年7月(現在|時点)"), r"2026年10月\1"),
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    root = Path(args[0]).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"フォルダが見つかりません: {root}")

    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    total = 0
    files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXTS or ".bak" in path.name:
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not TARGET.search(text):
            continue
        new = text
        changes = []
        for label, pat, rep in RULES:
            for m in pat.finditer(new):
                a, b = max(0, m.start() - 18), min(len(new), m.end() + 12)
                changes.append(f"    [{label}] …{new[a:b]}…".replace("\n", " "))
            new = pat.sub(rep, new)
        if new == text:
            continue
        files += 1
        total += len(changes)
        print(f"\n■ {path.relative_to(root)}（{len(changes)}か所）")
        print("\n".join(changes))
        if apply:
            shutil.copy2(path, path.with_name(f"{path.name}.bak-{stamp}"))
            path.write_text(new, encoding="utf-8")

    print(f"\n合計 {files} ファイル・{total} か所")
    if apply:
        print("書き換えました（元のファイルは .bak-" + stamp + "）。管理ツールからサーバーに反映してください。")
    else:
        print("確認だけ行いました。書き換えるには --apply を付けて実行してください。")


if __name__ == "__main__":
    main()
