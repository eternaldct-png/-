# テスト計画: コマドリ

自動: `python3 -m pytest tests/test_anime_studio.py`（27件・API と処理）、`bash tools/anime_studio/e2e/run.sh`（14件・ブラウザ）。
E2E はコンソールのエラーと 5xx で失敗する。文章AIは「AIなし」、声なしで動かす（AI の部分は偽の Claude で pytest が確認）。
axe（アクセシビリティの自動検査）は未導入。ラベル・ロールでの操作（E2E のセレクタ）と、キーボードでのフォーカス確認で代えている。

| ID | 内容 | 方法 | 結果 |
| --- | --- | --- | --- |
| F01-H1 | アイデア → 脚本 → キャラ（画像入れる）→ 場面（背景入れる）→ 絵コンテ → 絵 → 音 → 書き出し → ダウンロード | E2E / pytest `test_full_flow_to_mp4` | pass |
| F01-E1 | 空のアイデア | E2E / pytest | pass |
| F01-E2 | 「作りはじめる」の二度押しで作品が2本できない | E2E | pass |
| F01-E3 | スマホ幅 390px で横にはみ出さない | E2E | pass |
| F01-E4 | キーボードでフォーカスが当たる | E2E | pass |
| F01-E5 | 8000文字超・絵文字・アクセント・おかしな縦横比/尺 | pytest `test_create_project_validation` | pass |
| F01-E6 | 作っている途中にもう一度押す | pytest `test_double_generate_is_refused` | pass |
| F01-E7 | 絵が無いカットがあるまま書き出す → 理由つきで失敗 | pytest | pass |
| F01-E8 | アプリが途中で止まった → 再起動で「失敗」に戻り、やり直せる | pytest `test_recover_interrupted_jobs` | pass |
| F01-N1 | 他のサイト（ヘッダーなし）からの書き込み・別の Host | E2E / pytest | pass |
| F01-N2 | `/files` で作品フォルダの外を読む（`..`） | pytest | pass |
| F02-H1 | おまかせで書き出しまで自動 | E2E / pytest | pass |
| F03-H1 | 脚本を直すと後ろの段階が「古い」 | E2E / pytest | pass |
| F03-E1 | リロードしても直した内容が残る | E2E | pass |
| F04-H1 | カットを足す・並べ替え・消す | E2E / pytest | pass |
| F04-E1 | 長すぎるセリフの警告・合計の尺の警告 | E2E / pytest | pass |
| F04-E2 | 並べ替えの一覧が合わない・秒に文字・知らないカメラ | pytest | pass |
| F04-E3 | キャラの名前を変えるとカットの名前も変わる | pytest | pass |
| F05-H1 | キャラ帳に保存 → 新しい作品に出演 → キャラ帳から消しても作品側は残る | E2E / pytest | pass |
| F06-H1 | 自分の絵に差し替え → 絵を作り直しても残る | pytest | pass |
| F06-E1 | 画像でないファイル・拡張子違い | E2E / pytest | pass |
| F07-H1 | 曲を入れて、カットの秒数を曲の長さに合わせる | pytest `test_bgm_upload_and_fit` | pass |
| F07-E1 | 曲なしで合わせる・音でないファイル | pytest | pass |
| AI-1 | Claude（偽）の返事を正規化（知らないキャラ・カメラを落とす、秒を尺に合わせる） | pytest | pass |
| AI-2 | 壊れた返事 → 1回やり直して、だめなら理由つきで失敗 | pytest | pass |
| AI-3 | 「おまかせ」設定で Claude を勝手に使わない | pytest | pass |
| $-1 | fal.ai の月の上限を超える前に、APIを呼ばずに止める | pytest | pass |

## 手で確かめること（このクラウド環境ではできない）

- [ ] Mac で `start.command` をダブルクリックして起動できる
- [ ] Mac の読み上げ（say・Kyoko）で声が付く。キャラごとに声を変えられる
- [ ] Ollama を入れた状態で「おまかせ」が端末内AIを選ぶ・脚本の質
- [ ] Claude を選んだときの脚本・絵コンテの質
- [ ] fal.ai（画像・動画）を選んだとき。**モデル名・単価は fal.ai のページで確かめてから**
- [ ] ヒラギノで字幕が読みやすいか
