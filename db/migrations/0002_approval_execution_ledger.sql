-- Migration 0002: Approval execution ledger

CREATE TABLE IF NOT EXISTS approval_execution_ledger (
    approval_id     UUID PRIMARY KEY REFERENCES approvals(id) ON DELETE CASCADE,
    decided_status  TEXT NOT NULL,
    actor           TEXT NOT NULL DEFAULT '',
    decided_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    edited_payload  JSONB,
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ael_actor ON approval_execution_ledger (actor);
CREATE INDEX IF NOT EXISTS idx_ael_decided ON approval_execution_ledger (decided_at DESC);
CREATE INDEX IF NOT EXISTS idx_ael_status ON approval_execution_ledger (decided_status);
