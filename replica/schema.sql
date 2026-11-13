-- 会議ノート（自分専用）の SQLite スキーマ。
-- tools/meeting_notes/store.py が起動時にこのまま流す（IF NOT EXISTS で何度流しても同じ）。
-- 時刻はすべて UTC の ISO8601 文字列（例 2026-11-11T09:30:00+00:00）。表示時にブラウザのタイムゾーンへ変換する。
-- 自分専用・ログインなしのため owner 列は持たない（アクセス制御は「127.0.0.1 でしか待ち受けない」で担保）。

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meetings (
  id            TEXT PRIMARY KEY,               -- uuid4 hex
  title         TEXT NOT NULL DEFAULT '',
  started_at    TEXT NOT NULL,                  -- 会議の開始日時（UTC）
  duration_sec  REAL,                           -- 録音の長さ（分かれば）
  participants  TEXT NOT NULL DEFAULT '[]',     -- JSON 配列
  tags          TEXT NOT NULL DEFAULT '[]',     -- JSON 配列
  source        TEXT NOT NULL CHECK (source IN ('record','upload','transcript')),
  status        TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','transcribing','summarizing','done','failed')),
  error         TEXT NOT NULL DEFAULT '',
  audio_path    TEXT NOT NULL DEFAULT '',       -- data/audio/ からの相対パス。無ければ ''
  language      TEXT NOT NULL DEFAULT 'ja',
  -- 文字起こし: [{speaker, start, end, text}]（秒）
  transcript    TEXT NOT NULL DEFAULT '[]',
  -- ノート: {summary, sections:[{heading, bullets[]}], decisions[]}
  notes         TEXT NOT NULL DEFAULT '{}',
  notes_model   TEXT NOT NULL DEFAULT '',
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS meetings_started_at ON meetings (started_at DESC);
CREATE INDEX IF NOT EXISTS meetings_status ON meetings (status);

CREATE TABLE IF NOT EXISTS action_items (
  id          TEXT PRIMARY KEY,
  meeting_id  TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  owner       TEXT NOT NULL DEFAULT '',          -- 空 = 担当未定
  due         TEXT NOT NULL DEFAULT '',          -- 自由記述（「来週金曜」など）。AIが日付を確定できないことが多いため
  done        INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0,1)),
  done_at     TEXT NOT NULL DEFAULT '',
  position    INTEGER NOT NULL DEFAULT 0,
  manual      INTEGER NOT NULL DEFAULT 0 CHECK (manual IN (0,1)),  -- 手で足した行は再生成で消さない
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS action_items_meeting ON action_items (meeting_id, position);
CREATE INDEX IF NOT EXISTS action_items_open ON action_items (done, owner);

CREATE TABLE IF NOT EXISTS chat_messages (
  id          TEXT PRIMARY KEY,
  meeting_id  TEXT REFERENCES meetings(id) ON DELETE CASCADE,  -- NULL = 全会議への横断質問
  role        TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content     TEXT NOT NULL,
  created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS chat_messages_meeting ON chat_messages (meeting_id, created_at);

CREATE TABLE IF NOT EXISTS settings (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL
);

-- ── 口コミの不満への対応で足したもの（replica/fixes.md） ──

-- AI の使用量と費用（不満: 高い・いくらかかるか分からない）
CREATE TABLE IF NOT EXISTS ai_usage (
  id             TEXT PRIMARY KEY,
  meeting_id     TEXT,                -- 会議を消しても費用の記録は残す（外部キーにしない）
  kind           TEXT NOT NULL,       -- notes | ask | ask_all | speakers
  model          TEXT NOT NULL,
  input_tokens   INTEGER NOT NULL DEFAULT 0,
  output_tokens  INTEGER NOT NULL DEFAULT 0,
  cost_usd       REAL NOT NULL DEFAULT 0,
  created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ai_usage_created ON ai_usage (created_at);
CREATE INDEX IF NOT EXISTS ai_usage_meeting ON ai_usage (meeting_id);

-- 操作の記録（不満: 記録の透明性・監査ログが無い）
CREATE TABLE IF NOT EXISTS activity (
  id          TEXT PRIMARY KEY,
  at          TEXT NOT NULL,
  action      TEXT NOT NULL,
  meeting_id  TEXT,
  detail      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS activity_at ON activity (at DESC);

-- 録音中の途中保存（不満: 録音が消えた・取れていなかった）
CREATE TABLE IF NOT EXISTS recordings (
  id          TEXT PRIMARY KEY,
  path        TEXT NOT NULL,           -- audio/ からの相対パス
  ext         TEXT NOT NULL,
  bytes       INTEGER NOT NULL DEFAULT 0,
  chunks      INTEGER NOT NULL DEFAULT 0,
  meta        TEXT NOT NULL DEFAULT '{}',
  status      TEXT NOT NULL DEFAULT 'recording' CHECK (status IN ('recording','finished','discarded')),
  started_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
