-- Agent Soul — who the bot is. Lives in Postgres so the manager can edit it from
-- the admin console without a redeploy; the orchestrator injects it into every
-- system prompt. One row per tenant (id = 'default').
CREATE TABLE IF NOT EXISTS agent_soul (
    id              TEXT PRIMARY KEY DEFAULT 'default',
    agent_name      TEXT NOT NULL DEFAULT 'Zenovix',
    company_name    TEXT NOT NULL DEFAULT '',
    role_title      TEXT NOT NULL DEFAULT 'Digital Operations Manager',
    mission         TEXT NOT NULL DEFAULT '',
    personality     TEXT NOT NULL DEFAULT '',
    tone            TEXT NOT NULL DEFAULT 'warm, professional, concise',
    languages       TEXT NOT NULL DEFAULT 'English first; reply in the customer''s language',
    greeting        TEXT NOT NULL DEFAULT '',
    boundaries      TEXT NOT NULL DEFAULT '',
    style_rules     TEXT NOT NULL DEFAULT '',
    signature       TEXT NOT NULL DEFAULT '',
    extra           JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    version         INTEGER NOT NULL DEFAULT 1,
    updated_by      TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_agent_soul_updated_at ON agent_soul;
CREATE TRIGGER trg_agent_soul_updated_at
    BEFORE UPDATE ON agent_soul
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Currency policy: USD is the platform's primary currency. Products that were
-- seeded with a local currency but no price (unit_price = 0) simply switch to
-- USD; priced rows are left untouched so nothing is silently re-denominated.
UPDATE products SET currency = 'USD', updated_at = NOW()
WHERE currency <> 'USD' AND COALESCE(unit_price, 0) = 0 AND COALESCE(base_price, 0) = 0;
