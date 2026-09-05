-- v17: Reminders table

CREATE TABLE IF NOT EXISTS reminders (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    due_at          REAL NOT NULL,
    repeat_interval TEXT NOT NULL DEFAULT 'none',
    status          TEXT NOT NULL DEFAULT 'active',
    channel         TEXT NOT NULL DEFAULT 'telegram',
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    last_triggered_at REAL,
    trigger_count   INTEGER NOT NULL DEFAULT 0,
    snooze_until    REAL
);

CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders (user_id);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders (due_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders (status);
