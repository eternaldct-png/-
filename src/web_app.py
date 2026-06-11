"""
kazuto 投稿文ジェネレーター — スマホ対応Webアプリ

スマホで開いてボタンを押すだけで投稿文を生成し、コピーできる。
自動投稿なし。X API 不要。
"""
import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, session, redirect
from markupsafe import escape

sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))


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
  <a href="/schedule" style="margin-left:auto;text-decoration:none;display:flex;align-items:center;gap:4px;background:#181838;border:1.5px solid #2a2a4a;border-radius:10px;padding:7px 10px;color:#a78bfa;font-size:13px;font-weight:600;flex-shrink:0;">📅<span>予定</span></a>
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


# ── 商品購入ページ /goods（Stripe決済 + 注文一覧）──────────────────

def _load_goods_products():
    """persona/goods_config.yaml から販売商品の一覧を読み込む"""
    import yaml

    path = Path("persona/goods_config.yaml")
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    products = data.get("products", [])
    return [p for p in products if p.get("id") and p.get("name") and (p.get("price") or p.get("variants"))]


GOODS_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>商品のご注文・お支払い | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff; --surface2: #f1f0fa;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent-text: #9333ea; --accent-glow: rgba(124,58,237,0.10);
  --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding-bottom: 40px;
}
.header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 28px 18px 24px; text-align: center;
}
.header .badge {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
  color: white; background: var(--grad); padding: 4px 14px; border-radius: 999px; margin-bottom: 10px;
}
.header h1 { font-size: 19px; font-weight: 800; }
.header p { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.6; }
.main { padding: 22px 16px; max-width: 480px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.product-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 20px;
  box-shadow: var(--shadow);
}
.product-icon {
  width: 52px; height: 52px; border-radius: 14px; background: var(--grad);
  display: flex; align-items: center; justify-content: center; font-size: 24px; margin-bottom: 14px;
}
.product-photo {
  width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 14px;
  margin-bottom: 14px; border: 1px solid var(--border); background: var(--surface2);
}
.product-name { font-size: 17px; font-weight: 800; margin-bottom: 6px; }
.product-desc { font-size: 13px; color: var(--muted); line-height: 1.7; margin-bottom: 14px; white-space: pre-wrap; }
.variant-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.variant-label { font-size: 12px; font-weight: 700; color: var(--muted); min-width: 52px; flex-shrink: 0; }
.variant-select {
  flex: 1; padding: 9px 12px; border: 1.5px solid var(--border); border-radius: 10px;
  font-size: 14px; background: var(--surface2); color: var(--text); cursor: pointer;
  -webkit-appearance: none; appearance: none;
}
.variant-select:focus { outline: none; border-color: var(--accent-text); }
.product-price { font-size: 22px; font-weight: 800; color: var(--accent-text); margin-bottom: 16px; }
.buy-btn {
  width: 100%; padding: 15px; border: none; border-radius: 12px;
  background: var(--grad); color: white;
  font-size: 15px; font-weight: 800; cursor: pointer; letter-spacing: 0.02em;
  transition: opacity 0.2s, transform 0.1s;
  box-shadow: 0 6px 18px rgba(217,70,239,0.28);
}
.buy-btn:active { opacity: 0.85; transform: scale(0.98); }
.buy-btn:disabled { opacity: 0.4; cursor: not-allowed; box-shadow: none; }
.note { font-size: 12px; color: var(--muted); text-align: center; line-height: 1.8; margin-top: 4px; }
.empty { text-align: center; padding: 48px 24px; color: var(--muted); font-size: 14px; }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(10px);
  background: var(--surface); border: 1px solid #ef4444; color: #ef4444; box-shadow: var(--shadow);
  padding: 10px 20px; border-radius: 999px; font-size: 13px; font-weight: 600;
  white-space: nowrap; opacity: 0; transition: all 0.2s; pointer-events: none; z-index: 999;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>
<div class="header">
  <span class="badge">ETERNAL d.c.t</span>
  <h1>🛍 商品のご注文</h1>
  <p>商品を選んでお手続きください。<br>お支払いは安全な決済画面（Stripe）で行われます。</p>
</div>
<div class="main">
  <div id="products"></div>
  <p class="note">「購入手続きへ進む」を押すと決済画面に移動します。<br>お届け先のご住所・お名前・ご連絡先は決済画面でご入力いただきます。</p>
</div>
<div class="toast" id="toast"></div>
<script>
const PRODUCTS = __PRODUCTS_JSON__;
const _IMG_MAP = {};
PRODUCTS.forEach(p => { if (p.images) _IMG_MAP[p.id] = p.images; });

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function selOpts(items) {
  return items.map(item => {
    const val = item.label || item;
    const extra = item.price ? ` — ¥${item.price.toLocaleString()}` : '';
    const pa = item.price ? ` data-price="${item.price}"` : '';
    return `<option value="${escHtml(val)}"${pa}>${escHtml(val)}${extra}</option>`;
  }).join('');
}

function renderCard(p) {
  const v = p.variants && p.variants.size ? p.variants : null;
  const initPrice = v ? v.size[0].price : p.price;
  const initImg = p.images ? p.images[0].path : (p.image || null);
  const imgHtml = initImg
    ? `<img class="product-photo" id="img-${p.id}" src="${escHtml(initImg)}" alt="${escHtml(p.name)}">`
    : `<div class="product-icon">🛍</div>`;
  const varHtml = v ? `
    <div class="variant-row"><span class="variant-label">サイズ</span>
      <select class="variant-select" id="size-${p.id}" onchange="updatePrice('${p.id}',this)">${selOpts(v.size)}</select></div>
    ${v.color ? `<div class="variant-row"><span class="variant-label">カラー</span>
      <select class="variant-select" id="color-${p.id}" onchange="updateImage('${p.id}')">${selOpts(v.color)}</select></div>` : ''}
    ${v.design ? `<div class="variant-row"><span class="variant-label">デザイン</span>
      <select class="variant-select" id="design-${p.id}" onchange="updateImage('${p.id}')">${selOpts(v.design)}</select></div>` : ''}
  ` : '';
  return `<div class="product-card">
    ${imgHtml}
    <div class="product-name">${escHtml(p.name)}</div>
    ${p.description ? `<div class="product-desc">${escHtml(p.description)}</div>` : ''}
    ${varHtml}
    <div class="product-price" id="price-${p.id}">¥${initPrice.toLocaleString()}</div>
    <button class="buy-btn" onclick="checkout('${p.id}',this)">購入手続きへ進む</button>
  </div>`;
}

function render() {
  const el = document.getElementById('products');
  el.innerHTML = PRODUCTS.length ? PRODUCTS.map(renderCard).join('') : '<div class="empty">現在販売中の商品はありません。</div>';
}

function updatePrice(pid, sel) {
  const price = parseInt(sel.options[sel.selectedIndex].dataset.price || '0');
  if (price) document.getElementById('price-' + pid).textContent = '¥' + price.toLocaleString('ja-JP');
}

function updateImage(pid) {
  const imgs = _IMG_MAP[pid];
  if (!imgs) return;
  const colorEl = document.getElementById('color-' + pid);
  const designEl = document.getElementById('design-' + pid);
  const color = colorEl ? colorEl.value : null;
  const design = designEl ? designEl.value : null;
  const match = imgs.find(img => (!color || img.color === color) && (!design || img.design === design));
  if (match) document.getElementById('img-' + pid).src = match.path;
}

async function checkout(productId, btn) {
  btn.disabled = true;
  btn.textContent = '処理中…';
  const sizeEl = document.getElementById('size-' + productId);
  const colorEl = document.getElementById('color-' + productId);
  const designEl = document.getElementById('design-' + productId);
  const payload = { product_id: productId };
  if (sizeEl) payload.size = sizeEl.value;
  if (colorEl) payload.color = colorEl.value;
  if (designEl) payload.design = designEl.value;
  try {
    const res = await fetch('/api/goods/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.ok && data.url) { window.location.href = data.url; return; }
    toast(data.error || '決済画面の準備に失敗しました');
  } catch (e) {
    toast('通信エラーが発生しました');
  }
  btn.disabled = false;
  btn.textContent = '購入手続きへ進む';
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

render();
</script>
</body>
</html>"""


GOODS_RESULT_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>__TITLE__ | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
  box-shadow: var(--shadow);
  padding: 40px 30px; max-width: 380px; text-align: center;
}
.icon-badge {
  width: 64px; height: 64px; border-radius: 50%; background: var(--grad);
  display: flex; align-items: center; justify-content: center; font-size: 30px;
  margin: 0 auto 18px;
}
h1 { font-size: 18px; margin-bottom: 10px; font-weight: 800; }
p { font-size: 14px; color: var(--muted); line-height: 1.8; margin-bottom: 24px; }
a {
  display: inline-block; padding: 13px 30px; border-radius: 10px;
  background: var(--grad); color: white; font-weight: 700; font-size: 14px;
  text-decoration: none; box-shadow: 0 6px 18px rgba(217,70,239,0.28);
}
</style>
</head>
<body>
<div class="card">
  <div class="icon-badge">__ICON__</div>
  <h1>__HEADLINE__</h1>
  <p>__MESSAGE__</p>
  <a href="/goods">商品一覧に戻る</a>
</div>
</body>
</html>"""


GOODS_ADMIN_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>注文管理ログイン | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent: #9333ea; --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; box-shadow: var(--shadow); padding: 36px 28px; max-width: 340px; width: 100%; }
h1 { font-size: 17px; margin-bottom: 20px; text-align: center; font-weight: 800; }
input {
  width: 100%; padding: 13px 14px; margin-bottom: 14px;
  background: var(--bg); border: 1.5px solid var(--border); border-radius: 10px;
  color: var(--text); font-size: 15px; outline: none;
}
input:focus { border-color: var(--accent); }
button {
  width: 100%; padding: 14px; border: none; border-radius: 10px;
  background: var(--grad); color: white;
  font-size: 15px; font-weight: 700; cursor: pointer;
  box-shadow: 0 6px 18px rgba(217,70,239,0.28);
}
.error { color: #ef4444; font-size: 13px; text-align: center; margin-top: 14px; }
</style>
</head>
<body>
<div class="card">
  <h1>🔒 注文管理ログイン</h1>
  <form method="POST">
    <input type="password" name="password" placeholder="パスワード" autofocus required>
    <button type="submit">ログイン</button>
  </form>
  __ERROR__
</div>
</body>
</html>"""


GOODS_ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>注文一覧 | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding: 22px;
}
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 10px; }
.header h1 { font-size: 19px; font-weight: 800; }
.header .count { font-size: 13px; color: var(--muted); }
.header a {
  font-size: 13px; font-weight: 700; color: white; text-decoration: none;
  background: var(--grad); padding: 8px 16px; border-radius: 999px;
  box-shadow: 0 6px 18px rgba(217,70,239,0.22);
}
.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); box-shadow: var(--shadow); }
table { border-collapse: collapse; width: 100%; min-width: 760px; font-size: 13px; }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { background: var(--surface2, #f7f5fc); color: var(--muted); font-weight: 700; position: sticky; top: 0; }
td { background: var(--surface); }
tr:last-child td { border-bottom: none; }
td.address, td.contact, td.product { white-space: normal; min-width: 160px; }
.empty-row { text-align: center; color: var(--muted); padding: 48px 16px; white-space: normal; }
.note { font-size: 12px; color: var(--muted); margin-top: 16px; line-height: 1.8; }
.note a { color: var(--accent-text); font-weight: 600; }
</style>
</head>
<body>
<div class="header">
  <h1>📋 注文一覧</h1>
  <span class="count">__COUNT__ 件（お支払い完了分）</span>
  <a href="/goods/admin/logout">ログアウト</a>
</div>
<div class="table-wrap">
<table>
  <thead>
    <tr>
      <th>日時</th><th>商品</th><th>オプション</th><th>金額</th><th>お名前</th><th>お届け先住所</th><th>連絡先</th>
    </tr>
  </thead>
  <tbody>
    __ROWS__
  </tbody>
</table>
</div>
<p class="note">
  この一覧は Stripe に保存された注文情報をもとに表示しています（このサイト側ではお客様の個人情報を保存していません）。<br>
  より詳しい情報や返金などの操作は <a href="https://dashboard.stripe.com/payments">Stripe ダッシュボード</a> から行えます。
</p>
</body>
</html>"""


def _fetch_goods_orders(limit=100):
    """Stripe から /goods 経由の支払い完了済みセッションを取得し、一覧用データに整形する"""
    import stripe
    from datetime import datetime
    from zoneinfo import ZoneInfo

    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return []
    stripe.api_key = secret_key

    JST = ZoneInfo("Asia/Tokyo")
    orders = []
    try:
        result = stripe.checkout.Session.list(limit=limit)
        for s in result.auto_paging_iter():
            if s.get("payment_status") != "paid":
                continue
            metadata = s.get("metadata") or {}
            if "product_id" not in metadata:
                continue  # /goods 以外で作られたセッションは除外

            shipping = s.get("shipping_details") or s.get("shipping") or {}
            address = shipping.get("address") or {}
            customer = s.get("customer_details") or {}

            address_str = "".join(part for part in [
                address.get("postal_code", ""),
                address.get("state", ""),
                address.get("city", ""),
                address.get("line1", ""),
                address.get("line2", ""),
            ] if part)
            contact_str = " / ".join(part for part in [
                customer.get("email", ""),
                customer.get("phone", ""),
            ] if part)

            options_str = " / ".join(p for p in [
                metadata.get("color", ""), metadata.get("design", ""), metadata.get("size", ""),
            ] if p)
            orders.append({
                "date": datetime.fromtimestamp(s["created"], JST).strftime("%Y-%m-%d %H:%M"),
                "product": metadata.get("product_name", ""),
                "options": options_str,
                "amount": s.get("amount_total") or 0,
                "name": shipping.get("name") or customer.get("name") or "",
                "address": address_str,
                "contact": contact_str,
            })
    except Exception as e:
        print(f"[goods] Stripe fetch error: {e}")

    return orders


@app.route("/goods")
def goods_index():
    import json

    products = _load_goods_products()
    products_json = json.dumps(products, ensure_ascii=False).replace("</", "<\\/")
    html = GOODS_HTML.replace("__PRODUCTS_JSON__", products_json)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/goods/checkout", methods=["POST"])
def api_goods_checkout():
    import stripe

    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return jsonify({"error": "決済機能が設定されていません（管理者にお問い合わせください）"}), 500
    stripe.api_key = secret_key

    data = request.get_json(force=True)
    product_id = str(data.get("product_id", "")).strip()
    product = next((p for p in _load_goods_products() if p["id"] == product_id), None)
    if not product:
        return jsonify({"error": "商品が見つかりませんでした"}), 404

    selected_size = str(data.get("size", "")).strip()
    selected_color = str(data.get("color", "")).strip()
    selected_design = str(data.get("design", "")).strip()

    size_variants = (product.get("variants") or {}).get("size") or []
    if size_variants:
        matched = next((s for s in size_variants if s.get("label") == selected_size), None)
        if not matched:
            return jsonify({"error": "サイズを選択してください"}), 400
        unit_price = int(matched["price"])
    else:
        unit_price = int(product["price"])

    option_parts = [p for p in [selected_color, selected_design, selected_size] if p]
    display_name = f"{product['name']} [{' / '.join(option_parts)}]" if option_parts else product["name"]

    metadata = {"product_id": product["id"], "product_name": product["name"]}
    if selected_size:   metadata["size"] = selected_size
    if selected_color:  metadata["color"] = selected_color
    if selected_design: metadata["design"] = selected_design

    base_url = request.url_root.rstrip("/")
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {"name": display_name},
                    "unit_amount": unit_price,
                },
                "quantity": 1,
            }],
            shipping_address_collection={"allowed_countries": ["JP"]},
            phone_number_collection={"enabled": True},
            metadata=metadata,
            success_url=f"{base_url}/goods/success",
            cancel_url=f"{base_url}/goods/cancel",
        )
        return jsonify({"ok": True, "url": checkout_session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/goods/success")
def goods_success():
    html = (GOODS_RESULT_HTML
            .replace("__TITLE__", "ご注文ありがとうございます")
            .replace("__ICON__", "✅")
            .replace("__HEADLINE__", "ご注文ありがとうございます")
            .replace("__MESSAGE__", "決済が完了しました。ご入力いただいた内容を確認のうえ、発送のご連絡をいたします。"))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/goods/cancel")
def goods_cancel():
    html = (GOODS_RESULT_HTML
            .replace("__TITLE__", "お手続きがキャンセルされました")
            .replace("__ICON__", "↩️")
            .replace("__HEADLINE__", "お手続きがキャンセルされました")
            .replace("__MESSAGE__", "決済は行われていません。引き続き商品をご検討の場合は商品一覧からもう一度お手続きください。"))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/goods/admin", methods=["GET", "POST"])
def goods_admin():
    web_password = os.environ.get("WEB_PASSWORD", "")
    error_html = ""

    if request.method == "POST":
        if web_password and request.form.get("password", "") == web_password:
            session["goods_admin_ok"] = True
        else:
            error_html = '<p class="error">パスワードが違います</p>'

    if not session.get("goods_admin_ok"):
        html = GOODS_ADMIN_LOGIN_HTML.replace("__ERROR__", error_html)
        return html, (200 if not error_html else 401), {"Content-Type": "text/html; charset=utf-8"}

    orders = _fetch_goods_orders()
    if orders:
        rows = "".join(
            "<tr>"
            f"<td>{escape(o['date'])}</td>"
            f"<td class='product'>{escape(o['product'])}</td>"
            f"<td>{escape(o.get('options',''))}</td>"
            f"<td>¥{o['amount']:,}</td>"
            f"<td>{escape(o['name'])}</td>"
            f"<td class='address'>{escape(o['address'])}</td>"
            f"<td class='contact'>{escape(o['contact'])}</td>"
            "</tr>"
            for o in orders
        )
    else:
        rows = '<tr><td colspan="7" class="empty-row">注文はまだありません</td></tr>'

    html = GOODS_ADMIN_HTML.replace("__ROWS__", rows).replace("__COUNT__", str(len(orders)))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/goods/admin/logout")
def goods_admin_logout():
    session.pop("goods_admin_ok", None)
    return redirect("/goods/admin")


# ── スケジュールカレンダー ─────────────────────────────────────────

import uuid as _uuid
from pathlib import Path as _Path

_SCHEDULE_FILE = _Path("posts/schedule_events.json")


def _load_schedule():
    import json
    if _SCHEDULE_FILE.exists():
        with open(_SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_schedule(events):
    import json
    _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


SCHEDULE_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0d0d1f">
<title>スケジュール — kazuto</title>
<style>
:root {
  --bg: #0d0d1f;
  --surface: #181830;
  --surface2: #21213d;
  --accent: #7c3aed;
  --accent-light: #a78bfa;
  --text: #e2e8f0;
  --muted: #8892a4;
  --border: #2a2a4a;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --live: #ef4444;
  --goods: #f59e0b;
  --general: #818cf8;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  min-height: 100vh;
  padding-bottom: calc(84px + var(--safe-bottom));
}
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 14px 16px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  position: sticky; top: 0; z-index: 100;
}
.back-btn {
  color: var(--accent-light); text-decoration: none;
  font-size: 24px; line-height: 1; padding: 2px 4px 2px 0; flex-shrink: 0;
}
.header-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #2563eb, #1e40af);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 19px; flex-shrink: 0;
}
.header-title { font-size: 16px; font-weight: 700; }
.header-sub { font-size: 11px; color: var(--muted); margin-top: 1px; }
.month-nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px 8px;
  max-width: 540px; margin: 0 auto;
}
.month-btn {
  background: var(--surface); border: 1.5px solid var(--border);
  color: var(--text); width: 36px; height: 36px; border-radius: 10px;
  font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}
.month-btn:active { background: var(--surface2); }
.month-label { font-size: 17px; font-weight: 700; }
.legend {
  display: flex; gap: 12px; flex-wrap: wrap;
  padding: 4px 16px 10px;
  max-width: 540px; margin: 0 auto;
}
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--muted); }
.legend-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
.cal-wrap { max-width: 540px; margin: 0 auto; padding: 0 10px; }
.cal-header {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin-bottom: 3px;
}
.cal-header > div {
  text-align: center; font-size: 11px; font-weight: 600;
  color: var(--muted); padding: 3px 0;
}
.cal-header > .sat { color: #60a5fa; }
.cal-header > .sun { color: #f87171; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.cal-cell {
  min-height: 62px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 4px 3px 2px;
  cursor: pointer;
  transition: background 0.12s;
  overflow: hidden;
}
.cal-cell:active { background: var(--surface2); }
.cal-cell.other-month { opacity: 0.3; }
.day-num {
  font-size: 12px; font-weight: 600;
  width: 21px; height: 21px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 2px;
}
.cal-cell.today .day-num {
  background: var(--accent); color: white; border-radius: 50%;
}
.cal-cell.sat .day-num { color: #60a5fa; }
.cal-cell.sun .day-num { color: #f87171; }
.cal-cell.today.sat .day-num,
.cal-cell.today.sun .day-num { color: white; }
.event-chip {
  display: block; font-size: 9.5px; font-weight: 600;
  border-radius: 3px; padding: 1px 3px; margin-bottom: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  cursor: pointer; color: white;
}
.event-chip.live    { background: var(--live); }
.event-chip.goods   { background: var(--goods); }
.event-chip.general { background: var(--general); }
.event-more { font-size: 9px; color: var(--muted); }
.fab {
  position: fixed;
  bottom: calc(22px + var(--safe-bottom));
  right: 18px;
  width: 54px; height: 54px;
  background: var(--accent);
  border: none; border-radius: 50%; color: white;
  font-size: 26px; cursor: pointer;
  box-shadow: 0 4px 20px rgba(124,58,237,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; transition: transform 0.15s;
}
.fab:active { transform: scale(0.91); }
/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.72);
  z-index: 300; display: none; align-items: flex-end; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal {
  background: var(--surface); border-radius: 20px 20px 0 0;
  width: 100%; max-width: 540px; max-height: 92vh; overflow-y: auto;
  padding: 18px 16px calc(18px + var(--safe-bottom));
}
.modal-handle {
  width: 36px; height: 4px; background: var(--border);
  border-radius: 2px; margin: 0 auto 14px;
}
.modal-title { font-size: 17px; font-weight: 700; margin-bottom: 16px; }
.form-group { margin-bottom: 12px; }
.form-label {
  display: block; font-size: 10px; font-weight: 700;
  color: var(--muted); letter-spacing: 0.07em; text-transform: uppercase;
  margin-bottom: 5px;
}
.form-input {
  width: 100%; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--text); font-size: 14px; padding: 9px 11px; outline: none;
}
.form-input:focus { border-color: var(--accent); }
textarea.form-input { min-height: 64px; resize: vertical; font-family: inherit; }
select.form-input { appearance: none; }
.type-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
.type-btn {
  padding: 9px 4px; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; color: var(--muted); font-size: 12px; font-weight: 600;
  cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 3px;
  transition: all 0.13s;
}
.type-btn .ti { font-size: 17px; }
.type-btn.active-live    { border-color: var(--live);    color: var(--live);    background: rgba(239,68,68,0.1); }
.type-btn.active-goods   { border-color: var(--goods);   color: var(--goods);   background: rgba(245,158,11,0.1); }
.type-btn.active-general { border-color: var(--general); color: var(--general); background: rgba(129,140,248,0.1); }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.toggle-row {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; padding: 9px 11px;
}
.toggle-lbl { font-size: 13px; }
.toggle { position: relative; width: 42px; height: 24px; }
.toggle input { opacity: 0; width: 0; height: 0; }
.tslider {
  position: absolute; inset: 0; background: var(--border);
  border-radius: 12px; cursor: pointer; transition: background 0.2s;
}
.tslider::before {
  content: ""; position: absolute; width: 18px; height: 18px;
  border-radius: 50%; background: white; top: 3px; left: 3px;
  transition: transform 0.2s;
}
.toggle input:checked + .tslider { background: var(--accent); }
.toggle input:checked + .tslider::before { transform: translateX(18px); }
.btn-row { display: flex; gap: 8px; margin-top: 16px; }
.btn-save {
  flex: 1; padding: 13px; background: var(--accent); border: none;
  border-radius: 12px; color: white; font-size: 14px; font-weight: 700;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-save:active { opacity: 0.8; }
.btn-cancel {
  padding: 13px 16px; background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 12px; color: var(--muted); font-size: 14px; font-weight: 600; cursor: pointer;
}
.btn-del {
  padding: 13px 14px; background: rgba(239,68,68,0.1);
  border: 1.5px solid var(--live); border-radius: 12px;
  color: var(--live); font-size: 14px; font-weight: 600; cursor: pointer;
}
.gcal-badge {
  display: inline-flex; align-items: center; gap: 4px;
  background: rgba(66,133,244,0.12); border: 1px solid rgba(66,133,244,0.3);
  color: #60a5fa; border-radius: 6px; font-size: 11px; padding: 3px 8px; margin-bottom: 4px;
}
.toast {
  position: fixed; bottom: calc(88px + var(--safe-bottom)); left: 50%;
  transform: translateX(-50%) translateY(16px);
  background: var(--surface2); border: 1px solid var(--border); color: var(--text);
  padding: 9px 16px; border-radius: 20px; font-size: 13px;
  opacity: 0; transition: all 0.28s; white-space: nowrap; z-index: 400; pointer-events: none;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>

<div class="header">
  <a href="/" class="back-btn">‹</a>
  <div class="header-icon">📅</div>
  <div>
    <div class="header-title">スケジュール</div>
    <div class="header-sub">予定管理 &amp; Google カレンダー同期</div>
  </div>
  <button id="auth-btn" onclick="onAuthBtnClick()" style="margin-left:auto;background:#21213d;border:1.5px solid #2a2a4a;border-radius:10px;padding:7px 11px;color:#8892a4;font-size:12px;font-weight:600;cursor:pointer;flex-shrink:0;">🔒 ログイン</button>
</div>

<div class="month-nav">
  <button class="month-btn" onclick="changeMonth(-1)">‹</button>
  <span class="month-label" id="month-label"></span>
  <button class="month-btn" onclick="changeMonth(1)">›</button>
</div>

<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:var(--live)"></div>配信/ライブ</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--goods)"></div>グッズ/販売</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--general)"></div>汎用メモ</div>
</div>

<div class="cal-wrap">
  <div class="cal-header">
    <div>月</div><div>火</div><div>水</div><div>木</div><div>金</div>
    <div class="sat">土</div><div class="sun">日</div>
  </div>
  <div class="cal-grid" id="cal-grid"></div>
</div>

<button class="fab" id="fab" onclick="requireAuth(()=>openModal(null))" style="display:none">＋</button>

<!-- Modal -->
<div class="modal-overlay" id="modal-overlay" onclick="onBgClick(event)">
  <div class="modal" id="modal">
    <div class="modal-handle"></div>
    <div class="modal-title" id="modal-title">予定を追加</div>

    <div class="form-group">
      <label class="form-label">タイトル</label>
      <input type="text" class="form-input" id="f-title" placeholder="予定のタイトル">
    </div>

    <div class="form-group">
      <label class="form-label">種類</label>
      <div class="type-grid">
        <button class="type-btn" id="btn-live"    onclick="setType('live')">
          <span class="ti">🔴</span>配信/ライブ
        </button>
        <button class="type-btn" id="btn-goods"   onclick="setType('goods')">
          <span class="ti">🛍️</span>グッズ/販売
        </button>
        <button class="type-btn" id="btn-general" onclick="setType('general')">
          <span class="ti">📝</span>汎用メモ
        </button>
      </div>
    </div>

    <div class="form-group" id="platform-group" style="display:none">
      <label class="form-label">プラットフォーム</label>
      <select class="form-input" id="f-platform">
        <option value="">選択してください</option>
        <option value="YouTube">YouTube</option>
        <option value="TikTok">TikTok</option>
        <option value="X">X (Twitter)</option>
        <option value="Instagram">Instagram</option>
        <option value="その他">その他</option>
      </select>
    </div>

    <div class="form-group">
      <div class="toggle-row">
        <span class="toggle-lbl">終日</span>
        <label class="toggle">
          <input type="checkbox" id="f-all-day" onchange="onAllDayChange()">
          <span class="tslider"></span>
        </label>
      </div>
    </div>

    <div id="dt-fields">
      <div class="form-group">
        <div class="row2">
          <div>
            <label class="form-label">開始日</label>
            <input type="date" class="form-input" id="f-start-date">
          </div>
          <div>
            <label class="form-label">開始時刻</label>
            <input type="time" class="form-input" id="f-start-time" value="20:00">
          </div>
        </div>
      </div>
      <div class="form-group">
        <div class="row2">
          <div>
            <label class="form-label">終了日</label>
            <input type="date" class="form-input" id="f-end-date">
          </div>
          <div>
            <label class="form-label">終了時刻</label>
            <input type="time" class="form-input" id="f-end-time" value="22:00">
          </div>
        </div>
      </div>
    </div>

    <div id="ad-fields" style="display:none">
      <div class="form-group">
        <div class="row2">
          <div>
            <label class="form-label">開始日</label>
            <input type="date" class="form-input" id="f-start-date-ad">
          </div>
          <div>
            <label class="form-label">終了日</label>
            <input type="date" class="form-input" id="f-end-date-ad">
          </div>
        </div>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">メモ</label>
      <textarea class="form-input" id="f-desc" placeholder="詳細・メモ（任意）"></textarea>
    </div>

    <div id="gcal-status"></div>

    <div class="btn-row" id="btn-create">
      <button class="btn-cancel" onclick="closeModal()">キャンセル</button>
      <button class="btn-save"   onclick="saveEvent()">保存</button>
    </div>
    <div class="btn-row" id="btn-edit" style="display:none">
      <button class="btn-del"  onclick="deleteEvent()">削除</button>
      <button class="btn-save" onclick="saveEvent()">保存</button>
    </div>
  </div>
</div>

<!-- Login Modal -->
<div class="modal-overlay" id="login-overlay" onclick="onLoginBgClick(event)">
  <div class="modal" id="login-modal">
    <div class="modal-handle"></div>
    <div class="modal-title">ログイン</div>
    <div class="form-group">
      <label class="form-label">パスワード</label>
      <input type="password" class="form-input" id="login-pw" placeholder="パスワードを入力"
        onkeydown="if(event.key==='Enter')doLogin()">
    </div>
    <div id="login-err" style="color:#ef4444;font-size:13px;margin-bottom:8px;display:none"></div>
    <div class="btn-row">
      <button class="btn-cancel" onclick="closeLoginModal()">キャンセル</button>
      <button class="btn-save"   onclick="doLogin()">ログイン</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let curYear, curMonth, allEvents = [], editingId = null, selType = 'general';
let isAuthed = false;

(function() {
  const n = new Date();
  curYear = n.getFullYear(); curMonth = n.getMonth();
  checkAuth().then(fetchEvents);
})();

async function checkAuth() {
  try {
    const r = await fetch('/api/schedule/me');
    const d = await r.json();
    isAuthed = d.authed || false;
  } catch(e) { isAuthed = false; }
  updateAuthUI();
}

function updateAuthUI() {
  const btn = document.getElementById('auth-btn');
  if (isAuthed) {
    btn.textContent = '🔓 ログアウト';
    btn.style.color = '#a78bfa';
    btn.style.borderColor = '#7c3aed';
  } else {
    btn.textContent = '🔒 ログイン';
    btn.style.color = '#8892a4';
    btn.style.borderColor = '#2a2a4a';
  }
  document.getElementById('fab').style.display = isAuthed ? 'flex' : 'none';
}

function onAuthBtnClick() {
  if (isAuthed) {
    fetch('/schedule/logout').then(() => { isAuthed = false; updateAuthUI(); toast('ログアウトしました'); });
  } else {
    openLoginModal();
  }
}

function openLoginModal() {
  document.getElementById('login-pw').value = '';
  document.getElementById('login-err').style.display = 'none';
  document.getElementById('login-overlay').classList.add('open');
  setTimeout(() => document.getElementById('login-pw').focus(), 80);
}

function closeLoginModal() {
  document.getElementById('login-overlay').classList.remove('open');
}

function onLoginBgClick(e) {
  if (e.target === document.getElementById('login-overlay')) closeLoginModal();
}

async function doLogin() {
  const pw = document.getElementById('login-pw').value;
  const errEl = document.getElementById('login-err');
  try {
    const r = await fetch('/schedule/login', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ password: pw }),
    });
    if (r.ok) {
      isAuthed = true; updateAuthUI(); closeLoginModal();
      toast('ログインしました');
      if (_pendingAction) { const fn = _pendingAction; _pendingAction = null; fn(); }
    } else {
      errEl.textContent = 'パスワードが違います'; errEl.style.display = 'block';
      document.getElementById('login-pw').value = '';
      document.getElementById('login-pw').focus();
    }
  } catch(e) {
    errEl.textContent = '通信エラーが発生しました'; errEl.style.display = 'block';
  }
}

let _pendingAction = null;

function requireAuth(fn) {
  if (isAuthed) { fn(); }
  else { _pendingAction = fn; openLoginModal(); }
}

async function fetchEvents() {
  try {
    const r = await fetch('/api/schedule/events');
    const d = await r.json();
    if (d.ok) allEvents = d.events || [];
  } catch(e) {}
  renderCal();
}

function changeMonth(delta) {
  curMonth += delta;
  if (curMonth < 0)  { curMonth = 11; curYear--; }
  if (curMonth > 11) { curMonth = 0;  curYear++; }
  renderCal();
}

function fmtDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function renderCal() {
  document.getElementById('month-label').textContent = `${curYear}年${curMonth+1}月`;
  const grid = document.getElementById('cal-grid');
  grid.innerHTML = '';

  const first = new Date(curYear, curMonth, 1);
  let dow = first.getDay(); // 0=Sun
  dow = dow === 0 ? 6 : dow - 1; // Mon-based offset

  const daysInMonth = new Date(curYear, curMonth+1, 0).getDate();
  const daysInPrev  = new Date(curYear, curMonth,   0).getDate();
  const todayStr = fmtDate(new Date());

  const cells = [];
  for (let i = dow-1; i >= 0; i--)
    cells.push({ d: daysInPrev-i, m: curMonth-1, y: curYear, other: true });
  for (let d = 1; d <= daysInMonth; d++)
    cells.push({ d, m: curMonth, y: curYear, other: false });
  const rem = (7 - cells.length % 7) % 7;
  for (let d = 1; d <= rem; d++)
    cells.push({ d, m: curMonth+1, y: curYear, other: true });

  cells.forEach(cell => {
    const dt = new Date(cell.y, cell.m, cell.d);
    const ds = fmtDate(dt);
    const wd = dt.getDay();
    const div = document.createElement('div');
    div.className = 'cal-cell'
      + (cell.other ? ' other-month' : '')
      + (ds === todayStr ? ' today' : '')
      + (wd === 6 ? ' sat' : wd === 0 ? ' sun' : '');

    const dn = document.createElement('div');
    dn.className = 'day-num'; dn.textContent = cell.d;
    div.appendChild(dn);

    const dayEvs = allEvents.filter(ev => (ev.start_datetime || '').slice(0,10) === ds);
    dayEvs.slice(0,3).forEach(ev => {
      const chip = document.createElement('div');
      chip.className = `event-chip ${ev.event_type || 'general'}`;
      chip.textContent = ev.title || '(無題)';
      chip.onclick = e => { e.stopPropagation(); requireAuth(()=>openEditModal(ev)); };
      div.appendChild(chip);
    });
    if (dayEvs.length > 3) {
      const more = document.createElement('div');
      more.className = 'event-more'; more.textContent = `+${dayEvs.length-3}`;
      div.appendChild(more);
    }
    div.onclick = () => requireAuth(()=>openModal(ds));
    grid.appendChild(div);
  });
}

function setType(type) {
  selType = type;
  ['live','goods','general'].forEach(t => {
    document.getElementById(`btn-${t}`).className = 'type-btn' + (t===type ? ` active-${t}` : '');
  });
  document.getElementById('platform-group').style.display = type==='live' ? 'block' : 'none';
}

function onAllDayChange() {
  const v = document.getElementById('f-all-day').checked;
  document.getElementById('dt-fields').style.display = v ? 'none' : 'block';
  document.getElementById('ad-fields').style.display = v ? 'block' : 'none';
}

function openModal(preDate) {
  editingId = null;
  document.getElementById('modal-title').textContent = '予定を追加';
  document.getElementById('btn-create').style.display = '';
  document.getElementById('btn-edit').style.display   = 'none';
  document.getElementById('gcal-status').innerHTML = '';
  document.getElementById('f-title').value = '';
  document.getElementById('f-desc').value  = '';
  document.getElementById('f-platform').value = '';
  document.getElementById('f-all-day').checked = false;
  onAllDayChange();
  const ds = preDate || fmtDate(new Date());
  ['f-start-date','f-end-date','f-start-date-ad','f-end-date-ad'].forEach(id => {
    document.getElementById(id).value = ds;
  });
  document.getElementById('f-start-time').value = '20:00';
  document.getElementById('f-end-time').value   = '22:00';
  setType('general');
  document.getElementById('modal-overlay').classList.add('open');
  setTimeout(() => document.getElementById('f-title').focus(), 80);
}

function openEditModal(ev) {
  editingId = ev.id;
  document.getElementById('modal-title').textContent = '予定を編集';
  document.getElementById('btn-create').style.display = 'none';
  document.getElementById('btn-edit').style.display   = '';
  document.getElementById('f-title').value = ev.title || '';
  document.getElementById('f-desc').value  = ev.description || '';
  document.getElementById('f-platform').value = ev.platform || '';
  const ad = ev.all_day || false;
  document.getElementById('f-all-day').checked = ad;
  onAllDayChange();
  const sd = (ev.start_datetime || '').slice(0,10);
  const st = (ev.start_datetime || '').slice(11,16) || '20:00';
  const ed = (ev.end_datetime   || '').slice(0,10)  || sd;
  const et = (ev.end_datetime   || '').slice(11,16) || '22:00';
  document.getElementById('f-start-date').value    = sd;
  document.getElementById('f-start-time').value    = st;
  document.getElementById('f-end-date').value      = ed;
  document.getElementById('f-end-time').value      = et;
  document.getElementById('f-start-date-ad').value = sd;
  document.getElementById('f-end-date-ad').value   = ed;
  setType(ev.event_type || 'general');
  document.getElementById('gcal-status').innerHTML = ev.google_calendar_event_id
    ? '<div class="gcal-badge">📅 Google カレンダーと同期済み</div>' : '';
  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  editingId = null;
}

function onBgClick(e) {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}

async function saveEvent() {
  const title = document.getElementById('f-title').value.trim();
  if (!title) { toast('タイトルを入力してください'); return; }
  const ad = document.getElementById('f-all-day').checked;
  let start, end;
  if (ad) {
    start = document.getElementById('f-start-date-ad').value;
    end   = document.getElementById('f-end-date-ad').value || start;
    if (!start) { toast('日付を入力してください'); return; }
  } else {
    const sd = document.getElementById('f-start-date').value;
    const st = document.getElementById('f-start-time').value || '00:00';
    const ed = document.getElementById('f-end-date').value || sd;
    const et = document.getElementById('f-end-time').value  || st;
    if (!sd) { toast('日付を入力してください'); return; }
    start = `${sd}T${st}:00+09:00`;
    end   = `${ed}T${et}:00+09:00`;
  }
  const body = {
    title,
    description: document.getElementById('f-desc').value.trim(),
    event_type:  selType,
    platform:    document.getElementById('f-platform').value,
    start_datetime: start,
    end_datetime:   end,
    all_day: ad,
  };
  try {
    const url    = editingId ? `/api/schedule/events/${editingId}` : '/api/schedule/events';
    const method = editingId ? 'PUT' : 'POST';
    const r = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const d = await r.json();
    if (d.ok) {
      closeModal();
      await fetchEvents();
      const synced = d.event && d.event.google_calendar_event_id;
      toast((editingId ? '更新しました' : '保存しました') + (synced ? ' ✓ Google同期' : ''));
    } else { toast('保存に失敗しました'); }
  } catch(e) { toast('通信エラーが発生しました'); }
}

async function deleteEvent() {
  if (!editingId) return;
  if (!confirm('この予定を削除しますか？\nGoogleカレンダーからも削除されます。')) return;
  try {
    const r = await fetch(`/api/schedule/events/${editingId}`, { method: 'DELETE' });
    const d = await r.json();
    if (d.ok) { closeModal(); await fetchEvents(); toast('削除しました'); }
    else { toast('削除に失敗しました'); }
  } catch(e) { toast('通信エラーが発生しました'); }
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2600);
}
</script>
</body>
</html>
"""


@app.route("/schedule")
def schedule_index():
    return SCHEDULE_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/schedule/events", methods=["GET"])
def api_schedule_list():
    return jsonify({"ok": True, "events": _load_schedule()})


@app.route("/api/schedule/me")
def api_schedule_me():
    return jsonify({"authed": bool(session.get("schedule_ok"))})


@app.route("/schedule/login", methods=["POST"])
def schedule_login():
    data = request.get_json(force=True)
    pw = os.environ.get("WEB_PASSWORD", "")
    if pw and data.get("password") == pw:
        session["schedule_ok"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "パスワードが違います"}), 401


@app.route("/schedule/logout")
def schedule_logout():
    session.pop("schedule_ok", None)
    return redirect("/schedule")


@app.route("/api/schedule/events", methods=["POST"])
def api_schedule_create():
    if not session.get("schedule_ok"):
        return jsonify({"error": "unauthorized"}), 401
    from datetime import datetime, timezone
    data = request.get_json(force=True)
    event = {
        "id": str(_uuid.uuid4()),
        "title": str(data.get("title", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "event_type": data.get("event_type", "general"),
        "platform": data.get("platform", ""),
        "start_datetime": data.get("start_datetime", ""),
        "end_datetime": data.get("end_datetime", ""),
        "all_day": bool(data.get("all_day", False)),
        "google_calendar_event_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from google_calendar import sync_create
        event["google_calendar_event_id"] = sync_create(event)
    except Exception:
        pass
    events = _load_schedule()
    events.append(event)
    _save_schedule(events)
    return jsonify({"ok": True, "event": event})


@app.route("/api/schedule/events/<event_id>", methods=["PUT"])
def api_schedule_update(event_id):
    if not session.get("schedule_ok"):
        return jsonify({"error": "unauthorized"}), 401
    from datetime import datetime, timezone
    data = request.get_json(force=True)
    events = _load_schedule()
    for i, ev in enumerate(events):
        if ev["id"] == event_id:
            events[i].update({
                "title": str(data.get("title", ev["title"])).strip(),
                "description": str(data.get("description", ev.get("description", ""))).strip(),
                "event_type": data.get("event_type", ev["event_type"]),
                "platform": data.get("platform", ev.get("platform", "")),
                "start_datetime": data.get("start_datetime", ev["start_datetime"]),
                "end_datetime": data.get("end_datetime", ev.get("end_datetime", "")),
                "all_day": bool(data.get("all_day", ev.get("all_day", False))),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            try:
                from google_calendar import sync_update
                sync_update(ev.get("google_calendar_event_id"), events[i])
            except Exception:
                pass
            _save_schedule(events)
            return jsonify({"ok": True, "event": events[i]})
    return jsonify({"error": "not found"}), 404


@app.route("/api/schedule/events/<event_id>", methods=["DELETE"])
def api_schedule_delete(event_id):
    if not session.get("schedule_ok"):
        return jsonify({"error": "unauthorized"}), 401
    events = _load_schedule()
    for i, ev in enumerate(events):
        if ev["id"] == event_id:
            try:
                from google_calendar import sync_delete
                sync_delete(ev.get("google_calendar_event_id"))
            except Exception:
                pass
            events.pop(i)
            _save_schedule(events)
            return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
