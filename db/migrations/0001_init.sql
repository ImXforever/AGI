-- =============================================================================
-- Migration 0001: Initial schema — all 16 core tables
-- PetroAgent Platform
-- =============================================================================

-- Note: _migrations table is managed by Python (pg.py).
-- Only schema tables below:

-- 1. admins
CREATE TABLE IF NOT EXISTS admins (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('superadmin','admin','viewer')),
    is_bootstrap    BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_admins_username ON admins (username);

-- 2. customers
CREATE TABLE IF NOT EXISTS customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     TEXT,
    channel         TEXT NOT NULL DEFAULT 'telegram',
    name            TEXT NOT NULL DEFAULT '',
    company         TEXT NOT NULL DEFAULT '',
    phone           TEXT NOT NULL DEFAULT '',
    email           TEXT NOT NULL DEFAULT '',
    lead_score      INTEGER NOT NULL DEFAULT 0 CHECK (lead_score BETWEEN 0 AND 100),
    tags            JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_customers_external_id ON customers (external_id);
CREATE INDEX IF NOT EXISTS idx_customers_channel ON customers (channel);
CREATE INDEX IF NOT EXISTS idx_customers_lead_score ON customers (lead_score DESC);

-- 3. products
CREATE TABLE IF NOT EXISTS products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku             TEXT NOT NULL UNIQUE,
    name_ar         TEXT NOT NULL,
    name_en         TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    unit            TEXT NOT NULL DEFAULT 'kg',
    base_price      NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency        TEXT NOT NULL DEFAULT 'SAR',
    description_ar  TEXT NOT NULL DEFAULT '',
    description_en  TEXT NOT NULL DEFAULT '',
    specs           JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_active ON products (is_active) WHERE is_active = TRUE;

-- 4. conversations
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    channel         TEXT NOT NULL,
    external_ref    TEXT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','resolved','archived')),
    skill           TEXT,
    hitl_pending    BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations (customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations (channel);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations (status);
CREATE INDEX IF NOT EXISTS idx_conversations_external_ref ON conversations (external_ref);

-- 5. messages
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_role     TEXT NOT NULL CHECK (sender_role IN ('user','agent','system')),
    sender_id       TEXT NOT NULL DEFAULT '',
    text            TEXT NOT NULL DEFAULT '',
    attachments     JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    external_ref    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_sender_role ON messages (sender_role);

-- 6. approvals
CREATE TABLE IF NOT EXISTS approvals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    channel         TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','rejected','edited','timeout','escalated','cancelled')),
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at      TIMESTAMPTZ,
    actor           TEXT,
    note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals (status);
CREATE INDEX IF NOT EXISTS idx_approvals_conversation ON approvals (conversation_id);
CREATE INDEX IF NOT EXISTS idx_approvals_created ON approvals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals (status) WHERE status = 'pending';

-- 7. quotes
CREATE TABLE IF NOT EXISTS quotes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','sent','viewed','accepted','rejected','cancelled','expired')),
    items           JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal        NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax             NUMERIC(12,2) NOT NULL DEFAULT 0,
    total           NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency        TEXT NOT NULL DEFAULT 'SAR',
    valid_until     TIMESTAMPTZ,
    notes           TEXT NOT NULL DEFAULT '',
    pdf_url         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quotes_customer ON quotes (customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes (status);
CREATE INDEX IF NOT EXISTS idx_quotes_created ON quotes (created_at DESC);

-- 8. tickets
CREATE TABLE IF NOT EXISTS tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    subject         TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_progress','waiting','resolved','closed')),
    priority        TEXT NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('low','medium','high','urgent')),
    assigned_to     TEXT,
    category        TEXT NOT NULL DEFAULT '',
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets (customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets (priority);
CREATE INDEX IF NOT EXISTS idx_tickets_assigned ON tickets (assigned_to);

-- 9. ticket_notes
CREATE TABLE IF NOT EXISTS ticket_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author          TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ticket_notes_ticket ON ticket_notes (ticket_id);

-- 10. orders_imports
CREATE TABLE IF NOT EXISTS orders_imports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'csv',
    row_count       INTEGER NOT NULL DEFAULT 0,
    error_count     INTEGER NOT NULL DEFAULT 0,
    errors          JSONB NOT NULL DEFAULT '[]'::jsonb,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','completed','failed')),
    imported_by     TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_orders_imports_status ON orders_imports (status);

-- 11. orders
CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id        UUID REFERENCES quotes(id) ON DELETE SET NULL,
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    import_id       UUID REFERENCES orders_imports(id) ON DELETE SET NULL,
    order_number    TEXT UNIQUE,
    status          TEXT NOT NULL DEFAULT 'confirmed'
                    CHECK (status IN ('confirmed','processing','shipped','delivered','cancelled')),
    items           JSONB NOT NULL DEFAULT '[]'::jsonb,
    total           NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency        TEXT NOT NULL DEFAULT 'SAR',
    notes           TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_quote ON orders (quote_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders (order_number);

-- 12. audit_log
CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor           TEXT NOT NULL DEFAULT '',
    action          TEXT NOT NULL,
    entity_type     TEXT NOT NULL DEFAULT '',
    entity_id       TEXT NOT NULL DEFAULT '',
    old_value       JSONB,
    new_value       JSONB,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address      TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log (actor);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log (created_at DESC);

-- 13. fallback_templates
CREATE TABLE IF NOT EXISTS fallback_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key             TEXT NOT NULL UNIQUE,
    name_ar         TEXT NOT NULL,
    name_en         TEXT NOT NULL DEFAULT '',
    channel         TEXT NOT NULL DEFAULT '',
    subject         TEXT NOT NULL DEFAULT '',
    body_ar         TEXT NOT NULL,
    body_en         TEXT NOT NULL DEFAULT '',
    variables       JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fallback_templates_key ON fallback_templates (key);
CREATE INDEX IF NOT EXISTS idx_fallback_templates_channel ON fallback_templates (channel);

-- 14. faq
CREATE TABLE IF NOT EXISTS faq (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_ar     TEXT NOT NULL,
    question_en     TEXT NOT NULL DEFAULT '',
    answer_ar       TEXT NOT NULL,
    answer_en       TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    tags            JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    hit_count       INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_faq_category ON faq (category);
CREATE INDEX IF NOT EXISTS idx_faq_active ON faq (is_active) WHERE is_active = TRUE;

-- 15. troubleshooting
CREATE TABLE IF NOT EXISTS troubleshooting (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title_ar        TEXT NOT NULL,
    title_en        TEXT NOT NULL DEFAULT '',
    description_ar  TEXT NOT NULL DEFAULT '',
    description_en  TEXT NOT NULL DEFAULT '',
    symptom_ar      TEXT NOT NULL DEFAULT '',
    symptom_en      TEXT NOT NULL DEFAULT '',
    solution_ar     TEXT NOT NULL DEFAULT '',
    solution_en     TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    severity        TEXT NOT NULL DEFAULT 'medium'
                    CHECK (severity IN ('low','medium','high','critical')),
    tags            JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    hit_count       INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_troubleshooting_category ON troubleshooting (category);
CREATE INDEX IF NOT EXISTS idx_troubleshooting_active ON troubleshooting (is_active) WHERE is_active = TRUE;

-- 16. settings
CREATE TABLE IF NOT EXISTS settings (
    key             TEXT PRIMARY KEY,
    value           JSONB NOT NULL DEFAULT 'null'::jsonb,
    description     TEXT NOT NULL DEFAULT '',
    updated_by      TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Updated-at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'admins', 'customers', 'products', 'conversations',
            'quotes', 'tickets', 'orders', 'fallback_templates',
            'faq', 'troubleshooting', 'settings'
        ])
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_updated_at ON %s', t, t);
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %s
             FOR EACH ROW
             EXECUTE FUNCTION update_updated_at_column()',
            t, t
        );
    END LOOP;
END;
$$;

-- Migration tracking table is created/managed by app/storage/pg.py (version, name, checksum).



