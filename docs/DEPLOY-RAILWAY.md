# Kia-Agent Platform â€” Railway Deployment Guide

## Prerequisites

1. [Railway CLI](https://docs.railway.app/reference/cli) installed
2. Railway account with a project created
3. Cloudflare R2 bucket configured
4. Telegram bot created via [@BotFather](https://t.me/BotFather)

## Quick Deploy

```bash
# 1. Login to Railway
railway login

# 2. Link to your project
railway link

# 3. Set environment variables
railway variables set DATABASE_URL=$(railway postgresql url)
railway variables set REDIS_URL=$(railway redis url)

# 4. Deploy
railway up
```

## Step-by-Step Deployment

### 1. Create Railway Project

```bash
railway init Kia-Agent
```

### 2. Add Managed Services

```bash
# PostgreSQL
railway add --database postgresql

# Redis
railway add --database redis
```

Railway auto-generates `DATABASE_URL` and `REDIS_URL`.

### 3. Configure Environment Variables

Copy `.env.example` and set all required variables:

```bash
# Essential (auto-set by Railway)
# DATABASE_URL and REDIS_URL are set automatically

# Required
railway variables set TENANT_ID=acme-petro
railway variables set TENANT_NAME_AR="Ø´Ø±ÙƒØ© Ø£ÙƒÙ…Ù‰ Ù„Ù„Ø¨ØªØ±ÙˆÙ„"
railway variables set SUPPORT_CONTACT=support@acme-petro.com
railway variables set TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
railway variables set TELEGRAM_ADMIN_IDS=123456789
railway variables set ADMIN_USERNAME=admin
railway variables set ADMIN_BOOTSTRAP_PASSWORD="YourSecurePassword!123"
railway variables set CURRENCY=SAR

# Cloudflare R2
railway variables set R2_ENDPOINT=https://xxxx.r2.cloudflarestorage.com
railway variables set R2_ACCESS_KEY_ID=your-r2-key
railway variables set R2_SECRET_ACCESS_KEY=your-r2-secret
railway variables set R2_BUCKET=Kia-Agent-assets

# WhatsApp (optional)
railway variables set WHATSAPP_ENABLED=true
railway variables set WHATSAPP_PROVIDER=meta
railway variables set WHATSAPP_APP_SECRET=your-secret
railway variables set WHATSAPP_PHONE_NUMBER_ID=your-id
railway variables set WHATSAPP_API_TOKEN=your-token

# Email (optional)
railway variables set EMAIL_ENABLED=true
railway variables set EMAIL_FROM=noreply@yourdomain.com
railway variables set RESEND_API_KEY=re_your_key

# LLM
railway variables set LLM_MODE=router
railway variables set ROUTER_ACCESS_KEY=your-key
railway variables set OPENROUTER_API_KEY=your-key
```

### 4. Deploy

```bash
railway up
```

The `railway.json` config automatically:
- Builds using `Dockerfile`
- Runs `uvicorn` with 2 workers
- Health checks at `/healthz`

### 5. Custom Domain

```bash
railway domain
```

### 6. Verify

```bash
# Health check
curl https://your-app.up.railway.app/healthz

# Open admin UI
open https://your-app.up.railway.app/admin/

# API docs
open https://your-app.up.railway.app/api/docs
```

## Production Checklist

- [ ] `APP_ENV=production`
- [ ] `COOKIE_SECURE=true`
- [ ] Strong `ADMIN_BOOTSTRAP_PASSWORD` (12+ characters)
- [ ] `WEB_SECRET` explicitly set (32+ characters)
- [ ] `LLM_MODE=router` (not mock)
- [ ] `TELEGRAM_ADMIN_IDS` set to real admin IDs
- [ ] R2 bucket configured and accessible
- [ ] `LOG_JSON_ENABLED=true` for Railway log drain
- [ ] Backup cron running (`BACKUP_HOUR` set)
- [ ] `HITL_TIMEOUT_SECONDS` appropriate for your ops team

## Monitoring

Railway provides:
- **Logs**: Real-time JSON log streaming
- **Metrics**: CPU, memory, network
- **Deployments**: Automatic rollbacks
- **Health**: Built-in health checks via `railway.json`

## Troubleshooting

### App won't start
```bash
railway logs --tail 100
```

Common causes:
- Missing required env vars
- Database not ready (add startup delay)
- Invalid `LLM_MODE=mock` in production

### Database connection issues
```bash
railway connect postgresql
# Verify tables exist
\dt
```

### Redis connection issues
```bash
railway connect redis
PING
```

## Scaling

Railway auto-scales based on traffic. For high-traffic deployments:

```bash
railway variables set WEB_PORT=8080
# Railway handles horizontal scaling via replicas
```

## Rollback

```bash
railway rollback
```

## Cost Estimation

| Service | Estimated Monthly Cost |
|---------|----------------------|
| App (starter) | $5-20 |
| PostgreSQL (starter) | $5-10 |
| Redis (starter) | $5-10 |
| **Total** | **$15-40** |
