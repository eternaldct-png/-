"""LINE Messaging API クライアント（軽量・requests のみ使用）

予約アプリの通知・リマインド送信と、Webhook の署名検証を担当する。

Setup:
  1. https://developers.line.biz/ でプロバイダーと Messaging API チャネルを作成
  2. チャネルアクセストークン（長期）を発行
  3. Render に環境変数を設定:
       LINE_CHANNEL_ACCESS_TOKEN = <チャネルアクセストークン>
       LINE_CHANNEL_SECRET       = <チャネルシークレット>
  4. LINE Developers コンソールで Webhook URL を
       https://<アプリのURL>/line/webhook
     に設定し、Webhook の利用を ON にする
"""
import os
import sys
import hmac
import base64
import hashlib

import requests

API_BASE = "https://api.line.me/v2/bot"
TIMEOUT = 10


def is_configured():
    """チャネルアクセストークンが設定されていれば True"""
    return bool(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""))


def _headers():
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _log(msg):
    print(f"[line_messaging] {msg}", file=sys.stderr, flush=True)


def push_text(user_id, text):
    """指定ユーザーにテキストメッセージを push 送信。成功で True。"""
    if not is_configured():
        _log("push skipped: LINE_CHANNEL_ACCESS_TOKEN が未設定")
        return False
    if not user_id:
        return False
    try:
        r = requests.post(
            f"{API_BASE}/message/push",
            headers=_headers(),
            json={"to": user_id, "messages": [{"type": "text", "text": text[:4900]}]},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            _log(f"push failed: status={r.status_code} body={r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        _log(f"push error: {e}")
        return False


def reply_text(reply_token, text):
    """Webhook の replyToken に対してテキストで返信。成功で True。"""
    if not is_configured():
        _log("reply skipped: LINE_CHANNEL_ACCESS_TOKEN が未設定")
        return False
    if not reply_token:
        return False
    try:
        r = requests.post(
            f"{API_BASE}/message/reply",
            headers=_headers(),
            json={"replyToken": reply_token, "messages": [{"type": "text", "text": text[:4900]}]},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            _log(f"reply failed: status={r.status_code} body={r.text[:300]}")
        else:
            _log("reply ok")
        return r.status_code == 200
    except Exception as e:
        _log(f"reply error: {e}")
        return False


def verify_signature(body: bytes, signature: str) -> bool:
    """Webhook リクエストの X-Line-Signature を検証する"""
    secret = os.environ.get("LINE_CHANNEL_SECRET", "")
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)
