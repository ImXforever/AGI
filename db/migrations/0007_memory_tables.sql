-- 0007_memory_tables.sql
--
-- BUG #22: the entire long-term memory subsystem (app/core/memory.py) queries
-- three tables that NO migration ever created:
--
--   * user_memories  — remember / recall / list_all / delete_one / forget_all
--   * user_profile   — purchase_profile, persona_refresh, record_purchase_event
--   * purchases      — purchase_profile, recommend_for_user
--
-- Every one of those calls raised UndefinedTableError. build_memory_context()
-- wraps them in a bare `except: return ""`, so the failure was completely
-- silent: personalised memory injection returned an empty string on every turn
-- for every user since the feature shipped. MemoryProvider.remember() was not
-- wrapped and would surface the error to the caller.

CREATE TABLE IF NOT EXISTS user_memories (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT  NOT NULL,
    kind             TEXT    NOT NULL DEFAULT 'fact',
    content          TEXT    NOT NULL,
    importance       INTEGER NOT NULL DEFAULT 3,
    source           TEXT    NOT NULL DEFAULT '',
    dedup_key        TEXT    NOT NULL,
    recall_count     INTEGER NOT NULL DEFAULT 0,
    last_recalled_at BIGINT,
    created_at       DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM now()),
    CONSTRAINT user_memories_importance_check CHECK (importance BETWEEN 1 AND 5),
    CONSTRAINT user_memories_dedup_uniq UNIQUE (user_id, dedup_key)
);

CREATE INDEX IF NOT EXISTS idx_user_memories_user ON user_memories (user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_rank ON user_memories (user_id, importance DESC, id DESC);

CREATE TABLE IF NOT EXISTS user_profile (
    user_id             BIGINT PRIMARY KEY,
    buys_count          INTEGER DEFAULT 0,
    total_spent_credits INTEGER DEFAULT 0,
    last_categories     TEXT    DEFAULT '',
    persona             TEXT    DEFAULT '',
    persona_at          REAL,
    interests           TEXT    DEFAULT '',
    updated_at          REAL NOT NULL DEFAULT EXTRACT(EPOCH FROM now())
);

CREATE TABLE IF NOT EXISTS purchases (
    id            BIGSERIAL PRIMARY KEY,
    buyer_id      BIGINT  NOT NULL,
    product_id    UUID    NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    price_credits INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_purchases_buyer   ON purchases (buyer_id);
CREATE INDEX IF NOT EXISTS idx_purchases_product ON purchases (product_id);
