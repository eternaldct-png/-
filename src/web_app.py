"""
投稿管理ダッシュボード — スマホ対応Webアプリ
URLを開くだけでキューの確認・編集・即時投稿ができる

機能:
  - 未投稿/投稿済タブ表示
  - 手動で投稿文を追加（ボトムシート）
  - テキスト編集（リアルタイム文字数カウント）
  - スケジュール時刻変更
  - X への即時投稿
  - プラットフォームフィルタ（X / Instagram / note）
  - テキストコピー
  - テーマ指定 + 件数指定で生成（1 / 3 / 5件）
"""
import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, Response

sys.path.insert(0, str(Path(__file__).parent))

JST = ZoneInfo("Asia/Tokyo")
QUEUE_PATH = Path("posts/queue.json")
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "kazuto")

app = Flask(__name__)


# ── 認証 ─────────────────────────────────────────────────────

def _check_auth() -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        _, pwd = decoded.split(":", 1)
        return pwd == WEB_PASSWORD
    except Exception:
        return False


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _check_auth():
            return Response(
                "認証が必要です",
                401,
                {"WWW-Authenticate": 'Basic realm="kazuto投稿管理"'},
            )
        return f(*args, **kwargs)
    return decorated


# ── キュー操作 ────────────────────────────────────────────────

def _load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        return []
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_queue(queue: list[dict]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def _find_index(queue: list[dict], item_id: str) -> int:
    for i, item in enumerate(queue):
        if item.get("created_at") == item_id:
            return i
    return -1


# ── API エンドポイント ─────────────────────────────────────────

@app.route("/api/queue")
@require_auth
def api_queue():
    """全キューを返す（_id = created_at を付与）"""
    queue = _load_queue()
    for item in queue:
        item["_id"] = item.get("created_at", "")
    return jsonify(queue)


@app.route("/api/add", methods=["POST"])
@require_auth
def api_add():
    """投稿文を手動でキューに追加する"""
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    platform = data.get("platform", "x")
    scheduled_for = data.get("scheduled_for", "")

    if not text:
        return jsonify({"error": "テキストが空です"}), 400

    now = datetime.now(JST)
    if not scheduled_for:
        # デフォルト: 1時間後
        scheduled_for = (now + timedelta(hours=1)).isoformat()

    entry = {
        "text": text,
        "platform": platform,
        "scheduled_for": scheduled_for,
        "status": "pending",
        "created_at": now.isoformat(),
        "posted_at": None,
        "manually_added": True,
    }
    queue = _load_queue()
    queue.append(entry)
    _save_queue(queue)
    entry["_id"] = entry["created_at"]
    return jsonify({"ok": True, "item": entry})


@app.route("/api/edit", methods=["POST"])
@require_auth
def api_edit():
    """投稿テキストを編集する"""
    data = request.get_json(force=True)
    item_id = data.get("id", "")
    new_text = data.get("text", "").strip()

    queue = _load_queue()
    idx = _find_index(queue, item_id)
    if idx == -1:
        return jsonify({"error": "投稿が見つかりません"}), 404

    queue[idx]["text"] = new_text
    queue[idx]["edited_at"] = datetime.now(JST).isoformat()
    _save_queue(queue)
    return jsonify({"ok": True, "length": len(new_text)})


@app.route("/api/reschedule", methods=["POST"])
@require_auth
def api_reschedule():
    """投稿のスケジュール時刻を変更する"""
    data = request.get_json(force=True)
    item_id = data.get("id", "")
    new_time = data.get("scheduled_for", "")

    if not new_time:
        return jsonify({"error": "時刻が指定されていません"}), 400

    queue = _load_queue()
    idx = _find_index(queue, item_id)
    if idx == -1:
        return jsonify({"error": "投稿が見つかりません"}), 404

    queue[idx]["scheduled_for"] = new_time
    # 一度 expired になっていた場合は pending に戻す
    if queue[idx].get("status") == "expired":
        queue[idx]["status"] = "pending"
    _save_queue(queue)
    return jsonify({"ok": True})


@app.route("/api/delete", methods=["POST"])
@require_auth
def api_delete():
    """投稿をキューから削除する"""
    data = request.get_json(force=True)
    item_id = data.get("id", "")
    queue = _load_queue()
    before = len(queue)
    queue = [item for item in queue if item.get("created_at") != item_id]
    _save_queue(queue)
    return jsonify({"ok": True, "deleted": before - len(queue)})


@app.route("/api/post", methods=["POST"])
@require_auth
def api_post():
    """指定の投稿を X に今すぐ投稿する"""
    data = request.get_json(force=True)
    item_id = data.get("id", "")
    queue = _load_queue()
    idx = _find_index(queue, item_id)
    if idx == -1:
        return jsonify({"error": "投稿が見つかりません"}), 404

    item = queue[idx]
    try:
        from platforms.x import XAdapter
        adapter = XAdapter()
        result = adapter.post({"text": item["text"]}, dry_run=False)
        pid = result.get("platform_id", "")
        if pid and pid != "skipped_duplicate":
            queue[idx]["status"] = "posted"
            queue[idx]["posted_at"] = datetime.now(JST).isoformat()
            _save_queue(queue)
            return jsonify({"ok": True, "tweet_id": pid})
        return jsonify({"error": "投稿に失敗しました（重複または API エラー）"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
@require_auth
def api_generate():
    """kazuto ペルソナで新規投稿を生成してキューに追加する"""
    data = request.get_json(force=True)
    count = max(1, min(5, int(data.get("count", 3))))
    theme = data.get("theme", "").strip()  # テーマ指定（任意）

    try:
        import yaml
        from research import build_research_context
        from generate import generate_post
        from queue_manager import add_to_queue

        persona_path = Path("persona/kazuto_config.yaml")
        if not persona_path.exists():
            persona_path = Path("persona/config.yaml")

        with open(persona_path, "r", encoding="utf-8") as f:
            persona = yaml.safe_load(f)

        research = build_research_context(persona.get("interests", []))
        preferred_hours = persona.get("posting_schedule", {}).get(
            "preferred_hours", [7, 12, 17, 21, 23]
        )
        constraints = {
            "max_length": 140,
            "max_hashtags": 2,
            "max_tokens_hint": 300,
            "content_format": "text",
        }

        # テーマ指定がある場合、research context に追加
        if theme:
            research["theme_hint"] = theme

        posts = []
        recent = []
        for _ in range(count):
            text = generate_post(
                persona, research, platform="x",
                constraints=constraints, recent_posts=recent,
            )
            if isinstance(text, str) and text.strip():
                posts.append(text.strip())
                recent.append(text.strip())

        if posts:
            add_to_queue(posts, preferred_hours, platform="x")
            return jsonify({"ok": True, "count": len(posts)})
        return jsonify({"error": "生成に失敗しました"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
@require_auth
def api_status():
    """キューのサマリーを返す"""
    queue = _load_queue()
    pending = [q for q in queue if q.get("status") == "pending"]
    posted = [q for q in queue if q.get("status") == "posted"]
    return jsonify({
        "pending": len(pending),
        "posted": len(posted),
        "total": len(queue),
    })


# ── Web UI ─────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0f0f23">
<title>kazuto 投稿管理</title>
<style>
:root {
  --bg: #0f0f23;
  --card: #1a1a3e;
  --card2: #22224a;
  --accent: #8b5cf6;
  --accent2: #6d28d9;
  --green: #10b981;
  --yellow: #f59e0b;
  --red: #ef4444;
  --blue: #3b82f6;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --border: #2d2d5e;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic', sans-serif;
  min-height: 100vh;
  padding-bottom: calc(80px + var(--safe-bottom));
  overscroll-behavior: none;
}

/* ── ヘッダー ── */
.header {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 14px 16px 10px;
  position: sticky;
  top: 0;
  z-index: 200;
}
.header-row { display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 17px; font-weight: 700; }
.header h1 span { color: var(--accent); }
.badges { display: flex; gap: 6px; margin-top: 5px; }
.badge { font-size: 11px; padding: 2px 9px; border-radius: 999px; font-weight: 600; }
.badge-p { background: rgba(139,92,246,0.2); color: var(--accent); }
.badge-d { background: rgba(16,185,129,0.2); color: var(--green); }
.refresh-btn {
  width: 32px; height: 32px;
  background: var(--card2); border: none; border-radius: 8px;
  color: var(--muted); cursor: pointer; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
}

/* ── タブ ── */
.tabs {
  display: flex;
  background: var(--card);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 68px;
  z-index: 199;
}
.tab {
  flex: 1; padding: 9px; text-align: center;
  font-size: 13px; font-weight: 600; color: var(--muted);
  cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s;
}
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── フィルタチップ ── */
.filter-row {
  display: flex; gap: 6px; padding: 10px 14px 0;
  overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
.filter-row::-webkit-scrollbar { display: none; }
.chip {
  flex-shrink: 0; padding: 4px 12px;
  border: 1px solid var(--border); border-radius: 999px;
  background: transparent; color: var(--muted); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.chip.active { background: var(--accent); border-color: var(--accent); color: white; }

/* ── コンテナ ── */
.container { padding: 10px 14px; max-width: 600px; margin: 0 auto; }

/* ── 生成ボタンエリア ── */
.gen-area { margin-bottom: 12px; }
.gen-row { display: flex; gap: 8px; margin-bottom: 8px; }
.gen-main {
  flex: 1; padding: 12px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: white; border: none; border-radius: 12px;
  font-size: 14px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: opacity 0.2s;
}
.gen-main:active { opacity: 0.8; }
.gen-main:disabled { opacity: 0.5; cursor: not-allowed; }
.gen-opts-btn {
  padding: 12px 14px;
  background: var(--card2); border: 1px solid var(--border);
  border-radius: 12px; color: var(--muted); font-size: 18px;
  cursor: pointer;
}

/* 生成オプションパネル */
.gen-panel {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 12px; display: none;
}
.gen-panel.open { display: block; }
.gen-panel label { font-size: 11px; color: var(--muted); font-weight: 600; display: block; margin-bottom: 6px; }
.count-row { display: flex; gap: 6px; margin-bottom: 10px; }
.count-btn {
  flex: 1; padding: 7px; border: 1px solid var(--border); border-radius: 8px;
  background: transparent; color: var(--muted); font-size: 13px; font-weight: 600; cursor: pointer;
}
.count-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(139,92,246,0.1); }
.theme-input {
  width: 100%; padding: 9px 10px;
  background: var(--card2); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font-size: 13px; font-family: inherit; margin-bottom: 10px;
}
.theme-input:focus { outline: none; border-color: var(--accent); }
.theme-input::placeholder { color: var(--muted); }

/* ── カード ── */
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 13px; margin-bottom: 10px; transition: border-color 0.2s;
}
.card.editing { border-color: var(--accent); }
.card-meta {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
}
.card-left { display: flex; align-items: center; gap: 6px; }
.platform-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 5px;
  text-transform: uppercase;
}
.pb-x        { background: rgba(29,161,242,0.15); color: #60a5fa; }
.pb-instagram { background: rgba(225,48,108,0.15); color: #f472b6; }
.pb-note     { background: rgba(16,185,129,0.15); color: var(--green); }
.pb-tiktok   { background: rgba(239,68,68,0.15); color: var(--red); }
.manual-tag {
  font-size: 9px; padding: 1px 5px; border-radius: 4px;
  background: rgba(245,158,11,0.15); color: var(--yellow); font-weight: 600;
}

/* スケジュール時刻（タップで変更） */
.card-time {
  font-size: 11px; color: var(--muted); cursor: pointer;
  padding: 3px 6px; border-radius: 6px; transition: background 0.15s;
}
.card-time:hover, .card-time:active { background: var(--card2); }
.time-picker {
  font-size: 12px; background: var(--card2); border: 1px solid var(--accent);
  border-radius: 7px; color: var(--text); padding: 4px 7px; width: 100%;
  margin: 4px 0;
}
.time-picker:focus { outline: none; }

.card-text {
  font-size: 14px; line-height: 1.65; white-space: pre-wrap;
  word-break: break-word; min-height: 30px;
}

/* 文字数バー */
.char-bar-wrap { margin: 8px 0 6px; }
.char-bg { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
.char-bar { height: 100%; border-radius: 2px; transition: width 0.2s, background 0.2s; }
.char-ct {
  font-size: 11px; color: var(--muted); margin-top: 3px; text-align: right;
  font-variant-numeric: tabular-nums;
}
.char-ct.warn { color: var(--yellow); }
.char-ct.over { color: var(--red); }

/* カードアクション */
.card-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.btn {
  padding: 8px 6px; border: none; border-radius: 8px;
  font-size: 12px; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
  flex: 1; min-width: 50px; text-align: center;
}
.btn:active { opacity: 0.7; }
.btn-edit   { background: var(--card2); color: var(--text); }
.btn-post   { background: var(--accent); color: white; }
.btn-delete { background: rgba(239,68,68,0.12); color: var(--red); }
.btn-copy   { background: rgba(59,130,246,0.12); color: var(--blue); }
.btn-save   { background: var(--green); color: white; }
.btn-cancel { background: var(--card2); color: var(--muted); }
.btn-done   { background: rgba(16,185,129,0.15); color: var(--green); font-size: 11px; padding: 5px 10px; flex: 0; }

.edit-area {
  width: 100%; background: var(--card2); border: 1px solid var(--accent);
  border-radius: 10px; color: var(--text); font-size: 14px; line-height: 1.65;
  padding: 9px; resize: vertical; min-height: 90px; font-family: inherit;
}
.edit-area:focus { outline: none; }

/* ── FAB（手動追加） ── */
.fab {
  position: fixed;
  bottom: calc(20px + var(--safe-bottom));
  right: 18px;
  width: 52px; height: 52px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: white; border: none; border-radius: 50%;
  font-size: 24px; cursor: pointer; z-index: 300;
  box-shadow: 0 4px 16px rgba(139,92,246,0.5);
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.2s;
}
.fab:active { transform: scale(0.9); }

/* ── ボトムシート（手動追加） ── */
.sheet-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  z-index: 400; opacity: 0; pointer-events: none; transition: opacity 0.25s;
}
.sheet-overlay.open { opacity: 1; pointer-events: all; }
.sheet {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: var(--card);
  border-radius: 20px 20px 0 0;
  padding: 0 16px calc(20px + var(--safe-bottom));
  z-index: 500;
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  max-height: 90vh; overflow-y: auto;
}
.sheet.open { transform: translateY(0); }
.sheet-handle {
  width: 36px; height: 4px; background: var(--border);
  border-radius: 2px; margin: 10px auto 14px;
}
.sheet h2 { font-size: 16px; font-weight: 700; margin-bottom: 12px; }
.platform-row { display: flex; gap: 6px; margin-bottom: 10px; }
.plat-btn {
  flex: 1; padding: 8px;
  border: 1px solid var(--border); border-radius: 8px;
  background: transparent; color: var(--muted); font-size: 12px; font-weight: 600; cursor: pointer;
}
.plat-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(139,92,246,0.1); }
.sheet-input {
  width: 100%; padding: 9px 10px;
  background: var(--card2); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font-size: 13px; font-family: inherit; margin-bottom: 8px;
}
.sheet-input:focus { outline: none; border-color: var(--accent); }
.sheet-input::placeholder { color: var(--muted); }
.datetime-label { font-size: 11px; color: var(--muted); font-weight: 600; margin-bottom: 5px; }
.add-btn {
  width: 100%; padding: 13px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: white; border: none; border-radius: 12px;
  font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 8px;
}
.add-btn:active { opacity: 0.8; }

/* ── 空状態 ── */
.empty {
  text-align: center; color: var(--muted); padding: 50px 20px; font-size: 14px;
}
.empty .icon { font-size: 40px; margin-bottom: 10px; }

/* ── トースト ── */
.toast {
  position: fixed; bottom: calc(80px + var(--safe-bottom));
  left: 50%; transform: translateX(-50%) translateY(20px);
  background: var(--card2); color: var(--text);
  border: 1px solid var(--border); border-radius: 10px;
  padding: 9px 18px; font-size: 13px; font-weight: 600;
  opacity: 0; transition: all 0.3s; z-index: 999; white-space: nowrap;
  pointer-events: none;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.toast.ok  { border-color: var(--green); color: var(--green); }
.toast.err { border-color: var(--red);   color: var(--red);   }

/* ── ローディング ── */
.spin {
  display: inline-block; width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
  border-radius: 50%; animation: spin 0.6s linear infinite; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

.section-lbl {
  font-size: 10px; font-weight: 700; color: var(--muted);
  text-transform: uppercase; letter-spacing: 1px; margin: 4px 0 8px;
}
</style>
</head>
<body>

<!-- ヘッダー -->
<div class="header">
  <div class="header-row">
    <h1>🎤 <span>kazuto</span> 投稿管理</h1>
    <button class="refresh-btn" onclick="loadQueue()" title="更新">↻</button>
  </div>
  <div class="badges">
    <span class="badge badge-p" id="badge-p">pending 0</span>
    <span class="badge badge-d" id="badge-d">済 0</span>
  </div>
</div>

<!-- タブ -->
<div class="tabs">
  <div class="tab active" data-tab="pending" onclick="switchTab('pending')">未投稿</div>
  <div class="tab" data-tab="posted"  onclick="switchTab('posted')">投稿済</div>
</div>

<!-- フィルタ -->
<div class="filter-row" id="filter-row">
  <button class="chip active" data-plat="all" onclick="setFilter('all')">すべて</button>
  <button class="chip" data-plat="x"         onclick="setFilter('x')">X</button>
  <button class="chip" data-plat="instagram" onclick="setFilter('instagram')">Instagram</button>
  <button class="chip" data-plat="note"      onclick="setFilter('note')">note</button>
</div>

<div class="container">

  <!-- 生成エリア -->
  <div class="gen-area">
    <div class="gen-row">
      <button class="gen-main" id="gen-btn" onclick="doGenerate()">
        <span id="gen-icon">✨</span>
        <span id="gen-label">投稿を生成</span>
      </button>
      <button class="gen-opts-btn" onclick="toggleGenPanel()" title="生成オプション">⚙</button>
    </div>
    <div class="gen-panel" id="gen-panel">
      <label>生成件数</label>
      <div class="count-row">
        <button class="count-btn" data-n="1" onclick="selCount(1)">1件</button>
        <button class="count-btn active" data-n="3" onclick="selCount(3)">3件</button>
        <button class="count-btn" data-n="5" onclick="selCount(5)">5件</button>
      </div>
      <label>テーマ・指示（任意）</label>
      <input class="theme-input" id="gen-theme" type="text"
             placeholder="例: 今夜の配信告知、コラボ募集、音楽論…">
    </div>
  </div>

  <!-- 未投稿リスト -->
  <div id="tab-pending">
    <div class="section-lbl">未投稿の投稿文</div>
    <div id="list-pending"></div>
  </div>

  <!-- 投稿済リスト -->
  <div id="tab-posted" style="display:none">
    <div class="section-lbl">投稿済（直近30件）</div>
    <div id="list-posted"></div>
  </div>

</div>

<!-- 手動追加 FAB -->
<button class="fab" onclick="openSheet()" title="手動で追加">＋</button>

<!-- ボトムシート -->
<div class="sheet-overlay" id="overlay" onclick="closeSheet()"></div>
<div class="sheet" id="sheet">
  <div class="sheet-handle"></div>
  <h2>✏️ 投稿文を手動追加</h2>

  <div class="platform-row">
    <button class="plat-btn active" data-p="x"         onclick="selPlat('x')">X</button>
    <button class="plat-btn" data-p="instagram"        onclick="selPlat('instagram')">Instagram</button>
    <button class="plat-btn" data-p="note"             onclick="selPlat('note')">note</button>
  </div>

  <textarea class="edit-area" id="add-text"
            placeholder="ここに投稿文を入力…"
            oninput="updateAddBar()"></textarea>
  <div class="char-bar-wrap">
    <div class="char-bg"><div class="char-bar" id="add-bar"></div></div>
    <div class="char-ct" id="add-ct">0 / 140文字</div>
  </div>

  <div class="datetime-label">投稿予定日時（省略=1時間後）</div>
  <input class="sheet-input" type="datetime-local" id="add-time">

  <button class="add-btn" onclick="addPost()">キューに追加する</button>
</div>

<!-- トースト -->
<div class="toast" id="toast"></div>

<script>
// ── 状態 ─────────────────────────────────────────────────────
let queue = [];
let currentTab = 'pending';
let filterPlat = 'all';
let genCount = 3;

// ── API ──────────────────────────────────────────────────────
async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(path, opts);
    return r.json();
  } catch(e) {
    return { error: String(e) };
  }
}

// ── トースト ─────────────────────────────────────────────────
function toast(msg, type = 'ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + type;
  setTimeout(() => el.className = 'toast', 2600);
}

// ── ユーティリティ ────────────────────────────────────────────
function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function maxLen(platform) {
  return platform === 'x' ? 140 : platform === 'note' ? 5000 : 2200;
}
function charColor(n, max) {
  return n > max ? 'var(--red)' : n > max * 0.9 ? 'var(--yellow)' : 'var(--green)';
}
function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('ja-JP', { month:'numeric', day:'numeric', weekday:'short' })
    + ' ' + d.toTimeString().slice(0,5);
}
function toLocalDT(iso) {
  if (!iso) return '';
  // datetime-local input 用に "YYYY-MM-DDTHH:MM" へ変換
  const d = new Date(iso);
  const pad = n => String(n).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function safeId(id) { return id.replace(/[:.+]/g,'-'); }

// ── キュー読み込み ─────────────────────────────────────────────
async function loadQueue() {
  const res = await api('/api/queue');
  if (Array.isArray(res)) {
    queue = res;
    renderAll();
  } else {
    toast('読み込みエラー', 'err');
  }
}

// ── タブ・フィルタ ─────────────────────────────────────────────
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.getElementById('tab-pending').style.display = tab === 'pending' ? '' : 'none';
  document.getElementById('tab-posted').style.display  = tab === 'posted'  ? '' : 'none';
}
function setFilter(plat) {
  filterPlat = plat;
  document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.plat === plat));
  renderAll();
}

// ── レンダリング ──────────────────────────────────────────────
function renderAll() {
  let pending = queue.filter(q => q.status === 'pending');
  let posted  = queue.filter(q => q.status === 'posted')
                     .sort((a,b)=>(b.posted_at||'').localeCompare(a.posted_at||'')).slice(0,30);

  if (filterPlat !== 'all') {
    pending = pending.filter(q => (q.platform||'x') === filterPlat);
    posted  = posted.filter(q => (q.platform||'x') === filterPlat);
  }
  pending.reverse(); // 新しいものを上に

  document.getElementById('badge-p').textContent = `pending ${pending.length}`;
  document.getElementById('badge-d').textContent = `済 ${posted.length}`;

  document.getElementById('list-pending').innerHTML =
    pending.length ? pending.map(q => cardHTML(q, false)).join('') :
    `<div class="empty"><div class="icon">📭</div>未投稿の投稿文はありません<br>＋ボタンで手動追加、または「生成」で自動作成できます</div>`;

  document.getElementById('list-posted').innerHTML =
    posted.length ? posted.map(q => cardHTML(q, true)).join('') :
    `<div class="empty"><div class="icon">📬</div>投稿済の記録はありません</div>`;
}

function cardHTML(item, readOnly) {
  const id  = item._id || item.created_at;
  const sid = safeId(id);
  const plat = (item.platform || 'x').toLowerCase();
  const text = item.text || '';
  const max  = maxLen(plat);
  const n    = text.length;
  const cc   = charColor(n, max);
  const pct  = Math.min(100, Math.round(n/max*100)) + '%';
  const timeLabel = item.posted_at ? `投稿済 ${fmtTime(item.posted_at)}`
                                   : fmtTime(item.scheduled_for) || '時刻未設定';
  const manualTag = item.manually_added ? '<span class="manual-tag">手動</span>' : '';

  const actions = readOnly ? '' : `
    <div class="card-actions">
      <button class="btn btn-edit"   onclick="startEdit('${id}')">編集</button>
      <button class="btn btn-copy"   onclick="copyText('${id}')">コピー</button>
      <button class="btn btn-post"   onclick="postNow('${id}',this)">投稿する</button>
      <button class="btn btn-delete" onclick="delPost('${id}')">削除</button>
    </div>`;

  return `
<div class="card" id="card-${sid}">
  <div class="card-meta">
    <div class="card-left">
      <span class="platform-badge pb-${plat}">${plat}</span>
      ${manualTag}
    </div>
    <span class="card-time" id="time-${sid}" onclick="editTime('${id}')">${timeLabel}</span>
  </div>
  <div class="card-text" id="text-${sid}">${esc(text)}</div>
  <div class="char-bar-wrap">
    <div class="char-bg"><div class="char-bar" id="bar-${sid}" style="width:${pct};background:${cc}"></div></div>
    <div class="char-ct ${n>max?'over':n>max*0.9?'warn':''}" id="ct-${sid}">${n} / ${max}文字</div>
  </div>
  ${actions}
</div>`;
}

// ── 編集 ──────────────────────────────────────────────────────
function startEdit(id) {
  const sid  = safeId(id);
  const item = queue.find(q=>(q._id||q.created_at)===id);
  if (!item) return;
  const card = document.getElementById('card-'+sid);
  const textEl = document.getElementById('text-'+sid);
  card.classList.add('editing');
  textEl.outerHTML = `<textarea class="edit-area" id="ea-${sid}">${esc(item.text||'')}</textarea>`;
  const ta = document.getElementById('ea-'+sid);
  const max = maxLen(item.platform||'x');
  function upd() {
    const n = ta.value.length;
    const b = document.getElementById('bar-'+sid);
    const c = document.getElementById('ct-'+sid);
    if (b) { b.style.width = Math.min(100,Math.round(n/max*100))+'%'; b.style.background = charColor(n,max); }
    if (c) { c.textContent = `${n} / ${max}文字`; c.className = 'char-ct'+(n>max?' over':n>max*0.9?' warn':''); }
  }
  ta.addEventListener('input', upd); upd(); ta.focus();
  card.querySelector('.card-actions').innerHTML = `
    <button class="btn btn-save"   onclick="saveEdit('${id}')">保存</button>
    <button class="btn btn-cancel" onclick="renderAll()">キャンセル</button>`;
}

async function saveEdit(id) {
  const sid = safeId(id);
  const ta  = document.getElementById('ea-'+sid);
  if (!ta) return;
  const res = await api('/api/edit','POST',{id,text:ta.value});
  if (res.ok) {
    const item = queue.find(q=>(q._id||q.created_at)===id);
    if (item) item.text = ta.value;
    toast('保存しました ✓');
    renderAll();
  } else { toast(res.error||'保存失敗','err'); }
}

// ── スケジュール変更 ───────────────────────────────────────────
function editTime(id) {
  const sid = safeId(id);
  const item = queue.find(q=>(q._id||q.created_at)===id);
  if (!item || item.status === 'posted') return;
  const timeEl = document.getElementById('time-'+sid);
  const current = toLocalDT(item.scheduled_for);
  timeEl.outerHTML = `
    <span style="display:flex;gap:4px;align-items:center" id="time-${sid}">
      <input class="time-picker" type="datetime-local" id="dt-${sid}" value="${current}">
      <button class="btn btn-done" onclick="saveTime('${id}')">確定</button>
    </span>`;
}
async function saveTime(id) {
  const sid = safeId(id);
  const inp = document.getElementById('dt-'+sid);
  if (!inp || !inp.value) return;
  // datetime-local はローカル時刻 → ISO に変換
  const localDT = new Date(inp.value);
  const isoStr  = localDT.toISOString();
  const res = await api('/api/reschedule','POST',{id, scheduled_for: isoStr});
  if (res.ok) {
    const item = queue.find(q=>(q._id||q.created_at)===id);
    if (item) item.scheduled_for = isoStr;
    toast('スケジュールを変更しました ✓');
    renderAll();
  } else { toast(res.error||'変更失敗','err'); }
}

// ── 投稿 ──────────────────────────────────────────────────────
async function postNow(id, btn) {
  if (!confirm('このツイートをXに今すぐ投稿しますか？')) return;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>';
  const res = await api('/api/post','POST',{id});
  btn.disabled = false; btn.textContent = '投稿する';
  if (res.ok) {
    const item = queue.find(q=>(q._id||q.created_at)===id);
    if (item) { item.status='posted'; item.posted_at=new Date().toISOString(); }
    toast('投稿しました 🎤');
    renderAll();
  } else { toast(res.error||'投稿失敗','err'); }
}

// ── コピー ────────────────────────────────────────────────────
function copyText(id) {
  const item = queue.find(q=>(q._id||q.created_at)===id);
  if (!item) return;
  navigator.clipboard.writeText(item.text)
    .then(()=>toast('コピーしました 📋'))
    .catch(()=>toast('コピーに失敗しました','err'));
}

// ── 削除 ──────────────────────────────────────────────────────
async function delPost(id) {
  if (!confirm('この投稿文を削除しますか？')) return;
  const res = await api('/api/delete','POST',{id});
  if (res.ok) { queue=queue.filter(q=>(q._id||q.created_at)!==id); toast('削除しました'); renderAll(); }
  else toast(res.error||'削除失敗','err');
}

// ── 生成 ──────────────────────────────────────────────────────
function toggleGenPanel() {
  document.getElementById('gen-panel').classList.toggle('open');
}
function selCount(n) {
  genCount = n;
  document.querySelectorAll('.count-btn').forEach(b => b.classList.toggle('active', +b.dataset.n===n));
}
async function doGenerate() {
  const btn   = document.getElementById('gen-btn');
  const icon  = document.getElementById('gen-icon');
  const label = document.getElementById('gen-label');
  const theme = document.getElementById('gen-theme').value.trim();
  btn.disabled = true;
  icon.innerHTML = '<span class="spin"></span>';
  label.textContent = `${genCount}件生成中…`;
  const res = await api('/api/generate','POST',{count:genCount, theme});
  btn.disabled = false; icon.textContent='✨'; label.textContent='投稿を生成';
  if (res.ok) { toast(`${res.count}件生成しました 🎵`); await loadQueue(); }
  else toast(res.error||'生成失敗','err');
}

// ── ボトムシート（手動追加） ──────────────────────────────────
let addPlat = 'x';
function openSheet() {
  document.getElementById('overlay').classList.add('open');
  document.getElementById('sheet').classList.add('open');
  document.getElementById('add-text').value = '';
  document.getElementById('add-ct').textContent = '0 / 140文字';
  document.getElementById('add-bar').style.width = '0%';
  document.getElementById('add-time').value = '';
}
function closeSheet() {
  document.getElementById('overlay').classList.remove('open');
  document.getElementById('sheet').classList.remove('open');
}
function selPlat(p) {
  addPlat = p;
  document.querySelectorAll('.plat-btn').forEach(b => b.classList.toggle('active', b.dataset.p===p));
  updateAddBar();
}
function updateAddBar() {
  const ta  = document.getElementById('add-text');
  const bar = document.getElementById('add-bar');
  const ct  = document.getElementById('add-ct');
  const n   = ta.value.length;
  const max = maxLen(addPlat);
  bar.style.width = Math.min(100,Math.round(n/max*100))+'%';
  bar.style.background = charColor(n,max);
  ct.textContent = `${n} / ${max}文字`;
  ct.className = 'char-ct'+(n>max?' over':n>max*0.9?' warn':'');
}
async function addPost() {
  const text = document.getElementById('add-text').value.trim();
  const dtVal = document.getElementById('add-time').value;
  if (!text) { toast('投稿文を入力してください','err'); return; }
  const scheduled_for = dtVal ? new Date(dtVal).toISOString() : '';
  const res = await api('/api/add','POST',{text, platform:addPlat, scheduled_for});
  if (res.ok) {
    closeSheet();
    if (res.item) { res.item._id = res.item.created_at; queue.push(res.item); }
    toast('追加しました ✓'); renderAll();
  } else { toast(res.error||'追加失敗','err'); }
}

// ── 初期化 ────────────────────────────────────────────────────
loadQueue();
setInterval(loadQueue, 30000);
</script>
</body>
</html>"""


@app.route("/")
@require_auth
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
