"""ツヅリ（自分用のショートアニメ制作ツール）を起動する。

    python3 tools/anime_studio/run.py            # http://127.0.0.1:5056
    python3 tools/anime_studio/run.py --port 5060
"""
import argparse
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # リポジトリの直下を import できるようにする

from tools.anime_studio.app import create_app, default_data_dir  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="ツヅリ — アイデアからショートアニメを作る（自分専用）")
    p.add_argument("--port", type=int, default=5056)
    p.add_argument("--data", default=None, help="データの保存先（既定: ~/Tsuzuri）")
    p.add_argument("--no-browser", action="store_true", help="起動時にブラウザを開かない")
    args = p.parse_args()
    app = create_app(args.data)
    url = f"http://127.0.0.1:{args.port}"
    print(f"ツヅリを起動しました: {url}")
    print(f"データの保存先: {args.data or default_data_dir()}")
    print("止めるときは Ctrl + C")
    if not args.no_browser:
        webbrowser.open(url)
    # 127.0.0.1 だけで待ち受ける（同じWi-Fiの他の端末からは開けない）
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
