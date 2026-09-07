-- v16: Email follow-ups, scheduled reports, email logs

CREATE TABLE IF NOT EXISTS email_followups (
    id              TEXT PRIMARY KEY,
    email_id        TEXT NOT NULL,
    sender          TEXT NOT NULL,
    recipient       TEXT NOT NULL,
    subject         TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'standard',
    rule_name       TEXT NOT NULL DEFAULT 'standard',
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    last_followup_at REAL,
    followup_count  INTEGER NOT NULL DEFAULT 0,
    next_followup_at REAL NOT NULL,
    escalation_at   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_email_followups_status ON email_followups (status);
CREATE INDEX IF NOT EXISTS idx_email_followups_next ON email_followups (next_followup_at) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS email_logs (
    id              SERIAL PRIMARY KEY,
    message_id      TEXT,
    sender          TEXT NOT NULL,
    recipient       TEXT NOT NULL,
    subject         TEXT NOT NULL,
    category        TEXT,
    direction       TEXT NOT NULL DEFAULT 'inbound',
    status          TEXT NOT NULL DEFAULT 'received',
    auto_replied    BOOLEAN DEFAULT FALSE,
    followup_id     TEXT,
    response_time_ms REAL,
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE INDEX IF NOT EXISTS idx_email_logs_created ON email_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs (status);

CREATE TABLE IF NOT EXISTS scheduled_reports (
    id              SERIAL PRIMARY KEY,
    report_type     TEXT NOT NULL,
    schedule        TEXT NOT NULL,
    last_run_at     REAL,
    next_run_at     REAL,
    enabled         BOOLEAN DEFAULT TRUE,
    config          JSONB DEFAULT '{}',
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE TABLE IF NOT EXISTS website_events (
    id              SERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,
    change_type     TEXT,
    processed       BOOLEAN DEFAULT FALSE,
    approved        BOOLEAN DEFAULT FALSE,
    details         JSONB DEFAULT '{}',
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE INDEX IF NOT EXISTS idx_website_events_type ON website_events (event_type);
CREATE INDEX IF NOT EXISTS idx_website_events_created ON website_events (created_at);
