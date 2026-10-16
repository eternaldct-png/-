"""plan.yaml の各カットを Grok Imagine（xAI API）で「画像 → 動画」にする。

使い方（Mac のターミナル / Codex から）:
    export XAI_API_KEY=xai-...            # Render の XAI_API_KEY と同じキー
    python3 grok_video.py work/<id>/plan.yaml            # まだ動画が無いカットだけ生成
    python3 grok_video.py work/<id>/plan.yaml --only s2  # 1カットだけ作り直す（既存は上書き）
    python3 grok_video.py work/<id>/plan.yaml --dry-run  # 送信内容だけ表示（課金なし）

注意:
- xAI API は従量課金（SuperGrok のサブスクとは別会計）。1カット数十円〜が目安。
- エンドポイントやフィールド名は 2026-10 時点で公式ドキュメントを確認できていない。
  4xx が返ったら https://docs.x.ai の Video Generation ページを見て、下の定数か
  環境変数（XAI_VIDEO_URL / XAI_VIDEO_STATUS_URL / XAI_VIDEO_MODEL）を直すこと。
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests
import yaml

VIDEO_URL = os.environ.get("XAI_VIDEO_URL", "https://api.x.ai/v1/videos/generations")
STATUS_URL = os.environ.get("XAI_VIDEO_STATUS_URL", "https://api.x.ai/v1/videos/{id}")
MODEL = os.environ.get("XAI_VIDEO_MODEL", "grok-imagine-video")
DONE = {"done", "completed", "succeeded", "success"}
FAILED = {"failed", "error", "cancelled", "canceled", "expired"}


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def build_payload(shot, base_dir):
    payload = {
        "model": MODEL,
        "prompt": shot["video_prompt"].strip(),
        "duration": int(shot.get("duration", 6)),
        "aspect_ratio": "9:16",
        "resolution": "720p",
    }
    if shot.get("image"):
        payload["image"] = {"url": data_uri(base_dir / shot["image"])}
    return payload


def find_video_url(body):
    """レスポンスの形が多少違っても動画URLを探す。"""
    for key in ("video", "result", "output"):
        v = body.get(key)
        if isinstance(v, dict) and v.get("url"):
            return v["url"]
        if isinstance(v, str) and v.startswith("http"):
            return v
    if body.get("url"):
        return body["url"]
    data = body.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0].get("url")
    return None


def generate(shot, base_dir, key, timeout=900):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    r = requests.post(VIDEO_URL, headers=headers, json=build_payload(shot, base_dir), timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"{shot['id']}: 生成リクエスト失敗 {r.status_code}: {r.text[:500]}")
    body = r.json()
    url = find_video_url(body)
    req_id = body.get("request_id") or body.get("id")
    started = time.time()
    while not url:
        if not req_id:
            raise RuntimeError(f"{shot['id']}: request_id も動画URLも無い応答: {json.dumps(body)[:500]}")
        if time.time() - started > timeout:
            raise TimeoutError(f"{shot['id']}: {timeout}秒待っても完成しない")
        time.sleep(8)
        s = requests.get(STATUS_URL.format(id=req_id), headers=headers, timeout=60)
        if s.status_code >= 400:
            raise RuntimeError(f"{shot['id']}: 状態確認失敗 {s.status_code}: {s.text[:500]}")
        body = s.json()
        status = str(body.get("status", "")).lower()
        if status in FAILED:
            raise RuntimeError(f"{shot['id']}: 生成失敗: {json.dumps(body)[:500]}")
        url = find_video_url(body) if (status in DONE or not status) else None
        print(f"  {shot['id']}: {status or '...'} ({int(time.time() - started)}s)", flush=True)

    out = base_dir / shot["video"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as dl:
        dl.raise_for_status()
        with open(out, "wb") as f:
            for chunk in dl.iter_content(1 << 16):
                f.write(chunk)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--only", help="このカットidだけ生成（既存ファイルは上書き）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    plan_path = Path(args.plan)
    base_dir = plan_path.parent
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    shots = [s for s in plan["shots"] if not args.only or s["id"] == args.only]
    if not shots:
        sys.exit(f"カットが見つからない: {args.only}")

    key = os.environ.get("XAI_API_KEY")
    if not key and not args.dry_run:
        sys.exit("XAI_API_KEY が未設定")

    for shot in shots:
        out = base_dir / shot["video"]
        if out.exists() and not args.only:
            print(f"skip {shot['id']}（{out} がある）")
            continue
        if shot.get("image") and not (base_dir / shot["image"]).exists():
            sys.exit(f"{shot['id']}: 画像 {shot['image']} が無い（先に Codex で生成する）")
        if args.dry_run:
            p = build_payload(shot, base_dir)
            if "image" in p:
                p["image"] = {"url": p["image"]["url"][:40] + "..."}
            print(json.dumps(p, ensure_ascii=False, indent=2))
            continue
        print(f"generate {shot['id']} ({shot.get('duration', 6)}s)", flush=True)
        print("  ->", generate(shot, base_dir, key))


if __name__ == "__main__":
    main()
