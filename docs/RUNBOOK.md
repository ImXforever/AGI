# Kia-Agent Platform â€” Operations Runbook

## Service Overview

| Service | Port | Health Endpoint | Purpose |
|---------|------|-----------------|---------|
| app | 8080 | /healthz | Main API server |
| hermes | 3000 | /health | LLM bridge |
| admin-ui | 8081 | / | Dashboard |
| postgres | 5432 | pg_isready | Database |
| redis | 6379 | redis-cli ping | Cache + queues |
| cron | â€” | â€” | Nightly backups |

## Common Operations

### Restart App

```bash
# Docker
docker compose restart app

# Railway
railway service restart
```

### View Logs

```bash
# Docker
docker compose logs -f app

# Railway
railway logs --tail 200
```

### Database Operations

```bash
# Connect
psql $DATABASE_URL

# Check table sizes
SELECT schemaname, relname, pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname))
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;

# Active connections
SELECT count(*) FROM pg_stat_activity;
```

### Redis Operations

```bash
# Connect
redis-cli -u $REDIS_URL

# Check memory
INFO memory

# Check stream sizes
XLEN hitl:queue
XLEN bus:events
```

### View HITL Queue

```bash
# Pending approvals count
psql $DATABASE_URL -c "SELECT count(*) FROM approvals WHERE status = 'pending';"

# Recent approvals
psql $DATABASE_URL -c "SELECT id, status, channel, created_at FROM approvals ORDER BY created_at DESC LIMIT 10;"
```

## Troubleshooting

### High Memory Usage

1. Check Redis memory: `redis-cli INFO memory`
2. Check for stale streams: `XLEN bus:events`
3. Trim old events: `XTRIM bus:events MAXLEN ~10000`
4. Restart app: `docker compose restart app`

### Database Connection Pool Exhausted

1. Check active connections: `SELECT count(*), state FROM pg_stat_activity GROUP BY state;`
2. Kill idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '10 minutes';`
3. Restart app to reset pool

### LLM Timeout Errors

1. Check router health: `curl http://9router:20128/v1/models`
2. Check Hermes health: `curl http://hermes:3000/health`
3. Switch to direct mode temporarily: `LLM_MODE=direct`
4. Check upstream API status pages

### Telegram Webhook Not Receiving Messages

1. Check webhook status: `curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"`
2. Re-register webhook: `curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=https://your-domain/webhook/telegram"`
3. Check domain DNS and SSL

### WhatsApp Messages Not Delivering

1. Verify Meta app tokens are not expired
2. Check webhook verification: `GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE`
3. Check phone number ID matches config

### Stuck HITL Approvals

1. Check sweeper is running: `docker compose logs hitl-sweeper`
2. Manually timeout old approvals:
```sql
UPDATE approvals SET status = 'timeout', decided_at = NOW()
WHERE status = 'pending' AND created_at < NOW() - INTERVAL '1 hour';
```

### Backup Failures

1. Check R2 credentials: `aws s3 ls s3://$R2_BUCKET --endpoint-url $R2_ENDPOINT`
2. Check disk space on app volume
3. Manual backup: `python -m app.storage.archive --once`

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| Nightly backup | 03:00 UTC | PG dump to R2 |
| HITL sweeper | Every 30s | Timeout stale approvals |
| IMAP poll | Every 60s | Check inbound emails |
| Rate limit reset | Every 60s | Sliding window cleanup |

## Emergency Procedures

### Kill Switch â€” Stop All Outbound Messages

```bash
redis-cli SET "switch:outbound" "off"
# Or set RATE_LIMIT_PER_MINUTE=1 via env
```

### Force-Cancel All Pending Approvals

```bash
psql $DATABASE_URL -c "UPDATE approvals SET status = 'cancelled' WHERE status = 'pending';"
```

### Rollback Deployment (Railway)

```bash
railway rollback
```

### Restore Database from Backup

```bash
# Download latest backup from R2
aws s3 cp s3://$R2_BUCKET/backups/pg/latest.dump ./restore.dump --endpoint-url $R2_ENDPOINT

# Restore
pg_restore -d $DATABASE_URL ./restore.dump --clean --if-exists
```

## Monitoring Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Deep health check (PG, Redis, R2, Hermes, Router) |
| `GET /healthz?deep=0` | Shallow health (no external checks) |
| `GET /metrics` | Uptime and version info |
| `GET /config/snapshot` | Redacted configuration dump |
| `GET /api/docs` | OpenAPI documentation |

## Contacts

| Role | Contact |
|------|---------|
| On-call | @admin on Telegram |
| Escalation | SUPPORT_CONTACT from config |
| Infrastructure | Railway dashboard |
