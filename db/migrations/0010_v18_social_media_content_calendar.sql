-- v18: Content calendar + social media tables

CREATE TABLE IF NOT EXISTS content_calendar (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    caption         TEXT NOT NULL,
    platform        TEXT NOT NULL,
    scheduled_at    REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft',
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now())),
    published_at    REAL,
    post_id         TEXT,
    media_url       TEXT DEFAULT '',
    hashtags        JSONB DEFAULT '[]',
    created_by      TEXT DEFAULT 'admin',
    notes           TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_content_calendar_status ON content_calendar (status);
CREATE INDEX IF NOT EXISTS idx_content_calendar_scheduled ON content_calendar (scheduled_at) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_content_calendar_platform ON content_calendar (platform);

CREATE TABLE IF NOT EXISTS social_posts (
    id              TEXT PRIMARY KEY,
    platform        TEXT NOT NULL,
    post_id         TEXT NOT NULL,
    caption         TEXT NOT NULL,
    media_url       TEXT DEFAULT '',
    published_at    REAL NOT NULL,
    engagement_data JSONB DEFAULT '{}',
    created_at      REAL NOT NULL DEFAULT (extract(epoch from now()))
);

CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts (platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_published ON social_posts (published_at);
