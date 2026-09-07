-- 0016: reconcile audit_log with app/storage/pg.py::audit().
--
-- The writer inserts (action, actor, entity, entity_id, details, conversation_id,
-- channel) but the 0001 baseline only had entity_type / metadata, so every
-- audit() call failed with "column entity of relation audit_log does not exist"
-- (visible in production as audit_write_failed on each fleet run). Additive only.
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS entity          TEXT  NOT NULL DEFAULT '';
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS details         JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS conversation_id TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS channel         TEXT;

-- Keep the legacy column populated so older dashboards keep working.
UPDATE audit_log SET entity_type = entity WHERE entity_type = '' AND entity <> '';

CREATE INDEX IF NOT EXISTS idx_audit_log_entity_name ON audit_log (entity);
CREATE INDEX IF NOT EXISTS idx_audit_log_conversation ON audit_log (conversation_id);
