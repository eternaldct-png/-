"""Google Calendar sync (app → Google Calendar, one-way via service account).

Setup:
  1. Google Cloud Console でサービスアカウントを作成し JSON キーをダウンロード
  2. 自分のGoogleカレンダーをそのサービスアカウントのメールアドレスと共有（編集権限）
  3. Render に環境変数を設定:
       GOOGLE_SERVICE_ACCOUNT_JSON = <JSON キーの内容をそのまま>
       GOOGLE_CALENDAR_ID          = <カレンダーID（省略時: primary）>
"""
import os
import json


def _get_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return None

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        return None

    try:
        sa_info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except Exception:
        return None


def _calendar_id():
    return os.environ.get("GOOGLE_CALENDAR_ID", "primary")


def _gcal_dt(dt_str, all_day=False):
    if all_day:
        return {"date": dt_str[:10]}
    # datetime 文字列にタイムゾーン情報がなければ JST を付与
    if dt_str and "+" not in dt_str and not dt_str.endswith("Z"):
        dt_str = dt_str + "+09:00"
    return {"dateTime": dt_str, "timeZone": "Asia/Tokyo"}


_COLOR_MAP = {
    "live": "11",     # Tomato (赤)
    "goods": "5",     # Banana (黄)
    "general": "9",   # Blueberry (青)
}


def sync_create(event):
    """アプリのイベントをGoogleカレンダーに作成。google event id を返す（失敗時 None）。"""
    service = _get_service()
    if not service:
        return None
    all_day = event.get("all_day", False)
    body = {
        "summary": event.get("title", "(無題)"),
        "description": event.get("description", ""),
        "start": _gcal_dt(event["start_datetime"], all_day),
        "end": _gcal_dt(event.get("end_datetime") or event["start_datetime"], all_day),
        "colorId": _COLOR_MAP.get(event.get("event_type", "general"), "9"),
    }
    if event.get("platform"):
        body["description"] = f"[{event['platform']}] {body['description']}".strip(" []")
    try:
        result = service.events().insert(calendarId=_calendar_id(), body=body).execute()
        return result.get("id")
    except Exception:
        return None


def sync_update(google_event_id, event):
    """Googleカレンダーのイベントを更新。"""
    service = _get_service()
    if not service or not google_event_id:
        return False
    all_day = event.get("all_day", False)
    body = {
        "summary": event.get("title", "(無題)"),
        "description": event.get("description", ""),
        "start": _gcal_dt(event["start_datetime"], all_day),
        "end": _gcal_dt(event.get("end_datetime") or event["start_datetime"], all_day),
        "colorId": _COLOR_MAP.get(event.get("event_type", "general"), "9"),
    }
    if event.get("platform"):
        body["description"] = f"[{event['platform']}] {body['description']}".strip(" []")
    try:
        service.events().update(
            calendarId=_calendar_id(), eventId=google_event_id, body=body
        ).execute()
        return True
    except Exception:
        return False


def sync_delete(google_event_id):
    """Googleカレンダーのイベントを削除。"""
    service = _get_service()
    if not service or not google_event_id:
        return False
    try:
        service.events().delete(
            calendarId=_calendar_id(), eventId=google_event_id
        ).execute()
        return True
    except Exception:
        return False
