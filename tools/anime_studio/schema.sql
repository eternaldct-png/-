-- ツヅリ（自分用のアニメ制作ツール）のデータベース。設計の記録は replica/anime/architecture.md
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL DEFAULT 'story' CHECK (kind IN ('story','mv','quick')),
  idea TEXT NOT NULL DEFAULT '',
  style TEXT NOT NULL DEFAULT 'anime',
  aspect TEXT NOT NULL DEFAULT '9:16' CHECK (aspect IN ('16:9','9:16','1:1')),
  duration_sec INTEGER NOT NULL DEFAULT 30,
  language TEXT NOT NULL DEFAULT 'ja',
  mood TEXT NOT NULL DEFAULT '',
  auto INTEGER NOT NULL DEFAULT 0,          -- 1 = おまかせ（全段階を自動で承認して進む）
  script TEXT NOT NULL DEFAULT '{}',        -- 脚本 JSON {logline, scenes:[{no, place, summary, lines:[{speaker,text}]}]}
  stages TEXT NOT NULL DEFAULT '{}',        -- 段階ごとの状態 JSON
  bgm_path TEXT NOT NULL DEFAULT '',
  bgm_volume REAL NOT NULL DEFAULT 0.35,
  render_path TEXT NOT NULL DEFAULT '',
  render_warnings TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS projects_updated ON projects (updated_at DESC);

CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,   -- NULL = 素材ライブラリ
  name TEXT NOT NULL,
  look TEXT NOT NULL DEFAULT '',          -- 外見（画像生成のプロンプトにも使う）
  personality TEXT NOT NULL DEFAULT '',
  voice TEXT NOT NULL DEFAULT '',         -- say の声の名前（空 = 設定の既定）
  color TEXT NOT NULL DEFAULT '',         -- 仮の絵で使う色
  image_path TEXT NOT NULL DEFAULT '',
  library_id TEXT NOT NULL DEFAULT '',    -- ライブラリから持ってきたときの元 id
  sort INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS characters_project ON characters (project_id, sort);

CREATE TABLE IF NOT EXISTS scenes (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  color TEXT NOT NULL DEFAULT '',
  image_path TEXT NOT NULL DEFAULT '',
  sort INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS scenes_project ON scenes (project_id, sort);

CREATE TABLE IF NOT EXISTS shots (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  sort INTEGER NOT NULL DEFAULT 0,
  seconds REAL NOT NULL DEFAULT 4 CHECK (seconds > 0 AND seconds <= 30),
  scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
  characters TEXT NOT NULL DEFAULT '[]',  -- 登場キャラの名前の配列
  camera TEXT NOT NULL DEFAULT 'still' CHECK (camera IN ('still','zoom_in','zoom_out','pan_left','pan_right')),
  action TEXT NOT NULL DEFAULT '',        -- 何が起きるか（日本語）
  speaker TEXT NOT NULL DEFAULT '',
  dialogue TEXT NOT NULL DEFAULT '',
  caption TEXT NOT NULL DEFAULT '',       -- 画面の文字（任意）
  image_prompt TEXT NOT NULL DEFAULT '',  -- 画像生成用（英語）
  image_path TEXT NOT NULL DEFAULT '',
  image_source TEXT NOT NULL DEFAULT '',  -- placeholder | upload | fal
  video_path TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS shots_project ON shots (project_id, sort);

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  role TEXT NOT NULL,                     -- director | writer | character | scene | storyboard | animator | sound | editor | me | system
  text TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS logs_project ON logs (project_id, id);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,                     -- script | characters | scenes | storyboard | art | voice | render
  instruction TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),
  error TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_project ON jobs (project_id, created_at);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- fal.ai を使ったときの見積もり額（円）。月の上限の計算に使う
CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  yen REAL NOT NULL,
  what TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS spend_created ON spend (created_at);
