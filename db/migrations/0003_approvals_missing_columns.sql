-- 0003: add columns the application code writes/reads on `approvals`
-- (queue.py, repository.py, sweeper.py referenced them but 0001 never created them).

ALTER TABLE approvals ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS skill       TEXT NOT NULL DEFAULT '';
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS intent      TEXT NOT NULL DEFAULT '';
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS draft_text  TEXT NOT NULL DEFAULT '';
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS confidence  DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS needs_hitl  BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_approvals_skill ON approvals (skill);

DROP TRIGGER IF EXISTS trg_approvals_updated_at ON approvals;
CREATE TRIGGER trg_approvals_updated_at
    BEFORE UPDATE ON approvals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
