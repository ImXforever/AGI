-- v20: QA checks + automation rules tables

CREATE TABLE IF NOT EXISTS qa_checks (
    id              SERIAL PRIMARY KEY,
    response_text   TEXT NOT NULL,
    score_total     REAL NOT NULL,
    passed          BOOLEAN NOT NULL DEFAULT FALSE,
    rewritten       BOOLEAN NOT NULL DEFAULT FALSE,
    rewritten_text  TEXT DEFAULT '',
    checked_at      REAL NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE INDEX IF NOT EXISTS idx_qa_checks_passed ON qa_checks (passed);
CREATE INDEX IF NOT EXISTS idx_qa_checks_checked_at ON qa_checks (checked_at);

CREATE TABLE IF NOT EXISTS automation_rules (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    trigger_type    TEXT NOT NULL,
    conditions      JSONB NOT NULL DEFAULT '{}',
    actions         JSONB NOT NULL DEFAULT '[]',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INTEGER NOT NULL DEFAULT 0,
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    last_triggered  REAL,
    trigger_count   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_automation_rules_trigger ON automation_rules (trigger_type);
CREATE INDEX IF NOT EXISTS idx_automation_rules_enabled ON automation_rules (enabled) WHERE enabled = TRUE;
