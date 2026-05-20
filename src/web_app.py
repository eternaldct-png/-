"""
kazuto 投稿文ジェネレーター — スマホ対応Webアプリ

スマホで開いてボタンを押すだけで投稿文を生成し、コピーできる。
自動投稿なし。X API 不要。
"""
import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify

sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)


# ── 生成 API ──────────────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def api_generate():
    """投稿文を生成して返す（キュー保存・投稿なし）"""
    import yaml
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from research import build_research_context
    from generate import generate_post

    data = request.get_json(force=True)
    count = max(1, min(5, int(data.get("count", 1))))
    theme = data.get("theme", "").strip()
    slot = data.get("slot", "")  # "朝" / "昼" / "夕方" / "夜" / "深夜"

    try:
        persona_path = Path("persona/kazuto_config.yaml")
        if not persona_path.exists():
            persona_path = Path("persona/config.yaml")

        with open(persona_path, "r", encoding="utf-8") as f:
            persona = yaml.safe_load(f)

        JST = ZoneInfo("Asia/Tokyo")
        now = datetime.now(JST)

        # 時間帯 → 投稿スタイルのヒントを research context に乗せる
        slot_hint = {
            "朝":  "朝の一言。今日の意気込み・音楽への想いを短く。朝にふさわしいエネルギー。",
            "昼":  "音楽・歌に関する深い話、好きな曲、歌い方のtips。音楽好きが反応したくなる内容。",
            "夕方": "配信告知 または 事務所・ライバー関連。コミュニティ感・チーム感を出す。",
            "夜":  "配信中・配信後レポート または フォロワーへの問いかけ。ライブ感・エンゲージメント重視。",
            "深夜": "今日一日の締めくくり。感謝・振り返り。温かく短い言葉。",
        }.get(slot, "")

        research = build_research_context(persona.get("interests", []))
        if theme:
            research["theme_hint"] = theme
        if slot_hint:
            research["slot_hint"] = slot_hint

        max_length = max(50, min(2000, int(data.get("max_length", 140))))
        max_hashtags = 2 if max_length <= 140 else 3 if max_length <= 280 else 5
        max_tokens = 150 if max_length <= 140 else 300 if max_length <= 280 else 800

        constraints = {
            "max_length": max_length,
            "max_hashtags": max_hashtags,
            "max_tokens_hint": max_tokens,
            "content_format": "text",
        }

        posts = []
        recent = []
        for _ in range(count):
            text = generate_post(
                persona, research,
                platform="x",
                constraints=constraints,
                recent_posts=recent,
            )
            if isinstance(text, str) and text.strip():
                posts.append(text.strip())
                recent.append(text.strip())

        if posts:
            return jsonify({"ok": True, "posts": posts})
        return jsonify({"error": "生成に失敗しました。もう一度お試しください。"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── フロントエンド HTML ────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0d0d1f">
<title>kazuto 投稿ジェネレーター</title>
<style>
:root {
  --bg: #0d0d1f;
  --surface: #181830;
  --surface2: #21213d;
  --accent: #7c3aed;
  --accent-light: #a78bfa;
  --accent-glow: rgba(124,58,237,0.25);
  --green: #10b981;
  --text: #e2e8f0;
  --muted: #8892a4;
  --border: #2a2a4a;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  min-height: 100vh;
  padding-bottom: calc(24px + var(--safe-bottom));
}

/* ── ヘッダー ── */
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 18px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-icon {
  width: 38px; height: 38px;
  background: linear-gradient(135deg, var(--accent), #5b21b6);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
}
.header-title { font-size: 17px; font-weight: 700; }
.header-sub { font-size: 12px; color: var(--muted); margin-top: 1px; }

/* ── メインコンテンツ ── */
.main { padding: 18px 16px; max-width: 540px; margin: 0 auto; }

/* ── セクションラベル ── */
.section-label {
  font-size: 11px; font-weight: 700; color: var(--muted);
  letter-spacing: 0.08em; text-transform: uppercase;
  margin-bottom: 8px;
}

/* ── 時間帯ボタン ── */
.slot-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 18px;
}
.slot-btn {
  padding: 10px 4px 8px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  color: var(--muted);
  font-size: 12px; font-weight: 600;
  cursor: pointer;
  display: flex; flex-direction: column;
  align-items: center; gap: 3px;
  transition: all 0.15s;
}
.slot-btn .slot-time { font-size: 10px; color: var(--muted); font-weight: 400; }
.slot-btn.active {
  background: var(--accent-glow);
  border-color: var(--accent);
  color: var(--accent-light);
}
.slot-btn.active .slot-time { color: var(--accent-light); opacity: 0.8; }

/* ── テーマ入力 ── */
.theme-wrap { margin-bottom: 18px; }
.theme-input {
  width: 100%;
  padding: 12px 14px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 12px;
  color: var(--text);
  font-size: 15px;
  outline: none;
  transition: border-color 0.15s;
  -webkit-appearance: none;
}
.theme-input:focus { border-color: var(--accent); }
.theme-input::placeholder { color: var(--muted); }

/* ── 件数セレクタ ── */
.count-wrap { margin-bottom: 20px; }
.count-row { display: flex; gap: 8px; }
.count-btn {
  flex: 1; padding: 10px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  color: var(--muted); font-size: 14px; font-weight: 700;
  cursor: pointer; transition: all 0.15s;
}
.count-btn.active {
  background: var(--accent-glow);
  border-color: var(--accent);
  color: var(--accent-light);
}

/* ── 生成ボタン ── */
.gen-btn {
  width: 100%; padding: 16px;
  background: linear-gradient(135deg, var(--accent), #5b21b6);
  border: none; border-radius: 14px;
  color: white; font-size: 16px; font-weight: 800;
  cursor: pointer; letter-spacing: 0.03em;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: opacity 0.2s, transform 0.1s;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px var(--accent-glow);
}
.gen-btn:active { opacity: 0.85; transform: scale(0.98); }
.gen-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.gen-btn .spinner {
  width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: none;
}
.gen-btn.loading .spinner { display: block; }
.gen-btn.loading .btn-icon { display: none; }

/* ── 結果エリア ── */
.results { display: flex; flex-direction: column; gap: 14px; }

/* ── 投稿カード ── */
.post-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  animation: slideIn 0.25s ease-out;
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.post-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--border);
}
.post-num { font-size: 11px; font-weight: 700; color: var(--muted); }
.char-badge {
  font-size: 11px; font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(16,185,129,0.15);
  color: var(--green);
}
.char-badge.warn { background: rgba(245,158,11,0.15); color: #f59e0b; }
.char-badge.over { background: rgba(239,68,68,0.15); color: #ef4444; }
.post-text {
  padding: 14px;
  font-size: 15px; line-height: 1.7;
  white-space: pre-wrap; word-break: break-word;
  color: var(--text);
  border: none; outline: none;
  background: transparent;
  width: 100%;
  resize: none;
  min-height: 80px;
  font-family: inherit;
}
.post-actions {
  display: flex;
  gap: 8px;
  padding: 0 14px 12px;
}
.copy-btn {
  flex: 1; padding: 10px;
  background: var(--accent-glow);
  border: 1.5px solid var(--accent);
  border-radius: 10px;
  color: var(--accent-light); font-size: 13px; font-weight: 700;
  cursor: pointer; transition: all 0.15s;
  display: flex; align-items: center; justify-content: center; gap: 5px;
}
.copy-btn:active { opacity: 0.7; }
.copy-btn.copied {
  background: rgba(16,185,129,0.15);
  border-color: var(--green);
  color: var(--green);
}
.regen-btn {
  padding: 10px 14px;
  background: var(--surface2);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  color: var(--muted); font-size: 16px;
  cursor: pointer; transition: all 0.15s;
}
.regen-btn:active { opacity: 0.7; }

/* ── 空状態 ── */
.empty {
  text-align: center;
  padding: 48px 24px;
  color: var(--muted);
}
.empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.6; }
.empty-text { font-size: 14px; line-height: 1.6; }

/* ── トースト ── */
.toast {
  position: fixed;
  bottom: calc(24px + var(--safe-bottom));
  left: 50%; transform: translateX(-50%) translateY(10px);
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px 20px;
  border-radius: 999px;
  font-size: 13px; font-weight: 600;
  white-space: nowrap;
  opacity: 0; transition: all 0.2s;
  pointer-events: none; z-index: 999;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.toast.ok { border-color: var(--green); color: var(--green); }
.toast.err { border-color: #ef4444; color: #ef4444; }

/* ── テーマチップ ── */
.theme-chips {
  display: flex; flex-wrap: wrap; gap: 7px;
  margin-bottom: 4px;
}
.theme-chip {
  padding: 7px 13px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 999px;
  color: var(--muted); font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s; white-space: nowrap;
}
.theme-chip.active {
  background: var(--accent-glow);
  border-color: var(--accent);
  color: var(--accent-light);
}

/* ── 投稿先ボタン ── */
.platform-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px; margin-bottom: 4px;
}
.plat-btn {
  padding: 9px 4px;
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: 10px;
  color: var(--muted); font-size: 13px; font-weight: 700;
  cursor: pointer; transition: all 0.15s;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.plat-btn span { font-size: 10px; font-weight: 400; color: var(--muted); }
.plat-btn.active {
  background: var(--accent-glow);
  border-color: var(--accent);
  color: var(--accent-light);
}
.plat-btn.active span { color: var(--accent-light); opacity: 0.8; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<div class="header">
  <div class="header-icon">🎤</div>
  <div>
    <div class="header-title">kazuto 投稿ジェネレーター</div>
    <div class="header-sub">ColorSing配信者 / ライバー事務所代表</div>
  </div>
</div>

<div class="main">

  <!-- 時間帯 -->
  <div class="section-label">時間帯</div>
  <div class="slot-grid">
    <button class="slot-btn" data-slot="朝"    onclick="selectSlot(this)">☀️<span class="slot-time">07:00</span></button>
    <button class="slot-btn" data-slot="昼"    onclick="selectSlot(this)">🌤<span class="slot-time">12:00</span></button>
    <button class="slot-btn" data-slot="夕方"  onclick="selectSlot(this)">🌇<span class="slot-time">17:00</span></button>
    <button class="slot-btn" data-slot="夜"    onclick="selectSlot(this)">🌙<span class="slot-time">21:00</span></button>
    <button class="slot-btn" data-slot="深夜"  onclick="selectSlot(this)">⭐<span class="slot-time">23:00</span></button>
  </div>

  <!-- テーマ -->
  <div class="section-label">テーマ（任意）</div>
  <div class="theme-chips">
    <button class="theme-chip" data-theme="" onclick="selectTheme(this)">なんでも</button>
    <button class="theme-chip" data-theme="ColorSing配信・歌ってみた" onclick="selectTheme(this)">🎵 ColorSing配信</button>
    <button class="theme-chip" data-theme="音楽・好きな曲・歌い方のtips" onclick="selectTheme(this)">🎶 音楽・歌</button>
    <button class="theme-chip" data-theme="ライバー事務所・所属ライバー紹介" onclick="selectTheme(this)">🏢 ライバー事務所</button>
    <button class="theme-chip" data-theme="フォロワーへの問いかけ・アンケート" onclick="selectTheme(this)">💬 問いかけ</button>
    <button class="theme-chip" data-theme="コラボ募集・デュエット" onclick="selectTheme(this)">🤝 コラボ募集</button>
    <button class="theme-chip" data-theme="経営・起業・ライバー事務所代表としての考え" onclick="selectTheme(this)">💼 経営・起業</button>
    <button class="theme-chip" data-theme="今週の振り返り・来週の予告" onclick="selectTheme(this)">📅 振り返り</button>
    <button class="theme-chip" id="customChip" data-theme="custom" onclick="selectTheme(this)">✏️ カスタム</button>
  </div>
  <input id="theme" class="theme-input" type="text"
    placeholder="テーマを自由に入力…" maxlength="50"
    style="display:none; margin-top:8px;">

  <!-- 文字数 -->
  <div class="section-label" style="margin-top:18px;">文字数・投稿先</div>
  <div class="platform-row">
    <button class="plat-btn active" data-len="140"  onclick="selectPlatform(this)">X<span>140文字</span></button>
    <button class="plat-btn" data-len="280"  onclick="selectPlatform(this)">X Premium<span>280文字</span></button>
    <button class="plat-btn" data-len="500"  onclick="selectPlatform(this)">Instagram<span>500文字</span></button>
    <button class="plat-btn" data-len="1000" onclick="selectPlatform(this)">note<span>1000文字</span></button>
  </div>

  <!-- 件数 -->
  <div class="section-label" style="margin-top:18px;">生成件数</div>
  <div class="count-row" style="margin-bottom:20px;">
    <button class="count-btn active" data-count="1" onclick="selectCount(this)">1件</button>
    <button class="count-btn" data-count="3" onclick="selectCount(this)">3件</button>
    <button class="count-btn" data-count="5" onclick="selectCount(this)">5件</button>
  </div>

  <!-- 生成ボタン -->
  <button class="gen-btn" id="genBtn" onclick="generate()">
    <span class="spinner"></span>
    <span class="btn-icon">✨</span>
    投稿文を生成する
  </button>

  <!-- 結果 -->
  <div id="results" class="results">
    <div class="empty">
      <div class="empty-icon">🎵</div>
      <div class="empty-text">時間帯を選んで<br>「生成」ボタンを押してください</div>
    </div>
  </div>

</div>

<div class="toast" id="toast"></div>

<script>
let selectedSlot = '';
let selectedCount = 1;
let selectedTheme = '';
let selectedMaxLength = 140;

// 時間帯選択
function selectSlot(btn) {
  document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedSlot = btn.dataset.slot;
}

// テーマ選択
function selectTheme(btn) {
  document.querySelectorAll('.theme-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const customInput = document.getElementById('theme');
  if (btn.dataset.theme === 'custom') {
    customInput.style.display = 'block';
    customInput.focus();
    selectedTheme = '';
  } else {
    customInput.style.display = 'none';
    selectedTheme = btn.dataset.theme;
  }
}

// 投稿先・文字数選択
function selectPlatform(btn) {
  document.querySelectorAll('.plat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedMaxLength = parseInt(btn.dataset.len);
}

// 件数選択
function selectCount(btn) {
  document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedCount = parseInt(btn.dataset.count);
}

// 生成
async function generate() {
  const btn = document.getElementById('genBtn');
  btn.disabled = true;
  btn.classList.add('loading');

  const customInput = document.getElementById('theme');
  const theme = selectedTheme || customInput.value.trim();

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count: selectedCount, slot: selectedSlot, theme, max_length: selectedMaxLength }),
    });
    const data = await res.json();

    if (data.ok && data.posts && data.posts.length) {
      renderPosts(data.posts, selectedMaxLength);
    } else {
      toast(data.error || '生成に失敗しました', 'err');
    }
  } catch(e) {
    toast('通信エラーが発生しました', 'err');
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

// 1件だけ再生成して指定カードを更新
async function regenerateOne(idx) {
  const theme = document.getElementById('theme').value.trim();
  const card = document.querySelectorAll('.post-card')[idx];
  if (!card) return;

  const regenBtn = card.querySelector('.regen-btn');
  regenBtn.textContent = '⌛';
  regenBtn.disabled = true;

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count: 1, slot: selectedSlot, theme, max_length: selectedMaxLength }),
    });
    const data = await res.json();
    if (data.ok && data.posts && data.posts[0]) {
      const ta = card.querySelector('.post-text');
      ta.value = data.posts[0];
      updateCharBadge(card);
      toast('再生成しました ✓', 'ok');
    } else {
      toast(data.error || '再生成に失敗', 'err');
    }
  } catch(e) {
    toast('通信エラー', 'err');
  } finally {
    regenBtn.textContent = '🔄';
    regenBtn.disabled = false;
  }
}

// 結果表示
function renderPosts(posts, maxLen) {
  maxLen = maxLen || selectedMaxLength;
  const el = document.getElementById('results');
  el.innerHTML = '';
  posts.forEach((text, i) => {
    const card = document.createElement('div');
    card.className = 'post-card';
    card.dataset.maxlen = maxLen;
    card.innerHTML = `
      <div class="post-card-header">
        <span class="post-num">投稿 ${i + 1}</span>
        <span class="char-badge" id="badge-${i}">${text.length} / ${maxLen}文字</span>
      </div>
      <textarea class="post-text" id="text-${i}" oninput="onTextInput(this, ${i})">${escHtml(text)}</textarea>
      <div class="post-actions">
        <button class="copy-btn" onclick="copyPost(${i}, this)">📋 コピー</button>
        <button class="regen-btn" onclick="regenerateOne(${i})">🔄</button>
      </div>
    `;
    el.appendChild(card);
    updateCharBadge(card);
    autoResize(card.querySelector('.post-text'));
  });
}

// テキスト編集時
function onTextInput(ta, idx) {
  const card = ta.closest('.post-card');
  updateCharBadge(card);
  autoResize(ta);
}

function updateCharBadge(card) {
  const ta = card.querySelector('.post-text');
  const badge = card.querySelector('.char-badge');
  const n = ta.value.length;
  const max = parseInt(card.dataset.maxlen) || selectedMaxLength;
  badge.textContent = `${n} / ${max}文字`;
  badge.className = 'char-badge' + (n > max ? ' over' : n > max * 0.9 ? ' warn' : '');
}

function autoResize(ta) {
  ta.style.height = 'auto';
  ta.style.height = ta.scrollHeight + 'px';
}

// コピー
async function copyPost(idx, btn) {
  const ta = document.getElementById('text-' + idx);
  if (!ta) return;
  try {
    await navigator.clipboard.writeText(ta.value);
  } catch(e) {
    const range = document.createRange();
    range.selectNodeContents(ta);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand('copy');
    window.getSelection().removeAllRanges();
  }
  btn.textContent = '✓ コピーしました';
  btn.classList.add('copied');
  toast('コピーしました ✓', 'ok');
  setTimeout(() => {
    btn.textContent = '📋 コピー';
    btn.classList.remove('copied');
  }, 2000);
}

// トースト
function toast(msg, type) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (type ? ' ' + type : '');
  setTimeout(() => { el.className = 'toast'; }, 2200);
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// 初期選択
document.querySelector('.theme-chip').classList.add('active');
document.querySelector('.plat-btn').classList.add('active');

// 現在時刻から時間帯を自動選択
(function autoSelectSlot() {
  const h = new Date().getHours();
  let slot;
  if (h >= 5 && h < 10)       slot = '朝';
  else if (h >= 10 && h < 15) slot = '昼';
  else if (h >= 15 && h < 19) slot = '夕方';
  else if (h >= 19 && h < 22) slot = '夜';
  else                         slot = '深夜';

  const btn = document.querySelector(`.slot-btn[data-slot="${slot}"]`);
  if (btn) { btn.classList.add('active'); selectedSlot = slot; }
})();
</script>
</body>
</html>"""


# ── ルーティング ──────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


# ── note 下書き閲覧ページ ─────────────────────────────────────────

NOTE_DRAFTS_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>note 下書き</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
    background: #f5f5f0;
    color: #1a1a1a;
    min-height: 100vh;
  }
  header {
    background: #41C9B4;
    color: white;
    padding: 16px 20px;
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header h1 { font-size: 18px; font-weight: 700; }
  header .count {
    background: rgba(255,255,255,0.3);
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 13px;
  }
  .list-view { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .article-card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    cursor: pointer;
    transition: transform 0.1s;
    -webkit-tap-highlight-color: transparent;
  }
  .article-card:active { transform: scale(0.98); }
  .article-card h2 { font-size: 15px; font-weight: 600; line-height: 1.4; margin-bottom: 8px; }
  .article-card .meta { font-size: 12px; color: #888; display: flex; gap: 8px; flex-wrap: wrap; }
  .article-card .tag {
    background: #e8f8f5;
    color: #41C9B4;
    border-radius: 8px;
    padding: 2px 8px;
  }
  .article-card .status-draft { color: #f39c12; font-weight: 600; }
  .article-card .status-uploaded { color: #41C9B4; font-weight: 600; }
  .empty { text-align: center; padding: 60px 20px; color: #888; }
  .empty p { margin-top: 8px; font-size: 14px; }

  /* 詳細パネル */
  .detail-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 200;
    animation: fadeIn 0.2s;
  }
  .detail-overlay.open { display: block; }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  .detail-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    border-radius: 24px 24px 0 0;
    max-height: 92vh;
    display: flex;
    flex-direction: column;
    animation: slideUp 0.3s ease;
    z-index: 201;
  }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
  .detail-handle {
    width: 40px;
    height: 4px;
    background: #ddd;
    border-radius: 2px;
    margin: 12px auto 0;
    flex-shrink: 0;
  }
  .detail-header {
    padding: 16px 20px 12px;
    border-bottom: 1px solid #f0f0f0;
    flex-shrink: 0;
  }
  .detail-header h2 { font-size: 16px; font-weight: 700; line-height: 1.4; }
  .detail-header .close-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    background: #f0f0f0;
    border: none;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    -webkit-tap-highlight-color: transparent;
  }
  .detail-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    -webkit-overflow-scrolling: touch;
    white-space: pre-wrap;
    font-size: 14px;
    line-height: 1.8;
    color: #333;
  }
  .detail-footer {
    padding: 16px 20px;
    padding-bottom: max(16px, env(safe-area-inset-bottom));
    border-top: 1px solid #f0f0f0;
    flex-shrink: 0;
  }
  .copy-btn {
    width: 100%;
    background: #41C9B4;
    color: white;
    border: none;
    border-radius: 14px;
    padding: 16px;
    font-size: 17px;
    font-weight: 700;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    transition: background 0.2s;
  }
  .copy-btn:active { background: #35b09c; }
  .copy-btn.copied { background: #27ae60; }
  .delete-btn {
    width: 100%;
    background: none;
    color: #e74c3c;
    border: 2px solid #e74c3c;
    border-radius: 14px;
    padding: 12px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    margin-top: 10px;
    transition: background 0.2s, color 0.2s;
  }
  .delete-btn:active { background: #e74c3c; color: white; }
  /* 確認ダイアログ */
  .confirm-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 400;
    align-items: center;
    justify-content: center;
  }
  .confirm-overlay.open { display: flex; }
  .confirm-box {
    background: white;
    border-radius: 20px;
    padding: 24px 20px;
    margin: 20px;
    max-width: 320px;
    width: 100%;
    text-align: center;
  }
  .confirm-box h3 { font-size: 17px; margin-bottom: 8px; }
  .confirm-box p { font-size: 14px; color: #666; margin-bottom: 20px; line-height: 1.5; }
  .confirm-actions { display: flex; gap: 10px; }
  .confirm-actions button {
    flex: 1;
    padding: 12px;
    border-radius: 12px;
    border: none;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-cancel { background: #f0f0f0; color: #333; }
  .btn-delete { background: #e74c3c; color: white; }
  .toast {
    position: fixed;
    bottom: 100px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 14px;
    z-index: 300;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
    white-space: nowrap;
  }
  .toast.show { opacity: 1; }
</style>
</head>
<body>
<header>
  <h1>note 下書き</h1>
  <span class="count" id="count">0件</span>
</header>

<div class="list-view" id="list"></div>

<div class="detail-overlay" id="overlay" onclick="closeDetail()">
  <div class="detail-panel" onclick="event.stopPropagation()">
    <div class="detail-handle"></div>
    <div class="detail-header">
      <h2 id="detail-title"></h2>
      <button class="close-btn" onclick="closeDetail()">×</button>
    </div>
    <div class="detail-body" id="detail-body"></div>
    <div class="detail-footer">
      <button class="copy-btn" id="copy-btn" onclick="copyContent()">コピーして note に貼り付け</button>
      <button class="delete-btn" onclick="confirmDelete()">この記事を削除</button>
    </div>
  </div>
</div>

<div class="confirm-overlay" id="confirm-overlay">
  <div class="confirm-box">
    <h3>記事を削除しますか？</h3>
    <p id="confirm-title-text"></p>
    <div class="confirm-actions">
      <button class="btn-cancel" onclick="closeConfirm()">キャンセル</button>
      <button class="btn-delete" onclick="deleteArticle()">削除する</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let articles = [];
let currentContent = '';
let currentFilename = '';
let currentIndex = -1;

async function load() {
  const res = await fetch('/api/note-drafts');
  const data = await res.json();
  articles = data.articles || [];
  render();
}

function render() {
  const list = document.getElementById('list');
  document.getElementById('count').textContent = articles.length + '件';
  if (!articles.length) {
    list.innerHTML = '<div class="empty"><div style="font-size:48px">📝</div><p>下書き記事がありません</p></div>';
    return;
  }
  list.innerHTML = articles.map((a, i) => `
    <div class="article-card" onclick="openDetail(${i})">
      <h2>${a.title}</h2>
      <div class="meta">
        <span>${a.date}</span>
        <span class="${a.status === 'draft' ? 'status-draft' : 'status-uploaded'}">
          ${a.status === 'draft' ? '● 未投稿' : '✓ 投稿済'}
        </span>
        ${a.tags.map(t => `<span class="tag">${t}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

function openDetail(i) {
  const a = articles[i];
  currentIndex = i;
  currentContent = a.copy_text;
  currentFilename = a.filename;
  document.getElementById('detail-title').textContent = a.title;
  document.getElementById('detail-body').textContent = a.body;
  document.getElementById('copy-btn').textContent = 'コピーして note に貼り付け';
  document.getElementById('copy-btn').classList.remove('copied');
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function confirmDelete() {
  const a = articles[currentIndex];
  document.getElementById('confirm-title-text').textContent = '「' + a.title + '」';
  document.getElementById('confirm-overlay').classList.add('open');
}

function closeConfirm() {
  document.getElementById('confirm-overlay').classList.remove('open');
}

async function deleteArticle() {
  closeConfirm();
  const res = await fetch('/api/note-drafts/delete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: currentFilename}),
  });
  const data = await res.json();
  if (data.ok) {
    showToast('削除しました');
    closeDetail();
    await load();
  } else {
    showToast('削除に失敗しました: ' + (data.error || ''));
  }
}

function closeDetail() {
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
}

function copyContent() {
  navigator.clipboard.writeText(currentContent).then(() => {
    const btn = document.getElementById('copy-btn');
    btn.textContent = 'コピーしました！';
    btn.classList.add('copied');
    showToast('クリップボードにコピーしました');
  }).catch(() => {
    // fallback
    const ta = document.createElement('textarea');
    ta.value = currentContent;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('コピーしました');
  });
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}

load();
</script>
</body>
</html>
"""


@app.route("/note-drafts")
def note_drafts():
    return NOTE_DRAFTS_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/note-drafts")
def api_note_drafts():
    import yaml
    import re

    articles_dir = Path("posts/note/articles")
    result = []

    if not articles_dir.exists():
        return jsonify({"articles": []})

    for fp in sorted(articles_dir.glob("*.md"), reverse=True):
        content = fp.read_text(encoding="utf-8")

        # frontmatter パース
        meta, body = {}, content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except Exception:
                    pass

        title = meta.get("title", fp.stem)
        date = meta.get("date", "")
        tags = meta.get("tags", [])
        status = meta.get("note_status", "draft")

        # コピー用テキスト（タイトル＋本文）
        copy_text = f"{title}\n\n{body}"

        result.append({
            "title": title,
            "date": str(date)[:10] if date else "",
            "tags": [str(t) for t in tags],
            "status": status,
            "body": body,
            "copy_text": copy_text,
            "filename": fp.name,
        })

    return jsonify({"articles": result})


@app.route("/api/note-drafts/delete", methods=["POST"])
def api_note_drafts_delete():
    data = request.get_json(force=True)
    filename = data.get("filename", "").strip()

    if not filename or "/" in filename or "\\" in filename or not filename.endswith(".md"):
        return jsonify({"ok": False, "error": "invalid filename"})

    fp = Path("posts/note/articles") / filename
    if not fp.exists():
        return jsonify({"ok": False, "error": "file not found"})

    fp.unlink()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
