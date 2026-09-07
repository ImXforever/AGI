-- v19: CMS pages + team tasks tables

CREATE TABLE IF NOT EXISTS cms_pages (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    content         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft',
    created_by      TEXT NOT NULL,
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    updated_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    published_at    REAL,
    meta_description TEXT DEFAULT '',
    meta_keywords   TEXT DEFAULT '',
    versions        JSONB DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_cms_pages_status ON cms_pages (status);
CREATE INDEX IF NOT EXISTS idx_cms_pages_slug ON cms_pages (slug);

CREATE TABLE IF NOT EXISTS team_tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    assignee        TEXT NOT NULL,
    department      TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'normal',
    status          TEXT NOT NULL DEFAULT 'pending',
    created_by      TEXT NOT NULL,
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    due_at          REAL NOT NULL,
    completed_at    REAL,
    cross_links     JSONB DEFAULT '[]',
    notes           JSONB DEFAULT '[]',
    escalated_at    REAL
);

CREATE INDEX IF NOT EXISTS idx_team_tasks_assignee ON team_tasks (assignee);
CREATE INDEX IF NOT EXISTS idx_team_tasks_department ON team_tasks (department);
CREATE INDEX IF NOT EXISTS idx_team_tasks_status ON team_tasks (status);
CREATE INDEX IF NOT EXISTS idx_team_tasks_due ON team_tasks (due_at) WHERE status != 'completed';
