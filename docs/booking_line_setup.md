# 予約アプリ LINE通知・リマインド セットアップ手順

予約アプリ（`src/booking_app.py`）に LINE 通知を追加するための手順。
一度設定すれば、予約確定・キャンセル時に担当者のLINEへ通知が届き、
開始前（デフォルト24時間前）にリマインドも届く。

---

## 1. LINE公式アカウント（Messaging API）を作る

1. https://developers.line.biz/console/ にログイン（通常のLINEアカウントでOK）
2. プロバイダーを作成（名前は「ETERNAL d.c.t」など何でもよい）
3. 「Messaging API チャネル」を作成
   - チャネル名: 「ETERNAL 面談予約」など（友だち追加時に表示される名前）
4. 作成後、**LINE Official Account Manager**（https://manager.line.biz/）側で
   Messaging API の利用を有効化する
5. 以下の2つを控える:
   - **チャネルシークレット**（チャネル基本設定タブ）
   - **チャネルアクセストークン（長期）**（Messaging API設定タブで発行）

## 2. Render に環境変数を設定

`eternal-interview-booking` サービスの Environment に追加:

| 変数名 | 値 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | 手順1で発行したチャネルアクセストークン |
| `LINE_CHANNEL_SECRET` | チャネルシークレット |
| `REMINDER_SECRET` | 任意のランダム文字列（リマインドcron用） |

## 3. Webhook URL を設定

LINE Developers コンソール → Messaging API設定タブ:

- Webhook URL: `https://<予約アプリのURL>/line/webhook`
  （例: `https://eternal-interview-booking.onrender.com/line/webhook`）
- 「Webhookの利用」を **ON**
- 「応答メッセージ」（自動応答）は Official Account Manager 側で **OFF** にする
  （ONだとアプリの返信と二重になる）

## 4. メンバーが連携する

1. 公式アカウントのQRコード（Messaging API設定タブにある）を各メンバーに共有
2. 各メンバーが友だち追加し、トークで **「連携 自分の名前」** と送る
   - 例: 「連携 あまりん」「連携 kazuto」
3. 全員分の予約通知を受け取りたい人（管理者）は **「連携 admin」** と送る
4. 通知をやめたいときは **「解除」** と送る

連携状況は `/availability` ページ（ログイン後）の「💬 LINE通知」カードで確認できる。

## 5. リマインドの定期実行を設定

リマインドは `/tasks/send-reminders` を定期的に叩くことで送信される。
無料でやるなら https://cron-job.org を使う:

1. cron-job.org にアカウント登録
2. 新規cronジョブ作成:
   - URL: `https://<予約アプリのURL>/tasks/send-reminders?token=<REMINDER_SECRETの値>`
   - 実行間隔: **1時間ごと**
3. 保存すると、開始24時間前を過ぎた予約に1回だけリマインドが送られる
   （同じ予約に二重送信はされない）

リマインドを送るタイミングは `persona/booking_config.yaml` の
`line.reminder_hours_before` で変更できる（デフォルト: 24時間前）。

---

## 外販するとき（別の事業者向けにデプロイする）

コード変更は不要。以下だけで別ブランドの予約ツールになる:

1. リポジトリを複製（または同リポジトリから別サービスとしてデプロイ）
2. `persona/booking_config.yaml` を書き換える:
   ```yaml
   site:
     title: "サロン○○ 予約"
     subtitle: "施術のご予約"
     icon: "💅"
     event_label: "施術"    # 通知文・カレンダーにも反映される
   booking:
     start_hour: 10
     end_hour: 19
     days_ahead: 14
   members:
     - slug: staff-a
       name: スタッフA
   line:
     reminder_hours_before: 3
   ```
3. Render で新サービスとしてデプロイし、環境変数を設定
   （`FLASK_SECRET_KEY` / `AVAILABILITY_PASSWORD` / `DATABASE_URL` /
   LINE系3つ。Googleカレンダー同期が必要なら Google系2つも）
4. その事業者用のLINE公式アカウントを手順1〜5で作成・設定

提供できる価値（営業トーク用）:
- 予約ページはログイン不要・スマホ最適化済み
- 予約が入った瞬間に担当者のLINEに通知
- すっぽかし防止のLINEリマインド付き
- Googleカレンダー自動同期
- 月額固定費: Render無料枠 + LINE公式アカウント無料プラン（月200通まで無料）で0円運用可能
