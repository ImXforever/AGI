-- 0004: reconcile the database schema with what the application code queries.
--
-- The 0001 baseline diverged from app/ over time: several columns and whole
-- tables referenced by the admin API, tools and memory layer never existed.
-- This migration is additive only (no drops, no data loss).

-- ---------------------------------------------------------------------------
-- products: code uses unit_price / stock_qty / reorder_point / discount_tiers
-- ---------------------------------------------------------------------------
ALTER TABLE products ADD COLUMN IF NOT EXISTS unit_price     NUMERIC(12,2) NOT NULL DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS stock_qty      INTEGER       NOT NULL DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS reorder_point  INTEGER       NOT NULL DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS discount_tiers JSONB         NOT NULL DEFAULT '[]'::jsonb;

-- Keep the legacy base_price column in sync for existing rows / seeds.
UPDATE products SET unit_price = base_price WHERE unit_price = 0 AND base_price <> 0;

CREATE OR REPLACE FUNCTION products_sync_price() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.unit_price IS DISTINCT FROM OLD.unit_price THEN
        NEW.base_price := NEW.unit_price;
    ELSIF NEW.base_price IS DISTINCT FROM OLD.base_price THEN
        NEW.unit_price := NEW.base_price;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION products_sync_price_ins() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.unit_price = 0 AND NEW.base_price <> 0 THEN
        NEW.unit_price := NEW.base_price;
    ELSIF NEW.base_price = 0 AND NEW.unit_price <> 0 THEN
        NEW.base_price := NEW.unit_price;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_sync_price_ins ON products;
CREATE TRIGGER trg_products_sync_price_ins
    BEFORE INSERT ON products FOR EACH ROW EXECUTE FUNCTION products_sync_price_ins();

DROP TRIGGER IF EXISTS trg_products_sync_price ON products;
CREATE TRIGGER trg_products_sync_price
    BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION products_sync_price();

CREATE INDEX IF NOT EXISTS idx_products_low_stock ON products (stock_qty) WHERE is_active;

-- ---------------------------------------------------------------------------
-- customers: tools update name_ar / name_en
-- ---------------------------------------------------------------------------
ALTER TABLE customers ADD COLUMN IF NOT EXISTS name_ar TEXT NOT NULL DEFAULT '';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS name_en TEXT NOT NULL DEFAULT '';
UPDATE customers SET name_ar = name WHERE name_ar = '' AND name IS NOT NULL;

-- ---------------------------------------------------------------------------
-- faq / troubleshooting: extra columns the admin API selects
-- ---------------------------------------------------------------------------
ALTER TABLE faq            ADD COLUMN IF NOT EXISTS language   TEXT NOT NULL DEFAULT 'ar';
ALTER TABLE troubleshooting ADD COLUMN IF NOT EXISTS problem_ar TEXT NOT NULL DEFAULT '';
ALTER TABLE troubleshooting ADD COLUMN IF NOT EXISTS problem_en TEXT NOT NULL DEFAULT '';
UPDATE troubleshooting SET problem_ar = COALESCE(NULLIF(symptom_ar, ''), description_ar) WHERE problem_ar = '';
UPDATE troubleshooting SET problem_en = COALESCE(NULLIF(symptom_en, ''), description_en) WHERE problem_en = '';

-- ---------------------------------------------------------------------------
-- product_specs / msds_documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_specs (
    product_id       UUID PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    technical_specs  JSONB DEFAULT '{}'::jsonb,
    safety_data      TEXT,
    compliance_notes TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS msds_documents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    title_ar   TEXT NOT NULL DEFAULT '',
    title_en   TEXT NOT NULL DEFAULT '',
    r2_key     TEXT NOT NULL,
    version    INTEGER NOT NULL DEFAULT 1,
    language   TEXT NOT NULL DEFAULT 'ar',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_msds_product ON msds_documents (product_id);

-- ---------------------------------------------------------------------------
-- Support: support_tickets + ticket_events (distinct from the `tickets` table)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS support_tickets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    subject     TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    severity    TEXT NOT NULL DEFAULT 'normal'
                CHECK (severity IN ('low', 'normal', 'high', 'critical')),
    channel     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
    is_safety   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets (status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_customer ON support_tickets (customer_id);

CREATE TABLE IF NOT EXISTS ticket_events (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id  UUID REFERENCES support_tickets(id) ON DELETE CASCADE,
    actor      TEXT NOT NULL DEFAULT '',
    action     TEXT NOT NULL DEFAULT '',
    body       TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket ON ticket_events (ticket_id);

-- ---------------------------------------------------------------------------
-- Orders line items (analytics revenue queries)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id   UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    quantity   NUMERIC(12,3) NOT NULL DEFAULT 1,
    unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency   TEXT NOT NULL DEFAULT 'SAR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items (product_id);

-- ---------------------------------------------------------------------------
-- Customer notes, outbound messages, tool executions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    body        TEXT NOT NULL DEFAULT '',
    actor       TEXT NOT NULL DEFAULT 'system',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_customer_notes_customer ON customer_notes (customer_id);

CREATE TABLE IF NOT EXISTS outbound_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    channel         TEXT NOT NULL DEFAULT '',
    recipient_id    TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    approval_id     UUID,
    external_ref    TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          TEXT NOT NULL DEFAULT 'sent',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_outbound_conversation ON outbound_messages (conversation_id);

CREATE TABLE IF NOT EXISTS tool_executions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id UUID,
    tool_name   TEXT NOT NULL DEFAULT '',
    result      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tool_executions_approval ON tool_executions (approval_id);

-- ---------------------------------------------------------------------------
-- Fleet / memory helper tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_turns (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    role       TEXT   NOT NULL DEFAULT 'user',
    content    TEXT   NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_user ON conversation_turns (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS kb_notes (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    topic      TEXT   NOT NULL DEFAULT '',
    content    TEXT   NOT NULL DEFAULT '',
    source     TEXT   NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kb_notes_user ON kb_notes (user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- catalog_items: compatibility view over products
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW catalog_items AS
    SELECT id, sku, name_ar, name_en, category, unit_price, currency,
           stock_qty, is_active, created_at, updated_at
    FROM products;

-- ---------------------------------------------------------------------------
-- customers.display_name (written by repository.get_or_create_customer)
-- ---------------------------------------------------------------------------
ALTER TABLE customers ADD COLUMN IF NOT EXISTS display_name TEXT NOT NULL DEFAULT '';
UPDATE customers SET display_name = name WHERE display_name = '' AND name IS NOT NULL;
