"""
Grok（xAI API）クライアント
文章生成（X検索つき）・画像生成・動画生成を REST API で呼び出す。
追加ライブラリは不要（requests のみ）。

環境変数:
  XAI_API_KEY            … 必須。https://console.x.ai で発行
  GROK_MODEL             … 文章生成モデル（省略時: grok-latest）
  GROK_REASONING_EFFORT  … 思考の深さ none/low/medium/high（省略時: low。grok-4.20系には送らない）
  GROK_IMAGE_MODEL       … 画像生成モデル（省略時: grok-imagine-image）
  GROK_VIDEO_MODEL       … 動画生成モデル（省略時: grok-imagine-video）
"""
import base64
import mimetypes
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests

API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-latest"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_IMAGE_MODEL = "grok-imagine-image"
DEFAULT_VIDEO_MODEL = "grok-imagine-video"

# grok-4.20 系は reasoning.effort を送るとエラーになる
_NO_REASONING_EFFORT = re.compile(r"^grok-4\.20(-\d{4})?-(non-)?reasoning$")


class GrokError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("XAI_API_KEY", "").strip())


def _headers() -> dict:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        raise GrokError("XAI_API_KEY が設定されていません")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _request(method: str, path: str, timeout: float, **kwargs) -> dict:
    try:
        res = requests.request(method, f"{API_BASE}{path}", headers=_headers(), timeout=timeout, **kwargs)
    except requests.RequestException as e:
        raise GrokError(f"xAI API に接続できません: {e}") from e
    if res.status_code >= 400:
        detail = res.text[:500]
        try:
            err = res.json().get("error")
        except (ValueError, AttributeError):
            err = None
        if isinstance(err, dict):
            err = err.get("message")
        if isinstance(err, str) and err:
            detail = err
        raise GrokError(f"xAI API エラー {res.status_code}: {detail}")
    try:
        return res.json()
    except ValueError as e:
        raise GrokError(f"xAI API の応答がJSONではありません: {res.text[:200]}") from e


# ── 文章生成（Responses API） ─────────────────────────────────

def x_search_tool(from_date: str = None, to_date: str = None,
                  allowed_x_handles: list[str] = None, excluded_x_handles: list[str] = None) -> dict:
    """X（旧Twitter）検索ツールの定義。日付は YYYY-MM-DD"""
    tool = {"type": "x_search"}
    if from_date:
        tool["from_date"] = from_date
    if to_date:
        tool["to_date"] = to_date
    if allowed_x_handles:
        tool["allowed_x_handles"] = allowed_x_handles[:10]
    elif excluded_x_handles:
        tool["excluded_x_handles"] = excluded_x_handles[:10]
    return tool


def chat(
    system: str,
    user: str,
    model: str = None,
    max_output_tokens: int = None,
    tools: list[dict] = None,
    max_turns: int = None,
    include: list[str] = None,
    timeout: float = 90,
) -> tuple[str, list[str]]:
    """
    Grok に文章を書かせる

    Returns:
        (本文テキスト, 引用URLのリスト)
    """
    model = model or os.environ.get("GROK_MODEL", "").strip() or DEFAULT_MODEL
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "store": False,
    }
    if max_output_tokens:
        body["max_output_tokens"] = max_output_tokens
    if tools:
        body["tools"] = tools
    if max_turns:
        body["max_turns"] = max_turns
    if include:
        body["include"] = include
    effort = os.environ.get("GROK_REASONING_EFFORT", "").strip() or DEFAULT_REASONING_EFFORT
    if not _NO_REASONING_EFFORT.match(model):
        body["reasoning"] = {"effort": effort}

    data = _request("POST", "/responses", timeout=timeout, json=body)
    text, citations = parse_response_output(data)
    if not text:
        raise GrokError(f"Grok の応答が空でした（status={data.get('status')}）")
    return text, citations


def parse_response_output(data: dict) -> tuple[str, list[str]]:
    """Responses API の応答から本文と引用URLを取り出す"""
    texts = []
    citations = []
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("text"):
                texts.append(part["text"])
            for ann in part.get("annotations") or []:
                url = ann.get("url")
                if ann.get("type") == "url_citation" and url and url not in citations:
                    citations.append(url)
    if not texts and isinstance(data.get("output_text"), str):
        texts.append(data["output_text"])
    for url in data.get("citations") or []:
        if isinstance(url, str) and url not in citations:
            citations.append(url)
    return "\n".join(texts).strip(), citations


# ── 画像生成 ───────────────────────────────────────────────────

def image_to_data_uri(path: Path) -> str:
    """画像ファイルを API に渡せる data URI にする（PNG/JPEG 以外は PNG に変換）"""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0]
    raw = path.read_bytes()
    if mime not in ("image/png", "image/jpeg"):
        import io
        from PIL import Image
        buf = io.BytesIO()
        with Image.open(path) as img:
            img.save(buf, format="PNG")
        raw, mime = buf.getvalue(), "image/png"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def generate_images(
    prompt: str,
    output_dir: Path,
    n: int = 1,
    aspect_ratio: str = None,
    model: str = None,
    references: list[Path] = None,
    filename_prefix: str = "grok",
    timeout: float = 180,
) -> list[Path]:
    """
    Grok で画像を生成して保存する。references を渡すと参考画像（キャラ等）をもとに編集・生成する

    Returns:
        保存した画像ファイルのパス
    """
    model = model or os.environ.get("GROK_IMAGE_MODEL", "").strip() or DEFAULT_IMAGE_MODEL
    body = {"model": model, "prompt": prompt, "n": max(1, min(10, n)), "response_format": "b64_json"}
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio

    endpoint = "/images/generations"
    if references:
        endpoint = "/images/edits"
        urls = [{"url": image_to_data_uri(p), "type": "image_url"} for p in references]
        if len(urls) == 1:
            body["image"] = urls[0]
        else:
            body["images"] = urls

    data = _request("POST", endpoint, timeout=timeout, json=body)
    items = data.get("data") or []
    if not items:
        raise GrokError("画像が返ってきませんでした（内容がポリシーに抵触した可能性があります）")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    saved = []
    for i, item in enumerate(items, start=1):
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            raw = download_bytes(item["url"])
        else:
            continue
        ext = ".jpg" if raw[:3] == b"\xff\xd8\xff" else ".png"
        path = output_dir / f"{filename_prefix}_{stamp}_{i:02d}{ext}"
        path.write_bytes(raw)
        saved.append(path)
    if not saved:
        raise GrokError("画像データを取り出せませんでした")
    return saved


# ── 動画生成（非同期: 依頼 → 完了待ち → ダウンロード） ─────────────

def submit_video(
    prompt: str,
    duration: int = None,
    aspect_ratio: str = None,
    resolution: str = None,
    image: str = None,
    reference_images: list[str] = None,
    model: str = None,
    extra: dict = None,
    timeout: float = 60,
) -> str:
    """
    動画生成を依頼して request_id を返す

    Args:
        image: 1コマ目にする画像（https URL または data URI）
        reference_images: 登場させたいキャラ等の参考画像（最大7枚。プロンプトで <IMAGE_1> のように参照できる）
        extra: そのまま API に渡す追加パラメータ（generate_audio など）
    """
    model = model or os.environ.get("GROK_VIDEO_MODEL", "").strip() or DEFAULT_VIDEO_MODEL
    body = {"model": model, "prompt": prompt}
    if duration:
        body["duration"] = int(duration)
    if reference_images:
        body["reference_images"] = [{"url": u} for u in reference_images[:7]]
    if image:
        body["image"] = {"url": image}
    else:
        # 画像から作る場合は画像の縦横比に合わせる（指定すると引き伸ばされる）
        if aspect_ratio:
            body["aspect_ratio"] = aspect_ratio
    if resolution:
        body["resolution"] = resolution
    if extra:
        body.update(extra)

    data = _request("POST", "/videos/generations", timeout=timeout, json=body)
    request_id = data.get("request_id")
    if not request_id:
        raise GrokError(f"request_id が返ってきませんでした: {data}")
    return request_id


def get_video(request_id: str, timeout: float = 30) -> dict:
    return _request("GET", f"/videos/{request_id}", timeout=timeout)


def video_url_from_status(status: dict) -> Optional[str]:
    """
    完了していれば動画URLを返す。生成中なら None。失敗なら GrokError
    """
    state = status.get("status")
    video = status.get("video") or {}
    if state == "expired":
        raise GrokError("動画生成の依頼が期限切れになりました")
    if state == "failed":
        err = status.get("error") or {}
        msg = err.get("message") or err.get("code") if isinstance(err, dict) else err
        raise GrokError(f"動画生成に失敗しました: {msg or '理由不明'}")
    if state == "done" or (state is None and video.get("url")):
        if video.get("respect_moderation") is False:
            raise GrokError("動画がコンテンツポリシーによりブロックされました。プロンプトを変えてください")
        url = video.get("url") or (video.get("file_output") or {}).get("public_url")
        if not url:
            raise GrokError("動画生成は完了しましたがURLが返ってきませんでした")
        return url
    return None


def wait_video(request_id: str, poll_interval: float = 5, timeout: float = 900) -> str:
    """動画が完成するまで待って URL を返す"""
    deadline = time.monotonic() + timeout
    while True:
        url = video_url_from_status(get_video(request_id))
        if url:
            return url
        if time.monotonic() > deadline:
            raise GrokError(f"動画生成が {int(timeout)} 秒以内に終わりませんでした（request_id={request_id}）")
        time.sleep(poll_interval)


def download_bytes(url: str, timeout: float = 120) -> bytes:
    try:
        res = requests.get(url, timeout=timeout)
        res.raise_for_status()
    except requests.RequestException as e:
        raise GrokError(f"ダウンロードに失敗しました: {e}") from e
    return res.content


def download(url: str, path: Path, timeout: float = 300) -> Path:
    """生成物の URL は一時的なので、完成したらすぐ保存する"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=timeout) as res:
            res.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in res.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
    except requests.RequestException as e:
        tmp.unlink(missing_ok=True)
        raise GrokError(f"ダウンロードに失敗しました: {e}") from e
    tmp.replace(path)
    return path
