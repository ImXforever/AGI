# Kia-Agent Platform â€” Architecture

## Overview

Kia-Agent is an Arabic-first AI customer service platform for the oil and petroleum industry. It provides multi-channel messaging (Telegram, WhatsApp, Email), human-in-the-loop approval workflows, quote generation, ticket management, and analytics.

## High-Level Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   Telegram   â”‚     â”‚   WhatsApp   â”‚     â”‚    Email     â”‚
â”‚   (webhook)  â”‚     â”‚  (webhook)   â”‚     â”‚  (webhook/   â”‚
â”‚              â”‚     â”‚              â”‚     â”‚   IMAP poll) â”‚
â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
       â”‚                    â”‚                    â”‚
       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                            â”‚
                     â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”
                     â”‚   Gateway   â”‚
                     â”‚  (FastAPI)  â”‚
                     â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜
                            â”‚
              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â”‚             â”‚             â”‚
       â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â–¼â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”
       â”‚ Orchestrator â”‚ â”‚  HITL  â”‚ â”‚   Catalog   â”‚
       â”‚   (Router)   â”‚ â”‚  Queue â”‚ â”‚   Manager   â”‚
       â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”¬â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚             â”‚
              â”‚      â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”
              â”‚      â”‚  Admin API  â”‚
              â”‚      â”‚  (Dashboard)â”‚
              â”‚      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
       â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
       â”‚  LLM Router â”‚     â”‚    Hermes     â”‚
       â”‚  (9router)  â”‚â—„â”€â”€â”€â”€â”‚   Bridge      â”‚
       â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              â–¼
         LLM Providers
    (OpenRouter, Anthropic, DeepSeek, etc.)
```

## Core Components

### 1. Channel Adapters (`app/channels/`)

Each channel implements the `ChannelAdapter` protocol:
- `parse_incoming(payload) -> IncomingMessage | None`
- `send(recipient_id, text, ...) -> OutboundResult`
- `notify_admins(text)`

**Channels:**
- **Telegram** â€” aiogram-based, webhook mode, HTML parse mode
- **WhatsApp** â€” Meta Cloud API or Twilio provider, selectable via config
- **Email** â€” Resend for outbound, SendGrid webhook or IMAP for inbound

### 2. Conversation Pipeline (`app/core/pipeline.py`)

```
Incoming â†’ Dedup â†’ Rate Limit â†’ Session Load â†’ Orchestrator â†’ LLM â†’ Tools â†’ HITL Check â†’ Outbound
```

- **Deduplication**: Redis key `dedup:{channel}:{ext_ref}` with TTL
- **Rate Limiting**: Sliding window via Redis sorted set (Lua script)
- **Session Management**: Per-conversation context in Redis
- **Orchestrator**: Routes to specialized skills based on intent classification

### 3. Skill System

| Skill | Purpose |
|-------|---------|
| `orchestrator` | Intent classification, routing |
| `knowledge_agent` | Product knowledge, FAQs, troubleshooting |
| `customer_agent` | Customer info, greetings, general |
| `sales_agent` | Quotes, pricing, order placement |
| `support_agent` | Tickets, issue tracking, escalation |
| `analytics_agent` | Reporting, data queries |

### 4. Human-in-the-Loop (HITL)

When the agent encounters a **mutating tool** (create_quote, create_ticket, etc.), it creates an approval request:

1. Approval is stored in Redis (`hitl:meta:{id}`) and Postgres (`approvals`)
2. Admin receives notification via Telegram ping
3. Admin reviews in dashboard or via Telegram inline buttons
4. Decision is applied atomically via Lua script
5. If no decision within `HITL_TIMEOUT_SECONDS`, the sweeper applies fallback policy

**Fallback policies:**
- `auto_ack`: Automatically approve after timeout
- `silent`: Silently discard the pending action

### 5. LLM Router (`9router`)

Three modes:
- **router**: All requests go through 9router (port 20128) for load balancing, failover, and cost tracking
- **direct**: Direct connection to a single LLM provider
- **mock**: Testing mode (not allowed in production)

### 6. Hermes Bridge

Node.js sidecar that provides:
- Hermes runtime integration
- HTTP adapter for function calling
- Response streaming

### 7. Admin Dashboard (`admin/` + `app/admin_api/`)

**Authentication:**
- argon2id password hashing
- itsdangerous session tokens (7-day expiry)
- Cookie-based (httponly, secure, samesite=lax)
- Bearer token fallback for API access

**API endpoints:**
- `/admin/api/auth/*` â€” login, logout, session
- `/admin/api/approvals/*` â€” HITL queue management
- `/admin/api/stream` â€” SSE real-time updates
- `/admin/api/catalog/*` â€” Product CRUD + import
- `/admin/api/customers/*` â€” Customer management
- `/admin/api/quotes/*` â€” Quote management
- `/admin/api/tickets/*` â€” Ticket management
- `/admin/api/analytics/*` â€” Reports and metrics
- `/admin/api/audit/*` â€” Audit trail
- `/admin/api/templates/*` â€” Fallback templates
- `/admin/api/twa/*` â€” Telegram Web App login

### 8. Storage Layer

| Store | Purpose |
|-------|---------|
| **PostgreSQL** | Persistent data: 16 tables |
| **Redis** | Sessions, rate limits, HITL queue, event bus, dedup |
| **Cloudflare R2** | File storage: transcripts, attachments, quotes, reports, backups |

### 9. Database Schema (16 Tables)

```
admins           â†’ Authentication and authorization
customers        â†’ Customer profiles and lead scoring
products         â†’ Oil industry product catalog
conversations    â†’ Multi-channel conversation tracking
messages         â†’ Message history with attachments
approvals        â†’ HITL approval queue
approval_execution_ledger â†’ Decision audit trail
quotes           â†’ Price quotations
tickets          â†’ Support tickets
ticket_notes     â†’ Ticket annotations
orders_imports   â†’ CSV/JSON import staging
orders           â†’ Confirmed orders
audit_log        â†’ Full audit trail
fallback_templates â†’ Auto-response templates
faq              â†’ Frequently asked questions
troubleshooting  â†’ Troubleshooting knowledge base
settings         â†’ Runtime configuration
```

### 10. Deployment

- **Railway** â€” Primary PaaS deployment
- **Docker Compose** â€” Local development and self-hosting
- **GitHub Actions** â€” CI pipeline (lint, typecheck, test, build)

## Security

- All secrets are at least 16 characters (auto-generated if empty)
- Passwords hashed with argon2id (time_cost=3, memory_cost=64MB, parallelism=2)
- Session tokens signed with itsdangerous (HMAC-SHA256)
- Cookie flags: httponly, secure, samesite=lax
- TOTP 2FA support (optional, via TOTP_ENABLED)
- Rate limiting per channel per user
- Audit log for all mutations
- Secret scanning in CI pipeline

## Arabic-First Design

- Default language: Modern Standard Arabic (Fusha)
- Arabic-Indic numerals by default (configurable)
- RTL-aware message formatting
- Arabic product names and descriptions
- Arabic admin dashboard
- Language policy configurable per deployment
