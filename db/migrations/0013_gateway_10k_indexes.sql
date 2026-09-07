-- 10k-member lookups: customer identity and durable message dedup.
-- Redis TTL dedup is 24h; Postgres unique index is the long-term SoT.

CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_channel_external
    ON customers (channel, external_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_conv_extref
    ON messages (conversation_id, external_ref)
    WHERE external_ref IS NOT NULL AND btrim(external_ref) <> '';
