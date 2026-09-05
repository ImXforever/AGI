# Kia-Agent Platform â€” Configuration Contract

## Overview

All configuration is read from environment variables (optionally via `.env` file). The `app.config` module is the **single source of truth** â€” no other module should read `os.environ` directly.

## Loading Order

1. `.env` file (current directory or project root)
2. Actual environment variables (override `.env`)
3. Programmatic `env` dict passed to `load_config(env)`

## Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `TENANT_ID` | string | Unique tenant identifier (lowercase) |
| `TENANT_NAME_AR` | string | Arabic tenant name |
| `SUPPORT_CONTACT` | string | Support email/contact |
| `TELEGRAM_BOT_TOKEN` | string | Telegram bot token |
| `TELEGRAM_ADMIN_IDS` | csv | Comma-separated admin Telegram user IDs |
| `DATABASE_URL` | string | PostgreSQL connection URL |
| `REDIS_URL` | string | Redis connection URL |
| `R2_ENDPOINT` | string | Cloudflare R2 endpoint |
| `R2_ACCESS_KEY_ID` | string | R2 access key |
| `R2_SECRET_ACCESS_KEY` | string | R2 secret key |
| `R2_BUCKET` | string | R2 bucket name |
| `ADMIN_USERNAME` | string | Initial admin username |
| `ADMIN_BOOTSTRAP_PASSWORD` | string | Initial admin password |
| `CURRENCY` | string | ISO 4217 currency code (e.g. SAR) |

## Optional Variables (with defaults)

### Tenant
| Variable | Default | Description |
|----------|---------|-------------|
| `TENANT_NAME_EN` | (same as AR) | English tenant name |
| `BRAND_LOGO_URL` | "" | Brand logo URL |
| `BRAND_PRIMARY_COLOR` | "#0b6e4f" | Primary brand color |

### App
| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | "production" | `production`, `development`, or `test` |
| `LOG_LEVEL` | "INFO" | Logging level |
| `LOG_JSON_ENABLED` | "true" | JSON log format |
| `LOG_TO_DB` | "true" | Log to database |
| `BACKUP_HOUR` | "3" | Hour (0-23) for nightly backups |

### WhatsApp
| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_ENABLED` | "true" | Enable WhatsApp channel |
| `WHATSAPP_PROVIDER` | "meta" | `meta` or `twilio` |
| `WHATSAPP_VERIFY_TOKEN` | auto | Webhook verify token |
| `WHATSAPP_APP_SECRET` | "" | Meta app secret (required if meta) |
| `WHATSAPP_PHONE_NUMBER_ID` | "" | Meta phone number ID |
| `WHATSAPP_API_TOKEN` | "" | Meta API token |
| `WHATSAPP_BASE_URL` | Meta Graph URL | API base URL |
| `TWILIO_ACCOUNT_SID` | "" | Twilio SID (required if twilio) |
| `TWILIO_AUTH_TOKEN` | "" | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | "" | Twilio WhatsApp number |
| `TWILIO_BASE_URL` | Twilio URL | Twilio API base URL |

### Email
| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_ENABLED` | "true" | Enable email channel |
| `EMAIL_FROM` | "" | Sender email address |
| `EMAIL_REPLY_TO` | (same as FROM) | Reply-to address |
| `RESEND_API_KEY` | "" | Resend API key |
| `RESEND_BASE_URL` | Resend URL | Resend API base URL |
| `EMAIL_INBOUND_PROVIDER` | "sendgrid" | `sendgrid` or `imap` |
| `SENDGRID_API_KEY` | "" | SendGrid API key |
| `SENDGRID_WEBHOOK_PUBLIC_KEY` | "" | SendGrid webhook key |
| `RESEND_WEBHOOK_SECRET` | "" | Resend webhook secret |
| `IMAP_HOST` | "" | IMAP server host |
| `IMAP_PORT` | "993" | IMAP port |
| `IMAP_USER` | "" | IMAP username |
| `IMAP_PASSWORD` | "" | IMAP password |
| `IMAP_POLL_SECONDS` | "60" | IMAP polling interval |
| `RATE_LIMIT_PER_MINUTE` | "30" | Per-user rate limit |

### LLM
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODE` | "router" | `router`, `direct`, or `mock` |
| `ROUTER_BASE_URL` | "http://9router:20128/v1" | 9router endpoint |
| `ROUTER_ACCESS_KEY` | auto | Router access key |
| `ROUTER_TIMEOUT` | "120" | Request timeout (seconds) |
| `ROUTER_FALLBACK_TO_DIRECT` | "true" | Fallback to direct on router failure |
| `HERMES_BASE_URL` | "http://hermes:3000" | Hermes endpoint |
| `HERMES_SERVICE_TOKEN` | auto | Hermes auth token |
| `HERMES_TIMEOUT` | "180" | Hermes request timeout |
| `DIRECT_BASE_URL` | "" | Direct LLM base URL (required in direct mode) |
| `DIRECT_API_KEY` | "" | Direct LLM API key |
| `DIRECT_MODEL` | "" | Direct LLM model name |
| `LLM_MODEL_FAST` | "" | Fast model for routing |
| `LLM_MODEL_STANDARD` | "" | Standard model for complex tasks |
| `LLM_TEMPERATURE` | "0.3" | LLM temperature |

### Upstream API Keys
Prefixed with `OPENROUTER_`, `OPENAI_`, `DEEPSEEK_`, `ANTHROPIC_`, `GEMINI_`, `GOOGLE_`, `GROQ_`, `MISTRAL_`, `XAI_`, or `UPSTREAM_`. Passed through to 9router.

### HITL
| Variable | Default | Description |
|----------|---------|-------------|
| `HITL_TIMEOUT_SECONDS` | "600" | Approval timeout |
| `HITL_FALLBACK` | "auto_ack" | `auto_ack` or `silent` |
| `HITL_PING_TELEGRAM` | "true" | Notify admins on Telegram |

### Storage
| Variable | Default | Description |
|----------|---------|-------------|
| `R2_PREFIX` | "tenants/{id}" | R2 key prefix |
| `R2_SIGNED_URL_TTL` | "3600" | Signed URL expiry (seconds) |
| `PG_DUMP_RETENTION_DAYS` | "30" | Backup retention |
| `HOT_DATA_DAYS` | "90" | Hot data retention |
| `ARCHIVE_FINAL_OUTPUTS` | "true" | Archive completed outputs |

### Admin
| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_SECRET` | auto | Session signing secret |
| `WEB_PORT` | "8080" | Server port |
| `COOKIE_SECURE` | "true" | Secure cookie flag |
| `TOTP_ENABLED` | "false" | TOTP 2FA |

### Domain
| Variable | Default | Description |
|----------|---------|-------------|
| `TAX_RATE` | "0.15" | Tax rate (0-1) |
| `QUOTE_VALID_DAYS` | "7" | Quote validity period |
| `LEAD_SCORING_ENABLED` | "true" | Enable lead scoring |
| `NUMERAL_STYLE` | "arabic-indic" | `arabic-indic` or `western` |
| `REPLY_LANGUAGE_POLICY` | "fusha-formal" | Language policy |

## Validation Rules

1. `TENANT_ID` â€” required, lowercase
2. `LLM_MODE=mock` is **not allowed** when `APP_ENV=production`
3. `BACKUP_HOUR` must be 0-23
4. `TAX_RATE` must be 0.0-1.0
5. `WEB_SECRET` must be â‰¥ 16 characters if explicitly set (auto-generated otherwise)
6. `HITL_TIMEOUT_SECONDS` must be â‰¥ 1
7. Channel-specific variables are required only when that channel is enabled
8. `IMAP_*` variables are required only when `EMAIL_INBOUND_PROVIDER=imap`

## Frozen Dataclass Structure

```
Config
â”œâ”€â”€ tenant: TenantGroup
â”œâ”€â”€ channels: ChannelsGroup
â”œâ”€â”€ llm: LLMGroup
â”œâ”€â”€ hitl: HITLGroup
â”œâ”€â”€ storage: StorageGroup
â”œâ”€â”€ admin: AdminGroup
â”œâ”€â”€ ops: OpsGroup
â”œâ”€â”€ domain: DomainGroup
â””â”€â”€ upstream_keys: dict[str, str]
```

All groups are `@dataclass(frozen=True)` â€” immutable after construction.

## Security Notes

- Secrets are masked in `as_redacted_dict()` output
- Auto-generated secrets use `secrets.token_urlsafe(32)` (256 bits)
- Short secrets (< 16 chars) are rejected even if explicitly set
