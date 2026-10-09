"""
kazuto 投稿文ジェネレーター — スマホ対応Webアプリ

スマホで開いてボタンを押すだけで投稿文を生成し、コピーできる。
自動投稿なし。X API 不要。
"""
import hmac
import os
import sys
from pathlib import Path
from flask import Flask, Response, request, jsonify, session, redirect
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


# ── 自分の声で読み上げ API（Gemini TTS）────────────────────────────
# 自分の声で好きな文章をしゃべらせられるので、WEB_PASSWORD でログインした人だけに限る。

@app.route("/api/tts/login", methods=["POST"])
def api_tts_login():
    web_password = os.environ.get("WEB_PASSWORD", "")
    if not web_password:
        return jsonify({"error": "WEB_PASSWORD が未設定のため、読み上げは使えません"}), 503
    data = request.get_json(silent=True) or {}
    password = str(data.get("password", ""))
    if not hmac.compare_digest(password.encode("utf-8"), web_password.encode("utf-8")):
        return jsonify({"error": "パスワードが違います"}), 401
    session["tts_ok"] = True
    return jsonify({"ok": True})


@app.route("/api/tts", methods=["POST"])
def api_tts():
    """投稿文を自分の声で読み上げた WAV を返す"""
    import voice_tts

    # JSON 以外は受け付けない（他サイトからフォーム送信で叩かれるのを防ぐ）
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "不正なリクエストです"}), 400
    if not session.get("tts_ok"):
        return jsonify({"error": "ログインが必要です", "need_login": True}), 401

    text = voice_tts.clean_text_for_speech(str(data.get("text", "")))
    if not text:
        return jsonify({"error": "読み上げる文章がありません"}), 400

    try:
        wav = voice_tts.synthesize(text)
    except voice_tts.TTSError as e:
        return jsonify({"error": str(e)}), 502
    return Response(wav, mimetype="audio/wav", headers={"Cache-Control": "no-store"})


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
.regen-btn:disabled { opacity: 0.5; cursor: wait; }

/* ── 自分の声で読み上げ ── */
.voice-area:empty { display: none; }
.voice-area {
  padding: 0 14px 12px;
  display: flex; flex-direction: column; gap: 6px;
}
.voice-area audio { width: 100%; height: 40px; }
.voice-note { font-size: 12px; color: var(--muted); line-height: 1.5; }
.voice-err { font-size: 12px; color: #ef4444; line-height: 1.5; word-break: break-word; }
.voice-dl {
  align-self: flex-start;
  font-size: 12px; font-weight: 700;
  color: var(--accent-light); text-decoration: none;
}

/* ── パスワード入力 ── */
.pw-modal {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.pw-modal[hidden] { display: none; }
.pw-box {
  width: 100%; max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 16px 16px;
}
.pw-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
.pw-note { font-size: 12px; color: var(--muted); line-height: 1.6; margin-bottom: 12px; }
.pw-actions { display: flex; gap: 8px; margin-top: 12px; }

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

<div class="pw-modal" id="pwModal" hidden>
  <form class="pw-box" onsubmit="submitTtsLogin(event)">
    <div class="pw-title">🔒 読み上げ機能のログイン</div>
    <div class="pw-note">自分の声で読み上げる機能は、パスワードを知っている人だけが使えます（/goods/admin と同じパスワード）。</div>
    <input id="pwInput" class="theme-input" type="password" autocomplete="current-password" placeholder="パスワード">
    <div class="pw-actions">
      <button type="button" class="regen-btn" onclick="closeTtsLogin()">キャンセル</button>
      <button type="submit" class="copy-btn">ログイン</button>
    </div>
  </form>
</div>

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

  const regenBtn = card.querySelector('.regen-btn:not(.voice-btn)');
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
      clearVoice(idx);
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
  Object.keys(voiceCache).forEach(clearVoice);
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
        <button class="regen-btn voice-btn" onclick="speakPost(${i})" title="自分の声で読み上げ">🔊</button>
        <button class="regen-btn" onclick="regenerateOne(${i})">🔄</button>
      </div>
      <div class="voice-area" id="voice-${i}"></div>
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
  if (voiceCache[idx] && voiceCache[idx].text !== ta.value) clearVoice(idx);
}

// ── 自分の声で読み上げ ──
const voiceCache = {};   // idx → { text, url }（同じ文章なら API を呼ばずに再生する）
let pendingVoiceIdx = null;

function clearVoice(idx) {
  const cached = voiceCache[idx];
  if (cached) URL.revokeObjectURL(cached.url);
  delete voiceCache[idx];
  const area = document.getElementById('voice-' + idx);
  if (area) area.innerHTML = '';
}

function showVoicePlayer(idx, url) {
  const area = document.getElementById('voice-' + idx);
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  const fname = `kazuto_voice_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}_${idx + 1}.wav`;
  area.innerHTML = `<audio controls src="${url}"></audio>
    <a class="voice-dl" href="${url}" download="${fname}">⬇️ 音声を保存（WAV）</a>`;
  area.querySelector('audio').play().catch(() => {});
}

async function speakPost(idx) {
  const ta = document.getElementById('text-' + idx);
  const area = document.getElementById('voice-' + idx);
  if (!ta || !area) return;
  const text = ta.value;
  if (!text.trim()) { toast('読み上げる文章がありません', 'err'); return; }

  const cached = voiceCache[idx];
  if (cached && cached.text === text) {
    const audio = area.querySelector('audio');
    if (audio) { audio.currentTime = 0; audio.play().catch(() => {}); return; }
  }

  const btn = ta.closest('.post-card').querySelector('.voice-btn');
  btn.textContent = '⌛';
  btn.disabled = true;
  area.innerHTML = '<div class="voice-note">🎙 自分の声で読み上げ中…（長い文章だと30秒ほどかかります）</div>';

  try {
    const res = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (res.ok) {
      const blob = await res.blob();
      // 待っている間に作り直し・書き換えをした場合は、古い音声を出さない
      if (!ta.isConnected || ta.value !== text) { area.innerHTML = ''; return; }
      clearVoice(idx);
      const url = URL.createObjectURL(blob);
      voiceCache[idx] = { text, url };
      showVoicePlayer(idx, url);
      return;
    }
    const data = await res.json().catch(() => ({}));
    if (data.need_login) {
      area.innerHTML = '';
      openTtsLogin(idx);
      return;
    }
    area.innerHTML = '';
    const err = document.createElement('div');
    err.className = 'voice-err';
    err.textContent = data.error || '読み上げに失敗しました';
    area.appendChild(err);
  } catch(e) {
    area.innerHTML = '<div class="voice-err">通信エラーが発生しました</div>';
  } finally {
    btn.textContent = '🔊';
    btn.disabled = false;
  }
}

function openTtsLogin(idx) {
  pendingVoiceIdx = idx;
  const input = document.getElementById('pwInput');
  input.value = '';
  document.getElementById('pwModal').hidden = false;
  input.focus();
}

function closeTtsLogin() {
  document.getElementById('pwModal').hidden = true;
  pendingVoiceIdx = null;
}

async function submitTtsLogin(ev) {
  ev.preventDefault();
  const password = document.getElementById('pwInput').value;
  try {
    const res = await fetch('/api/tts/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { toast(data.error || 'ログインに失敗しました', 'err'); return; }
    const idx = pendingVoiceIdx;
    closeTtsLogin();
    toast('ログインしました ✓', 'ok');
    if (idx !== null) speakPost(idx);
  } catch(e) {
    toast('通信エラーが発生しました', 'err');
  }
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


AUDITION_ADMIN_EDIT_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>応募データ編集 | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #fff; --surface2: #fcfbff;
  --accent: #7c3aed; --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280;
  --border: #e7e3f0; --warn: #9a5b00; --warn-bg: #fff7e6;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --shadow: 0 6px 24px rgba(124,58,237,.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  min-height: 100vh; padding: 24px; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
}
.page { width: min(900px, 100%); margin: 0 auto; }
.header { margin-bottom: 18px; }
.back { display: inline-block; color: var(--accent-text); text-decoration: none; font-size: 13px; font-weight: 800; margin-bottom: 12px; }
h1 { font-size: clamp(21px, 4vw, 28px); margin-bottom: 6px; }
.meta { color: var(--muted); font-size: 12px; }
.notice { background: var(--warn-bg); border: 1px solid #f3d3a1; color: var(--warn); padding: 12px 15px; border-radius: 12px; margin-bottom: 14px; font-size: 13px; line-height: 1.6; }
.error { background: #fff1f2; border: 1px solid #fecdd3; color: #b91c1c; padding: 12px 15px; border-radius: 12px; margin-bottom: 14px; font-size: 13px; font-weight: 700; }
.section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); padding: 20px; margin-bottom: 14px; }
.section h2 { font-size: 15px; margin-bottom: 16px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px; }
.field.full { grid-column: 1 / -1; }
label { display: block; color: var(--muted); font-size: 11px; font-weight: 800; margin-bottom: 6px; }
input, select, textarea {
  width: 100%; color: var(--text); background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; padding: 11px 12px; font: inherit; font-size: 14px; outline: none;
}
input:focus, select:focus, textarea:focus { border-color: #b794f6; box-shadow: 0 0 0 3px rgba(124,58,237,.1); }
textarea { min-height: 110px; line-height: 1.7; resize: vertical; }
.activity-field { background: var(--warn-bg); border: 1px solid #f3d3a1; border-radius: 13px; padding: 14px; }
.activity-field label { color: var(--warn); font-size: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; position: sticky; bottom: 10px; padding: 12px; border: 1px solid var(--border); border-radius: 14px; background: rgba(255,255,255,.94); backdrop-filter: blur(10px); box-shadow: var(--shadow); }
.button { border: 0; border-radius: 10px; padding: 11px 18px; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
.button.cancel { color: var(--muted); background: var(--bg); border: 1px solid var(--border); }
.button.save { color: white; background: var(--grad); box-shadow: 0 6px 18px rgba(217,70,239,.22); }
@media (max-width: 640px) {
  body { padding: 14px; }
  .section { padding: 16px; }
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: auto; }
  .actions { display: grid; grid-template-columns: 1fr 1.4fr; }
  .button { text-align: center; padding-inline: 10px; }
}
</style>
</head>
<body>
<div class="page">
  <header class="header">
    <a class="back" href="/audition/admin">← 応募一覧に戻る</a>
    <h1>✏️ 応募データを編集</h1>
    <p class="meta">応募日時：__CREATED_AT__　／　応募者：__DISPLAY_NAME__</p>
  </header>
  __ERROR__
  <p class="notice">活動名が未記入の場合は、下の欄に入力して「変更を保存する」を押してください。</p>
  <form method="POST">
    <input type="hidden" name="csrf_token" value="__CSRF_TOKEN__">
    <section class="section">
      <h2>活動名</h2>
      <div class="activity-field">
        <label for="activity_name">活動名（配信上の名前）</label>
        <input id="activity_name" type="text" name="activity_name" value="__ACTIVITY_NAME__" placeholder="例）かずと" autofocus>
      </div>
    </section>
    <section class="section">
      <h2>基本情報</h2>
      <div class="form-grid">
        <div class="field"><label for="name">お名前（本名）</label><input id="name" type="text" name="name" value="__NAME__" required></div>
        <div class="field"><label for="furigana">ふりがな</label><input id="furigana" type="text" name="furigana" value="__FURIGANA__"></div>
        <div class="field"><label for="gender">性別</label><select id="gender" name="gender">__GENDER_OPTIONS__</select></div>
        <div class="field"><label for="email">メール</label><input id="email" type="email" name="email" value="__EMAIL__"></div>
        <div class="field"><label for="prefecture">都道府県</label><select id="prefecture" name="prefecture">__PREFECTURE_OPTIONS__</select></div>
        <div class="field"><label for="minor_consent">未成年者の同意</label><select id="minor_consent" name="minor_consent">__MINOR_OPTIONS__</select></div>
      </div>
    </section>
    <section class="section">
      <h2>活動について</h2>
      <div class="form-grid">
        <div class="field"><label for="experience">配信・ライバー経験</label><select id="experience" name="experience">__EXPERIENCE_OPTIONS__</select></div>
        <div class="field"><label for="frequency">配信頻度</label><select id="frequency" name="frequency">__FREQUENCY_OPTIONS__</select></div>
        <div class="field full"><label for="history">活動歴・実績</label><textarea id="history" name="history">__HISTORY__</textarea></div>
        <div class="field full"><label for="genre">得意なジャンル・企画</label><textarea id="genre" name="genre">__GENRE__</textarea></div>
        <div class="field full"><label for="sns">SNSアカウント</label><textarea id="sns" name="sns">__SNS__</textarea></div>
      </div>
    </section>
    <section class="section">
      <h2>アピール</h2>
      <div class="form-grid">
        <div class="field full"><label for="self_pr">自己PR</label><textarea id="self_pr" name="self_pr">__SELF_PR__</textarea></div>
        <div class="field full"><label for="motivation">応募動機</label><textarea id="motivation" name="motivation">__MOTIVATION__</textarea></div>
        <div class="field full"><label for="other">その他</label><textarea id="other" name="other">__OTHER__</textarea></div>
      </div>
    </section>
    <div class="actions">
      <a class="button cancel" href="/audition/admin">キャンセル</a>
      <button class="button save" type="submit">変更を保存する</button>
    </div>
  </form>
</div>
</body>
</html>"""


AUDITION_ADMIN_NEW_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>応募データを手動で追加 | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #fff; --surface2: #fcfbff;
  --accent: #7c3aed; --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280;
  --border: #e7e3f0; --warn: #9a5b00; --warn-bg: #fff7e6;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --shadow: 0 6px 24px rgba(124,58,237,.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  min-height: 100vh; padding: 24px; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
}
.page { width: min(900px, 100%); margin: 0 auto; }
.header { margin-bottom: 18px; }
.back { display: inline-block; color: var(--accent-text); text-decoration: none; font-size: 13px; font-weight: 800; margin-bottom: 12px; }
h1 { font-size: clamp(21px, 4vw, 28px); margin-bottom: 6px; }
.meta { color: var(--muted); font-size: 12px; }
.notice { background: var(--warn-bg); border: 1px solid #f3d3a1; color: var(--warn); padding: 12px 15px; border-radius: 12px; margin-bottom: 14px; font-size: 13px; line-height: 1.6; }
.error { background: #fff1f2; border: 1px solid #fecdd3; color: #b91c1c; padding: 12px 15px; border-radius: 12px; margin-bottom: 14px; font-size: 13px; font-weight: 700; }
.section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); padding: 20px; margin-bottom: 14px; }
.section h2 { font-size: 15px; margin-bottom: 16px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px; }
.field.full { grid-column: 1 / -1; }
label { display: block; color: var(--muted); font-size: 11px; font-weight: 800; margin-bottom: 6px; }
input, select, textarea {
  width: 100%; color: var(--text); background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: 10px; padding: 11px 12px; font: inherit; font-size: 14px; outline: none;
}
input:focus, select:focus, textarea:focus { border-color: #b794f6; box-shadow: 0 0 0 3px rgba(124,58,237,.1); }
textarea { min-height: 110px; line-height: 1.7; resize: vertical; }
.activity-field { background: var(--warn-bg); border: 1px solid #f3d3a1; border-radius: 13px; padding: 14px; }
.activity-field label { color: var(--warn); font-size: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 10px; position: sticky; bottom: 10px; padding: 12px; border: 1px solid var(--border); border-radius: 14px; background: rgba(255,255,255,.94); backdrop-filter: blur(10px); box-shadow: var(--shadow); }
.button { border: 0; border-radius: 10px; padding: 11px 18px; font-size: 14px; font-weight: 800; cursor: pointer; text-decoration: none; }
.button.cancel { color: var(--muted); background: var(--bg); border: 1px solid var(--border); }
.button.save { color: white; background: var(--grad); box-shadow: 0 6px 18px rgba(217,70,239,.22); }
@media (max-width: 640px) {
  body { padding: 14px; }
  .section { padding: 16px; }
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: auto; }
  .actions { display: grid; grid-template-columns: 1fr 1.4fr; }
  .button { text-align: center; padding-inline: 10px; }
}
</style>
</head>
<body>
<div class="page">
  <header class="header">
    <a class="back" href="/audition/admin">← 応募一覧に戻る</a>
    <h1>➕ 応募データを手動で追加</h1>
    <p class="meta">Googleフォームや口頭・メールなどサイト外で届いた応募を、管理者が手動で登録します。</p>
  </header>
  __ERROR__
  <p class="notice">お名前だけ入力すれば登録できます。他の項目は分かる範囲で構いません。</p>
  <form method="POST">
    <input type="hidden" name="csrf_token" value="__CSRF_TOKEN__">
    <section class="section">
      <h2>活動名</h2>
      <div class="activity-field">
        <label for="activity_name">活動名（配信上の名前）</label>
        <input id="activity_name" type="text" name="activity_name" value="__ACTIVITY_NAME__" placeholder="例）かずと" autofocus>
      </div>
    </section>
    <section class="section">
      <h2>基本情報</h2>
      <div class="form-grid">
        <div class="field"><label for="name">お名前（本名）</label><input id="name" type="text" name="name" value="__NAME__" required></div>
        <div class="field"><label for="furigana">ふりがな</label><input id="furigana" type="text" name="furigana" value="__FURIGANA__"></div>
        <div class="field"><label for="gender">性別</label><select id="gender" name="gender">__GENDER_OPTIONS__</select></div>
        <div class="field"><label for="email">メール</label><input id="email" type="email" name="email" value="__EMAIL__"></div>
        <div class="field"><label for="prefecture">都道府県</label><select id="prefecture" name="prefecture">__PREFECTURE_OPTIONS__</select></div>
        <div class="field"><label for="minor_consent">未成年者の同意</label><select id="minor_consent" name="minor_consent">__MINOR_OPTIONS__</select></div>
      </div>
    </section>
    <section class="section">
      <h2>活動について</h2>
      <div class="form-grid">
        <div class="field"><label for="experience">配信・ライバー経験</label><select id="experience" name="experience">__EXPERIENCE_OPTIONS__</select></div>
        <div class="field"><label for="frequency">配信頻度</label><select id="frequency" name="frequency">__FREQUENCY_OPTIONS__</select></div>
        <div class="field full"><label for="history">活動歴・実績</label><textarea id="history" name="history">__HISTORY__</textarea></div>
        <div class="field full"><label for="genre">得意なジャンル・企画</label><textarea id="genre" name="genre">__GENRE__</textarea></div>
        <div class="field full"><label for="sns">SNSアカウント</label><textarea id="sns" name="sns">__SNS__</textarea></div>
      </div>
    </section>
    <section class="section">
      <h2>アピール</h2>
      <div class="form-grid">
        <div class="field full"><label for="self_pr">自己PR</label><textarea id="self_pr" name="self_pr">__SELF_PR__</textarea></div>
        <div class="field full"><label for="motivation">応募動機</label><textarea id="motivation" name="motivation">__MOTIVATION__</textarea></div>
        <div class="field full"><label for="other">その他</label><textarea id="other" name="other">__OTHER__</textarea></div>
      </div>
    </section>
    <div class="actions">
      <a class="button cancel" href="/audition/admin">キャンセル</a>
      <button class="button save" type="submit">追加する</button>
    </div>
  </form>
</div>
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


# ── オーディション申請フォーム /audition ─────────────────────────

AUDITION_FILE = Path("posts/audition_applications.json")

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]

AUDITION_REQUIRED_FIELDS = [
    "name", "furigana", "email", "prefecture", "minor_consent",
    "experience", "genre", "frequency", "self_pr", "motivation",
]


def _audition_is_open():
    """Render の環境変数で、保存済みフォームの公開・停止を切り替える。"""
    status = os.environ.get("AUDITION_STATUS", "closed").strip().lower()
    return status in {"open", "true", "1", "on"}


AUDITION_COLUMNS = [
    "id", "created_at", "name", "furigana", "gender", "email", "prefecture",
    "minor_consent", "activity_name", "experience", "history", "genre",
    "frequency", "sns", "self_pr", "motivation", "other",
]

AUDITION_EDITABLE_FIELDS = AUDITION_COLUMNS[2:]

_audition_table_ready = False


def _audition_db_conn():
    """Supabase(Postgres) への接続。DATABASE_URL 未設定・接続失敗時は None。"""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg2
        return psycopg2.connect(url, sslmode="require")
    except Exception as e:
        print(f"[audition] DB connection failed: {e}", file=sys.stderr)
        return None


def _audition_db_ready():
    """管理画面の表示用。DBに接続できて表が用意できていれば True。"""
    conn = _audition_db_conn()
    if not conn:
        return False
    try:
        return _ensure_audition_table(conn)
    finally:
        conn.close()


def _insert_audition_row(cur, entry):
    import uuid

    values = []
    for col in AUDITION_COLUMNS:
        v = entry.get(col, "")
        values.append(str(v).strip() if v is not None else "")
    if not values[0]:
        values[0] = str(uuid.uuid4())
    placeholders = ", ".join(["%s"] * len(AUDITION_COLUMNS))
    cols = ", ".join(AUDITION_COLUMNS)
    cur.execute(
        f"INSERT INTO audition_applications ({cols}) VALUES ({placeholders}) "
        "ON CONFLICT (id) DO NOTHING",
        values,
    )


def _ensure_audition_table(conn):
    """応募テーブルを作成し、旧方式（JSONファイル）の応募をDBへ取り込む。"""
    global _audition_table_ready
    if _audition_table_ready:
        return True
    try:
        col_defs = ",\n                        ".join(
            f"{c} TEXT NOT NULL DEFAULT ''" for c in AUDITION_COLUMNS[1:]
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS audition_applications (
                        id TEXT PRIMARY KEY,
                        {col_defs},
                        seq BIGSERIAL
                    )
                    """
                )
                # 「確認済み」は編集フォームの対象外（AUDITION_COLUMNSに入れると
                # 編集保存のたびに空欄で上書きされてしまうため別カラムで管理）
                cur.execute(
                    "ALTER TABLE audition_applications "
                    "ADD COLUMN IF NOT EXISTS checked TEXT NOT NULL DEFAULT ''"
                )
        # ファイルに残っている応募をDBへ移行（重複はスキップ）
        legacy = _load_audition_file()
        if legacy:
            with conn:
                with conn.cursor() as cur:
                    for row in legacy:
                        _insert_audition_row(cur, row)
        _audition_table_ready = True
        return True
    except Exception as e:
        print(f"[audition] table setup failed: {e}", file=sys.stderr)
        return False


def _load_audition_file():
    import json

    try:
        if AUDITION_FILE.exists():
            with open(AUDITION_FILE, "r", encoding="utf-8") as f:
                rows = json.load(f)
            return rows if isinstance(rows, list) else []
    except Exception as e:
        print(f"[audition] file load failed: {e}", file=sys.stderr)
    return []


def _append_audition_file(entry):
    import json

    try:
        rows = _load_audition_file()
        rows.append(entry)
        AUDITION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDITION_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[audition] file save failed: {e}", file=sys.stderr)
        return False


def _replace_audition_file(rows):
    """応募ファイル全体を原子的に置き換える。削除中の書き込み中断でJSONを壊さない。"""
    import json

    AUDITION_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = AUDITION_FILE.with_suffix(AUDITION_FILE.suffix + ".tmp")
    try:
        with open(temporary_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        temporary_file.replace(AUDITION_FILE)
        return True
    except Exception as e:
        print(f"[audition] file replace failed: {e}", file=sys.stderr)
        try:
            temporary_file.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _load_audition_applications():
    """古い順に応募を返す。DBが使えるときはDBを正とする。"""
    conn = _audition_db_conn()
    if conn:
        try:
            if _ensure_audition_table(conn):
                import psycopg2.extras
                with conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(
                            "SELECT * FROM audition_applications ORDER BY seq ASC"
                        )
                        return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"[audition] DB load failed: {e}", file=sys.stderr)
        finally:
            conn.close()
    return _load_audition_file()


def _delete_audition_application(application_id):
    """応募をDBと控えJSONの両方から削除する。

    DATABASE_URL が設定済みでDBに接続できないときは、DB側にデータが
    残ったまま「削除完了」と見せないため失敗とする。
    """
    application_id = str(application_id or "").strip()
    if not application_id:
        return False

    original_rows = _load_audition_file()
    remaining_rows = [
        row for row in original_rows if str(row.get("id", "")) != application_id
    ]
    removed_from_file = len(remaining_rows) != len(original_rows)

    if not os.environ.get("DATABASE_URL", ""):
        if removed_from_file and not _replace_audition_file(remaining_rows):
            raise RuntimeError("控えファイルから削除できませんでした")
        return removed_from_file

    conn = _audition_db_conn()
    if not conn:
        raise RuntimeError("データベースに接続できませんでした")

    try:
        if not _ensure_audition_table(conn):
            raise RuntimeError("応募テーブルを確認できませんでした")

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM audition_applications WHERE id = %s",
                    (application_id,),
                )
                removed_from_db = cur.rowcount > 0

            # DBトランザクション中に控えも更新。失敗したらDB削除をロールバック。
            if removed_from_file and not _replace_audition_file(remaining_rows):
                raise RuntimeError("控えファイルから削除できませんでした")

        return removed_from_db or removed_from_file
    except Exception:
        # DBのcommit失敗時は、先に更新した控えJSONも可能な限り元に戻す。
        if removed_from_file:
            _replace_audition_file(original_rows)
        raise
    finally:
        conn.close()


def _update_audition_application(application_id, updates):
    """応募をDBと控えJSONの両方で同時に更新する。"""
    application_id = str(application_id or "").strip()
    if not application_id:
        return False

    clean_updates = {
        field: str(updates.get(field, "")).strip()
        for field in AUDITION_EDITABLE_FIELDS
    }
    original_rows = _load_audition_file()
    updated_rows = []
    updated_in_file = False
    for row in original_rows:
        if str(row.get("id", "")) == application_id:
            row = {**row, **clean_updates}
            updated_in_file = True
        updated_rows.append(row)

    if not os.environ.get("DATABASE_URL", ""):
        if updated_in_file and not _replace_audition_file(updated_rows):
            raise RuntimeError("控えファイルを更新できませんでした")
        return updated_in_file

    conn = _audition_db_conn()
    if not conn:
        raise RuntimeError("データベースに接続できませんでした")

    try:
        if not _ensure_audition_table(conn):
            raise RuntimeError("応募テーブルを確認できませんでした")

        assignments = ", ".join(f"{field} = %s" for field in AUDITION_EDITABLE_FIELDS)
        values = [clean_updates[field] for field in AUDITION_EDITABLE_FIELDS]
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE audition_applications SET {assignments} WHERE id = %s",
                    (*values, application_id),
                )
                updated_in_db = cur.rowcount > 0

            # DBトランザクション中に控えも更新し、片方だけの更新を防ぐ。
            if updated_in_file and not _replace_audition_file(updated_rows):
                raise RuntimeError("控えファイルを更新できませんでした")

        return updated_in_db or updated_in_file
    except Exception:
        if updated_in_file:
            _replace_audition_file(original_rows)
        raise
    finally:
        conn.close()


def _audition_is_checked(application):
    """管理画面で✓（確認済み）が付いている応募なら True。"""
    return str(application.get("checked", "")).strip().lower() in ("1", "true", "yes", "on")


def _set_audition_checked(application_id, checked):
    """「確認済み」フラグだけをDBと控えJSONの両方で更新する（他の項目には触れない）。"""
    application_id = str(application_id or "").strip()
    if not application_id:
        return False
    checked_value = "true" if checked else ""

    original_rows = _load_audition_file()
    updated_rows = []
    updated_in_file = False
    for row in original_rows:
        if str(row.get("id", "")) == application_id:
            row = {**row, "checked": checked_value}
            updated_in_file = True
        updated_rows.append(row)

    if not os.environ.get("DATABASE_URL", ""):
        if updated_in_file and not _replace_audition_file(updated_rows):
            raise RuntimeError("控えファイルを更新できませんでした")
        return updated_in_file

    conn = _audition_db_conn()
    if not conn:
        raise RuntimeError("データベースに接続できませんでした")

    try:
        if not _ensure_audition_table(conn):
            raise RuntimeError("応募テーブルを確認できませんでした")

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE audition_applications SET checked = %s WHERE id = %s",
                    (checked_value, application_id),
                )
                updated_in_db = cur.rowcount > 0

            if updated_in_file and not _replace_audition_file(updated_rows):
                raise RuntimeError("控えファイルを更新できませんでした")

        return updated_in_db or updated_in_file
    except Exception:
        if updated_in_file:
            _replace_audition_file(original_rows)
        raise
    finally:
        conn.close()


def _save_audition_application(entry):
    """応募を保存する。DBに入れば True、ファイルにしか残せなければ False を返す。
    どちらにも保存できなかった場合は例外を送出する（呼び出し側でエラー応答する）。

    ファイルはRenderの再デプロイ・スリープ復帰で消えるため、DB保存はできる限り
    その場で成功させたい。接続やINSERTがデプロイ切り替え等で一時的に失敗しても、
    ファイルだけの保存に落ちる前に何度か再試行する。"""
    import time

    global _audition_table_ready

    saved_db = False
    last_error = None
    attempts = 3 if os.environ.get("DATABASE_URL", "") else 1
    for attempt in range(attempts):
        if attempt:
            time.sleep(0.4 * attempt)
        conn = _audition_db_conn()
        if not conn:
            last_error = "connection failed"
            continue
        try:
            if _ensure_audition_table(conn):
                with conn:
                    with conn.cursor() as cur:
                        _insert_audition_row(cur, entry)
                saved_db = True
        except Exception as e:
            last_error = e
            # 次にDBへつながったときに、ファイルに残った分をまとめて取り込み直す
            _audition_table_ready = False
        finally:
            conn.close()
        if saved_db:
            break

    if not saved_db and last_error is not None:
        print(f"[audition] DB save failed after retries: {last_error}", file=sys.stderr)

    # DBの有無にかかわらずファイルにも控えを残す（DB障害時の保険）
    saved_file = _append_audition_file(entry)

    if not saved_db and not saved_file:
        raise RuntimeError("応募データを保存できませんでした")
    return saved_db


def _audition_line_admin_user_ids():
    """面談予約アプリ（booking_app）と共有のDBから、「連携 admin」済みのLINEユーザーIDを取得する。
    DATABASE_URL未設定・テーブル未作成・接続失敗の場合は空リストを返す（通知はスキップ）。"""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return []
    try:
        import psycopg2
        conn = psycopg2.connect(url, sslmode="require")
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT line_user_id FROM booking_line_links WHERE person=%s",
                        ("admin",),
                    )
                    return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
    except Exception as e:
        print(f"[audition] LINE admin lookup failed: {e}")
        return []


def _format_audition_line_text(entry):
    """応募内容を全項目LINE本文に整形する。未入力の任意項目も「（未記入）」として残す。"""

    def v(key):
        s = str(entry.get(key, "") or "").strip()
        return s if s else "（未記入）"

    lines = [
        "🎤 新しいオーディション応募がありました",
        "",
        f"📅 応募日時: {v('created_at')}",
        "",
        "―― 基本情報 ――",
        f"お名前: {v('name')}（{v('furigana')}）",
        f"性別: {v('gender')}",
        f"メール: {v('email')}",
        f"都道府県: {v('prefecture')}",
        f"保護者の同意（未成年のみ）: {v('minor_consent')}",
        "",
        "―― 活動について ――",
        f"活動名: {v('activity_name')}",
        f"配信・ライバー活動の経験: {v('experience')}",
        "【活動歴・実績】",
        v("history"),
        "【得意なジャンル・企画】",
        v("genre"),
        f"活動できる頻度: {v('frequency')}",
        "【SNSアカウント】",
        v("sns"),
        "",
        "―― アピール ――",
        "【自己PR】",
        v("self_pr"),
        "",
        "【応募動機】",
        v("motivation"),
        "",
        "―― その他ご質問・ご要望 ――",
        v("other"),
    ]
    return "\n".join(lines)


def _split_line_text(text, limit=4800):
    """LINEの1通あたりの文字数上限を超える場合、行単位で分割して (1/2) 等の見出しを付ける。"""
    if len(text) <= limit:
        return [text]

    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + 1 + len(line) > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)

    total = len(chunks)
    return [f"({i}/{total})\n{c}" for i, c in enumerate(chunks, 1)]


def _notify_audition_line(entry):
    import line_messaging

    if not line_messaging.is_configured():
        return
    user_ids = _audition_line_admin_user_ids()
    if not user_ids:
        return
    messages = _split_line_text(_format_audition_line_text(entry))
    for uid in user_ids:
        for msg in messages:
            line_messaging.push_text(uid, msg)


# 次回の募集でも再利用する受付フォーム本体。
# AUDITION_STATUS=open のときだけ /audition で公開する。
AUDITION_FORM_TEMPLATE_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>ライバー・配信者オーディション応募 | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff; --surface2: #f1f0fa;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding-bottom: 40px;
}
.header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 28px 18px 24px; text-align: center; }
.header .badge {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
  color: white; background: var(--grad); padding: 4px 14px; border-radius: 999px; margin-bottom: 10px;
}
.header h1 { font-size: 19px; font-weight: 800; }
.header p { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.6; }
.main { padding: 22px 16px; max-width: 480px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 20px; box-shadow: var(--shadow); }
.card h2 { font-size: 14px; font-weight: 800; margin-bottom: 14px; }
.field { margin-bottom: 14px; }
.field:last-child { margin-bottom: 0; }
.field label { display: block; font-size: 12.5px; font-weight: 700; color: var(--muted); margin-bottom: 6px; }
.field .req { color: #ec4899; margin-left: 2px; }
.field input[type=text], .field input[type=email], .field select, .field textarea {
  width: 100%; padding: 11px 12px; border: 1.5px solid var(--border); border-radius: 10px;
  font-size: 14px; background: var(--surface2); color: var(--text); font-family: inherit;
  -webkit-appearance: none; appearance: none;
}
.field textarea { min-height: 84px; resize: vertical; line-height: 1.6; }
.field input:focus, .field select:focus, .field textarea:focus { outline: none; border-color: var(--accent-text); }
.radio-row { display: flex; gap: 16px; flex-wrap: wrap; }
.radio-row label { display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 500; color: var(--text); }
.radio-row input { width: auto; }
.agree-row { display: flex; align-items: flex-start; gap: 8px; font-size: 12.5px; color: var(--muted); line-height: 1.7; }
.agree-row input { width: auto; margin-top: 3px; }
.submit-btn {
  width: 100%; padding: 15px; border: none; border-radius: 12px;
  background: var(--grad); color: white;
  font-size: 15px; font-weight: 800; cursor: pointer; letter-spacing: 0.02em;
  transition: opacity 0.2s, transform 0.1s;
  box-shadow: 0 6px 18px rgba(217,70,239,0.28);
}
.submit-btn:active { opacity: 0.85; transform: scale(0.98); }
.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; box-shadow: none; }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(10px);
  background: var(--surface); border: 1px solid #ef4444; color: #ef4444; box-shadow: var(--shadow);
  padding: 10px 20px; border-radius: 999px; font-size: 13px; font-weight: 600;
  white-space: nowrap; opacity: 0; transition: all 0.2s; pointer-events: none; z-index: 999;
  max-width: 90vw; overflow: hidden; text-overflow: ellipsis;
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.success-card { text-align: center; padding: 40px 24px; }
.success-card .icon { font-size: 40px; margin-bottom: 14px; }
.success-card h2 { font-size: 17px; margin-bottom: 8px; }
.success-card p { font-size: 13px; color: var(--muted); line-height: 1.8; }
</style>
</head>
<body>
<div class="header">
  <span class="badge">ETERNAL d.c.t</span>
  <h1>🎤 ライバー・配信者オーディション応募</h1>
  <p>下記フォームに必要事項をご記入のうえ送信してください。<br>審査結果はご入力いただいたメールアドレスへご連絡します。</p>
</div>
<div class="main" id="main">
  <form id="auditionForm">
    <div class="card">
      <h2>基本情報</h2>
      <div class="field">
        <label>お名前（本名）<span class="req">*</span></label>
        <input type="text" name="name" required>
      </div>
      <div class="field">
        <label>ふりがな<span class="req">*</span></label>
        <input type="text" name="furigana" required>
      </div>
      <div class="field">
        <label>性別</label>
        <select name="gender">
          <option value=""></option>
          <option value="男性">男性</option>
          <option value="女性">女性</option>
          <option value="その他">その他</option>
          <option value="回答しない">回答しない</option>
        </select>
      </div>
      <div class="field">
        <label>メールアドレス<span class="req">*</span></label>
        <input type="email" name="email" required>
      </div>
      <div class="field">
        <label>お住まいの都道府県<span class="req">*</span></label>
        <select name="prefecture" required>
          <option value=""></option>
          __PREFECTURE_OPTIONS__
        </select>
      </div>
      <div class="field">
        <label>未成年の方のみ：保護者の同意<span class="req">*</span></label>
        <select name="minor_consent" required>
          <option value="該当しない（成人）">該当しない（成人）</option>
          <option value="同意している">同意している</option>
          <option value="まだ得ていない">まだ得ていない</option>
        </select>
      </div>
    </div>

    <div class="card">
      <h2>活動について</h2>
      <div class="field">
        <label>活動名（希望する名前があれば）</label>
        <input type="text" name="activity_name">
      </div>
      <div class="field">
        <label>配信・ライバー活動の経験<span class="req">*</span></label>
        <div class="radio-row">
          <label><input type="radio" name="experience" value="あり" required>あり</label>
          <label><input type="radio" name="experience" value="なし">なし</label>
        </div>
      </div>
      <div class="field">
        <label>経験がある場合、活動歴・実績（プラットフォーム名／フォロワー数など）</label>
        <textarea name="history"></textarea>
      </div>
      <div class="field">
        <label>得意なジャンル・企画<span class="req">*</span></label>
        <textarea name="genre" required placeholder="例）雑談、ゲーム実況、歌枠 など"></textarea>
      </div>
      <div class="field">
        <label>週にどのくらい配信・活動できますか<span class="req">*</span></label>
        <select name="frequency" required>
          <option value=""></option>
          <option value="週1回未満">週1回未満</option>
          <option value="週1〜2回">週1〜2回</option>
          <option value="週3〜4回">週3〜4回</option>
          <option value="週5回以上">週5回以上</option>
        </select>
      </div>
      <div class="field">
        <label>SNSアカウント（X / Instagram / TikTok など）</label>
        <textarea name="sns"></textarea>
      </div>
    </div>

    <div class="card">
      <h2>アピール</h2>
      <div class="field">
        <label>自己PR（400字程度）<span class="req">*</span></label>
        <textarea name="self_pr" required></textarea>
      </div>
      <div class="field">
        <label>応募動機<span class="req">*</span></label>
        <textarea name="motivation" required></textarea>
      </div>
    </div>

    <div class="card">
      <h2>確認事項</h2>
      <div class="field">
        <label class="agree-row">
          <input type="checkbox" name="agree" required>
          <span>応募規約・プライバシーポリシーの内容を確認し、同意します<span class="req">*</span></span>
        </label>
      </div>
      <div class="field">
        <label>その他ご質問・ご要望</label>
        <textarea name="other"></textarea>
      </div>
    </div>

    <button type="submit" class="submit-btn" id="submitBtn">応募する</button>
  </form>
</div>
<div class="toast" id="toast"></div>
<script>
const PREFECTURE_OPTIONS_MARK = '__PREFECTURE_OPTIONS__';

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3200);
}

document.getElementById('auditionForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const btn = document.getElementById('submitBtn');
  const data = Object.fromEntries(new FormData(form).entries());
  data.agree = form.agree.checked;

  btn.disabled = true;
  btn.textContent = '送信中…';
  try {
    const res = await fetch('/api/audition/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (result.ok) {
      document.getElementById('main').innerHTML = `
        <div class="card success-card">
          <div class="icon">✅</div>
          <h2>応募ありがとうございます</h2>
          <p>内容を確認のうえ、ご入力いただいたメールアドレスへ<br>審査結果をご連絡いたします。</p>
        </div>`;
      return;
    }
    toast(result.error || '送信に失敗しました');
  } catch (err) {
    toast('通信エラーが発生しました');
  }
  btn.disabled = false;
  btn.textContent = '応募する';
});
</script>
</body>
</html>"""


AUDITION_CLOSED_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#f7f7fb">
<title>オーディション受付終了 | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 16px 48px rgba(124,58,237,0.12);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  display: grid; place-items: center; padding: 24px 16px;
}
.card {
  width: 100%; max-width: 480px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 24px;
  box-shadow: var(--shadow); overflow: hidden; text-align: center;
}
.accent { height: 7px; background: var(--grad); }
.content { padding: 46px 28px 42px; }
.brand {
  display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: 0.12em;
  color: white; background: var(--grad); padding: 5px 15px; border-radius: 999px;
  margin-bottom: 24px;
}
.icon {
  width: 74px; height: 74px; margin: 0 auto 22px; border-radius: 50%;
  display: grid; place-items: center; background: #f5efff; font-size: 34px;
}
h1 { font-size: 23px; font-weight: 850; letter-spacing: 0.02em; margin-bottom: 14px; }
.lead { font-size: 15px; font-weight: 700; line-height: 1.8; margin-bottom: 18px; }
.note { font-size: 13px; color: var(--muted); line-height: 1.9; }
.divider { width: 44px; height: 2px; margin: 26px auto; background: var(--grad); border-radius: 2px; }
.thanks { font-size: 13px; color: var(--muted); line-height: 1.8; }
@media (max-width: 380px) {
  .content { padding: 38px 22px 34px; }
  h1 { font-size: 21px; }
}
</style>
</head>
<body>
<main class="card" aria-labelledby="page-title">
  <div class="accent"></div>
  <div class="content">
    <span class="brand">ETERNAL d.c.t</span>
    <div class="icon" aria-hidden="true">🎤</div>
    <h1 id="page-title">受付は終了しました</h1>
    <p class="lead">ライバー・配信者オーディションの<br>新規受付は終了いたしました。</p>
    <p class="note">次回の募集が決まりましたら、<br>ETERNAL d.c.tの公式案内にてお知らせします。</p>
    <div class="divider"></div>
    <p class="thanks">たくさんのご応募をいただき、<br>ありがとうございました。</p>
  </div>
</main>
</body>
</html>"""


AUDITION_ADMIN_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>応募一覧ログイン | ETERNALd.c.t</title>
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
  <h1>🔒 応募一覧ログイン</h1>
  <form method="POST">
    <input type="password" name="password" placeholder="パスワード" autofocus required>
    <button type="submit">ログイン</button>
  </form>
  __ERROR__
</div>
</body>
</html>"""


AUDITION_ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>オーディション応募一覧 | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff; --surface2: #f7f5fc;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent: #7c3aed; --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280; --border: #e7e3f0;
  --danger: #dc2626; --danger-bg: #fff1f2;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding: 24px;
}
.page { width: min(1240px, 100%); margin: 0 auto; }
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; flex-wrap: wrap; gap: 14px; }
.title-wrap { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.header h1 { font-size: clamp(20px, 3vw, 26px); font-weight: 850; letter-spacing: -.02em; }
.header .count { font-size: 13px; color: var(--muted); }
.logout {
  font-size: 13px; font-weight: 700; color: white; text-decoration: none;
  background: var(--grad); padding: 8px 16px; border-radius: 999px;
  box-shadow: 0 6px 18px rgba(217,70,239,0.22);
}
.toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
  padding: 12px; margin-bottom: 16px; box-shadow: var(--shadow);
}
.search-wrap { flex: 1 1 300px; position: relative; }
.search-wrap span { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--muted); }
#applicant-search {
  width: 100%; border: 1px solid var(--border); background: var(--bg); color: var(--text);
  border-radius: 11px; padding: 11px 13px 11px 38px; font-size: 14px; outline: none;
}
#applicant-search:focus { border-color: #b794f6; box-shadow: 0 0 0 3px rgba(124,58,237,.1); }
.view-switch { display: inline-flex; background: var(--surface2); padding: 4px; border-radius: 10px; gap: 3px; }
.view-button { border: 0; background: transparent; color: var(--muted); border-radius: 8px; padding: 8px 12px; font-weight: 750; cursor: pointer; }
.view-button.active { background: var(--surface); color: var(--accent-text); box-shadow: 0 2px 8px rgba(31,35,51,.08); }
.result-count { color: var(--muted); font-size: 12px; min-width: 68px; text-align: right; }
.message { padding: 12px 15px; border-radius: 12px; margin-bottom: 16px; font-size: 13px; font-weight: 700; }
.message.ok { background: #edfaf1; border: 1px solid #b7e6c6; color: #1a7f45; }
.message.error { background: var(--danger-bg); border: 1px solid #fecdd3; color: #b91c1c; }
.card-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.app-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); overflow: hidden; transition: opacity .15s, border-color .15s; }
.app-card.checked { opacity: .55; border-color: #22c55e; }
.card-head { display: flex; justify-content: space-between; gap: 12px; padding: 17px 18px 13px; border-bottom: 1px solid var(--border); }
.check-toggle {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: 8px; border: 2px solid var(--border);
  display: flex; align-items: center; justify-content: center; font-size: 15px; color: white;
  background: var(--surface); cursor: pointer; transition: background .15s, border-color .15s;
}
.app-card.checked .check-toggle { background: #22c55e; border-color: #22c55e; }
.name { font-size: 17px; font-weight: 850; line-height: 1.35; }
.furigana { color: var(--muted); font-size: 11px; margin-top: 3px; }
.date { color: var(--muted); font-size: 11px; white-space: nowrap; }
.activity { color: var(--accent-text); font-size: 13px; font-weight: 800; margin-top: 6px; }
.missing-badge { display: inline-flex; align-items: center; gap: 4px; background: #fff7e6; border: 1px solid #f3d3a1; color: #9a5b00; border-radius: 999px; padding: 3px 8px; font-size: 11px; font-weight: 850; white-space: nowrap; }
.quick-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 14px 18px; gap: 12px 18px; }
.field dt, .long-field dt { color: var(--muted); font-size: 10px; font-weight: 750; margin-bottom: 4px; }
.field dd { font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }
.long-details { border-top: 1px solid var(--border); }
.long-details summary { cursor: pointer; list-style: none; padding: 13px 18px; font-size: 13px; font-weight: 800; color: var(--accent-text); }
.long-details summary::-webkit-details-marker { display: none; }
.long-details summary::after { content: '・・・'; float: right; letter-spacing: 2px; color: var(--muted); }
.long-content { border-top: 1px solid var(--border); background: #fcfbff; padding: 15px 18px; display: grid; gap: 14px; }
.long-field dd { font-size: 13px; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.card-actions, .table-actions { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
.card-actions { padding: 12px 18px; border-top: 1px solid var(--border); }
.edit-link { display: inline-block; border: 1px solid #d8ccf4; background: #f7f2ff; color: var(--accent-text); padding: 7px 11px; border-radius: 9px; font-size: 12px; font-weight: 800; text-decoration: none; white-space: nowrap; }
.edit-link:hover { background: #efe7ff; }
.delete-form { display: inline; }
.delete-button { border: 1px solid #fecdd3; background: var(--danger-bg); color: var(--danger); padding: 7px 11px; border-radius: 9px; font-size: 12px; font-weight: 800; cursor: pointer; }
.delete-button:hover { background: #ffe4e6; }
.table-view { display: none; }
.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); box-shadow: var(--shadow); }
table { border-collapse: collapse; width: 100%; min-width: 860px; font-size: 13px; }
th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); vertical-align: middle; }
th { background: var(--surface2); color: var(--muted); font-weight: 750; position: sticky; top: 0; }
tr:last-child td { border-bottom: none; }
.detail-button { border: 0; color: var(--accent-text); background: transparent; padding: 6px; font-weight: 800; cursor: pointer; white-space: nowrap; }
.empty-state { text-align: center; color: var(--muted); padding: 54px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; }
.hidden { display: none !important; }
.status { font-size: 13px; margin-top: 16px; line-height: 1.8; padding: 12px 16px; border-radius: 12px; }
.status.ok { background: #edfaf1; border: 1px solid #b7e6c6; color: #1a7f45; }
.status.warn { background: #fff6e8; border: 1px solid #f3d3a1; color: #9a5b00; }
@media (max-width: 760px) {
  body { padding: 14px; }
  .card-grid { grid-template-columns: 1fr; }
  .toolbar { align-items: stretch; }
  .view-switch { flex: 1; }
  .view-button { flex: 1; }
  .result-count { width: 100%; text-align: left; padding-left: 2px; }
}
@media (max-width: 430px) {
  .quick-grid { grid-template-columns: 1fr; }
  .card-head { flex-direction: column; }
}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div class="title-wrap">
      <h1>🎤 オーディション応募一覧</h1>
      <span class="count">__COUNT__ 件</span>
    </div>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <a class="logout" href="/audition/admin/slides">🖥 未確認をスライド表示</a>
      <a class="logout" href="/audition/admin/new">＋ 新規追加</a>
      <a class="logout" href="/audition/admin/logout">ログアウト</a>
    </div>
  </div>
  __MESSAGE__
  <div class="toolbar">
    <label class="search-wrap">
      <span>🔍</span>
      <input id="applicant-search" type="search" placeholder="名前・活動名・メール・都道府県で検索">
    </label>
    <div class="view-switch" aria-label="表示切り替え">
      <button class="view-button active" type="button" data-view="cards">▦ カード</button>
      <button class="view-button" type="button" data-view="table">☰ 一覧</button>
    </div>
    <span class="result-count" id="result-count">__COUNT__ 件を表示</span>
  </div>
  <section class="card-view" id="card-view">
    <div class="card-grid">__CARDS__</div>
  </section>
  <section class="table-view" id="table-view">
    <div class="table-wrap">
      <table>
        <thead><tr><th>応募日時</th><th>お名前</th><th>活動名</th><th>都道府県</th><th>頻度</th><th>経験</th><th>詳細</th><th>操作</th></tr></thead>
        <tbody>__ROWS__</tbody>
      </table>
    </div>
  </section>
  <p class="empty-state hidden" id="no-results">条件に一致する応募はありません</p>
  __STORAGE_NOTE__
</div>
<script>
(() => {
  const search = document.getElementById('applicant-search');
  const cards = [...document.querySelectorAll('.app-card')];
  const rows = [...document.querySelectorAll('tr[data-search]')];
  const resultCount = document.getElementById('result-count');
  const noResults = document.getElementById('no-results');

  function setView(view) {
    const table = view === 'table';
    document.getElementById('card-view').style.display = table ? 'none' : 'block';
    document.getElementById('table-view').style.display = table ? 'block' : 'none';
    document.querySelectorAll('.view-button').forEach(button => {
      button.classList.toggle('active', button.dataset.view === view);
    });
    localStorage.setItem('audition-admin-view', view);
  }

  function filterApplicants() {
    const query = search.value.trim().toLocaleLowerCase('ja');
    let visible = 0;
    cards.forEach(card => {
      const match = !query || card.dataset.search.toLocaleLowerCase('ja').includes(query);
      card.classList.toggle('hidden', !match);
      if (match) visible += 1;
    });
    rows.forEach(row => {
      const match = !query || row.dataset.search.toLocaleLowerCase('ja').includes(query);
      row.classList.toggle('hidden', !match);
    });
    resultCount.textContent = `${visible} 件を表示`;
    noResults.classList.toggle('hidden', visible !== 0);
  }

  const csrfToken = '__CSRF_TOKEN_JS__';
  document.querySelectorAll('.check-toggle').forEach(toggle => {
    toggle.addEventListener('click', async () => {
      const card = toggle.closest('.app-card');
      const id = card.dataset.id;
      const nowChecked = !card.classList.contains('checked');
      card.classList.toggle('checked', nowChecked);
      try {
        const res = await fetch(`/audition/admin/check/${encodeURIComponent(id)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ checked: nowChecked, csrf_token: csrfToken }),
        });
        if (!res.ok) throw new Error('failed');
      } catch (e) {
        card.classList.toggle('checked', !nowChecked);
      }
    });
  });

  document.querySelectorAll('.view-button').forEach(button => {
    button.addEventListener('click', () => setView(button.dataset.view));
  });
  document.querySelectorAll('.detail-button').forEach(button => {
    button.addEventListener('click', () => {
      setView('cards');
      const card = document.getElementById(button.dataset.target);
      if (card) {
        card.querySelector('details').open = true;
        card.scrollIntoView({behavior: 'smooth', block: 'start'});
      }
    });
  });
  search.addEventListener('input', filterApplicants);
  setView(localStorage.getItem('audition-admin-view') === 'table' ? 'table' : 'cards');
})();
</script>
</body>
</html>"""



AUDITION_SLIDES_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>応募者スライド | ETERNALd.c.t</title>
<style>
:root {
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280; --border: #e7e3f0;
  --paper: #ffffff; --soft: #faf8ff; --backdrop: #15121f;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body {
  background: var(--backdrop); color: var(--text); overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
}
.stage { position: relative; width: min(100vw - 24px, (100vh - 76px) * 16 / 9); aspect-ratio: 16 / 9; }
body.is-fs .stage { width: min(100vw, 100vh * 16 / 9); }
.slide {
  position: absolute; inset: 0; container-type: size;
  background: var(--paper); border-radius: 14px; overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,.45);
  opacity: 0; visibility: hidden; transition: opacity .25s ease, visibility .25s;
}
body.is-fs .slide { border-radius: 0; }
.slide.active { opacity: 1; visibility: visible; }
.slide-inner { position: absolute; inset: 0; display: flex; flex-direction: column; padding: 6.5cqh 5cqw 4cqh; }
.slide-inner::before { content: ''; position: absolute; left: 0; right: 0; top: 0; height: 1.2cqh; background: var(--grad); }
.s-head { display: flex; align-items: baseline; gap: 2cqw; margin-bottom: 3.6cqh; min-width: 0; }
.s-no { font-size: 1.6cqw; font-weight: 850; color: var(--accent-text); letter-spacing: .08em; white-space: nowrap; }
.s-name { font-size: 4.2cqw; font-weight: 900; letter-spacing: -.01em; line-height: 1.2; overflow-wrap: anywhere; }
.s-name .missing { color: #9a5b00; font-size: .7em; }
.s-title { font-size: 3.4cqw; font-weight: 900; }
.s-sub { font-size: 1.4cqw; color: var(--muted); font-weight: 750; }
.s-body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 2.4cqw; }
.col {
  background: var(--soft); border: 1px solid var(--border); border-radius: 1.4cqw;
  padding: 2.2cqw 2.4cqw; display: flex; flex-direction: column; min-height: 0;
}
.chip {
  align-self: flex-start; font-size: 1.25cqw; font-weight: 850; color: #fff; background: var(--grad);
  padding: .45cqw 1.3cqw; border-radius: 999px; margin-bottom: 1.4cqw; letter-spacing: .06em;
}
.col-text {
  flex: 1; min-height: 0; overflow: hidden; font-size: var(--fs, 1.8cqw); line-height: 1.75;
  white-space: pre-wrap; overflow-wrap: anywhere;
}
.col-text.empty { color: var(--muted); }
.overflowing .fit-check, .fit-check.overflowing { overflow-y: auto; }
.index {
  flex: 1; min-height: 0; overflow: hidden; list-style: none; font-size: var(--fs, 2cqw);
  display: grid; grid-template-columns: repeat(auto-fill, minmax(26cqw, 1fr)); align-content: start; gap: .5em 2.4cqw;
}
.index a {
  display: flex; gap: .7em; align-items: baseline; color: var(--text); text-decoration: none; font-weight: 800;
  padding: .35em .6em; border-radius: .5em; border: 1px solid var(--border); background: var(--soft);
  overflow-wrap: anywhere;
}
.index a:hover { border-color: #b794f6; }
.index .no { color: var(--accent-text); font-size: .75em; letter-spacing: .06em; }
.index .missing { color: #9a5b00; }
.s-foot {
  display: flex; justify-content: space-between; margin-top: 2.6cqh;
  font-size: 1.1cqw; color: var(--muted); font-weight: 750; letter-spacing: .08em;
}
.cover .slide-inner { background: var(--grad); color: #fff; justify-content: center; padding: 8cqh 8cqw; }
.cover .slide-inner::before { display: none; }
.cover-kicker { font-size: 1.6cqw; font-weight: 800; letter-spacing: .3em; opacity: .9; }
.cover-title { font-size: 5.6cqw; font-weight: 900; line-height: 1.25; margin: 3cqh 0 4cqh; letter-spacing: -.01em; }
.cover-meta { font-size: 1.8cqw; font-weight: 750; }
.cover-meta strong { font-size: 1.4em; }
.cover-note { font-size: 1.3cqw; opacity: .85; margin-top: 1.4cqh; }
.controls { display: flex; align-items: center; gap: 8px; color: #e9e5f5; font-size: 13px; transition: opacity .2s; }
body.is-fs .controls { position: fixed; bottom: 12px; left: 50%; transform: translateX(-50%); opacity: 0; background: rgba(21,18,31,.85); padding: 6px 10px; border-radius: 12px; }
body.is-fs .controls:hover { opacity: 1; }
.ctrl {
  border: 1px solid rgba(255,255,255,.18); background: rgba(255,255,255,.06); color: #e9e5f5;
  border-radius: 9px; padding: 7px 12px; font-size: 13px; font-weight: 750; cursor: pointer; text-decoration: none;
}
.ctrl:hover { background: rgba(255,255,255,.14); }
.ctrl:disabled { opacity: .35; cursor: default; }
#counter { min-width: 64px; text-align: center; font-variant-numeric: tabular-nums; font-weight: 750; }
@media screen and (max-width: 820px) and (orientation: portrait) {
  body { overflow: auto; justify-content: flex-start; gap: 0; }
  .stage { width: 100%; aspect-ratio: auto; height: calc(100vh - 56px); height: calc(100dvh - 56px); }
  .slide { border-radius: 0; }
  .slide-inner { padding: 30px 18px 16px; overflow-y: auto; }
  .s-head { flex-direction: column; gap: 4px; margin-bottom: 16px; }
  .s-no { font-size: 12px; }
  .s-name { font-size: 26px; }
  .s-title { font-size: 24px; }
  .s-sub { font-size: 13px; }
  .s-body { flex: none; grid-template-columns: 1fr; gap: 14px; }
  .col { padding: 16px; border-radius: 12px; }
  .chip { font-size: 12px; padding: 4px 12px; margin-bottom: 10px; }
  .col-text { font-size: 15px; overflow: visible; }
  .index { flex: none; overflow: visible; font-size: 15px; grid-template-columns: 1fr; }
  .s-foot { font-size: 11px; margin-top: 16px; }
  .cover .slide-inner { padding: 28px 22px; }
  .cover-kicker { font-size: 12px; }
  .cover-title { font-size: 30px; margin: 14px 0 18px; }
  .cover-meta { font-size: 15px; }
  .cover-note { font-size: 12px; }
  .controls { height: 56px; flex-wrap: wrap; justify-content: center; }
  .hide-sm { display: none; }
}
@page { size: 13.333in 7.5in; margin: 0; }
@media print {
  html, body { height: auto; overflow: visible; background: #fff; display: block; }
  .controls { display: none; }
  .stage { width: 13.333in; aspect-ratio: auto; }
  .slide {
    position: relative; inset: auto; width: 13.333in; height: 7.5in; border-radius: 0; box-shadow: none;
    opacity: 1; visibility: visible; transition: none; break-after: page;
  }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
</head>
<body>
<main class="stage" id="stage">
__SLIDES__
</main>
<nav class="controls" aria-label="スライド操作">
  <a class="ctrl" href="/audition/admin">← 管理画面</a>
  <button class="ctrl" id="prev" type="button" aria-label="前のスライド">‹</button>
  <span id="counter">1 / __TOTAL__</span>
  <button class="ctrl" id="next" type="button" aria-label="次のスライド">›</button>
  <button class="ctrl hide-sm" id="fullscreen" type="button">⛶ 全画面</button>
  <button class="ctrl hide-sm" id="print" type="button">PDF保存</button>
</nav>
<script>
(() => {
  const slides = [...document.querySelectorAll('.slide')];
  const counter = document.getElementById('counter');
  const prevButton = document.getElementById('prev');
  const nextButton = document.getElementById('next');
  const portrait = window.matchMedia('screen and (max-width: 820px) and (orientation: portrait)');
  let current = 0;

  function show(index) {
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach((slide, i) => slide.classList.toggle('active', i === current));
    counter.textContent = `${current + 1} / ${slides.length}`;
    prevButton.disabled = current === 0;
    nextButton.disabled = current === slides.length - 1;
    history.replaceState(null, '', `#${current + 1}`);
    const inner = slides[current].querySelector('.slide-inner');
    if (inner) inner.scrollTop = 0;
  }

  // 文字量に合わせて、枠からはみ出さない最大の文字サイズに自動調整する
  function fit(el) {
    const checks = el.classList.contains('fit-check') ? [el] : [...el.querySelectorAll('.fit-check')];
    const over = () => checks.some(c => c.scrollHeight > c.clientHeight + 1);
    let size = parseFloat(el.dataset.max);
    const min = parseFloat(el.dataset.min);
    el.classList.remove('overflowing');
    el.style.setProperty('--fs', `${size}cqw`);
    while (size > min && over()) {
      size = Math.round((size - 0.05) * 100) / 100;
      el.style.setProperty('--fs', `${size}cqw`);
    }
    el.classList.toggle('overflowing', over());
  }

  function fitAll() {
    document.querySelectorAll('.fit').forEach(el => {
      if (portrait.matches) {
        el.classList.remove('overflowing');
        el.style.removeProperty('--fs');
      } else {
        fit(el);
      }
    });
  }

  prevButton.addEventListener('click', () => show(current - 1));
  nextButton.addEventListener('click', () => show(current + 1));
  document.getElementById('print').addEventListener('click', () => window.print());
  document.getElementById('fullscreen').addEventListener('click', () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
  });
  document.addEventListener('fullscreenchange', () => {
    document.body.classList.toggle('is-fs', !!document.fullscreenElement);
  });

  document.addEventListener('keydown', e => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(e.key)) { e.preventDefault(); show(current + 1); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(e.key)) { e.preventDefault(); show(current - 1); }
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(slides.length - 1);
    else if (e.key === 'f' || e.key === 'F') document.getElementById('fullscreen').click();
  });

  document.querySelectorAll('[data-goto]').forEach(link => {
    link.addEventListener('click', e => { e.preventDefault(); show(Number(link.dataset.goto) - 1); });
  });

  let touchX = null, touchY = null;
  const stage = document.getElementById('stage');
  stage.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; touchY = e.touches[0].clientY; }, { passive: true });
  stage.addEventListener('touchend', e => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    const dy = e.changedTouches[0].clientY - touchY;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) show(current + (dx < 0 ? 1 : -1));
    touchX = touchY = null;
  });

  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(fitAll, 150); });
  fitAll();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitAll);
  show((parseInt(location.hash.slice(1), 10) || 1) - 1);
})();
</script>
</body>
</html>"""

@app.route("/audition")
def audition_index():
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
    }
    if not _audition_is_open():
        return AUDITION_CLOSED_HTML, 200, headers

    prefecture_options = "".join(f'<option value="{p}">{p}</option>' for p in PREFECTURES)
    html = AUDITION_FORM_TEMPLATE_HTML.replace("__PREFECTURE_OPTIONS__", prefecture_options)
    return html, 200, headers


@app.route("/api/audition/submit", methods=["POST"])
def api_audition_submit():
    import uuid
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if not _audition_is_open():
        return jsonify({"error": "オーディションの受付は終了しました"}), 410

    data = request.get_json(force=True) or {}

    for field in AUDITION_REQUIRED_FIELDS:
        if not str(data.get(field, "")).strip():
            return jsonify({"error": "必須項目が未入力です"}), 400
    if not data.get("agree"):
        return jsonify({"error": "応募規約への同意が必要です"}), 400

    JST = ZoneInfo("Asia/Tokyo")
    entry = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "name": str(data.get("name", "")).strip(),
        "furigana": str(data.get("furigana", "")).strip(),
        "gender": str(data.get("gender", "")).strip(),
        "email": str(data.get("email", "")).strip(),
        "prefecture": str(data.get("prefecture", "")).strip(),
        "minor_consent": str(data.get("minor_consent", "")).strip(),
        "activity_name": str(data.get("activity_name", "")).strip(),
        "experience": str(data.get("experience", "")).strip(),
        "history": str(data.get("history", "")).strip(),
        "genre": str(data.get("genre", "")).strip(),
        "frequency": str(data.get("frequency", "")).strip(),
        "sns": str(data.get("sns", "")).strip(),
        "self_pr": str(data.get("self_pr", "")).strip(),
        "motivation": str(data.get("motivation", "")).strip(),
        "other": str(data.get("other", "")).strip(),
    }
    try:
        _save_audition_application(entry)
    except Exception as e:
        print(f"[audition] save failed: {e}", file=sys.stderr)
        return jsonify({"error": "応募の保存に失敗しました。時間をおいて再度お試しください。"}), 500

    try:
        _notify_audition_line(entry)
    except Exception as e:
        print(f"[audition] LINE notify failed: {e}")

    return jsonify({"ok": True})


@app.route("/audition/admin", methods=["GET", "POST"])
def audition_admin():
    import secrets

    web_password = os.environ.get("WEB_PASSWORD", "")
    error_html = ""

    if request.method == "POST":
        if web_password and request.form.get("password", "") == web_password:
            session["audition_admin_ok"] = True
        else:
            error_html = '<p class="error">パスワードが違います</p>'

    if not session.get("audition_admin_ok"):
        html = AUDITION_ADMIN_LOGIN_HTML.replace("__ERROR__", error_html)
        return html, (200 if not error_html else 401), {"Content-Type": "text/html; charset=utf-8"}

    csrf_token = session.get("audition_admin_csrf")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(24)
        session["audition_admin_csrf"] = csrf_token

    applications = list(reversed(_load_audition_applications()))
    if applications:
        def delete_form(application_id):
            return (
                f'<form class="delete-form" method="POST" action="/audition/admin/delete/{escape(application_id)}" '
                'onsubmit="return confirm(\'この応募データを完全に削除します。元に戻せません。よろしいですか？\')">'
                f'<input type="hidden" name="csrf_token" value="{escape(csrf_token)}">'
                '<button class="delete-button" type="submit">削除</button></form>'
            )

        def edit_link(application_id):
            return (
                f'<a class="edit-link" href="/audition/admin/edit/{escape(application_id)}">'
                '✏️ 編集</a>'
            )

        def activity_display(application):
            activity_name = str(application.get("activity_name", "")).strip()
            if activity_name:
                return str(escape(activity_name))
            return '<span class="missing-badge">⚠ 未記入</span>'

        cards = "".join(
            (
                f'<article class="app-card{" checked" if _audition_is_checked(a) else ""}" '
                f'id="app-{escape(a.get("id", ""))}" data-id="{escape(a.get("id", ""))}" '
                f'data-search="{escape(" ".join(str(a.get(key, "")) for key in AUDITION_COLUMNS))}">'
                '<div class="card-head">'
                f'<div class="check-toggle" title="確認済みにする">✓</div>'
                '<div>'
                f'<div class="name">{escape(a.get("name", ""))}</div>'
                f'<div class="furigana">{escape(a.get("furigana", ""))}</div>'
                f'<div class="activity">{activity_display(a)}</div>'
                f'</div><time class="date">{escape(a.get("created_at", ""))}</time></div>'
                '<dl class="quick-grid">'
                f'<div class="field"><dt>メール</dt><dd>{escape(a.get("email", ""))}</dd></div>'
                f'<div class="field"><dt>都道府県</dt><dd>{escape(a.get("prefecture", ""))}</dd></div>'
                f'<div class="field"><dt>性別</dt><dd>{escape(a.get("gender", "") or "未記入")}</dd></div>'
                f'<div class="field"><dt>未成年者の同意</dt><dd>{escape(a.get("minor_consent", "") or "未記入")}</dd></div>'
                f'<div class="field"><dt>配信経験</dt><dd>{escape(a.get("experience", ""))}</dd></div>'
                f'<div class="field"><dt>配信頻度</dt><dd>{escape(a.get("frequency", ""))}</dd></div>'
                f'<div class="field"><dt>得意ジャンル</dt><dd>{escape(a.get("genre", "") or "未記入")}</dd></div>'
                f'<div class="field"><dt>SNS</dt><dd>{escape(a.get("sns", "") or "未記入")}</dd></div>'
                '</dl>'
                '<details class="long-details"><summary>自己PR・応募動機を表示</summary><dl class="long-content">'
                f'<div class="long-field"><dt>活動歴・実績</dt><dd>{escape(a.get("history", "") or "未記入")}</dd></div>'
                f'<div class="long-field"><dt>自己PR</dt><dd>{escape(a.get("self_pr", "") or "未記入")}</dd></div>'
                f'<div class="long-field"><dt>応募動機</dt><dd>{escape(a.get("motivation", "") or "未記入")}</dd></div>'
                f'<div class="long-field"><dt>その他</dt><dd>{escape(a.get("other", "") or "未記入")}</dd></div>'
                '</dl></details>'
                f'<div class="card-actions">{edit_link(a.get("id", ""))}{delete_form(a.get("id", ""))}</div>'
                '</article>'
            )
            for a in applications
        )
        rows = "".join(
            f'<tr data-search="{escape(" ".join(str(a.get(key, "")) for key in AUDITION_COLUMNS))}">'
            f"<td>{escape(a.get('created_at',''))}</td>"
            f"<td>{escape(a.get('name',''))}</td>"
            f"<td>{activity_display(a)}</td>"
            f"<td>{escape(a.get('prefecture',''))}</td>"
            f"<td>{escape(a.get('frequency',''))}</td>"
            f"<td>{escape(a.get('experience',''))}</td>"
            f'<td><button class="detail-button" type="button" data-target="app-{escape(a.get("id", ""))}">詳細を見る</button></td>'
            f'<td><div class="table-actions">{edit_link(a.get("id", ""))}{delete_form(a.get("id", ""))}</div></td>'
            "</tr>"
            for a in applications
        )
    else:
        cards = '<p class="empty-state">応募はまだありません</p>'
        rows = '<tr><td colspan="8" class="empty-state">応募はまだありません</td></tr>'

    message = session.pop("audition_admin_message", None)
    if message:
        message_class = "ok" if message.get("ok") else "error"
        message_html = f'<p class="message {message_class}">{escape(message.get("text", ""))}</p>'
    else:
        message_html = ""

    if _audition_db_ready():
        storage_note = (
            '<p class="status ok">✅ 応募データはデータベース（Postgres）に保存されています。'
            'サーバーの再起動・再デプロイでも消えません。</p>'
        )
    elif os.environ.get("DATABASE_URL", ""):
        storage_note = (
            '<p class="status warn">⚠️ データベースに接続できていません。'
            '現在の応募はサーバー上のファイルにのみ保存されており、再デプロイやスリープ復帰で消える可能性があります。'
            'Render の環境変数 DATABASE_URL の値をご確認ください。</p>'
        )
    else:
        storage_note = (
            '<p class="status warn">⚠️ データベース未設定のため、応募はサーバー上のファイルにのみ保存されています。'
            'Render 無料プランではスリープ復帰・再デプロイでファイルが消えるため、応募も消えます。'
            'Render の環境変数に DATABASE_URL（面談予約アプリ eternal-interview-booking と同じ値）を設定してください。'
            '設定すると、その時点でファイルに残っている応募は自動でデータベースへ移行されます。</p>'
        )

    html = (
        AUDITION_ADMIN_HTML
        .replace("__ROWS__", rows)
        .replace("__CARDS__", cards)
        .replace("__COUNT__", str(len(applications)))
        .replace("__MESSAGE__", message_html)
        .replace("__STORAGE_NOTE__", storage_note)
        .replace("__CSRF_TOKEN_JS__", escape(csrf_token))
    )
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/audition/admin/new", methods=["GET", "POST"])
def audition_admin_new():
    """Googleフォーム経由ではなく、口頭・メールなどサイト外で届いた応募を
    管理者が手動で登録するためのフォーム。"""
    import hmac
    import secrets
    import uuid
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if not session.get("audition_admin_ok"):
        return redirect("/audition/admin")

    csrf_token = session.get("audition_admin_csrf")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(24)
        session["audition_admin_csrf"] = csrf_token

    form_values = {field: "" for field in AUDITION_EDITABLE_FIELDS}
    error_html = ""

    if request.method == "POST":
        submitted_token = str(request.form.get("csrf_token", ""))
        if not hmac.compare_digest(str(csrf_token), submitted_token):
            return "不正なリクエストです。管理画面を再読み込みしてください。", 403

        form_values = {
            field: str(request.form.get(field, "")).strip()
            for field in AUDITION_EDITABLE_FIELDS
        }
        if not form_values["name"]:
            error_html = '<p class="error">お名前は空欄にできません。</p>'
        else:
            JST = ZoneInfo("Asia/Tokyo")
            entry = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
                **form_values,
            }
            try:
                _save_audition_application(entry)
                session["audition_admin_message"] = {
                    "ok": True,
                    "text": "応募データを手動で追加しました。",
                }
                return redirect(f"/audition/admin#app-{entry['id']}")
            except Exception as e:
                print(f"[audition] manual add failed: {e}", file=sys.stderr)
                error_html = '<p class="error">追加に失敗しました。データは登録されていません。</p>'

    def options_html(values, current):
        current = str(current or "")
        choices = list(values)
        if current and current not in choices:
            choices.insert(0, current)
        options = [
            f'<option value=""{" selected" if not current else ""}>未記入</option>'
        ]
        for value in choices:
            selected = " selected" if value == current else ""
            options.append(
                f'<option value="{escape(value)}"{selected}>{escape(value)}</option>'
            )
        return "".join(options)

    replacements = {
        "__CSRF_TOKEN__": escape(csrf_token),
        "__ACTIVITY_NAME__": escape(form_values.get("activity_name", "")),
        "__NAME__": escape(form_values.get("name", "")),
        "__FURIGANA__": escape(form_values.get("furigana", "")),
        "__EMAIL__": escape(form_values.get("email", "")),
        "__HISTORY__": escape(form_values.get("history", "")),
        "__GENRE__": escape(form_values.get("genre", "")),
        "__SNS__": escape(form_values.get("sns", "")),
        "__SELF_PR__": escape(form_values.get("self_pr", "")),
        "__MOTIVATION__": escape(form_values.get("motivation", "")),
        "__OTHER__": escape(form_values.get("other", "")),
        "__GENDER_OPTIONS__": options_html(
            ["男性", "女性", "その他", "回答しない"],
            form_values.get("gender", ""),
        ),
        "__PREFECTURE_OPTIONS__": options_html(
            PREFECTURES,
            form_values.get("prefecture", ""),
        ),
        "__MINOR_OPTIONS__": options_html(
            ["該当しない（成人）", "同意している", "まだ得ていない"],
            form_values.get("minor_consent", ""),
        ),
        "__EXPERIENCE_OPTIONS__": options_html(
            ["あり", "なし"],
            form_values.get("experience", ""),
        ),
        "__FREQUENCY_OPTIONS__": options_html(
            ["週1回未満", "週1〜2回", "週3〜4回", "週5回以上"],
            form_values.get("frequency", ""),
        ),
        "__ERROR__": error_html,
    }
    html = AUDITION_ADMIN_NEW_HTML
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, str(value))
    return html, 200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
    }


@app.route("/audition/admin/edit/<application_id>", methods=["GET", "POST"])
def audition_admin_edit(application_id):
    import hmac
    import secrets

    if not session.get("audition_admin_ok"):
        return redirect("/audition/admin")

    csrf_token = session.get("audition_admin_csrf")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(24)
        session["audition_admin_csrf"] = csrf_token

    applications = _load_audition_applications()
    application = next(
        (
            dict(row)
            for row in applications
            if str(row.get("id", "")) == str(application_id)
        ),
        None,
    )
    if not application:
        session["audition_admin_message"] = {
            "ok": False,
            "text": "編集対象の応募データは見つかりませんでした。",
        }
        return redirect("/audition/admin")

    error_html = ""
    if request.method == "POST":
        submitted_token = str(request.form.get("csrf_token", ""))
        if not hmac.compare_digest(str(csrf_token), submitted_token):
            return "不正なリクエストです。管理画面を再読み込みしてください。", 403

        updates = {
            field: str(request.form.get(field, "")).strip()
            for field in AUDITION_EDITABLE_FIELDS
        }
        application.update(updates)
        if not updates["name"]:
            error_html = '<p class="error">お名前は空欄にできません。</p>'
        else:
            try:
                if _update_audition_application(application_id, updates):
                    session["audition_admin_message"] = {
                        "ok": True,
                        "text": "応募データの変更を保存しました。",
                    }
                    return redirect(f"/audition/admin#app-{application_id}")
                error_html = '<p class="error">対象の応募データは見つかりませんでした。</p>'
            except Exception as e:
                print(f"[audition] update failed: {e}", file=sys.stderr)
                error_html = '<p class="error">保存に失敗しました。データは更新されていません。</p>'

    def options_html(values, current):
        current = str(current or "")
        choices = list(values)
        if current and current not in choices:
            choices.insert(0, current)
        options = [
            f'<option value=""{" selected" if not current else ""}>未記入</option>'
        ]
        for value in choices:
            selected = " selected" if value == current else ""
            options.append(
                f'<option value="{escape(value)}"{selected}>{escape(value)}</option>'
            )
        return "".join(options)

    replacements = {
        "__CREATED_AT__": escape(application.get("created_at", "")),
        "__DISPLAY_NAME__": escape(application.get("name", "")),
        "__CSRF_TOKEN__": escape(csrf_token),
        "__ACTIVITY_NAME__": escape(application.get("activity_name", "")),
        "__NAME__": escape(application.get("name", "")),
        "__FURIGANA__": escape(application.get("furigana", "")),
        "__EMAIL__": escape(application.get("email", "")),
        "__HISTORY__": escape(application.get("history", "")),
        "__GENRE__": escape(application.get("genre", "")),
        "__SNS__": escape(application.get("sns", "")),
        "__SELF_PR__": escape(application.get("self_pr", "")),
        "__MOTIVATION__": escape(application.get("motivation", "")),
        "__OTHER__": escape(application.get("other", "")),
        "__GENDER_OPTIONS__": options_html(
            ["男性", "女性", "その他", "回答しない"],
            application.get("gender", ""),
        ),
        "__PREFECTURE_OPTIONS__": options_html(
            PREFECTURES,
            application.get("prefecture", ""),
        ),
        "__MINOR_OPTIONS__": options_html(
            ["該当しない（成人）", "同意している", "まだ得ていない"],
            application.get("minor_consent", ""),
        ),
        "__EXPERIENCE_OPTIONS__": options_html(
            ["あり", "なし"],
            application.get("experience", ""),
        ),
        "__FREQUENCY_OPTIONS__": options_html(
            ["週1回未満", "週1〜2回", "週3〜4回", "週5回以上"],
            application.get("frequency", ""),
        ),
        "__ERROR__": error_html,
    }
    html = AUDITION_ADMIN_EDIT_HTML
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, str(value))
    return html, 200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
    }


@app.route("/audition/admin/delete/<application_id>", methods=["POST"])
def audition_admin_delete(application_id):
    import hmac

    if not session.get("audition_admin_ok"):
        return redirect("/audition/admin")

    expected_token = str(session.get("audition_admin_csrf", ""))
    submitted_token = str(request.form.get("csrf_token", ""))
    if not expected_token or not hmac.compare_digest(expected_token, submitted_token):
        return "不正なリクエストです。管理画面を再読み込みしてください。", 403

    try:
        deleted = _delete_audition_application(application_id)
        if deleted:
            session["audition_admin_message"] = {
                "ok": True,
                "text": "応募データを1件削除しました。",
            }
        else:
            session["audition_admin_message"] = {
                "ok": False,
                "text": "対象の応募データは見つかりませんでした。",
            }
    except Exception as e:
        print(f"[audition] delete failed: {e}", file=sys.stderr)
        session["audition_admin_message"] = {
            "ok": False,
            "text": "削除に失敗しました。データは削除されていません。",
        }

    return redirect("/audition/admin")


@app.route("/audition/admin/check/<application_id>", methods=["POST"])
def audition_admin_check(application_id):
    import hmac

    if not session.get("audition_admin_ok"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    expected_token = str(session.get("audition_admin_csrf", ""))
    submitted_token = str(data.get("csrf_token", ""))
    if not expected_token or not hmac.compare_digest(expected_token, submitted_token):
        return jsonify({"error": "不正なリクエストです。管理画面を再読み込みしてください。"}), 403

    try:
        updated = _set_audition_checked(application_id, bool(data.get("checked")))
    except Exception as e:
        print(f"[audition] check toggle failed: {e}", file=sys.stderr)
        return jsonify({"error": "更新に失敗しました"}), 500

    if not updated:
        return jsonify({"error": "対象の応募データは見つかりませんでした"}), 404
    return jsonify({"ok": True})


@app.route("/audition/admin/slides")
def audition_admin_slides():
    """未確認（✓なし）の応募者の活動名・自己PR・応募動機を、応募順のスライドで表示する。"""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if not session.get("audition_admin_ok"):
        return redirect("/audition/admin")

    applicants = [a for a in _load_audition_applications() if not _audition_is_checked(a)]
    total = 1 + (1 + len(applicants) if applicants else 0)
    today = datetime.now(ZoneInfo("Asia/Tokyo"))
    today_label = f"{today.year}年{today.month}月{today.day}日"

    def footer(page):
        return (
            '<footer class="s-foot"><span>ETERNALd.c.t AUDITION</span>'
            f"<span>{page} / {total}</span></footer>"
        )

    def activity_html(application):
        activity_name = str(application.get("activity_name", "")).strip()
        if activity_name:
            return str(escape(activity_name))
        return '<span class="missing">⚠ 活動名 未記入</span>'

    def text_block(value):
        value = str(value or "").replace("\r\n", "\n").strip()
        if not value:
            return '<div class="col-text fit-check empty">未記入</div>'
        return f'<div class="col-text fit-check">{escape(value)}</div>'

    if applicants:
        cover_meta = (
            f'<p class="cover-meta">未確認の応募 <strong>{len(applicants)}</strong> 名'
            f" ・ {today_label} 時点</p>"
            '<p class="cover-note">→ キー / スワイプで次へ　F で全画面</p>'
        )
    else:
        cover_meta = (
            f'<p class="cover-meta">未確認の応募はありません（{today_label} 時点）</p>'
            '<p class="cover-note">管理画面で✓を外すと、その応募がスライドに入ります</p>'
        )

    slides = [
        '<section class="slide cover"><div class="slide-inner">'
        '<p class="cover-kicker">ETERNALd.c.t AUDITION</p>'
        '<h1 class="cover-title">応募者紹介<br>自己PR・応募動機</h1>'
        f"{cover_meta}</div></section>"
    ]

    if applicants:
        index_items = "".join(
            f'<li><a href="#{n + 3}" data-goto="{n + 3}">'
            f'<span class="no">{n + 1:02d}</span><span>{activity_html(a)}</span></a></li>'
            for n, a in enumerate(applicants)
        )
        slides.append(
            '<section class="slide"><div class="slide-inner">'
            '<header class="s-head"><h2 class="s-title">応募者一覧</h2>'
            f'<span class="s-sub">未確認 {len(applicants)} 名・応募順</span></header>'
            f'<ol class="index fit fit-check" data-max="2" data-min="0.9">{index_items}</ol>'
            f"{footer(2)}</div></section>"
        )
        for n, a in enumerate(applicants):
            slides.append(
                '<section class="slide"><div class="slide-inner">'
                f'<header class="s-head"><span class="s-no">No.{n + 1:02d}</span>'
                f'<h2 class="s-name">{activity_html(a)}</h2></header>'
                '<div class="s-body fit" data-max="1.8" data-min="0.85">'
                f'<article class="col"><h3 class="chip">自己PR</h3>{text_block(a.get("self_pr"))}</article>'
                f'<article class="col"><h3 class="chip">応募動機</h3>{text_block(a.get("motivation"))}</article>'
                f"</div>{footer(n + 3)}</div></section>"
            )

    html = (
        AUDITION_SLIDES_HTML
        .replace("__TOTAL__", str(total))
        .replace("__SLIDES__", "\n".join(slides))
    )
    return html, 200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
    }

@app.route("/audition/admin/logout")
def audition_admin_logout():
    session.pop("audition_admin_ok", None)
    return redirect("/audition/admin")


# ── LINEスタンプメーカー ──────────────────────────────────────────
# ChatGPT などで手動生成したキャラクターのポーズ違い画像（最大16枚）をアップロードすると、
# 背景透過・白ふち・セリフ合成・LINEスタンプサイズ調整をまとめて行う。外部APIキーは不要。

import re as _re
import shutil
import tempfile
import uuid

STICKER_TMP_ROOT = Path(tempfile.gettempdir()) / "line_stickers"
_STICKER_JOB_RE = _re.compile(r"^[0-9a-f]{32}$")
_STICKER_FILE_RE = _re.compile(r"^\d{2}\.png$")
_STICKER_JOB_MAX_AGE = 2 * 60 * 60  # 2時間でクリーンアップ


def _cleanup_old_sticker_jobs():
    import time

    if not STICKER_TMP_ROOT.exists():
        return
    now = time.time()
    for job_dir in STICKER_TMP_ROOT.iterdir():
        try:
            if job_dir.is_dir() and now - job_dir.stat().st_mtime > _STICKER_JOB_MAX_AGE:
                shutil.rmtree(job_dir, ignore_errors=True)
        except OSError:
            pass


STICKERS_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>LINEスタンプメーカー | ETERNALd.c.t</title>
<style>
:root {
  --bg: #f7f7fb; --surface: #ffffff; --surface2: #f1f0fa;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent-text: #9333ea; --text: #1f2333; --muted: #6b7280; --border: #eceaf5;
  --shadow: 0 6px 24px rgba(124,58,237,0.08);
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding-bottom: 40px;
}
.header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 28px 18px 24px; text-align: center; }
.header .badge {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
  color: white; background: var(--grad); padding: 4px 14px; border-radius: 999px; margin-bottom: 10px;
}
.header h1 { font-size: 19px; font-weight: 800; }
.header p { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.6; }
.main { padding: 22px 16px; max-width: 480px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 20px; box-shadow: var(--shadow); }
.card h2 { font-size: 14px; font-weight: 800; margin-bottom: 10px; }
.steps { font-size: 12.5px; color: var(--muted); line-height: 1.9; padding-left: 4px; }
.steps li { margin-bottom: 6px; }
.file-btn {
  display: block; width: 100%; padding: 18px; text-align: center; border: 2px dashed var(--border);
  border-radius: 14px; font-size: 15px; font-weight: 700; color: var(--accent-text);
  background: var(--surface2); cursor: pointer; margin-bottom: 12px;
}
input[type=file] { display: none; }
.count-note { font-size: 12px; color: var(--muted); text-align: center; margin-bottom: 14px; min-height: 18px; }
.thumb-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
.thumb-grid img { width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid var(--border); }
.submit-btn {
  width: 100%; padding: 16px; border: none; border-radius: 12px; background: var(--grad); color: white;
  font-size: 16px; font-weight: 800; cursor: pointer; letter-spacing: 0.02em;
  box-shadow: 0 6px 18px rgba(217,70,239,0.28);
}
.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; box-shadow: none; }
.error-box {
  background: #fff1f2; border: 1px solid #fecdd3; border-radius: 12px; padding: 16px;
  text-align: center; margin-top: 12px;
}
.error-box p { color: #e11d48; font-size: 13px; font-weight: 600; margin-bottom: 10px; }
.error-box a {
  display: inline-block; font-size: 13px; font-weight: 700; color: var(--accent-text);
  text-decoration: none; padding: 8px 20px; border: 1.5px solid var(--border); border-radius: 8px;
  background: var(--surface);
}
</style>
</head>
<body>
<div class="header">
  <span class="badge">ETERNAL d.c.t</span>
  <h1>🎨 LINEスタンプメーカー</h1>
  <p>画像をアップロードするだけで背景透過＋白ふちのLINEスタンプに自動加工します。</p>
</div>
<div class="main">
  <div class="card">
    <h2>使い方</h2>
    <ol class="steps">
      <li>ChatGPT（Plus等）に元写真1〜2枚を渡し、「このキャラクターのポーズ・表情違いを16種類、背景は無地の単色で生成して」と依頼して16枚ダウンロードする</li>
      <li>その画像（最大16枚）をこのページにアップロードする</li>
      <li>「スタンプを作成する」を押すと背景透過＋白ふちで完成、そのまま保存できる</li>
    </ol>
  </div>
  <div class="card">
    <h2>画像をアップロード（最大16枚）</h2>
    <form id="stkForm" action="/stickers/generate" method="post" enctype="multipart/form-data">
      <label class="file-btn" for="photoInput">📷 写真を選ぶ</label>
      <input type="file" id="photoInput" name="photos" accept="image/*" multiple>
      <div class="count-note" id="countNote"></div>
      <div class="thumb-grid" id="thumbGrid"></div>
      <button class="submit-btn" id="submitBtn" type="submit" disabled>スタンプを作成する</button>
      __ERROR__
    </form>
  </div>
</div>
<script>
document.getElementById('photoInput').addEventListener('change', function (e) {
  const files = Array.from(e.target.files).slice(0, 16);
  const grid = document.getElementById('thumbGrid');
  const submitBtn = document.getElementById('submitBtn');
  const countNote = document.getElementById('countNote');
  grid.innerHTML = '';
  if (!files.length) {
    submitBtn.disabled = true;
    countNote.textContent = '';
    return;
  }
  files.forEach(function (file) {
    const reader = new FileReader();
    reader.onload = function (ev) {
      const img = document.createElement('img');
      img.src = ev.target.result;
      grid.appendChild(img);
    };
    reader.readAsDataURL(file);
  });
  submitBtn.disabled = false;
  countNote.textContent = files.length + '枚 選択中';
});
</script>
</body>
</html>"""


STICKERS_RESULT_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>スタンプ完成 | ETERNALd.c.t</title>
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
  padding-bottom: 48px;
}
.header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 16px 18px; display: flex; align-items: center; gap: 12px;
}
.back-btn {
  flex-shrink: 0; font-size: 13px; font-weight: 700; color: var(--accent-text);
  text-decoration: none; padding: 8px 14px; border: 1.5px solid var(--border);
  border-radius: 10px; background: var(--surface); white-space: nowrap;
}
.header-text { flex: 1; text-align: center; }
.header-text h1 { font-size: 16px; font-weight: 800; }
.header-text p { font-size: 11px; color: var(--muted); margin-top: 3px; }
.header-spacer { flex-shrink: 0; width: 72px; }
.main { padding: 18px 14px; max-width: 520px; margin: 0 auto; }
.zip-btn {
  display: block; text-align: center; width: 100%; padding: 16px; border-radius: 14px;
  background: var(--grad); color: white; font-weight: 800; font-size: 15px; text-decoration: none;
  box-shadow: 0 6px 18px rgba(217,70,239,0.28); margin-bottom: 10px;
}
.save-hint {
  font-size: 11.5px; color: var(--muted); text-align: center; margin-bottom: 18px; line-height: 1.7;
}
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.stk-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
  padding: 10px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 8px;
}
.stk-img-wrap {
  width: 100%; aspect-ratio: 1/1; border-radius: 10px; overflow: hidden;
  background: repeating-conic-gradient(#e8e8e8 0% 25%, #f8f8f8 0% 50%) 50% / 14px 14px;
  display: flex; align-items: center; justify-content: center;
}
.stk-img-wrap img { width: 100%; height: 100%; object-fit: contain; }
.stk-save {
  display: block; text-align: center; font-size: 13px; font-weight: 800; color: white;
  text-decoration: none; padding: 10px; border-radius: 10px;
  background: var(--grad); box-shadow: 0 3px 10px rgba(217,70,239,0.25);
}
</style>
</head>
<body>
<div class="header">
  <a class="back-btn" href="/stickers">← 戻る</a>
  <div class="header-text">
    <h1>✅ 完成（__COUNT__枚）</h1>
    <p>タップして保存してください</p>
  </div>
  <div class="header-spacer"></div>
</div>
<div class="main">
  <a class="zip-btn" href="/stickers/zip/__JOB_ID__">📦 ZIPでまとめてダウンロード</a>
  <p class="save-hint">スマホの場合：「保存」ボタンをタップ → 写真アプリに保存<br>または画像を長押し →「写真に追加」</p>
  <div class="grid">
    __THUMBS__
  </div>
</div>
</body>
</html>"""


_STICKERS_ERROR_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>エラー | LINEスタンプメーカー</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #f7f7fb; min-height: 100vh; display: flex; align-items: center; justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', sans-serif; padding: 24px;
}
.card {
  background: white; border-radius: 18px; padding: 36px 28px; text-align: center; max-width: 340px;
  box-shadow: 0 6px 24px rgba(124,58,237,0.08); border: 1px solid #eceaf5;
}
.icon { font-size: 40px; margin-bottom: 14px; }
h1 { font-size: 16px; font-weight: 800; margin-bottom: 10px; }
p { font-size: 13px; color: #6b7280; line-height: 1.7; margin-bottom: 24px; }
a {
  display: inline-block; padding: 12px 28px; border-radius: 10px; font-weight: 800; font-size: 14px;
  background: linear-gradient(135deg,#7c3aed,#d946ef,#ec4899); color: white; text-decoration: none;
  box-shadow: 0 4px 12px rgba(217,70,239,0.25);
}
</style>
</head>
<body>
<div class="card">
  <div class="icon">⚠️</div>
  <h1>__TITLE__</h1>
  <p>__MSG__</p>
  <a href="/stickers">← 戻る</a>
</div>
</body>
</html>"""


def _stickers_error(title, msg, status):
    html = _STICKERS_ERROR_HTML.replace("__TITLE__", title).replace("__MSG__", msg)
    return html, status, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/stickers")
def stickers_index():
    return STICKERS_HTML.replace("__ERROR__", ""), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/stickers/generate", methods=["POST"])
def stickers_generate():
    from sticker_generator import process_sticker

    files = [f for f in request.files.getlist("photos") if f and f.filename]

    if not files:
        return _stickers_error("画像が選択されていません", "写真を選んでから「スタンプを作成する」を押してください。", 400)

    files = files[:16]

    _cleanup_old_sticker_jobs()
    STICKER_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    job_dir = STICKER_TMP_ROOT / job_id
    job_dir.mkdir(parents=True)

    saved_names = []
    for f in files:
        try:
            png_bytes = process_sticker(f.read())
        except Exception:
            continue
        name = f"{len(saved_names) + 1:02d}.png"
        (job_dir / name).write_bytes(png_bytes)
        saved_names.append(name)

    if not saved_names:
        shutil.rmtree(job_dir, ignore_errors=True)
        return _stickers_error(
            "処理に失敗しました",
            "画像を正常に処理できませんでした。別の画像でお試しください。",
            500,
        )

    thumbs_html = "".join(
        f'<div class="stk-card">'
        f'<div class="stk-img-wrap"><img src="/stickers/file/{job_id}/{name}" alt="sticker {i+1}"></div>'
        f'<a class="stk-save" href="/stickers/file/{job_id}/{name}" download="{name}">保存</a>'
        f'</div>'
        for i, name in enumerate(saved_names)
    )
    html = (STICKERS_RESULT_HTML
            .replace("__THUMBS__", thumbs_html)
            .replace("__JOB_ID__", job_id)
            .replace("__COUNT__", str(len(saved_names))))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/stickers/file/<job_id>/<filename>")
def stickers_file(job_id, filename):
    from flask import send_file

    if not _STICKER_JOB_RE.match(job_id) or not _STICKER_FILE_RE.match(filename):
        return _stickers_error("見つかりません", "ファイルが存在しないか、有効期限が切れています。", 404)
    path = STICKER_TMP_ROOT / job_id / filename
    if not path.exists():
        return _stickers_error("見つかりません", "ファイルが存在しないか、有効期限が切れています。", 404)
    return send_file(path, mimetype="image/png")


@app.route("/stickers/zip/<job_id>")
def stickers_zip(job_id):
    import io
    import zipfile
    from flask import send_file

    if not _STICKER_JOB_RE.match(job_id):
        return _stickers_error("見つかりません", "ZIPファイルが存在しないか、有効期限が切れています。", 404)
    job_dir = STICKER_TMP_ROOT / job_id
    if not job_dir.exists():
        return _stickers_error("見つかりません", "ZIPファイルが存在しないか、有効期限が切れています。", 404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(job_dir.glob("*.png")):
            zf.write(p, p.name)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="line_stickers.zip")


# ── /motion モーション動画ショーケース ───────────────────────────────

MOTION_CONFIG_PATH = Path("persona/motion_config.yaml")
_MOTION_ASPECTS = {"16:9", "9:16", "1:1", "4:5"}


def _motion_aspect(value):
    """縦横比を "16:9" 形式に正規化する。

    YAML でクォートせずに 16:9 と書くと 60進数の整数（969）として読まれるため、
    整数なら元の "16:9" に戻してから判定する。
    """
    if isinstance(value, int) and not isinstance(value, bool):
        value = f"{value // 60}:{value % 60}"
    value = str(value or "").strip()
    return value if value in _MOTION_ASPECTS else "16:9"


def _motion_media_url(value):
    """動画・ポスター画像のURLを検証する（/static/ 配下か https:// のみ許可）"""
    value = str(value or "").strip()
    if value.startswith("/static/") or value.startswith("https://"):
        return value
    return ""


def _youtube_id(value):
    """YouTube の URL（通常・短縮・Shorts・埋め込み）または動画IDから11桁の動画IDを取り出す"""
    import re

    value = str(value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})", value)
    return m.group(1) if m else ""


def _load_motion_config():
    """persona/motion_config.yaml からページ設定と作品一覧を読み込む"""
    import yaml

    if not MOTION_CONFIG_PATH.exists():
        return {"title": "MOTION WORKS", "lead": "", "contact_url": "", "contact_label": ""}, []
    with open(MOTION_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    page = data.get("page") or {}
    contact_url = str(page.get("contact_url") or "").strip()
    page_info = {
        "title": str(page.get("title") or "MOTION WORKS"),
        "lead": str(page.get("lead") or ""),
        "contact_url": contact_url if contact_url.startswith("https://") else "",
        "contact_label": str(page.get("contact_label") or "制作について相談する"),
    }

    works = []
    for w in data.get("works") or []:
        if not isinstance(w, dict) or not w.get("id") or not w.get("title"):
            continue
        work = {
            "id": str(w["id"]),
            "title": str(w["title"]),
            "category": str(w.get("category") or ""),
            "description": str(w.get("description") or ""),
            "aspect": _motion_aspect(w.get("aspect")),
            "video": _motion_media_url(w.get("video")),
            "poster": _motion_media_url(w.get("poster")),
            "youtube": _youtube_id(w.get("youtube")),
            "duration": str(w.get("duration") or ""),
            "use": str(w.get("use") or ""),
        }
        # 動画も YouTube も未設定の枠は「制作中」扱い（?preview=1 のときだけ表示）
        work["placeholder"] = not (work["video"] or work["youtube"])
        works.append(work)
    return page_info, works


MOTION_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ | ETERNALd.c.t</title>
<meta name="description" content="ETERNALd.c.t が制作するモーション動画の作例集です。">
<meta property="og:title" content="__TITLE__ | ETERNALd.c.t">
<meta property="og:description" content="ETERNALd.c.t が制作するモーション動画の作例集です。">
<meta property="og:type" content="website">
<style>
:root {
  color-scheme: dark;
  --bg: #0d0b14; --surface: #17141f; --surface2: #221e2c;
  --grad: linear-gradient(135deg, #7c3aed, #d946ef, #ec4899);
  --accent: #e879f9; --text: #f4f2f8; --muted: #a8a3b6; --border: #2c2738;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
[hidden] { display: none !important; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', 'Noto Sans JP', sans-serif;
}
body.modal-open { overflow: hidden; }
a { color: inherit; }
.hero {
  position: relative; overflow: hidden; text-align: center;
  padding: 64px 16px 44px; border-bottom: 1px solid var(--border);
}
.hero::before {
  content: ""; position: absolute; inset: -40%; z-index: 0; opacity: 0.35;
  background: radial-gradient(circle at 30% 40%, #7c3aed 0, transparent 38%),
              radial-gradient(circle at 70% 60%, #ec4899 0, transparent 34%);
  animation: drift 14s ease-in-out infinite alternate;
}
@keyframes drift { from { transform: translate(-4%, -3%) rotate(0deg); } to { transform: translate(4%, 3%) rotate(8deg); } }
.hero > * { position: relative; z-index: 1; }
.badge {
  display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: 0.24em;
  color: white; background: var(--grad); padding: 5px 16px; border-radius: 999px; margin-bottom: 16px;
}
.hero h1 { font-size: clamp(24px, 5.4vw, 40px); font-weight: 900; line-height: 1.35; }
.hero p {
  font-size: 14px; color: var(--muted); margin: 14px auto 0; max-width: 560px;
  line-height: 1.9; white-space: pre-wrap;
}
.cta {
  display: inline-block; margin-top: 26px; padding: 14px 28px; border-radius: 999px;
  background: var(--grad); color: white; font-weight: 800; font-size: 15px; text-decoration: none;
  box-shadow: 0 8px 26px rgba(217,70,239,0.35); transition: transform 0.15s, opacity 0.15s;
}
.cta:hover { transform: translateY(-1px); }
.cta:active { opacity: 0.85; transform: scale(0.98); }
.preview-bar {
  background: #3b2a06; color: #fcd34d; border-bottom: 1px solid #6b4e0e;
  font-size: 12px; line-height: 1.7; text-align: center; padding: 10px 16px;
}
.filters {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;
  padding: 26px 16px 8px; max-width: 1120px; margin: 0 auto;
}
.chip {
  border: 1px solid var(--border); background: var(--surface); color: var(--muted);
  padding: 8px 16px; border-radius: 999px; font-size: 13px; font-weight: 700; cursor: pointer;
}
.chip[aria-pressed="true"] { background: var(--grad); color: white; border-color: transparent; }
.grid { max-width: 1120px; margin: 0 auto; padding: 18px 16px 8px; column-width: 300px; column-gap: 18px; }
.card {
  break-inside: avoid; -webkit-column-break-inside: avoid; margin-bottom: 18px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 18px; overflow: hidden;
}
.media {
  position: relative; display: block; width: 100%; border: 0; padding: 0; cursor: pointer;
  background: var(--surface2); color: white; overflow: hidden;
}
.media video, .media img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
.ar-16x9 { aspect-ratio: 16 / 9; }
.ar-9x16 { aspect-ratio: 9 / 16; }
.ar-1x1 { aspect-ratio: 1 / 1; }
.ar-4x5 { aspect-ratio: 4 / 5; }
.play {
  position: absolute; right: 12px; bottom: 12px; width: 40px; height: 40px; border-radius: 50%;
  background: rgba(13,11,20,0.72); display: flex; align-items: center; justify-content: center;
  font-size: 14px; padding-left: 3px; transition: transform 0.15s;
}
.media:hover .play, .media:focus-visible .play { transform: scale(1.1); background: #d946ef; }
.media:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; }
.placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  cursor: default; background: linear-gradient(120deg, #1d1828, #2d2140, #1d1828);
  background-size: 300% 300%; animation: shimmer 6s ease-in-out infinite;
  color: var(--muted); font-size: 12px; font-weight: 700; letter-spacing: 0.08em;
}
.placeholder strong { font-size: 15px; color: var(--text); letter-spacing: 0.2em; }
@keyframes shimmer { 0%, 100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }
.card-body { padding: 16px 18px 18px; }
.tag {
  display: inline-block; font-size: 11px; font-weight: 800; color: var(--accent);
  border: 1px solid rgba(232,121,249,0.4); padding: 2px 10px; border-radius: 999px; margin-bottom: 10px;
}
.card h3 { font-size: 16px; font-weight: 800; line-height: 1.5; }
.desc { font-size: 13px; color: var(--muted); line-height: 1.8; margin-top: 6px; white-space: pre-wrap; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 12px; font-size: 12px; color: var(--muted); }
.meta b { color: var(--text); font-weight: 700; margin-right: 4px; }
.empty { text-align: center; color: var(--muted); font-size: 14px; padding: 56px 16px; }
.bottom-cta { text-align: center; padding: 48px 16px 20px; }
.bottom-cta h2 { font-size: 20px; font-weight: 900; }
.bottom-cta p { font-size: 13px; color: var(--muted); margin-top: 8px; line-height: 1.8; }
footer { text-align: center; font-size: 12px; color: var(--muted); padding: 36px 16px 44px; }
footer a { color: var(--muted); }
.modal {
  position: fixed; inset: 0; z-index: 100; background: rgba(5,4,9,0.9);
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.modal-inner {
  position: relative; width: 100%; max-height: 100%; overflow-y: auto;
  max-width: max(360px, min(960px, calc(68vh * var(--r, 1.7778))));
  background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
}
.modal-media { margin: 0 auto; background: #000; width: min(100%, calc(68vh * var(--r, 1.7778))); aspect-ratio: var(--ar, 16 / 9); }
.modal-media video, .modal-media iframe { width: 100%; height: 100%; border: 0; display: block; background: #000; }
.modal-body { padding: 16px 20px 22px; }
.modal-body h2 { font-size: 18px; font-weight: 800; line-height: 1.5; }
.modal-close {
  position: absolute; top: 10px; right: 10px; z-index: 2; width: 38px; height: 38px; border-radius: 50%;
  border: 0; background: rgba(13,11,20,0.8); color: white; font-size: 20px; cursor: pointer;
}
@media (prefers-reduced-motion: reduce) {
  .hero::before, .placeholder { animation: none; }
}
</style>
</head>
<body>
<header class="hero">
  <span class="badge">MOTION WORKS</span>
  <h1 id="pageTitle"></h1>
  <p id="pageLead"></p>
  <a class="cta" id="ctaTop" target="_blank" rel="noopener" hidden></a>
</header>
<div class="preview-bar" id="previewBar" hidden>
  プレビュー表示中 —「制作中」の枠は公開ページ（URL末尾の ?preview=1 なし）には表示されません
</div>
<nav class="filters" id="filters" aria-label="カテゴリで絞り込み"></nav>
<main class="grid" id="grid"></main>
<p class="empty" id="empty" hidden>現在、作例を準備中です。</p>
<section class="bottom-cta" id="ctaBottom" hidden>
  <h2>「こんな動画がほしい」を、かたちに。</h2>
  <p>用途・尺・ご予算がざっくりでも大丈夫です。お気軽にご相談ください。</p>
  <a class="cta" id="ctaBottomLink" target="_blank" rel="noopener"></a>
</section>
<footer>&copy; ETERNALd.c.t ・ <a href="https://eternaldct.net" target="_blank" rel="noopener">eternaldct.net</a></footer>

<div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle" hidden>
  <div class="modal-inner" id="modalInner">
    <button class="modal-close" id="modalClose" aria-label="閉じる">&times;</button>
    <div class="modal-media" id="modalMedia"></div>
    <div class="modal-body">
      <span class="tag" id="modalTag"></span>
      <h2 id="modalTitle"></h2>
      <p class="desc" id="modalDesc"></p>
      <div class="meta" id="modalMeta"></div>
    </div>
  </div>
</div>

<script>
const DATA = __MOTION_JSON__;
const RATIOS = { "16:9": [16, 9], "9:16": [9, 16], "1:1": [1, 1], "4:5": [4, 5] };
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const visibleVideos = new Set();
let activeFilter = "";
let lastFocus = null;

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text) node.textContent = text;
  return node;
}

function metaRow(work) {
  const meta = el("div", "meta");
  [["尺", work.duration], ["用途", work.use]].forEach(([label, value]) => {
    if (!value) return;
    const item = el("span");
    item.appendChild(el("b", "", label));
    item.appendChild(document.createTextNode(value));
    meta.appendChild(item);
  });
  return meta;
}

// 画面内に入った動画だけ読み込んで再生し、画面外に出たら止める（通信量とバッテリー対策）
const observer = ("IntersectionObserver" in window && !reduceMotion) ? new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    const video = entry.target;
    if (entry.isIntersecting) {
      visibleVideos.add(video);
      if (!video.getAttribute("src")) video.src = video.dataset.src;
      if (!document.body.classList.contains("modal-open")) video.play().catch(() => {});
    } else {
      visibleVideos.delete(video);
      video.pause();
    }
  });
}, { threshold: 0.35 }) : null;

function buildMedia(work) {
  const ratioClass = "ar-" + work.aspect.replace(":", "x");
  if (work.placeholder) {
    const box = el("div", "media placeholder " + ratioClass);
    box.appendChild(el("strong", "", "COMING SOON"));
    box.appendChild(el("span", "", "制作中 ・ " + work.aspect));
    return box;
  }
  const btn = el("button", "media " + ratioClass);
  btn.type = "button";
  btn.setAttribute("aria-label", "「" + work.title + "」を再生");
  if (work.video) {
    const video = document.createElement("video");
    video.muted = true; video.loop = true; video.playsInline = true;
    video.setAttribute("muted", ""); video.setAttribute("playsinline", "");
    video.preload = "none";
    if (work.poster) video.poster = work.poster;
    video.dataset.src = work.video;
    if (observer) {
      observer.observe(video);
    } else if (!work.poster) {
      // 自動再生しない環境では、ポスター画像の代わりに冒頭のフレームを表示する
      video.preload = "metadata";
      video.src = work.video + "#t=0.1";
    }
    btn.appendChild(video);
  } else {
    const img = document.createElement("img");
    img.loading = "lazy"; img.alt = "";
    img.src = work.poster || ("https://i.ytimg.com/vi/" + work.youtube + "/hqdefault.jpg");
    btn.appendChild(img);
  }
  btn.appendChild(el("span", "play", "▶"));
  btn.addEventListener("click", () => openModal(work, btn));
  return btn;
}

function render() {
  const grid = document.getElementById("grid");
  if (observer) grid.querySelectorAll("video").forEach((v) => observer.unobserve(v));
  visibleVideos.clear();
  grid.replaceChildren();
  const works = DATA.works.filter((w) => !activeFilter || w.category === activeFilter);
  works.forEach((work) => {
    const card = el("article", "card");
    card.appendChild(buildMedia(work));
    const body = el("div", "card-body");
    if (work.category) body.appendChild(el("span", "tag", work.category));
    body.appendChild(el("h3", "", work.title));
    if (work.description) body.appendChild(el("p", "desc", work.description));
    body.appendChild(metaRow(work));
    card.appendChild(body);
    grid.appendChild(card);
  });
  document.getElementById("empty").hidden = DATA.works.length > 0;
}

function renderFilters() {
  const cats = [...new Set(DATA.works.map((w) => w.category).filter(Boolean))];
  const nav = document.getElementById("filters");
  if (cats.length < 2) { nav.hidden = true; return; }
  ["", ...cats].forEach((cat) => {
    const chip = el("button", "chip", cat || "すべて");
    chip.type = "button";
    chip.setAttribute("aria-pressed", String(cat === activeFilter));
    chip.addEventListener("click", () => {
      activeFilter = cat;
      nav.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      render();
    });
    nav.appendChild(chip);
  });
}

function openModal(work, trigger) {
  lastFocus = trigger;
  const [w, h] = RATIOS[work.aspect] || [16, 9];
  const inner = document.getElementById("modalInner");
  inner.style.setProperty("--ar", w + " / " + h);
  inner.style.setProperty("--r", String(w / h));
  const media = document.getElementById("modalMedia");
  media.replaceChildren();
  if (work.video) {
    const video = document.createElement("video");
    video.controls = true; video.autoplay = true; video.playsInline = true; video.loop = true;
    video.setAttribute("playsinline", "");
    if (work.poster) video.poster = work.poster;
    video.src = work.video;
    media.appendChild(video);
  } else {
    const iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube-nocookie.com/embed/" + work.youtube + "?autoplay=1&rel=0&playsinline=1";
    iframe.title = work.title;
    iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    iframe.allowFullscreen = true;
    media.appendChild(iframe);
  }
  const tag = document.getElementById("modalTag");
  tag.textContent = work.category; tag.hidden = !work.category;
  document.getElementById("modalTitle").textContent = work.title;
  document.getElementById("modalDesc").textContent = work.description;
  document.getElementById("modalMeta").replaceWith(Object.assign(metaRow(work), { id: "modalMeta" }));
  visibleVideos.forEach((v) => v.pause());
  document.body.classList.add("modal-open");
  document.getElementById("modal").hidden = false;
  document.getElementById("modalClose").focus();
}

function closeModal() {
  const modal = document.getElementById("modal");
  if (modal.hidden) return;
  modal.hidden = true;
  document.getElementById("modalMedia").replaceChildren();
  document.body.classList.remove("modal-open");
  visibleVideos.forEach((v) => v.play().catch(() => {}));
  if (lastFocus) lastFocus.focus();
}

document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

(function init() {
  document.getElementById("pageTitle").textContent = DATA.page.title;
  document.getElementById("pageLead").textContent = DATA.page.lead;
  if (DATA.page.contact_url) {
    [document.getElementById("ctaTop"), document.getElementById("ctaBottomLink")].forEach((a) => {
      a.href = DATA.page.contact_url;
      a.textContent = DATA.page.contact_label;
      a.hidden = false;
    });
    document.getElementById("ctaBottom").hidden = false;
  }
  document.getElementById("previewBar").hidden = !DATA.preview;
  renderFilters();
  render();
})();
</script>
</body>
</html>"""


@app.route("/motion")
def motion_index():
    import json

    page_info, works = _load_motion_config()
    preview = request.args.get("preview") == "1"
    if not preview:
        works = [w for w in works if not w["placeholder"]]
    payload = {"page": page_info, "works": works, "preview": preview}
    # "<" を < に置き換えて、YAML 内の文字列で </script> が閉じられないようにする
    data_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    html = MOTION_HTML.replace("__TITLE__", str(escape(page_info["title"]))).replace("__MOTION_JSON__", data_json)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


# ── 枠周り記録 /waku（来てくれた人・行った人の記録 → 歌推しまであと何が必要か） ──
# 記録は各自のブラウザ（localStorage）に保存する。サーバーは歌推しの条件を埋め込んだページを返すだけ。

WAKU_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ | ETERNALd.c.t</title>
<style>
:root {
  --bg: #0d0d1a; --surface: #141428; --surface2: #1a1a2e; --border: #2a2a4e; --line: #1e1e3a;
  --text: #e0e0ff; --muted: #9ca3af; --faint: #6b7280;
  --accent: #7c3aed; --accent-2: #a78bfa; --accent-3: #c4b5fd;
  --ok: #34d399; --ok-bg: rgba(16,185,129,.14); --ng: #f87171; --ng-bg: rgba(239,68,68,.13);
  --came: #38bdf8; --went: #f472b6;
  --warn: #fbbf24; --pa: #f59e0b; --pb: #10b981; --pc: #3b82f6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
[hidden] { display: none !important; }
body {
  background: var(--bg); color: var(--text); min-height: 100vh; line-height: 1.5;
  font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Yu Gothic UI', sans-serif;
  padding: 16px;
}
.page { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 1.25rem; color: var(--accent-3); }
.subtitle { color: var(--muted); font-size: .78rem; margin-top: 2px; }
.tabs { display: flex; gap: 8px; position: sticky; top: 0; z-index: 5; background: var(--bg); padding: 10px 0; margin: 4px 0 6px; }
.tab-btn {
  flex: 1 1 auto; min-height: 44px; padding: 10px 8px; border: 2px solid var(--accent); border-radius: 10px;
  background: transparent; color: var(--accent-2); font-size: .85rem; font-weight: 800; cursor: pointer; white-space: nowrap;
}
.tab-btn.active { background: var(--accent); color: #fff; }
.section { display: none; }
.section.active { display: block; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 14px; }
.notice { padding: 10px 14px; border-radius: 10px; font-size: .8rem; margin-bottom: 12px; }
.notice.error { background: var(--ng-bg); border: 1px solid rgba(248,113,113,.4); color: #fecaca; }
label { display: block; color: var(--muted); font-size: .8rem; font-weight: 700; margin-bottom: 12px; }
input, select {
  display: block; width: 100%; margin-top: 6px; padding: 11px 12px; border: 2px solid var(--border);
  border-radius: 10px; background: var(--surface2); color: var(--text); font-size: 16px; color-scheme: dark;
}
input:focus, select:focus { outline: none; border-color: var(--accent); }
.grid3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0 10px; }
@media (max-width: 560px) { .grid3 { grid-template-columns: 1fr 1fr; } }
.jun-hint { margin: -4px 0 12px; font-size: .8rem; color: var(--accent-2); font-weight: 700; }
.primary {
  width: 100%; padding: 14px; border: none; border-radius: 12px; cursor: pointer;
  background: linear-gradient(135deg, #7c3aed, #a855f7); color: #fff; font-size: 1rem; font-weight: 800;
}
.form-msg { margin-top: 10px; font-size: .85rem; min-height: 1.3em; }
.form-msg.ok { color: var(--ok); }
.form-msg.error { color: var(--ng); }
.entry-layout { display: grid; gap: 14px; }
@media (min-width: 900px) { .entry-layout { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); align-items: start; } }
.side-title { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; font-size: .9rem; font-weight: 800; color: var(--accent-3); margin-bottom: 10px; }
.side-title label { margin: 0; display: flex; align-items: center; gap: 6px; font-size: .75rem; }
.side-title select { width: auto; margin: 0; padding: 4px 8px; font-size: 14px; }
.hint { color: var(--muted); font-size: .82rem; }
.filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0 10px; padding-bottom: 4px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.stat { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 6px 12px; font-size: .78rem; color: var(--muted); }
.stat b { color: var(--text); font-size: 1.05rem; margin: 0 2px; }
.sec-note { color: var(--muted); font-size: .76rem; margin-bottom: 10px; }
.empty { text-align: center; color: var(--faint); padding: 26px 12px; border: 1px dashed var(--border); border-radius: 12px; font-size: .85rem; }
.badge { display: inline-block; font-size: .72rem; font-weight: 800; padding: 2px 9px; border-radius: 999px; white-space: nowrap; }
.badge.ok { background: var(--ok-bg); color: var(--ok); }
.badge.ng { background: var(--ng-bg); color: var(--ng); }
.badge.none { background: var(--line); color: var(--accent-3); }
.badge.warn { background: #2a1f05; color: var(--warn); }
.patterns { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
@media (max-width: 640px) { .patterns { grid-template-columns: 1fr; } }
.pattern { background: var(--surface2); border-radius: 10px; padding: 10px 12px; border-left: 4px solid var(--pa); font-size: .84rem; }
.pattern.p1 { border-left-color: var(--pb); }
.pattern.p2 { border-left-color: var(--pc); }
.pattern-name { font-size: .75rem; font-weight: 800; margin-bottom: 4px; }
.prow { display: flex; justify-content: space-between; gap: 8px; padding: 2px 0; }
.prow span { color: var(--muted); }
.c0 { color: var(--pa); } .c1 { color: var(--pb); } .c2 { color: var(--pc); }
.target-card summary { list-style: none; cursor: pointer; margin-bottom: 0; }
.target-card summary::-webkit-details-marker { display: none; }
.target-card[open] summary { margin-bottom: 10px; }
.partner-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; }
.partner { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 12px; }
.partner-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.partner-name { font-size: 1.05rem; font-weight: 800; }
.counts { display: flex; flex-wrap: wrap; gap: 2px 12px; color: var(--muted); font-size: .76rem; margin: 4px 0 4px; }
.counts b { color: var(--text); }
.dir { background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 10px; margin-top: 8px; }
.dir.done { border-color: rgba(52,211,153,.5); }
.dir-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-weight: 800; font-size: .86rem; }
.dir-head .went { color: var(--went); }
.dir-head .came { color: var(--came); }
.dir-meta { color: var(--muted); font-size: .76rem; margin: 4px 0; }
.dir-meta b { color: var(--text); }
.monthly { font-size: .82rem; margin: 6px 0 4px; }
.monthly b { font-size: 1.05rem; }
.bar { height: 6px; background: var(--line); border-radius: 999px; overflow: hidden; margin-bottom: 4px; }
.bar span { display: block; height: 100%; background: linear-gradient(90deg, #7c3aed, #34d399); }
.need { font-size: .8rem; margin: 6px 0 2px; color: var(--accent-3); }
.need b { color: var(--text); }
.need.ok { color: var(--ok); font-weight: 700; }
.over { color: var(--warn); font-size: .72rem; margin-left: 6px; }
.prog-row { display: flex; justify-content: space-between; gap: 10px; font-size: .8rem; padding: 4px 0; border-top: 1px solid var(--line); }
.prog-row .pl { font-weight: 800; white-space: nowrap; }
.prog-row .pv { text-align: right; }
.prog-row .pv.done { color: var(--ok); font-weight: 800; }
.jun-group { margin-bottom: 18px; }
.jun-title { display: flex; justify-content: space-between; align-items: baseline; font-size: .98rem; color: var(--accent-3); border-bottom: 1px solid var(--border); padding: 6px 2px; margin-bottom: 10px; }
.jun-title small { color: var(--muted); font-weight: 600; }
.date-row { display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 10px; margin-bottom: 8px; }
@media (max-width: 560px) { .date-row { grid-template-columns: 1fr; gap: 4px; } }
.date-label { font-weight: 800; font-size: .9rem; padding-top: 8px; }
.rec { display: flex; align-items: center; gap: 8px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 6px 6px 6px 10px; margin-bottom: 6px; font-size: .85rem; }
.rec .type { font-size: .72rem; font-weight: 800; white-space: nowrap; border-radius: 6px; padding: 1px 6px; }
.type.came { color: var(--came); border: 1px solid rgba(56,189,248,.5); }
.type.went { color: var(--went); border: 1px solid rgba(244,114,182,.5); }
.type.missed { color: var(--ng); border: 1px solid rgba(248,113,113,.5); }
.rec .name { font-weight: 800; }
.rec small { color: var(--muted); font-size: .74rem; flex: 1; }
.del { border: none; background: transparent; color: var(--faint); font-size: 1rem; line-height: 1; width: 30px; height: 30px; border-radius: 50%; cursor: pointer; flex-shrink: 0; margin-left: auto; }
.del:hover { background: var(--ng-bg); color: var(--ng); }
.backup-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.btn { display: inline-flex; align-items: center; gap: 4px; margin: 0; padding: 9px 14px; border-radius: 10px; border: 1px solid var(--border); background: var(--surface2); color: var(--accent-3); font-size: .82rem; font-weight: 700; cursor: pointer; }
.footer { color: var(--faint); font-size: .72rem; text-align: center; margin: 20px 0 8px; }
.footer a { color: var(--accent-2); }
</style>
</head>
<body>
<div class="page">
  <h1>🎤 __TITLE__</h1>
  <p class="subtitle">来てくれた人・行った人の記録から、歌推しまであと何が必要かをチェック</p>

  <nav class="tabs">
    <button type="button" class="tab-btn active" data-tab="entry">✏️ 記録</button>
    <button type="button" class="tab-btn" data-tab="oshi">🎯 歌推し</button>
    <button type="button" class="tab-btn" data-tab="history">📅 履歴</button>
  </nav>

  <div id="storage-error" class="notice error" hidden>⚠️ このブラウザでは記録を保存できません（シークレットモード・プライベートブラウズなど）。通常のモードで開いてください。</div>

  <section id="tab-entry" class="section active">
    <div class="entry-layout">
      <form id="entry-form" class="card" autocomplete="off" novalidate>
        <label>日付<input type="date" id="f-date" required></label>
        <div id="f-jun" class="jun-hint"></div>
        <label>どっち？
          <select id="f-type">
            <option value="came">🎧 来てくれた（自分の枠に）</option>
            <option value="went">🎤 行った（相手の枠に）</option>
            <option value="missed">❌ 行けなかった（相手の枠に）</option>
          </select>
        </label>
        <label>相手の名前
          <input type="text" id="f-name" list="name-list" maxlength="40" placeholder="名前を入力" required>
        </label>
        <div id="amount-fields">
          <div class="grid3">
            <label><span id="l-viewing">視聴時間</span><select id="f-viewing"></select></label>
            <label><span id="l-coins">コイン</span><select id="f-coins"></select></label>
            <label><span id="l-superlike">スーパーいいね</span>
              <select id="f-superlike">
                <option value="0">なし</option>
                <option value="1">💙 あり</option>
              </select>
            </label>
          </div>
          <label id="coins-other-wrap" hidden>コイン（直接入力）
            <input type="number" id="f-coins-other" min="0" step="1" inputmode="numeric" placeholder="例: 1200">
          </label>
        </div>
        <button type="submit" class="primary">記録する</button>
        <p id="form-msg" class="form-msg" role="status"></p>
      </form>
      <div>
        <div id="partner-card" class="card"></div>
        <div id="day-card" class="card"></div>
      </div>
    </div>
  </section>

  <div id="period-bar" class="card filters" hidden>
    <label>月<select id="p-month"></select></label>
    <label id="p-jun-wrap">旬
      <select id="p-jun">
        <option value="">月全体</option>
        <option value="上旬">上旬（1〜10日）</option>
        <option value="中旬">中旬（11〜20日）</option>
        <option value="下旬">下旬（21日〜末日）</option>
      </select>
    </label>
    <label id="p-day-wrap">日にち<select id="p-day"></select></label>
    <label id="o-jun-wrap">今見る旬
      <select id="o-jun">
        <option value="上旬">上旬</option>
        <option value="中旬">中旬</option>
        <option value="下旬">下旬</option>
      </select>
    </label>
  </div>

  <section id="tab-oshi" class="section">
    <div class="card filters">
      <label>目標の月間推しPt<select id="o-target"></select></label>
      <label>どっちの歌推し？
        <select id="o-dir">
          <option value="both">両方</option>
          <option value="went">🎤 自分 → 相手（行った分）</option>
          <option value="came">🎧 相手 → 自分（来てくれた分）</option>
        </select>
      </label>
      <label>絞り込み
        <select id="o-show">
          <option value="">すべて</option>
          <option value="todo">歌推し未達だけ</option>
          <option value="done">歌推し達成だけ</option>
          <option value="notyet">この旬に行けていない相手</option>
          <option value="return">来てくれたのに行けていない相手</option>
        </select>
      </label>
      <label>並び順
        <select id="o-sort">
          <option value="close">あと少しの順</option>
          <option value="count">回数が多い順</option>
          <option value="name">名前順</option>
        </select>
      </label>
      <label>相手<select id="o-partner"></select></label>
    </div>
    <div id="o-target-card"></div>
    <div id="o-stats" class="stats"></div>
    <p id="o-hint" class="sec-note"></p>
    <div id="o-list"></div>
  </section>

  <section id="tab-history" class="section">
    <div class="card filters">
      <label>どっち？
        <select id="h-type">
          <option value="">すべて</option>
          <option value="came">🎧 来てくれた</option>
          <option value="went">🎤 行った</option>
          <option value="missed">❌ 行けなかった</option>
        </select>
      </label>
      <label>相手<select id="h-partner"></select></label>
    </div>
    <div id="h-stats" class="stats"></div>
    <div id="h-list"></div>
  </section>

  <section class="card">
    <div class="side-title">💾 バックアップ</div>
    <p class="sec-note">記録はこのスマホ（ブラウザ）の中だけに保存されます。機種変更・ブラウザのデータ削除・しばらく開かなかったときに消えることがあるので、ときどき「バックアップを保存」してください。別のスマホへ移すときも、保存したファイルを「バックアップから戻す」で読み込めます。</p>
    <div class="backup-actions">
      <button type="button" class="btn" id="b-export">💾 バックアップを保存</button>
      <label class="btn">📂 バックアップから戻す<input type="file" id="b-import" accept="application/json,.json" hidden></label>
      <button type="button" class="btn" id="b-csv">📄 CSVで書き出し</button>
    </div>
    <p id="b-msg" class="form-msg"></p>
  </section>

  <datalist id="name-list"></datalist>
  <p class="footer">
    歌推しの条件は<a href="https://thunderous-rugelach-1c3cc5.netlify.app/coloring_calculator" target="_blank" rel="noopener">歌推し計算ツール</a>と同じ数値です。
    旬ごとの推しPtと月間推しPtは、ここに記録した視聴時間・コイン・スーパーいいねから出した目安です。
  </p>
</div>

<script>
const CONFIG = __WAKU_JSON__;
const STORE_KEY = 'eternal-waku-records-v1';
const SETTINGS_KEY = 'eternal-waku-settings-v1';
const TYPES = {
  came: { icon: '🎧', label: '来てくれた' },
  went: { icon: '🎤', label: '行った' },
  missed: { icon: '❌', label: '行けなかった' },
};
const JUN_RANGE = { '上旬': [1, 10], '中旬': [11, 20], '下旬': [21, 31] };
const JUNS = Object.keys(JUN_RANGE);
const LETTERS = ['A', 'B', 'C'];
const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];
const TIERS = new Map(CONFIG.tiers.map(t => [t.label, t]));
const TIERS_ASC = [...CONFIG.tiers].sort((a, b) => a.pt - b.pt);
const TIERS_DESC = [...TIERS_ASC].reverse();

const $ = id => document.getElementById(id);
const uniq = list => [...new Set(list)];
const byName = (a, b) => a.localeCompare(b, 'ja');
const normName = s => String(s || '').replace(/\s+/g, ' ').trim();

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function fmtMinutes(m) {
  m = Math.round(m);
  if (m <= 0) return '0分';
  const h = Math.floor(m / 60), r = m % 60;
  if (!h) return `${r}分`;
  return r ? `${h}時間${r}分` : `${h}時間`;
}
function fmtCoins(c) {
  if (c >= 10000) return (c / 10000).toLocaleString('ja-JP', { maximumFractionDigits: 2 }) + '万';
  return Number(c).toLocaleString('ja-JP');
}
function fmtPt(pt) {
  if (pt < 100) return `${pt}pt`;
  return (pt / 1000).toLocaleString('ja-JP', { maximumFractionDigits: 2 }) + 'K';
}
function fmtMonth(m) { const [y, mo] = m.split('-'); return `${y}年${Number(mo)}月`; }
function fmtDate(d) {
  const dt = new Date(d + 'T00:00:00');
  return `${dt.getMonth() + 1}/${dt.getDate()}（${WEEKDAYS[dt.getDay()]}）`;
}
function junOf(d) { const day = Number(d.slice(8, 10)); return day <= 10 ? '上旬' : day <= 20 ? '中旬' : '下旬'; }
function daysInMonth(m) { const [y, mo] = m.split('-').map(Number); return new Date(y, mo, 0).getDate(); }
// その月を開いたときに最初に見る旬（今月なら今日の旬、過ぎた月なら下旬）
function defaultJun(month) {
  const t = todayStr();
  if (month === t.slice(0, 7)) return junOf(t);
  return month < t.slice(0, 7) ? '下旬' : '上旬';
}
function junIsOver(month, jun) {
  const t = todayStr(), cur = t.slice(0, 7);
  if (month !== cur) return month < cur;
  return JUNS.indexOf(jun) < JUNS.indexOf(junOf(t));
}

// ── 保存（このブラウザの localStorage） ─────────────────
function validRecord(r) {
  return r && typeof r === 'object' && typeof r.id === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(r.date)
    && TYPES[r.type] && typeof r.name === 'string' && r.name.trim() !== ''
    && Number.isFinite(r.minutes) && Number.isFinite(r.coins);
}
function cleanRecord(r) {
  const amounts = r.type !== 'missed';
  return {
    id: r.id, date: r.date, type: r.type, name: normName(r.name).slice(0, 40),
    minutes: amounts ? Math.max(0, Math.round(r.minutes)) : 0,
    coins: amounts ? Math.max(0, Math.round(r.coins)) : 0,
    sl: amounts && !!r.sl,
    created: r.created || '',
  };
}

let storageOk = true;
function loadRecords() {
  try {
    const data = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
    return Array.isArray(data) ? data.filter(validRecord).map(cleanRecord) : [];
  } catch (e) {
    storageOk = false;
    return [];
  }
}
function saveRecords() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state.records));
    return true;
  } catch (e) {
    storageOk = false;
    $('storage-error').hidden = false;
    return false;
  }
}
function loadSettings() {
  try { return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}') || {}; } catch (e) { return {}; }
}
function saveSettings() {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ target: state.target, dir: state.dir, sort: state.sort }));
  } catch (e) { /* 設定は保存できなくても動く */ }
}

const settings = loadSettings();
const state = {
  records: loadRecords(),
  tab: 'entry',
  month: todayStr().slice(0, 7),
  jun: '',
  day: '',
  activeJun: junOf(todayStr()),
  target: CONFIG.targets.includes(settings.target) ? settings.target : CONFIG.default_target,
  dir: ['both', 'went', 'came'].includes(settings.dir) ? settings.dir : 'both',
  sort: ['close', 'count', 'name'].includes(settings.sort) ? settings.sort : 'close',
  lastName: '',
  targetOpen: false,
};
function currentTarget() { return TIERS.get(state.target) || TIERS.get(CONFIG.default_target) || TIERS_ASC[0]; }
function allNames() { return uniq(state.records.map(r => r.name)).sort(byName); }

// ── 集計（旬ごと → 月間） ─────────────────────────
// 視聴時間・コイン・スーパーいいねは旬ごとにゼロから数え直す。
// 各旬の推しPt = その旬の記録でクリアしたいちばん上の段階。月間推しPt = 3つの旬の合計。
function emptySide() { return { count: 0, minutes: 0, coins: 0, slDates: new Set() }; }
function emptyPartner(name) {
  const jun = {};
  for (const j of JUNS) jun[j] = { went: emptySide(), came: emptySide(), missed: 0 };
  return { name, jun };
}
function aggregateMonth(month) {
  const map = new Map();
  for (const r of state.records) {
    if (!r.date.startsWith(month + '-')) continue;
    if (!map.has(r.name)) map.set(r.name, emptyPartner(r.name));
    const bucket = map.get(r.name).jun[junOf(r.date)];
    if (r.type === 'missed') { bucket.missed++; continue; }
    const side = bucket[r.type];
    side.count++;
    side.minutes += r.minutes;
    side.coins += r.coins;
    if (r.sl) side.slDates.add(r.date);
  }
  return map;
}
function countOf(p, kind, jun) {
  return (jun ? [jun] : JUNS).reduce((n, j) => n + (kind === 'missed' ? p.jun[j].missed : p.jun[j][kind].count), 0);
}

// ある段階のパターンA/B/Cそれぞれ「あと何が足りないか」と、どこまで進んだか（0〜1）
function progress(side, tier) {
  return tier.patterns.map(pt => {
    const needMin = Math.round(pt.viewing_hours * 60);
    const lack = {
      coins: Math.max(0, pt.coins - side.coins),
      minutes: Math.max(0, needMin - side.minutes),
      sl: Math.max(0, pt.super_like_days - side.slDates.size),
    };
    lack.done = !lack.coins && !lack.minutes && !lack.sl;
    const parts = [];
    if (pt.coins) parts.push(Math.min(1, side.coins / pt.coins));
    if (needMin) parts.push(Math.min(1, side.minutes / needMin));
    if (pt.super_like_days) parts.push(Math.min(1, side.slDates.size / pt.super_like_days));
    lack.rate = parts.length ? parts.reduce((a, b) => a + b, 0) / parts.length : 1;
    return lack;
  });
}
function earnedPt(side) {
  if (!side.count) return 0;
  for (const t of TIERS_DESC) if (progress(side, t).some(x => x.done)) return t.pt;
  return 0;
}
// kind: 'went'（自分→相手）/ 'came'（相手→自分）
function oshiStatus(p, kind, jun, target) {
  const earned = {};
  for (const j of JUNS) earned[j] = earnedPt(p.jun[j][kind]);
  const monthly = JUNS.reduce((n, j) => n + earned[j], 0);
  const others = monthly - earned[jun];
  const st = { earned, monthly, done: monthly >= target.pt, rate: 1, need: null, prog: null };
  if (!st.done) {
    // この旬で何Kに届けば、月間が目標に届くか
    st.need = TIERS_ASC.find(t => t.pt >= target.pt - others) || target;
    st.prog = progress(p.jun[jun][kind], st.need);
    const best = Math.max(...st.prog.map(x => x.rate));
    st.rate = Math.min(1, (others + Math.max(earned[jun], best * st.need.pt)) / target.pt);
  }
  return st;
}
function lackText(l) {
  if (l.done) return '✅ クリア';
  return 'あと ' + [
    l.coins ? '🪙' + fmtCoins(l.coins) : '',
    l.minutes ? '👀' + fmtMinutes(l.minutes) : '',
    l.sl ? '💙' + l.sl + '日' : '',
  ].filter(Boolean).join('・');
}

// ── 表示パーツ ────────────────────────────────
function dirBlock(kind, p, ctx) {
  const title = kind === 'went'
    ? `<span class="went">🎤 自分 → ${esc(p.name)}</span>`
    : `<span class="came">🎧 ${esc(p.name)} → 自分</span>`;
  const monthCount = countOf(p, kind);
  if (kind === 'came' && !monthCount) {
    return `<div class="dir"><div class="dir-head">${title}<span class="badge none">今月は来てくれた記録なし</span></div></div>`;
  }
  const st = oshiStatus(p, kind, ctx.jun, ctx.target);
  const side = p.jun[ctx.jun][kind];
  const badge = st.done ? '<span class="badge ok">✅ 歌推し達成</span>'
    : `<span class="badge ${monthCount ? 'none' : 'ng'}">あと ${fmtPt(ctx.target.pt - st.monthly)}</span>`;
  const juns = JUNS.map(j => `${j} ${fmtPt(st.earned[j])}`).join('・');
  let html = `<div class="monthly">月間 <b>${fmtPt(st.monthly)}</b> ／ 目標 ${esc(ctx.target.label)}</div>
    <div class="bar"><span style="width:${Math.round(st.rate * 100)}%"></span></div>
    <div class="dir-meta">${juns}</div>
    <div class="dir-meta">${ctx.jun}: ${kind === 'went' ? '行った' : '来てくれた'} <b>${side.count}回</b> ・ 👀${fmtMinutes(side.minutes)} ・ 🪙${fmtCoins(side.coins)} ・ 💙${side.slDates.size}日</div>`;
  if (st.done) {
    html += `<div class="need ok">月間 ${fmtPt(st.monthly)} で歌推しの条件をクリアしています</div>`;
  } else {
    const over = junIsOver(ctx.month, ctx.jun) ? '<span class="over">※この旬は終わっています</span>' : '';
    html += `<div class="need">${ctx.jun}で <b>${esc(st.need.label)}</b> に届けば歌推し（月間 ${esc(ctx.target.label)}）${over}</div>`
      + st.prog.map((x, i) => `<div class="prog-row"><span class="pl c${i}">${LETTERS[i]} ${esc(CONFIG.pattern_names[i])}</span><span class="pv${x.done ? ' done' : ''}">${lackText(x)}</span></div>`).join('');
  }
  return `<div class="dir${st.done ? ' done' : ''}"><div class="dir-head">${title}${badge}</div>${html}</div>`;
}

function partnerCard(p, ctx, dir) {
  const flags = [];
  if (countOf(p, 'came', ctx.jun) && !countOf(p, 'went', ctx.jun)) flags.push('<span class="badge warn">お返しまだ</span>');
  const byJun = kind => JUNS.map(j => j[0] + countOf(p, kind, j)).join('・');
  const missed = countOf(p, 'missed');
  return `<article class="partner">
    <div class="partner-head"><span class="partner-name">${esc(p.name)}</span>${flags.join('')}</div>
    <div class="counts">
      <span>今月 🎤行った <b>${countOf(p, 'went')}</b>回（${byJun('went')}）</span>
      <span>🎧来てくれた <b>${countOf(p, 'came')}</b>回（${byJun('came')}）</span>
      ${missed ? `<span>❌行けなかった <b>${missed}</b>回</span>` : ''}
    </div>
    ${dir !== 'came' ? dirBlock('went', p, ctx) : ''}
    ${dir !== 'went' ? dirBlock('came', p, ctx) : ''}
  </article>`;
}

function targetCard(tier) {
  return `<details class="card target-card"${state.targetOpen ? ' open' : ''}>
    <summary class="side-title">🎯 歌推しの決まり（目標 月間${esc(tier.label)}）— タップで開く</summary>
    <p class="sec-note">視聴時間・コイン・スーパーいいねは上旬・中旬・下旬ごとにゼロに戻ります。各旬の推しPtは、その旬でクリアしたいちばん上の段階です。月間推しPt（上旬＋中旬＋下旬）が ${esc(tier.label)} 以上で歌推し。月が変わると月間もリセットされます。</p>
    <p class="sec-note">1つの旬で ${esc(tier.label)} を取る場合の条件（どれか1つのパターンをすべて満たせばOK）:</p>
    <div class="patterns">${tier.patterns.map((p, i) => `
      <div class="pattern p${i}">
        <div class="pattern-name c${i}">パターン${LETTERS[i]} — ${esc(CONFIG.pattern_names[i])}</div>
        <div class="prow"><span>🪙 コイン</span><b>${fmtCoins(p.coins)}</b></div>
        <div class="prow"><span>👀 視聴時間</span><b>${p.viewing_hours ? fmtMinutes(p.viewing_hours * 60) : '不要'}</b></div>
        <div class="prow"><span>💙 スーパーいいね</span><b>${p.super_like_days ? p.super_like_days + '日分' : '不要'}</b></div>
      </div>`).join('')}
    </div>
  </details>`;
}

function recRow(r) {
  const t = TYPES[r.type];
  const detail = r.type === 'missed' ? '' : [
    r.minutes ? '👀' + fmtMinutes(r.minutes) : '',
    r.coins ? '🪙' + fmtCoins(r.coins) : '',
    r.sl ? '💙' : '',
  ].filter(Boolean).join(' ');
  return `<div class="rec"><span class="type ${r.type}">${t.icon} ${t.label}</span><span class="name">${esc(r.name)}</span>`
    + `<small>${detail}</small><button type="button" class="del" data-id="${esc(r.id)}" title="この記録を削除" aria-label="削除">×</button></div>`;
}

function fillSelect(sel, values, allLabel) {
  const cur = sel.value;
  const list = uniq([...values, ...(cur ? [cur] : [])]).sort(byName);
  sel.innerHTML = `<option value="">${allLabel}</option>` + list.map(n => `<option value="${esc(n)}">${esc(n)}</option>`).join('');
  sel.value = cur;
}
function fillTargetSelect(sel) {
  sel.innerHTML = CONFIG.targets.map(l => `<option value="${esc(l)}">月間 ${esc(l)}</option>`).join('');
  sel.value = currentTarget().label;
}

// ── 記録タブ ──────────────────────────────────
function syncEntryFields() {
  const type = $('f-type').value;
  $('amount-fields').hidden = type === 'missed';
  $('coins-other-wrap').hidden = $('f-coins').value !== 'other';
  const who = type === 'came' ? '相手の' : '自分の';
  $('l-viewing').textContent = who + '視聴時間';
  $('l-coins').textContent = type === 'came' ? '相手がくれたコイン' : '自分が使ったコイン';
  $('l-superlike').textContent = who + 'スーパーいいね';
}

function renderEntry() {
  syncEntryFields();
  const date = $('f-date').value || todayStr();
  $('f-jun').textContent = `${fmtDate(date)} ・ ${fmtMonth(date.slice(0, 7))}の${junOf(date)}`;
  const name = normName($('f-name').value) || state.lastName;
  const month = date.slice(0, 7);
  if (name) {
    const p = aggregateMonth(month).get(name) || emptyPartner(name);
    const ctx = { target: currentTarget(), jun: junOf(date), month };
    $('partner-card').innerHTML = `<div class="side-title"><span>📈 ${fmtMonth(month)}の ${esc(name)}</span>`
      + `<label>目標<select id="e-target"></select></label></div>` + partnerCard(p, ctx, 'both');
    fillTargetSelect($('e-target'));
  } else {
    $('partner-card').innerHTML = '<div class="hint">相手の名前を入れると、その月に何回来てくれたか・行ったか、月間推しPt、歌推しまでにこの旬であと何が必要かがここに出ます。</div>';
  }
  const dayRecs = state.records.filter(r => r.date === date);
  $('day-card').innerHTML = `<div class="side-title">🗓 ${fmtDate(date)}の記録</div>`
    + (dayRecs.length ? dayRecs.map(recRow).join('') : '<div class="hint">まだ記録はありません</div>');
}

function submitEntry(e) {
  e.preventDefault();
  const msg = $('form-msg');
  const date = $('f-date').value, type = $('f-type').value, name = normName($('f-name').value);
  let coins = $('f-coins').value;
  if (coins === 'other') coins = $('f-coins-other').value.trim() || '0';
  coins = Number(coins);
  const fail = text => { msg.className = 'form-msg error'; msg.textContent = '⚠️ ' + text; };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return fail('日付を選んでください');
  if (!name) return fail('相手の名前を入れてください');
  if (name.length > 40) return fail('名前は40文字以内で入れてください');
  if (!Number.isInteger(coins) || coins < 0 || coins > 100000000) return fail('コインは0以上の整数で入れてください');
  if (!storageOk) return fail('このブラウザでは保存できません（シークレットモードなど）');

  const record = cleanRecord({
    id: (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2)),
    date, type, name, coins,
    minutes: Number($('f-viewing').value),
    sl: $('f-superlike').value === '1',
    created: new Date().toISOString(),
  });
  state.records.push(record);
  if (!saveRecords()) {
    state.records.pop();
    return fail('保存できませんでした（空き容量・シークレットモードを確認してください）');
  }
  state.lastName = record.name;
  renderNameList();
  msg.className = 'form-msg ok';
  msg.textContent = `✅ 記録しました：${TYPES[type].icon} ${record.name}（${fmtDate(date)}・${TYPES[type].label}）`;
  $('f-name').value = '';
  $('f-viewing').value = '0';
  $('f-coins').value = '0';
  $('f-coins-other').value = '';
  $('f-superlike').value = '0';
  renderEntry();
}

// ── 歌推しタブ ────────────────────────────────
function renderOshi() {
  const target = currentTarget();
  const jun = state.activeJun;
  const ctx = { target, jun, month: state.month };
  const show = $('o-show').value;
  fillTargetSelect($('o-target'));
  $('o-dir').value = state.dir;
  $('o-sort').value = state.sort;
  $('o-target-card').innerHTML = targetCard(target);

  const agg = aggregateMonth(state.month);
  fillSelect($('o-partner'), show === 'notyet' ? allNames() : [...agg.keys()], 'すべての相手');
  const partnerFilter = $('o-partner').value;
  // 「この旬に行けていない相手」は、これまでに記録したことがある全員が対象
  let partners = show === 'notyet'
    ? allNames().map(n => agg.get(n) || emptyPartner(n)).filter(p => !countOf(p, 'went', jun))
    : [...agg.values()];
  if (partnerFilter) partners = partners.filter(p => p.name === partnerFilter);

  const kinds = p => state.dir === 'went' ? ['went'] : state.dir === 'came' ? ['came']
    : ['went', ...(countOf(p, 'came') ? ['came'] : [])];
  for (const p of partners) {
    const sts = kinds(p).map(k => oshiStatus(p, k, jun, target));
    const open = sts.filter(s => !s.done);
    p.anyDone = sts.some(s => s.done);
    p.anyTodo = open.length > 0;
    p.closeness = open.length ? Math.max(...open.map(s => s.rate)) : 2;
  }
  if (show === 'todo') partners = partners.filter(p => p.anyTodo);
  if (show === 'done') partners = partners.filter(p => p.anyDone);
  if (show === 'return') partners = partners.filter(p => countOf(p, 'came', jun) && !countOf(p, 'went', jun));

  const total = p => countOf(p, 'went') + countOf(p, 'came') + countOf(p, 'missed');
  partners.sort(state.sort === 'name' ? (a, b) => byName(a.name, b.name)
    : state.sort === 'count' ? (a, b) => total(b) - total(a) || byName(a.name, b.name)
    : (a, b) => (a.closeness > 1) - (b.closeness > 1) || b.closeness - a.closeness || byName(a.name, b.name));

  const all = [...agg.values()];
  const sum = kind => all.reduce((n, p) => n + countOf(p, kind), 0);
  const achieved = kind => all.filter(p => countOf(p, kind) && oshiStatus(p, kind, jun, target).done).length;
  $('o-stats').innerHTML = `<span class="stat">${esc(fmtMonth(state.month))}・今見る旬は${jun}</span>`
    + `<span class="stat">🎤 行った<b>${sum('went')}</b>回</span>`
    + `<span class="stat">🎧 来てくれた<b>${sum('came')}</b>回</span>`
    + `<span class="stat">❌<b>${sum('missed')}</b>回</span>`
    + `<span class="stat">自分→相手 歌推し達成<b>${achieved('went')}</b>人</span>`
    + `<span class="stat">相手→自分 歌推し達成<b>${achieved('came')}</b>人</span>`;

  $('o-hint').textContent = {
    todo: '月間推しPtがまだ目標に届いていない相手です。',
    done: '月間推しPtが目標以上になっている相手です。',
    notyet: `これまでに記録したことがある相手のうち、${jun}にまだ一度も「行った」がない人です。`,
    return: `${jun}に来てくれたのに、まだ自分が行けていない相手です。`,
  }[show] || '';

  if (!partners.length) {
    $('o-list').innerHTML = `<div class="empty">${state.records.length ? '条件に合う相手はいません' : 'まだ記録がありません。「✏️ 記録」タブから追加できます。'}</div>`;
    return;
  }
  $('o-list').innerHTML = `<div class="partner-grid">${partners.map(p => partnerCard(p, ctx, state.dir)).join('')}</div>`;
}

// ── 履歴タブ ──────────────────────────────────
function periodRecords() {
  return state.records.filter(r => r.date.startsWith(state.month + '-')
    && (!state.jun || junOf(r.date) === state.jun)
    && (!state.day || Number(r.date.slice(8, 10)) === Number(state.day)));
}
function periodLabel() {
  let s = fmtMonth(state.month);
  if (state.jun) s += ' ' + state.jun;
  if (state.day) s += ` ${state.day}日`;
  return s;
}
function renderHistory() {
  const recs = periodRecords();
  fillSelect($('h-partner'), uniq(recs.map(r => r.name)), 'すべての相手');
  const type = $('h-type').value, partner = $('h-partner').value;
  const list = recs.filter(r => (!type || r.type === type) && (!partner || r.name === partner))
    .sort((a, b) => a.date.localeCompare(b.date) || String(a.created).localeCompare(String(b.created)));
  const count = t => list.filter(r => r.type === t).length;
  $('h-stats').innerHTML = `<span class="stat">${esc(periodLabel())}</span>`
    + `<span class="stat">🎧 来てくれた<b>${count('came')}</b>回</span>`
    + `<span class="stat">🎤 行った<b>${count('went')}</b>回</span>`
    + `<span class="stat">❌ 行けなかった<b>${count('missed')}</b>回</span>`;
  if (!list.length) {
    $('h-list').innerHTML = `<div class="empty">${esc(periodLabel())} の記録はありません</div>`;
    return;
  }
  let html = '';
  for (const jun of JUNS) {
    const js = list.filter(r => junOf(r.date) === jun);
    if (!js.length) continue;
    const [lo, hi] = JUN_RANGE[jun];
    html += `<section class="jun-group"><h3 class="jun-title"><span>${fmtMonth(state.month)} ${jun}（${lo}〜${Math.min(hi, daysInMonth(state.month))}日）</span><small>${js.length}件</small></h3>`;
    for (const d of uniq(js.map(r => r.date))) {
      html += `<div class="date-row"><div class="date-label">${fmtDate(d)}</div><div>${js.filter(r => r.date === d).map(recRow).join('')}</div></div>`;
    }
    html += '</section>';
  }
  $('h-list').innerHTML = html;
}

// ── 期間・タブ ────────────────────────────────
function renderPeriodBar() {
  const months = uniq([...state.records.map(r => r.date.slice(0, 7)), todayStr().slice(0, 7), state.month]).sort().reverse();
  $('p-month').innerHTML = months.map(m => `<option value="${esc(m)}">${esc(fmtMonth(m))}</option>`).join('');
  $('p-month').value = state.month;
  $('p-jun').value = state.jun;
  $('o-jun').value = state.activeJun;
  const [lo, hi] = state.jun ? JUN_RANGE[state.jun] : [1, 31];
  let opts = '<option value="">すべての日</option>';
  for (let d = lo; d <= Math.min(hi, daysInMonth(state.month)); d++) opts += `<option value="${d}">${d}日</option>`;
  $('p-day').innerHTML = opts;
  $('p-day').value = state.day;
  // 歌推しは「月＋今見る旬」、履歴は「月＋旬＋日にち」で絞る
  $('p-jun-wrap').hidden = $('p-day-wrap').hidden = state.tab !== 'history';
  $('o-jun-wrap').hidden = state.tab !== 'oshi';
}

function renderNameList() {
  $('name-list').innerHTML = allNames().map(n => `<option value="${esc(n)}"></option>`).join('');
}

function render() {
  if (state.tab === 'entry') return renderEntry();
  renderPeriodBar();
  if (state.tab === 'oshi') renderOshi();
  else renderHistory();
}

function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.section[id^="tab-"]').forEach(s => s.classList.toggle('active', s.id === 'tab-' + tab));
  $('period-bar').hidden = tab === 'entry';
  render();
}

// ── バックアップ ───────────────────────────────
function download(filename, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function backupMsg(text, ok) {
  $('b-msg').className = 'form-msg ' + (ok ? 'ok' : 'error');
  $('b-msg').textContent = text;
}
$('b-export').addEventListener('click', () => {
  const body = JSON.stringify({ app: 'eternal-waku', version: 1, exported_at: new Date().toISOString(), records: state.records }, null, 2);
  download(`waku-backup-${todayStr()}.json`, body, 'application/json');
  backupMsg(`✅ ${state.records.length}件をバックアップしました（ダウンロードしたファイルを保管してください）`, true);
});
$('b-csv').addEventListener('click', () => {
  const q = v => `"${String(v).replace(/"/g, '""')}"`;
  const rows = [['日付', '旬', '種類', '相手', '視聴時間（分）', 'コイン', 'スーパーいいね']]
    .concat([...state.records].sort((a, b) => a.date.localeCompare(b.date))
      .map(r => [r.date, junOf(r.date), TYPES[r.type].label, r.name, r.minutes, r.coins, r.sl ? 'あり' : '']));
  download(`waku-${todayStr()}.csv`, '﻿' + rows.map(r => r.map(q).join(',')).join('\r\n'), 'text/csv');
  backupMsg(`✅ ${state.records.length}件をCSVで書き出しました`, true);
});
$('b-import').addEventListener('change', async e => {
  const file = e.target.files[0];
  e.target.value = '';
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    const incoming = (Array.isArray(data) ? data : data.records || []).filter(validRecord).map(cleanRecord);
    const have = new Set(state.records.map(r => r.id));
    const added = incoming.filter(r => !have.has(r.id));
    if (!incoming.length) return backupMsg('⚠️ このファイルには読み込める記録がありません', false);
    state.records.push(...added);
    if (!saveRecords()) {
      state.records.splice(state.records.length - added.length, added.length);
      return backupMsg('⚠️ 保存できませんでした', false);
    }
    renderNameList();
    render();
    backupMsg(`✅ ${added.length}件を戻しました（すでにあった${incoming.length - added.length}件はそのまま）`, true);
  } catch (err) {
    backupMsg('⚠️ バックアップファイルを読み込めませんでした', false);
  }
});

// ── 初期化 ───────────────────────────────────
$('f-date').value = todayStr();
$('f-viewing').innerHTML = '<option value="0">なし</option>'
  + CONFIG.viewing_minutes.map(m => `<option value="${m}">${fmtMinutes(m)}</option>`).join('');
$('f-coins').innerHTML = '<option value="0">なし</option>'
  + CONFIG.coin_presets.map(c => `<option value="${c}">${Number(c).toLocaleString('ja-JP')}</option>`).join('')
  + '<option value="other">その他（直接入力）</option>';

document.querySelectorAll('.tab-btn').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));
$('entry-form').addEventListener('submit', submitEntry);
['f-date', 'f-type', 'f-coins'].forEach(id => $(id).addEventListener('change', renderEntry));
$('f-name').addEventListener('input', renderEntry);
$('p-month').addEventListener('change', e => {
  state.month = e.target.value;
  state.day = '';
  state.activeJun = defaultJun(state.month);
  render();
});
$('p-jun').addEventListener('change', e => { state.jun = e.target.value; state.day = ''; render(); });
$('p-day').addEventListener('change', e => { state.day = e.target.value; render(); });
$('o-jun').addEventListener('change', e => { state.activeJun = e.target.value; render(); });
$('o-dir').addEventListener('change', e => { state.dir = e.target.value; saveSettings(); renderOshi(); });
$('o-sort').addEventListener('change', e => { state.sort = e.target.value; saveSettings(); renderOshi(); });
['o-show', 'o-partner'].forEach(id => $(id).addEventListener('change', renderOshi));
['h-type', 'h-partner'].forEach(id => $(id).addEventListener('change', renderHistory));
document.addEventListener('change', e => {
  if (e.target.id === 'o-target' || e.target.id === 'e-target') {
    state.target = e.target.value;
    saveSettings();
    render();
  }
});
document.addEventListener('toggle', e => {
  if (e.target.classList && e.target.classList.contains('target-card')) state.targetOpen = e.target.open;
}, true);
document.addEventListener('click', e => {
  const del = e.target.closest('.del');
  if (!del) return;
  const r = state.records.find(x => x.id === del.dataset.id);
  if (!r || !confirm(`${fmtDate(r.date)} ${TYPES[r.type].label}：${r.name}\nこの記録を削除します。よろしいですか？`)) return;
  const before = state.records;
  state.records = state.records.filter(x => x.id !== r.id);
  if (!saveRecords()) {
    state.records = before;
    alert('削除を保存できませんでした');
    return;
  }
  renderNameList();
  render();
});

// ブラウザに「この記録は消さないで」と頼む（対応ブラウザのみ）
if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
try { localStorage.setItem(STORE_KEY + '-check', '1'); localStorage.removeItem(STORE_KEY + '-check'); } catch (e) { storageOk = false; }
$('storage-error').hidden = storageOk;
renderNameList();
render();
</script>
</body>
</html>"""


@app.route("/waku")
def waku_index():
    import json

    import waku_tracker

    config = waku_tracker.load_config()
    # "<" を < に置き換えて、YAML 内の文字列で </script> が閉じられないようにする
    data_json = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")
    html = WAKU_HTML.replace("__TITLE__", str(escape(config["title"]))).replace("__WAKU_JSON__", data_json)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
