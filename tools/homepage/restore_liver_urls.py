#!/usr/bin/env python3
"""ライバー個別ページのURL（英字表記 en）を前のURLに戻す（Mac で実行する1回きりのスクリプト）。

使い方:
    python3 restore_liver_urls.py <eternaldct-new-site のパス>          # 確認だけ（何も書き換えない）
    python3 restore_liver_urls.py <eternaldct-new-site のパス> --apply  # 書き換え＋再生成＋.htaccess追記

やること:
  1. 同じフォルダの livers-data.practical-hamilton.js
     （ETERNAL- の claude/practical-hamilton-a8o004 ブランチのコピー）と Mac の js/livers-data.js を比べる
  2. 違いが下の11人の en だけか確認。ほかの違いは表示するだけで上書きしない
  3. --apply のとき: 11人の en だけ直す → seo-pdca/build_livers.py で再生成 → liver-<en>.html の確認
     → .htaccess の末尾に301リダイレクトを追記（同じ目印がすでにあれば追記しない）
  書き換える前に *.bak-日時 のバックアップを作る。サーバーへの反映は管理ツールから手で行う。
"""
import datetime
import difflib
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE / "livers-data.practical-hamilton.js"

EN = {
    "しー": "shi",
    "なっしーpart2": "nasshipart2",
    "みぃみん": "miimin",
    "ココ": "koko",
    "あじゃる": "ajaru",
    "ひすみや・ライバー.ド.ライバー": "hisumiya-raiba-do-raiba",
    "ジャン": "jan",
    "梅ちゃん": "ume-chan",
    "ぴかぴか暴走マグマもちちゃん": "pikapika-bousou-magma-mochi-chan",
    "月影朱華": "tsukikage-shuka",
    "柚華ゆずまる": "yuzuka-yuzumaru",
}

REDIRECTS = [
    ("liver-shii", "liver-shi"),
    ("liver-nasshi", "liver-nasshipart2"),
    ("liver-mimin", "liver-miimin"),
    ("liver-coco", "liver-koko"),
    ("liver-ajyaru", "liver-ajaru"),
    ("liver-hisumiya", "liver-hisumiya-raiba-do-raiba"),
    ("liver-jyan", "liver-jan"),
]
MARKER = "# --- ライバー個別ページ 旧URL→今までのURL (2026-10) ---"

PAIR = re.compile(r'(name:\s*"([^"]*)",\s*\n\s*en:\s*")([^"]*)(")')


def set_en(text):
    """11人の en だけ EN の値にした文字列と、見つからなかった名前を返す。"""
    found = set()

    def repl(m):
        name = m.group(2)
        if name in EN:
            found.add(name)
            return m.group(1) + EN[name] + m.group(4)
        return m.group(0)

    return PAIR.sub(repl, text), sorted(set(EN) - found)


def backup(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    dst = path.with_name(path.name + ".bak-" + stamp)
    shutil.copy2(path, dst)
    return dst


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)
    site = Path(args[0]).expanduser().resolve()
    js = site / "js" / "livers-data.js"
    if not js.exists():
        sys.exit(f"見つかりません: {js}")

    mac = js.read_text(encoding="utf-8")
    ref = REF.read_text(encoding="utf-8")
    fixed, missing = set_en(mac)
    if missing:
        sys.exit("Mac の livers-data.js に見つからない名前があります（中止）: " + ", ".join(missing))

    # --- 手順2: 11人の en 以外の違い ---
    print("== 11人の en（Mac → 直したあと）==")
    for name, en in EN.items():
        cur = dict((m.group(2), m.group(3)) for m in PAIR.finditer(mac))[name]
        print(f"  {name}: {cur} → {en}" + ("" if cur != en else "（変更なし）"))
    other = list(difflib.unified_diff(ref.splitlines(), fixed.splitlines(),
                                      "ブランチ", "Mac(11人のen修正後)", lineterm="", n=1))
    if other:
        print("\n⚠ 11人の en 以外にも違いがあります（Mac側を残し、上書きしません）:")
        print("\n".join(other))
    else:
        print("\n✓ 違いは11人の en だけでした。")

    if not apply:
        print("\n確認だけ行いました。書き換えるには --apply を付けて実行してください。")
        return

    # --- 11人の en だけ直す ---
    if fixed != mac:
        print("\nバックアップ:", backup(js))
        js.write_text(fixed, encoding="utf-8")
        print("書き換えました:", js)

    # --- 手順3: 再生成 ---
    build = next((p for p in (site / "seo-pdca" / "build_livers.py",
                              site.parent / "seo-pdca" / "build_livers.py") if p.exists()), None)
    if build is None:
        print("\n⚠ seo-pdca/build_livers.py が見つかりません。手で再生成してください。")
    else:
        print(f"\n再生成: python3 {build}（作業フォルダ {build.parent.parent}）")
        r = subprocess.run([sys.executable, str(build)], cwd=build.parent.parent)
        if r.returncode != 0:
            sys.exit(f"build_livers.py がエラーで終了しました（{r.returncode}）。.htaccess は触っていません。")
    ng = [en for en in EN.values() if not list(site.rglob(f"liver-{en}.html"))]
    for en in EN.values():
        print(("  ✓ " if en not in ng else "  ✗ ") + f"liver-{en}.html")
    if ng:
        sys.exit("できていないページがあります。.htaccess は触っていません。")

    # --- 手順5: .htaccess の末尾に追記（上書きしない）---
    ht = site / ".htaccess"
    cur = ht.read_text(encoding="utf-8") if ht.exists() else ""
    if MARKER in cur:
        print("\n.htaccess には追記済みです（何もしません）。")
    else:
        if ht.exists():
            print("\nバックアップ:", backup(ht))
        lines = ["", MARKER]
        lines += [f"RedirectMatch 301 ^/{old}(\\.html)?$ /{new}.html" for old, new in REDIRECTS]
        lines += ["# --- ここまで ---", ""]
        with ht.open("a", encoding="utf-8") as f:
            if cur and not cur.endswith("\n"):
                f.write("\n")
            f.write("\n".join(lines))
        print("追記しました:", ht)
        print("\n".join(lines))

    print("\n次: 管理ツールからサーバーに反映してください（.htaccess も含めて）。")


if __name__ == "__main__":
    main()
