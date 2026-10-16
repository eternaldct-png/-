# shorts_pipeline — AIショート動画の制作パイプライン

TikTok / YouTube ショート / Instagram リール向けの縦型動画を、Mac 上の **Codex アプリ**に
「企画 → 画像 → 動画 → 編集 → 検証 → 修正」まで作らせるための道具一式。投稿は人が確認してから行う。

| 工程 | 担当 | 費用 |
|---|---|---|
| 企画・台本 | Codex | ChatGPT サブスク内 |
| 画像 | Codex の画像生成 | ChatGPT サブスク内 |
| 動画（画像→動画） | Grok Imagine（`grok_video.py` / xAI API） | 従量課金（API はサブスクと別会計） |
| 編集の下地 | `assemble.py`（ffmpeg） | 無料 |
| 仕上げ | CapCut デスクトップ版を Codex が画面操作（computer use） | CapCut のプラン次第 |
| 検証 | `qc.py`（機械チェック）＋ Codex の目視採点 | 無料 |
| 投稿 | 人（AI生成ラベルをオン） | — |

Codex への作業手順は [`AGENTS.md`](AGENTS.md)。Codex がこのフォルダで作業すると自動で読み込まれる。

## Mac の初期設定（1回だけ）
1. Homebrew で `brew install ffmpeg`、`pip3 install pyyaml requests`
2. このリポジトリを Mac に clone し、`python3 tools/motion_render/fetch_fonts.py`（テロップ用フォント）
3. `~/.zshrc` に `export XAI_API_KEY=xai-...`（Render の `XAI_API_KEY` と同じ値）
4. Codex アプリに ChatGPT アカウントでログインし、このリポジトリを開く
5. Codex の設定で **Computer Use** プラグインを入れ、画面収録とアクセシビリティを許可し、CapCut を「常に許可」にする
6. CapCut デスクトップ版を入れてログインしておく

## 1本作るとき（Codex に送る文）
```
tools/shorts_pipeline/AGENTS.md の手順で、ショート動画を1本作って。
目的: オーディション応募を増やす / ターゲット: 歌が好きな20〜30代
キャラ: tools/motion_render/chars/c1.webp
```

## 手動で動かすとき
```bash
cd tools/shorts_pipeline
mkdir -p work/<id> && cp plan_template.yaml work/<id>/plan.yaml   # 中身を埋める
python3 grok_video.py work/<id>/plan.yaml --dry-run
python3 grok_video.py work/<id>/plan.yaml
python3 assemble.py work/<id>/plan.yaml
python3 qc.py work/<id>/out/final.mp4
```

## わかっている制限
- `grok_video.py` のエンドポイント・フィールド名は公式ドキュメントで確認できていない（2026-10 時点）。エラーになったら docs.x.ai を見て直す。
- CapCut の画面操作は、CapCut のアップデートで画面が変わると失敗することがある。その場合は `out/final.mp4`（ffmpeg 版）を使う。
- TikTok の投稿 API は、TikTok の審査を通っていないアプリから投稿すると非公開になる。自動投稿はしない。
