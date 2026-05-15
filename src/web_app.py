"""
投稿管理ダッシュボード — スマホ対応Webアプリ
URLを開くだけでキューの確認・編集・即時投稿ができる
"""
import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, Response

sys.path.insert(0, str(Path(__file__).parent))

JST = ZoneInfo("Asia/Tokyo")
QUEUE_PATH = Path("posts/queue.json")
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "kazuto")

app = Flask(__name__)


# ── 認証 ──────────────────────────────────────────────────────

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


# ── キュー操作 ─────────────────────────────────────────────────

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
    """指定の投稿をXに今すぐ投稿する"""
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
    """kazutoペルソナで新規投稿を3件生成してキューに追加する"""
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
        constraints = {"max_length": 140, "max_hashtags": 2, "max_tokens_hint": 300,
                       "content_format": "text"}

        posts = []
        for _ in range(3):
            text = generate_post(persona, research, platform="x", constraints=constraints)
            if isinstance(text, str) and text.strip():
                posts.append(text.strip())

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
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
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
    --text: #e2e8f0;
    --muted: #94a3b8;
    --border: #2d2d5e;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', sans-serif;
    min-height: 100vh;
    padding-bottom: 80px;
  }
  .header {
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 16px 20px 12px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(10px);
  }
  .header h1 { font-size: 18px; font-weight: 700; letter-spacing: 0.5px; }
  .header h1 span { color: var(--accent); }
  .badges { display: flex; gap: 8px; margin-top: 6px; }
  .badge {
    font-size: 12px;
    padding: 2px 10px;
    border-radius: 999px;
    font-weight: 600;
  }
  .badge-pending { background: rgba(139,92,246,0.2); color: var(--accent); }
  .badge-posted  { background: rgba(16,185,129,0.2); color: var(--green); }

  .tabs {
    display: flex;
    background: var(--card);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 70px;
    z-index: 99;
  }
  .tab {
    flex: 1;
    padding: 10px;
    text-align: center;
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  .container { padding: 12px 14px; max-width: 600px; margin: 0 auto; }

  .gen-btn {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    margin-bottom: 14px;
    transition: opacity 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .gen-btn:active { opacity: 0.8; }
  .gen-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
  }
  .card.editing { border-color: var(--accent); }

  .card-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }
  .card-platform {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(29,161,242,0.15);
    color: #60a5fa;
    text-transform: uppercase;
  }
  .card-time { font-size: 12px; color: var(--muted); }

  .card-text {
    font-size: 14px;
    line-height: 1.65;
    white-space: pre-wrap;
    word-break: break-word;
    min-height: 40px;
  }

  .char-bar-wrap { margin: 10px 0 8px; }
  .char-bar-bg {
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .char-bar { height: 100%; border-radius: 2px; transition: width 0.2s, background 0.2s; }
  .char-count { font-size: 11px; color: var(--muted); margin-top: 4px; text-align: right; }
  .char-count.warn  { color: var(--yellow); }
  .char-count.over  { color: var(--red); }

  .card-actions { display: flex; gap: 8px; margin-top: 10px; }
  .btn {
    flex: 1;
    padding: 9px 6px;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  .btn:active { opacity: 0.75; }
  .btn-edit   { background: var(--card2); color: var(--text); }
  .btn-post   { background: var(--accent); color: white; }
  .btn-delete { background: rgba(239,68,68,0.15); color: var(--red); }
  .btn-save   { background: var(--green); color: white; }
  .btn-cancel { background: var(--card2); color: var(--muted); }

  .edit-area {
    width: 100%;
    background: var(--card2);
    border: 1px solid var(--accent);
    border-radius: 10px;
    color: var(--text);
    font-size: 14px;
    line-height: 1.65;
    padding: 10px;
    resize: vertical;
    min-height: 100px;
    font-family: inherit;
  }
  .edit-area:focus { outline: none; }

  .empty {
    text-align: center;
    color: var(--muted);
    padding: 60px 20px;
    font-size: 14px;
  }
  .empty .icon { font-size: 40px; margin-bottom: 12px; }

  .toast {
    position: fixed;
    bottom: 90px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: var(--card2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 600;
    opacity: 0;
    transition: all 0.3s;
    z-index: 999;
    white-space: nowrap;
  }
  .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
  .toast.success { border-color: var(--green); color: var(--green); }
  .toast.error   { border-color: var(--red);   color: var(--red);   }

  .loading {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .section-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
    margin-top: 4px;
  }
</style>
</head>
<body>

<div class="header">
  <h1>🎤 <span>kazuto</span> 投稿管理</h1>
  <div class="badges">
    <span class="badge badge-pending" id="badge-pending">pending 0</span>
    <span class="badge badge-posted"  id="badge-posted">済 0</span>
  </div>
</div>

<div class="tabs">
  <div class="tab active" data-tab="pending" onclick="switchTab('pending')">未投稿</div>
  <div class="tab" data-tab="posted" onclick="switchTab('posted')">投稿済</div>
</div>

<div class="container">
  <button class="gen-btn" id="gen-btn" onclick="generatePosts()">
    <span id="gen-icon">✨</span>
    <span id="gen-label">新規投稿を3件生成</span>
  </button>

  <div id="tab-pending">
    <div class="section-label">未投稿の投稿文</div>
    <div id="list-pending"></div>
  </div>

  <div id="tab-posted" style="display:none">
    <div class="section-label">投稿済（直近20件）</div>
    <div id="list-posted"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let queue = [];
let currentTab = 'pending';

async function apiFetch(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json();
}

function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  setTimeout(() => t.className = 'toast', 2500);
}

function charColor(n, max = 140) {
  if (n > max) return 'var(--red)';
  if (n > max * 0.9) return 'var(--yellow)';
  return 'var(--green)';
}

function charBarWidth(n, max = 140) {
  return Math.min(100, Math.round(n / max * 100)) + '%';
}

function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const now = new Date();
  const diff = d - now;
  const pad = n => String(n).padStart(2, '0');
  const label = d.toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric', weekday: 'short' });
  return `${label} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function renderCard(item, readOnly = false) {
  const id = item._id || item.created_at;
  const text = item.text || '';
  const n = text.length;
  const max = 140;
  const cc = charColor(n, max);
  const pct = charBarWidth(n, max);
  const timeLabel = item.posted_at
    ? `投稿済 ${formatTime(item.posted_at)}`
    : `予定: ${formatTime(item.scheduled_for)}`;

  const actions = readOnly
    ? ''
    : `<div class="card-actions">
        <button class="btn btn-edit"   onclick="startEdit('${id}')">編集</button>
        <button class="btn btn-post"   onclick="postNow('${id}')">投稿する</button>
        <button class="btn btn-delete" onclick="deletePost('${id}')">削除</button>
       </div>`;

  return `
  <div class="card" id="card-${id.replace(/[:.+]/g,'-')}">
    <div class="card-meta">
      <span class="card-platform">${item.platform || 'x'}</span>
      <span class="card-time">${timeLabel}</span>
    </div>
    <div class="card-text" id="text-${id.replace(/[:.+]/g,'-')}">${escHtml(text)}</div>
    <div class="char-bar-wrap">
      <div class="char-bar-bg"><div class="char-bar" style="width:${pct};background:${cc}"></div></div>
      <div class="char-count ${n > max ? 'over' : n > max*0.9 ? 'warn' : ''}">${n} / ${max}文字</div>
    </div>
    ${actions}
  </div>`;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.getElementById('tab-pending').style.display = tab === 'pending' ? '' : 'none';
  document.getElementById('tab-posted').style.display  = tab === 'posted'  ? '' : 'none';
}

async function loadQueue() {
  try {
    queue = await apiFetch('/api/queue');
    renderAll();
  } catch(e) {
    showToast('読み込みエラー', 'error');
  }
}

function renderAll() {
  const pending = queue.filter(q => q.status === 'pending').reverse();
  const posted  = queue.filter(q => q.status === 'posted')
                       .sort((a,b) => (b.posted_at||'').localeCompare(a.posted_at||'')).slice(0, 20);

  document.getElementById('badge-pending').textContent = `pending ${pending.length}`;
  document.getElementById('badge-posted').textContent  = `済 ${posted.length}`;

  document.getElementById('list-pending').innerHTML = pending.length
    ? pending.map(q => renderCard(q, false)).join('')
    : `<div class="empty"><div class="icon">📭</div>未投稿の投稿文はありません<br>上の「生成」ボタンで作成できます</div>`;

  document.getElementById('list-posted').innerHTML = posted.length
    ? posted.map(q => renderCard(q, true)).join('')
    : `<div class="empty"><div class="icon">📬</div>投稿済の記録はありません</div>`;
}

function cardId(id) { return 'card-' + id.replace(/[:.+]/g,'-'); }
function textId(id) { return 'text-' + id.replace(/[:.+]/g,'-'); }

function startEdit(id) {
  const item = queue.find(q => (q._id||q.created_at) === id);
  if (!item) return;
  const cid = cardId(id);
  const card = document.getElementById(cid);
  const textEl = document.getElementById(textId(id));
  const text = item.text || '';

  card.classList.add('editing');
  textEl.outerHTML = `
    <textarea class="edit-area" id="edit-${cid}" oninput="onEditInput(this,'${id}')">${escHtml(text)}</textarea>`;

  // Update char bar live
  const max = 140;
  const ta = document.getElementById('edit-' + cid);
  const barEl = card.querySelector('.char-bar');
  const countEl = card.querySelector('.char-count');
  function updateBar() {
    const n = ta.value.length;
    barEl.style.width = charBarWidth(n, max);
    barEl.style.background = charColor(n, max);
    countEl.textContent = `${n} / ${max}文字`;
    countEl.className = 'char-count ' + (n > max ? 'over' : n > max*0.9 ? 'warn' : '');
  }
  ta.addEventListener('input', updateBar);
  updateBar();
  ta.focus();

  // Replace buttons
  card.querySelector('.card-actions').innerHTML = `
    <button class="btn btn-save"   onclick="saveEdit('${id}')">保存</button>
    <button class="btn btn-cancel" onclick="cancelEdit('${id}')">キャンセル</button>`;
}

async function saveEdit(id) {
  const cid = cardId(id);
  const ta = document.getElementById('edit-' + cid);
  if (!ta) return;
  const newText = ta.value;
  const res = await apiFetch('/api/edit', 'POST', { id, text: newText });
  if (res.ok) {
    const item = queue.find(q => (q._id||q.created_at) === id);
    if (item) item.text = newText;
    showToast('保存しました ✓');
    renderAll();
  } else {
    showToast(res.error || '保存に失敗しました', 'error');
  }
}

function cancelEdit(id) {
  renderAll();
}

async function postNow(id) {
  if (!confirm('このツイートを今すぐXに投稿しますか？')) return;
  const item = queue.find(q => (q._id||q.created_at) === id);
  const btn = event.target;
  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span>';
  const res = await apiFetch('/api/post', 'POST', { id });
  btn.disabled = false;
  btn.textContent = '投稿する';
  if (res.ok) {
    if (item) { item.status = 'posted'; item.posted_at = new Date().toISOString(); }
    showToast('投稿しました 🎤');
    renderAll();
  } else {
    showToast(res.error || '投稿に失敗しました', 'error');
  }
}

async function deletePost(id) {
  if (!confirm('この投稿文を削除しますか？')) return;
  const res = await apiFetch('/api/delete', 'POST', { id });
  if (res.ok) {
    queue = queue.filter(q => (q._id||q.created_at) !== id);
    showToast('削除しました');
    renderAll();
  } else {
    showToast(res.error || '削除に失敗しました', 'error');
  }
}

async function generatePosts() {
  const btn = document.getElementById('gen-btn');
  const icon = document.getElementById('gen-icon');
  const label = document.getElementById('gen-label');
  btn.disabled = true;
  icon.innerHTML = '<span class="loading"></span>';
  label.textContent = '生成中…（30秒ほどかかります）';

  const res = await apiFetch('/api/generate', 'POST', {});

  btn.disabled = false;
  icon.textContent = '✨';
  label.textContent = '新規投稿を3件生成';

  if (res.ok) {
    showToast(`${res.count}件の投稿を生成しました 🎵`);
    await loadQueue();
  } else {
    showToast(res.error || '生成に失敗しました', 'error');
  }
}

// 初回ロード
loadQueue();
// 30秒ごとに自動更新
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
