-- 0005: reconcile the remaining objects that app/core/repository.py queries.
--
-- Found by putting the repository layer under integration test for the first
-- time: every one of these caused a hard runtime error (UndefinedTableError /
-- UndefinedColumnError) the moment the code path was exercised.
-- Additive only — no drops, no data loss.

-- ---------------------------------------------------------------------------
-- attachments: store_attachment() writes here, but the table never existed.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      UUID,
    filename        TEXT NOT NULL DEFAULT '',
    content_type    TEXT NOT NULL DEFAULT '',
    r2_key          TEXT NOT NULL DEFAULT '',
    size            BIGINT NOT NULL DEFAULT 0,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attachments_conversation ON attachments (conversation_id);
CREATE INDEX IF NOT EXISTS idx_attachments_message      ON attachments (message_id);

-- ---------------------------------------------------------------------------
-- approvals.edited_text: an approver may amend the draft before it is sent.
-- update_approval_status(edited_text=...) wrote to a column that did not exist.
-- ---------------------------------------------------------------------------
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS edited_text TEXT;

-- ---------------------------------------------------------------------------
-- conversations.status: repository.set_conversation_status() is called with
-- 'closed' by the pipeline, but the CHECK constraint only allowed
-- active/resolved/archived, so closing a conversation raised
-- CheckViolationError. Accept 'closed' as a synonym going forward.
-- ---------------------------------------------------------------------------
ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_status_check;
ALTER TABLE conversations ADD  CONSTRAINT conversations_status_check
    CHECK (status IN ('active', 'resolved', 'archived', 'closed'));

-- ---------------------------------------------------------------------------
-- customers.lead_score_bant: tools.set_lead_score() writes the BANT breakdown
-- alongside the numeric score, but the column was never created, so every
-- lead-scoring call raised UndefinedColumnError.
-- ---------------------------------------------------------------------------
ALTER TABLE customers ADD COLUMN IF NOT EXISTS lead_score_bant JSONB;
