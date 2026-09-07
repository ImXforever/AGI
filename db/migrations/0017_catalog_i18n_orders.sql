-- 0017 (1.4.0): English-first catalog reference, per-language display data,
-- product images, customer-facing product codes, editable business variables
-- and the Telegram order (quote-request) flow.
--
-- Additive only. name_ar stays for old rows but is no longer required: the
-- canonical reference language of the database is English (name_en).

-- ---------------------------------------------------------------------------
-- products: English canonical + per-language display + image + unique code
-- ---------------------------------------------------------------------------
ALTER TABLE products ALTER COLUMN name_ar SET DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS code        TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS title_en    TEXT  NOT NULL DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS names       JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE products ADD COLUMN IF NOT EXISTS titles      JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url   TEXT  NOT NULL DEFAULT '';
ALTER TABLE products ADD COLUMN IF NOT EXISTS sort_order  INTEGER NOT NULL DEFAULT 100;

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_code ON products (code) WHERE code IS NOT NULL AND code <> '';

-- Give every existing product a short customer-facing code (101, 102, ...).
-- Seeds carry their own codes; this only fills rows that have none.
DO $$
DECLARE
    r RECORD;
    n INTEGER := 100;
BEGIN
    FOR r IN SELECT id FROM products WHERE code IS NULL OR code = '' ORDER BY created_at, sku LOOP
        LOOP
            n := n + 1;
            EXIT WHEN NOT EXISTS (SELECT 1 FROM products WHERE code = n::text);
        END LOOP;
        UPDATE products SET code = n::text WHERE id = r.id;
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- product images: stored in Postgres so the bot can send them without a
-- public bucket URL (Railway bucket URLs are signed and expire).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_images (
    product_id  UUID PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    mime        TEXT  NOT NULL DEFAULT 'image/jpeg',
    data        BYTEA NOT NULL,
    size        INTEGER NOT NULL DEFAULT 0,
    updated_by  TEXT  NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- catalog categories: English key, per-language labels, order, icon
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catalog_categories (
    key         TEXT PRIMARY KEY,
    name_en     TEXT  NOT NULL DEFAULT '',
    names       JSONB NOT NULL DEFAULT '{}'::jsonb,
    icon        TEXT  NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 100,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_catalog_categories_updated_at ON catalog_categories;
CREATE TRIGGER trg_catalog_categories_updated_at
    BEFORE UPDATE ON catalog_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Every category already used by a product gets a row (label = key).
INSERT INTO catalog_categories (key, name_en)
SELECT DISTINCT category, initcap(replace(category, '-', ' '))
FROM products
WHERE category <> ''
ON CONFLICT (key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- customers: remembered language (was written by the bot but never existed)
-- ---------------------------------------------------------------------------
ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_language TEXT NOT NULL DEFAULT '';

-- ---------------------------------------------------------------------------
-- quotes: customer-facing reference + source channel for the order flow
-- ---------------------------------------------------------------------------
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS reference   TEXT;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS channel     TEXT NOT NULL DEFAULT '';
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS approval_id UUID;
ALTER TABLE quotes ADD COLUMN IF NOT EXISTS language    TEXT NOT NULL DEFAULT 'en';
CREATE UNIQUE INDEX IF NOT EXISTS uq_quotes_reference ON quotes (reference) WHERE reference IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_quotes_approval ON quotes (approval_id);

-- ---------------------------------------------------------------------------
-- settings: the manager-editable business variables live here (key/value).
-- Defaults are code-side (app/core/business_settings.py); nothing to seed.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_settings_updated ON settings (updated_at DESC);
