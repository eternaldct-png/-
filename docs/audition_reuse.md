# オーディションフォームの受付切り替え

`/audition` の応募フォームは、次回のイベントでも再利用できるように
`src/web_app.py` の `AUDITION_FORM_TEMPLATE_HTML` として保存しています。

## 現在の状態

- `AUDITION_STATUS=closed`
- `/audition` は「受付は終了しました」画面を表示
- `/api/audition/submit` は HTTP 410 を返し、新しい応募を保存しない
- 過去の応募データと `/audition/admin` はそのまま保持

## 次回の受付を開始する

1. Render の `kazuto-post-generator` サービスを開く
2. Environment の `AUDITION_STATUS` を `open` に変更する
3. 必要に応じて `AUDITION_FORM_TEMPLATE_HTML` のタイトル・設問・案内文を編集する
4. `/audition` でフォームが表示され、テスト送信できることを確認する

`open` のほか、`true`、`1`、`on` でも受付中として扱います。
それ以外の値、または環境変数が未設定の場合は安全側で受付終了になります。

## 受付を終了する

Render の `AUDITION_STATUS` を `closed` に戻します。
画面表示だけでなく送信APIも停止するため、古い画面を開いたままの利用者からも新規応募は登録されません。
