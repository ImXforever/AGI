-- 0006_unify_tickets.sql
--
-- BUG #21: split-brain ticket storage.
--
-- The agent tool layer (app/core/tools/support.py, analytics.py) wrote and read
-- `support_tickets`, while the admin API (app/admin_api/tickets.py) and
-- app/core/repository.get_ticket_stats() read `tickets`. The two tables were
-- never joined or synced, so:
--   * a ticket opened by the AI never appeared in the operator dashboard,
--   * a ticket opened by an operator was invisible to get_ticket / analytics,
--   * "open tickets" metrics counted only half the system.
--
-- This migration makes `tickets` the single canonical table: it absorbs the
-- support-only columns, ingests every existing support_tickets row, repoints
-- ticket_events, and drops the duplicate.

-- 1. Canonical table gains the support-side columns.
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS severity  TEXT NOT NULL DEFAULT 'normal';
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS channel   TEXT NOT NULL DEFAULT '';
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS is_safety BOOLEAN NOT NULL DEFAULT FALSE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tickets_severity_check'
    ) THEN
        ALTER TABLE tickets ADD CONSTRAINT tickets_severity_check
            CHECK (severity IN ('low', 'normal', 'high', 'critical'));
    END IF;
END $$;

-- The support side used a 'pending' status that the tickets CHECK rejected.
ALTER TABLE tickets DROP CONSTRAINT IF EXISTS tickets_status_check;
ALTER TABLE tickets ADD CONSTRAINT tickets_status_check
    CHECK (status IN ('open', 'pending', 'in_progress', 'waiting', 'resolved', 'closed'));

CREATE INDEX IF NOT EXISTS idx_tickets_safety ON tickets (is_safety) WHERE is_safety;

-- 2. Migrate any rows that only exist on the support side.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'support_tickets') THEN

        INSERT INTO tickets (id, customer_id, subject, description, status,
                             priority, severity, channel, is_safety,
                             created_at, updated_at)
        SELECT s.id, s.customer_id, s.subject, s.body, s.status,
               CASE s.severity
                   WHEN 'critical' THEN 'urgent'
                   WHEN 'high'     THEN 'high'
                   WHEN 'low'      THEN 'low'
                   ELSE 'medium'
               END,
               s.severity, s.channel, s.is_safety, s.created_at, s.updated_at
        FROM support_tickets s
        ON CONFLICT (id) DO NOTHING;

        -- 3. Repoint ticket_events at the canonical table.
        ALTER TABLE ticket_events DROP CONSTRAINT IF EXISTS ticket_events_ticket_id_fkey;
        DELETE FROM ticket_events e
        WHERE e.ticket_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.id = e.ticket_id);
        ALTER TABLE ticket_events ADD CONSTRAINT ticket_events_ticket_id_fkey
            FOREIGN KEY (ticket_id) REFERENCES tickets (id) ON DELETE CASCADE;

        DROP TABLE support_tickets;
    END IF;
END $$;
