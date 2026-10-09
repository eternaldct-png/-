"""レンダラーが使うフォント（Google Fonts・OFL）を fonts/ にダウンロードし、fonts.css を作る。

使い方: python3 fetch_fonts.py
フォントは容量が大きいのでリポジトリには含めない（.gitignore 済み）。
"""
import re
import urllib.request
from pathlib import Path

FAMILIES = [
    "Noto+Sans+JP:wght@500;700;900",
    "M+PLUS+Rounded+1c:wght@800",
    "Montserrat:wght@700;800;900",
    "Zen+Maru+Gothic:wght@700",
    "Dela+Gothic+One",
    "Shippori+Mincho:wght@800",
]
FONT_DIR = Path(__file__).resolve().parent / "fonts"


def main():
    FONT_DIR.mkdir(exist_ok=True)
    rules = []
    for fam in FAMILIES:
        # User-Agent を付けないと分割されていない TTF の URL が返ってくる
        css = urllib.request.urlopen(f"https://fonts.googleapis.com/css2?family={fam}").read().decode()
        for block in re.findall(r"@font-face\s*\{(.*?)\}", css, re.S):
            name = re.search(r"font-family: '([^']+)'", block).group(1)
            weight = re.search(r"font-weight: (\d+)", block).group(1)
            url = re.search(r"url\((.*?)\)", block).group(1)
            filename = f"{name.replace(' ', '')}-{weight}.ttf"
            path = FONT_DIR / filename
            if not path.exists():
                print("download", filename)
                path.write_bytes(urllib.request.urlopen(url).read())
            rules.append(f"@font-face {{ font-family: '{name}'; font-weight: {weight}; src: url('{filename}') format('truetype'); }}")
    (FONT_DIR / "fonts.css").write_text("\n".join(rules) + "\n", encoding="utf-8")
    print(f"{len(rules)} fonts ready in {FONT_DIR}")


if __name__ == "__main__":
    main()
