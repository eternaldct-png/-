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
