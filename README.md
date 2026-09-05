<div align="center">

<br/>

<img src="https://img.shields.io/badge/Kia--Agent-Platform-d97757?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6bTAgN0wyIDE0bDEwIDUgMTAtNXoiLz48L3N2Zz4=" alt="Kia-Agent" height="40"/>

<br/><br/>

# ⚡ Kia-Agent Platform

### Your entire digital operation. One AI team. Zero missed messages.

<br/>

[![Version](https://img.shields.io/badge/version-20.0.0-d97757?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Proprietary-1f2937?style=for-the-badge)](#-license)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](#-testing)
[![Coverage](https://img.shields.io/badge/coverage-84%25-2dd4bf?style=for-the-badge)](#-testing)
[![Status](https://img.shields.io/badge/status-production--ready-7c5cff?style=for-the-badge)](#)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.app/)
[![Ruff](https://img.shields.io/badge/ruff-checked-D7FF64?style=flat-square)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-typed-blue?style=flat-square)](https://mypy-lang.org/)
[![i18n](https://img.shields.io/badge/i18n-20%20languages-f59e0b?style=flat-square)](#️-languages)
[![Channels](https://img.shields.io/badge/channels-5-ec4899?style=flat-square)](#-communication-channels)
[![HITL](https://img.shields.io/badge/HITL-6--layer-8b5cf6?style=flat-square)](#-human-in-the-loop-hitl)

<br/>

**Kia-Agent** is a production-grade, multi-agent AI platform that runs the day-to-day digital operations of your business — email, website, social media, sales, support and internal tasks — across **5 channels** and **20 languages**, while keeping a human firmly in the loop for everything that matters.

<br/>

[🚀 Quick Start](#-quick-start) · [✨ Features](#-features) · [🏗️ Architecture](#️-architecture) · [📡 API](#-api-reference) · [☁️ Deploy](#️-deployment) · [❓ FAQ](#-faq)

<br/>

</div>

---

## 🧭 Why Kia-Agent?

Every growing company hits the same wall: **100–500 inbound messages a day**, spread across Telegram, WhatsApp, email, Instagram and X — in three, four, five different languages. Someone has to read them, classify them, answer the pricing questions, register the leads, open the tickets, schedule the follow-ups and publish this week's posts.

Usually that "someone" is your most expensive people.

Kia-Agent replaces that wall with an **orchestrated team of five specialised AI agents**. It answers, quotes, registers orders, opens tickets, schedules content and writes your daily report — and escalates **only the sensitive decisions** to a human manager through a 6-layer approval system.

<table>
<tr>
<td width="50%" valign="top">

### 😩 Before

- ⏱️ First response: **2–8 hours**
- 🌍 Languages covered: **1–2**
- 📥 Messages touched by humans: **100%**
- 🧾 Quotes: **manual, next day**
- 📊 Daily ops report: **nobody has time**
- 🔁 Follow-ups: **forgotten**

</td>
<td width="50%" valign="top">

### 🚀 With Kia-Agent

- ⏱️ First response: **< 30 seconds**
- 🌍 Languages covered: **20**
- 📥 Messages touched by humans: **~15%** (sensitive only)
- 🧾 Quotes: **instant, catalog-driven**
- 📊 Daily ops report: **every morning, automatically**
- 🔁 Follow-ups: **24h → 48h → 72h, guaranteed**

</td>
</tr>
</table>

> 🎯 **Built for SMBs** in oil & gas, manufacturing, services and trade.
> 📦 Ships as **SaaS**, **white-label**, or **per-license** on your own infrastructure.
> ✅ **v20.0.0 — 100% feature complete, production-ready.**

---

## 📚 Table of Contents

<details>
<summary><b>Click to expand</b></summary>

- [🧭 Why Kia-Agent?](#-why-kia-agent)
- [✨ Features](#-features)
  - [🤖 AI & Agents](#-ai--agents)
  - [📱 Communication Channels](#-communication-channels)
  - [🌍 Internationalization](#-internationalization)
  - [📧 Smart Email](#-smart-email)
  - [📣 Social Media](#-social-media)
  - [🛒 Sales & CRM](#-sales--crm)
  - [📝 CMS & Content](#-cms--content)
  - [👥 Team Coordination](#-team-coordination)
  - [🔔 Reminders & Calendar](#-reminders--calendar)
  - [📈 Reporting](#-reporting)
  - [🔒 Security & Access Control](#-security--access-control)
  - [✅ Quality & Automation](#-quality--automation)
- [🏗️ Architecture](#️-architecture)
  - [System Diagram](#system-diagram)
  - [How a Message Travels](#how-a-message-travels)
  - [Human-in-the-Loop (HITL)](#-human-in-the-loop-hitl)
  - [Project Structure](#project-structure)
- [🚀 Quick Start](#-quick-start)
- [🧰 Tech Stack](#-tech-stack)
- [🔧 Environment Variables](#-environment-variables)
- [📡 API Reference](#-api-reference)
- [🗣️ Languages](#️-languages)
- [☁️ Deployment](#️-deployment)
- [🧪 Testing](#-testing)
- [🛡️ Security](#️-security)
- [❓ FAQ](#-faq)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

</details>

---

## ✨ Features

### 🤖 AI & Agents

| Capability | Description |
|---|---|
| 🧠 **Central Orchestrator** | Intent classification + skill routing sends every message to the right agent |
| 👥 **5 Specialised Agents** | `Knowledge` · `Customer` · `Sales` · `Support` · `Analytics` — each with its own prompts, tools and guardrails |
| 🚢 **Fleet Coordination** | Multi-agent teams with explicit role assignment for complex, multi-step requests |
| 🔮 **Hermes LLM Client** | OpenAI-compatible with automatic **provider failover** (OpenRouter → direct → Hermes bridge) |
| ⚡ **Prompt Cache** | Cuts latency and tokens on repeated system prompts |
| 🧬 **Long-Term Memory** | Per-customer persona generation that survives across sessions |
| 📚 **RAG** | Retrieval-augmented answers grounded in your catalog, docs and policies |
| 🧹 **Post-Processing** | Text normalization, RTL fixes, platform-aware truncation |

### 📱 Communication Channels

| Channel | Provider(s) | Capabilities |
|---|---|---|
| ✈️ **Telegram** | aiogram 3.x | Bot, inline keyboards, webhooks, callback handling, TWA login |
| 💬 **WhatsApp** | Meta Cloud API · Twilio | Inbound/outbound messages, templates, media |
| 📧 **Email** | Resend · SendGrid · IMAP | Outbound sending, inbound polling, threading |
| 📸 **Instagram** | Graph API | Publish, reply to comments, reply to DMs, engagement metrics |
| 🐦 **Twitter / X** | API v2 | Publish, reply, mentions, search, analytics |

### 🌍 Internationalization

- ✅ **20 languages** out of the box → see [Languages](#️-languages)
- ✅ Full **RTL** support for Arabic and Hebrew
- ✅ Language picker with flags on `/start`
- ✅ **100% of UI strings translated** — menus, help, errors, agent responses
- ✅ Agents auto-detect and reply in the customer's language

### 📧 Smart Email

- 🗂️ **Automatic triage** into 8 deterministic categories
- 🤖 **Auto-reply** for the 10 most common questions:
  `pricing` · `stock` · `shipping` · `meeting` · `catalog` · `warranty` · `payment` · `MOQ` · `samples` · `technical support`
- 🔁 **Follow-up engine** with 3 rule sets → `standard` · `urgent` · `sales`
- 🚨 **Escalation chain** at **24h → 48h → 72h** with no response

### 📣 Social Media

- 📅 **Content calendar** with scheduled publishing
- 🔌 Instagram + Twitter/X adapters behind a common interface
- ⏰ **Auto-publish** at the scheduled time via the cron scheduler
- 📊 Engagement reporting per post and per platform
- ✂️ Platform-specific character limits enforced *before* publish

### 🛒 Sales & CRM

- 🎯 **Smart lead registration** using **BANT** (Budget · Authority · Need · Timeline)
- 🧾 **Auto quote generation** from the product catalog
- 🔍 Product catalog with full-text search
- 👤 Customer management with history and persona
- 🎫 Ticket system with priority and SLA tracking

### 📝 CMS & Content

- 🗃️ Lightweight CMS with **version control**
- 👁️ Page preview and one-click **revert**
- ✅ **Publish workflow** gated by HITL approval
- 🏷️ Meta tags and SEO fields per page

### 👥 Team Coordination

- 📌 Task assignment with **assignee + department**
- 🔗 Cross-linking between related tasks, tickets and leads
- ⏫ **Auto-escalation** for overdue tasks
- 🖥️ Team overview dashboard

### 🔔 Reminders & Calendar

- ⏰ Smart reminders with repeat → `none` · `daily` · `weekly` · `monthly`
- 😴 Snooze and cancel from any channel
- 📆 **Google Calendar API** integration
- 🔄 Two-way task ↔ calendar sync

### 📈 Reporting

- 📄 Daily, weekly, email and website reports
- ⏲️ Cron scheduler for periodic delivery
- 📡 **SSE stream** for real-time dashboard updates

### 🔒 Security & Access Control

| Layer | Implementation |
|---|---|
| 🪪 **RBAC** | 3 levels → `admin` · `associate` · `viewer` |
| 🧑‍⚖️ **HITL** | 6-layer approval backed by Redis atomic ops + Lua scripts + Postgres ledger |
| 🛡️ **Guard** | 3-layer input/output prompt-injection protection |
| 🚦 **Rate limiting** | Per-user token bucket (atomic Lua) |
| 📜 **Audit trail** | Immutable log for every mutation |
| 🔐 **2FA** | Optional TOTP for admin accounts |
| 📲 **TWA login** | Telegram Web App authentication |
| 🍪 **Cookies** | `HttpOnly` · `Secure` · `SameSite=Strict` |
| 🔑 **Passwords** | Argon2id hashing (OWASP parameters) |

### ✅ Quality & Automation

- 🎯 **QA Engine** scores every response on *clarity · tone · accuracy · completeness · safety*
- ✍️ **Auto-rewrite** when a response falls below threshold
- ⚙️ **Automation rules**: `trigger → condition → action`
- 📦 4 pre-built templates → `auto-reply` · `escalation` · `auto-tag` · `form-to-ticket`

---

## 🏗️ Architecture

Kia-Agent is an **event-driven system built on Redis Streams**. Every inbound message flows through a deterministic pipeline before reaching the orchestrator, and every outbound action flows through the HITL gate before reaching a channel.

### System Diagram

```text
                        ┌─────────────────────────────────────────────────────────────┐
                        │                        CHANNELS                             │
                        │  ✈️ Telegram   💬 WhatsApp   📧 Email   📸 Instagram   🐦 X   │
                        └───────┬───────────┬──────────┬───────────┬───────────┬──────┘
                                │           │          │           │           │
                                ▼           ▼          ▼           ▼           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                          INGEST PIPELINE  (Redis Streams · consumer groups)              │
│                                                                                          │
│   ingest ─▶ dedup ─▶ rate-limit ─▶ store ─▶ publish ─▶ dispatch ─▶ orchestrator ─▶ respond │
│                                                                                          │
└──────────────────────────────────────────┬───────────────────────────────────────────────┘
                                           │
                                           ▼
                   ┌───────────────────────────────────────────────────┐
                   │          🛡️ GUARD  —  3-layer input filter         │
                   └───────────────────────┬───────────────────────────┘
                                           │
                                           ▼
   ┌───────────────────────────────────────────────────────────────────────────────┐
   │                              🧠 ORCHESTRATOR                                  │
   │              intent classification  ·  skill routing  ·  memory               │
   │                                                                               │
   │   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
   │   │ Knowledge │ │ Customer  │ │  Sales    │ │  Support  │ │ Analytics │       │
   │   │   Agent   │ │   Agent   │ │   Agent   │ │   Agent   │ │   Agent   │       │
   │   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘       │
   │         └─────────────┴──────┬──────┴─────────────┴─────────────┘             │
   │                              │  🚢 Fleet Coordinator (multi-agent teams)      │
   └──────────────────────────────┼────────────────────────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
    ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
    │ 🔮 Hermes LLM    │ │ 📚 RAG Store     │ │ ⚡ Prompt Cache  │
    │  (failover)      │ │  (R2 / Postgres) │ │  (Redis)         │
    └──────────────────┘ └──────────────────┘ └──────────────────┘
                                  │
                                  ▼
                   ┌───────────────────────────────────┐
                   │   ✅ QA ENGINE  (score + rewrite)   │
                   └───────────────┬───────────────────┘
                                   ▼
                   ┌───────────────────────────────────┐
                   │   🛡️ GUARD  —  output filter       │
                   └───────────────┬───────────────────┘
                                   ▼
        ┌────────────────────────────────────────────────────────────┐
        │              🧑‍⚖️ HITL — 6-Layer Human-in-the-Loop           │
        │  policy ─▶ risk score ─▶ RBAC ─▶ Redis lock (Lua) ─▶ ledger │
        │                      ─▶ human decision                     │
        └────────────────────────────┬───────────────────────────────┘
                                     ▼
          ┌──────────────────────────────────────────────────────┐
          │   ⚙️ AUTOMATION ENGINE  (trigger → condition → action) │
          └──────────────────────────┬───────────────────────────┘
                                     ▼
              ┌───────────────────────────────────────────────┐
              │  📤 Channel Adapters  ·  📊 Reports  ·  📅 Calendar │
              └───────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────────────────┐
   │  🗄️ STORAGE   PostgreSQL (asyncpg)  ·  Redis (hiredis + Lua)  ·  R2 / S3    │
   │  🖥️ ADMIN     FastAPI  ·  21 API modules  ·  SSE dashboard  ·  RBAC + 2FA   │
   └─────────────────────────────────────────────────────────────────────────────┘
```

### How a Message Travels

| # | Stage | What happens |
|:---:|---|---|
| 1 | **Ingest** | A channel adapter normalises the raw payload into a `Message` event and pushes it to the `kia:inbound` stream |
| 2 | **Dedup** | Provider IDs are checked against a Redis set with rolling TTL — retried webhooks never double-process |
| 3 | **Rate limit** | Per-user token bucket implemented as a Lua script (atomic, no race conditions) |
| 4 | **Store** | The message is persisted to Postgres **before** any AI work. Nothing is ever lost |
| 5 | **Publish / Dispatch** | Consumer groups pick up the event — horizontal scaling = start more workers |
| 6 | **Orchestrator** | Intent classified, memory loaded, routed to an agent (or a Fleet team) |
| 7 | **QA + Guard** | Draft is scored and filtered; low scores trigger an auto-rewrite |
| 8 | **HITL** | Low-risk replies go out instantly; high-risk actions wait for human approval |
| 9 | **Respond** | Adapter formats for the platform (limits, RTL, keyboards) and sends |

### 🧑‍⚖️ Human-in-the-Loop (HITL)

The HITL system is the reason Kia-Agent can be trusted with real money and real customers. Every outbound **action** (not just replies) passes through six independent layers:

| Layer | Name | Purpose | Backed by |
|:---:|---|---|---|
| 1 | **Policy** | Declarative YAML rules: which action types *always* need approval | `config/hitl.yaml` |
| 2 | **Risk Score** | LLM + heuristics score the action 0–1 (amount, sentiment, novelty, customer tier) | Analytics agent |
| 3 | **RBAC Gate** | Which role may approve this action class | Postgres `roles` |
| 4 | **Atomic Lock** | Exactly-once claim of the approval by a single reviewer | Redis Lua script |
| 5 | **Ledger** | Append-only record of request → decision → dispatch | Postgres `hitl_ledger` |
| 6 | **Human Decision** | Approve / reject / edit from Telegram inline buttons or the admin dashboard | Any channel |

> 💡 If any layer fails closed (e.g. Redis unavailable), the action is **held**, never auto-sent.

### Project Structure

```text
kia-agent/
├── app/
│   ├── core/                  # 43 core modules
│   │   ├── orchestrator.py    # routing + intent classification
│   │   ├── agents/            # knowledge · customer · sales · support · analytics
│   │   ├── fleet/             # multi-agent team coordination
│   │   ├── hitl/              # 6-layer approval, Lua scripts, ledger
│   │   ├── pipeline/          # Redis Streams stages
│   │   ├── guard/             # input/output injection protection
│   │   ├── qa/                # response scoring + rewrite
│   │   ├── automation/        # rules engine + templates
│   │   ├── llm/               # Hermes client, failover, prompt cache
│   │   ├── memory/            # long-term memory + persona
│   │   ├── rag/               # retrieval
│   │   └── i18n/              # 20 locale files
│   ├── channels/              # 5 adapters
│   │   ├── telegram/
│   │   ├── whatsapp/
│   │   ├── email/
│   │   ├── instagram/
│   │   └── twitter/
│   ├── admin/                 # 21 admin API modules (FastAPI routers)
│   ├── storage/               # 7 storage modules (postgres · redis · r2 · …)
│   ├── scheduler/             # cron, reminders, follow-ups, content calendar
│   ├── reports/               # daily · weekly · email · website
│   └── main.py                # FastAPI app factory
├── migrations/                # 12 SQL migrations
├── tests/                     # 54 test files (unit + integration)
├── config/                    # YAML config + automation templates
├── scripts/                   # secret scanner, config lint, seeders
├── docker/
├── .github/workflows/         # lint · typecheck · test · config-lint · secret-scan
├── docker-compose.yml
├── Dockerfile
├── railway.json
├── pyproject.toml
└── README.md
```

<div align="center">

| 🐍 Python files | 📁 Total files | 📏 Lines of code | 🧩 Core modules | 🖥️ Admin APIs | 📡 Channels | 🗄️ Storage | 🧬 Migrations | 🧪 Test files |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **175** | **249** | **~46,500** | **43** | **21** | **5** | **7** | **12** | **54** |

</div>

---

## 🚀 Quick Start

> ⏱️ Get a local instance running in **under five minutes**.

### Requirements

| Dependency | Minimum | Recommended |
|---|:---:|:---:|
| 🐍 Python | 3.11 | 3.12 |
| 🐘 PostgreSQL | 14 | 16 |
| 🟥 Redis | 7 | 7.2 |
| 🐳 Docker *(optional)* | 24 | latest |

### 1️⃣ Clone & install

```bash
git clone https://github.com/kia-agent/kia-agent-platform.git
cd kia-agent-platform

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e ".[dev]"
```

### 2️⃣ Configure

```bash
cp .env.example .env
```

Set at minimum:

```dotenv
DATABASE_URL=postgresql://kia:kia@localhost:5432/kia_agent
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=sk-or-...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-sonnet
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
PUBLIC_BASE_URL=https://your-tunnel.example.com
ADMIN_SECRET_KEY=change-me   # openssl rand -hex 32
```

👉 Full reference: [Environment Variables](#-environment-variables)

### 3️⃣ Start the databases

```bash
docker compose up -d postgres redis
```

### 4️⃣ Migrate & seed an admin

```bash
kia migrate up
kia admin create --email you@company.com --role admin
```

### 5️⃣ Launch

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --port 8000

# Production
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
```

### 6️⃣ Verify

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "version": "20.0.0",
  "postgres": "up",
  "redis": "up",
  "llm": "up",
  "channels": ["telegram"]
}
```

🎉 Open Telegram, send `/start` to your bot, pick a language — you're talking to Kia-Agent.

<details>
<summary><b>🛠️ Useful CLI commands</b></summary>

```bash
kia --help
kia migrate up | down | status
kia admin create | list | reset-password
kia worker --group pipeline --concurrency 8
kia scheduler
kia webhooks register --channel <telegram|whatsapp|instagram>
kia webhooks status
kia catalog import products.csv
kia i18n check
kia report run --type daily
```

</details>

---

## 🧰 Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Language** | Python 3.12 | Fully async, typed |
| **Web framework** | FastAPI · uvicorn · gunicorn | OpenAPI docs at `/docs` |
| **Database** | PostgreSQL 14+ via `asyncpg` | 12 versioned SQL migrations |
| **Cache / Streams** | Redis 7 via `hiredis` + Lua | Streams, locks, rate limits, prompt cache |
| **LLM** | OpenAI-compatible API | OpenRouter · direct · Hermes bridge, with failover |
| **Object storage** | Cloudflare R2 / S3-compatible | Documents, media, RAG sources |
| **Telegram** | aiogram 3.x | Webhook mode, inline keyboards, TWA |
| **HTTP client** | httpx | WhatsApp, Email, Instagram, Twitter |
| **Password hashing** | argon2-cffi | OWASP-recommended parameters |
| **Config** | python-dotenv · PyYAML | Env + YAML overlays |
| **Linting** | ruff | `E F W I N UP B A SIM TCH` |
| **Type checking** | mypy | Relaxed strict mode |
| **Testing** | pytest · pytest-asyncio · pytest-cov | 54 test files |
| **Security scanning** | bandit · custom secret scanner | Runs on every push |
| **CI/CD** | GitHub Actions | lint → typecheck → test → config-lint → secret-scan |
| **Containers** | Docker multi-stage | ~180 MB final image, non-root |
| **PaaS** | Railway | One-click deploy template |

---

## 🔧 Environment Variables

All configuration is via environment variables (12-factor). Variables marked ✅ must be set for the service to boot.

<details open>
<summary><b>🏠 Core</b></summary>

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `APP_ENV` | | `production` | `development` · `staging` · `production` |
| `APP_NAME` | | `Kia-Agent` | Shown in UI and outbound messages |
| `LOG_LEVEL` | | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |
| `PORT` | | `8000` | HTTP port |
| `PUBLIC_BASE_URL` | ✅ | — | Public HTTPS URL used for webhooks |
| `ADMIN_SECRET_KEY` | ✅ | — | 32+ byte secret for sessions and tokens |
| `DEFAULT_LANGUAGE` | | `en` | Fallback locale code |
| `TIMEZONE` | | `UTC` | IANA timezone for schedulers and reports |
| `RUN_MIGRATIONS_ON_START` | | `false` | Auto-migrate on boot (Railway-friendly) |

</details>

<details>
<summary><b>🗄️ Storage</b></summary>

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `DATABASE_URL` | ✅ | — | `postgresql://user:pass@host:5432/db` |
| `DATABASE_POOL_MIN` | | `2` | asyncpg pool minimum |
| `DATABASE_POOL_MAX` | | `20` | asyncpg pool maximum |
| `REDIS_URL` | ✅ | — | `redis://host:6379/0` |
| `REDIS_STREAM_PREFIX` | | `kia` | Namespace for streams and keys |
| `R2_ACCOUNT_ID` | | — | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | | — | R2 / S3 access key |
| `R2_SECRET_ACCESS_KEY` | | — | R2 / S3 secret key |
| `R2_BUCKET` | | `kia-agent` | Bucket name |
| `S3_ENDPOINT_URL` | | — | Override for any S3-compatible provider |

</details>

<details>
<summary><b>🔮 LLM</b></summary>

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `LLM_PROVIDER` | | `openrouter` | `openrouter` · `direct` · `hermes` |
| `LLM_API_KEY` | ✅ | — | API key for the primary provider |
| `LLM_BASE_URL` | | `https://openrouter.ai/api/v1` | OpenAI-compatible base URL |
| `LLM_MODEL` | | `anthropic/claude-sonnet` | Primary model |
| `LLM_FALLBACK_MODEL` | | — | Used when the primary fails |
| `LLM_FALLBACK_API_KEY` | | — | Key for fallback provider |
| `LLM_FALLBACK_BASE_URL` | | — | Base URL for fallback provider |
| `HERMES_BRIDGE_URL` | | — | Hermes bridge endpoint |
| `LLM_TIMEOUT_SECONDS` | | `45` | Per-request timeout |
| `LLM_MAX_TOKENS` | | `2048` | Max completion tokens |
| `PROMPT_CACHE_TTL` | | `3600` | Seconds to cache system prompts |

</details>

<details>
<summary><b>📱 Channels</b></summary>

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `TELEGRAM_BOT_TOKEN` | | — | Token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | | — | Secret token for webhook verification |
| `TELEGRAM_ADMIN_IDS` | | — | Comma-separated admin chat IDs |
| `WHATSAPP_PROVIDER` | | `meta` | `meta` · `twilio` |
| `WHATSAPP_ACCESS_TOKEN` | | — | Meta Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | | — | Meta phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | | — | Webhook verify token |
| `TWILIO_ACCOUNT_SID` | | — | Twilio SID (if provider = twilio) |
| `TWILIO_AUTH_TOKEN` | | — | Twilio auth token |
| `TWILIO_WHATSAPP_FROM` | | — | `whatsapp:+1415...` |
| `EMAIL_PROVIDER` | | `resend` | `resend` · `sendgrid` |
| `RESEND_API_KEY` | | — | Resend API key |
| `SENDGRID_API_KEY` | | — | SendGrid API key |
| `EMAIL_FROM` | | — | `Kia-Agent <ops@company.com>` |
| `IMAP_HOST` | | — | Inbound IMAP host |
| `IMAP_PORT` | | `993` | IMAP port |
| `IMAP_USER` | | — | IMAP username |
| `IMAP_PASSWORD` | | — | IMAP password / app password |
| `IMAP_POLL_SECONDS` | | `60` | Inbound polling interval |
| `INSTAGRAM_ACCESS_TOKEN` | | — | Graph API long-lived token |
| `INSTAGRAM_BUSINESS_ID` | | — | IG business account ID |
| `TWITTER_BEARER_TOKEN` | | — | X API v2 bearer token |
| `TWITTER_API_KEY` | | — | Consumer key |
| `TWITTER_API_SECRET` | | — | Consumer secret |
| `TWITTER_ACCESS_TOKEN` | | — | User access token |
| `TWITTER_ACCESS_SECRET` | | — | User access secret |

</details>

<details>
<summary><b>🔒 Security & HITL</b></summary>

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `RATE_LIMIT_PER_MINUTE` | | `30` | Per-user inbound message limit |
| `HITL_QUOTE_THRESHOLD` | | `5000` | Quotes above this amount require approval |
| `HITL_APPROVAL_TTL_HOURS` | | `24` | Pending approvals expire after this |
| `HITL_ESCALATION_HOURS` | | `24,48,72` | Escalation chain checkpoints |
| `GUARD_STRICT_MODE` | | `true` | Reject on suspected injection instead of sanitising |
| `QA_MIN_SCORE` | | `0.75` | Responses below this are auto-rewritten |
| `QA_MAX_REWRITES` | | `2` | Rewrite attempts before human escalation |
| `TOTP_ENABLED` | | `false` | Enforce 2FA for admin users |
| `COOKIE_SECURE` | | `true` | Set `false` only for local HTTP dev |
| `CORS_ORIGINS` | | — | Comma-separated allowed origins |

</details>

<details>
<summary><b>🔌 Integrations</b></summary>

| Variable | Required | Default | Description |
|---|:---:|---|---|
| `GOOGLE_CALENDAR_CREDENTIALS_JSON` | | — | Service account JSON (base64) |
| `GOOGLE_CALENDAR_ID` | | `primary` | Target calendar |
| `REPORT_DAILY_CRON` | | `0 7 * * *` | Daily report schedule |
| `REPORT_WEEKLY_CRON` | | `0 8 * * 1` | Weekly report schedule |
| `REPORT_RECIPIENTS` | | — | Comma-separated emails |

</details>

---

## 📡 API Reference

The admin API is served under `/api/v1/admin` and documented interactively at **`/docs`** (Swagger) and **`/redoc`**. All endpoints require a bearer token or session cookie and are subject to RBAC.

### System endpoints

| Method | Path | Auth | Description |
|---|---|:---:|---|
| `GET` | `/health` | — | Liveness + dependency status |
| `GET` | `/ready` | — | Readiness probe (migrations applied, streams consumed) |
| `GET` | `/metrics` | viewer | Prometheus-style metrics |
| `GET` | `/api/v1/admin/stream` | viewer | **SSE** real-time event stream for the dashboard |

### Admin API modules (21)

| # | Module | Base path | Key endpoints | Min role |
|:---:|---|---|---|:---:|
| 1 | 🔐 **Auth** | `/auth` | `POST /login` · `POST /logout` · `POST /totp/enable` · `POST /twa` | — |
| 2 | 👤 **Users** | `/users` | `GET /` · `POST /` · `PATCH /{id}` · `DELETE /{id}` | admin |
| 3 | 🪪 **Roles** | `/roles` | `GET /` · `PUT /{user_id}` | admin |
| 4 | 💬 **Conversations** | `/conversations` | `GET /` · `GET /{id}` · `POST /{id}/takeover` · `POST /{id}/release` | associate |
| 5 | ✉️ **Messages** | `/messages` | `GET /` · `POST /send` · `GET /{id}` | associate |
| 6 | 🧑‍⚖️ **Approvals (HITL)** | `/approvals` | `GET /pending` · `POST /{id}/approve` · `POST /{id}/reject` · `GET /ledger` | associate |
| 7 | 🧑‍💼 **Customers** | `/customers` | `GET /` · `POST /` · `GET /{id}` · `PATCH /{id}` · `GET /{id}/persona` | associate |
| 8 | 🎯 **Leads** | `/leads` | `GET /` · `POST /` · `PATCH /{id}` · `POST /{id}/qualify` | associate |
| 9 | 🧾 **Quotes** | `/quotes` | `GET /` · `POST /generate` · `GET /{id}` · `POST /{id}/send` | associate |
| 10 | 📦 **Products** | `/products` | `GET /` · `POST /` · `PATCH /{id}` · `GET /search` · `POST /import` | associate |
| 11 | 🎫 **Tickets** | `/tickets` | `GET /` · `POST /` · `PATCH /{id}` · `POST /{id}/assign` · `POST /{id}/close` | associate |
| 12 | ✅ **Tasks** | `/tasks` | `GET /` · `POST /` · `PATCH /{id}` · `POST /{id}/link` · `GET /overview` | associate |
| 13 | ⏰ **Reminders** | `/reminders` | `GET /` · `POST /` · `POST /{id}/snooze` · `DELETE /{id}` | associate |
| 14 | 📆 **Calendar** | `/calendar` | `GET /events` · `POST /sync` · `POST /events` | associate |
| 15 | 📧 **Email** | `/email` | `GET /inbox` · `POST /triage/{id}` · `GET /followups` · `POST /rules` | associate |
| 16 | 📣 **Social** | `/social` | `GET /calendar` · `POST /posts` · `POST /posts/{id}/publish` · `GET /engagement` | associate |
| 17 | 📝 **CMS** | `/cms` | `GET /pages` · `POST /pages` · `GET /pages/{id}/versions` · `POST /pages/{id}/revert` · `POST /pages/{id}/publish` | associate |
| 18 | ⚙️ **Automation** | `/automation` | `GET /rules` · `POST /rules` · `PATCH /rules/{id}` · `GET /templates` · `POST /rules/{id}/test` | admin |
| 19 | 🎯 **QA** | `/qa` | `GET /scores` · `GET /scores/{message_id}` · `POST /rescore/{message_id}` | viewer |
| 20 | 📈 **Reports** | `/reports` | `GET /daily` · `GET /weekly` · `GET /email` · `GET /website` · `POST /run` | viewer |
| 21 | 📜 **Audit** | `/audit` | `GET /` · `GET /{id}` · `GET /export` | admin |

### Example — approve a pending quote

```bash
curl -X POST https://your-host/api/v1/admin/approvals/apr_01J9K3.../approve \
  -H "Authorization: Bearer $KIA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note": "Discount OK, ship priority"}'
```

```json
{
  "id": "apr_01J9K3...",
  "status": "approved",
  "layer": 6,
  "decided_by": "usr_admin_01",
  "ledger_seq": 48213,
  "action_dispatched": true
}
```

### Example — generate a quote

```bash
curl -X POST https://your-host/api/v1/admin/quotes/generate \
  -H "Authorization: Bearer $KIA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cus_01HZX...",
    "items": [{"sku": "PMP-4400", "qty": 12}],
    "currency": "USD",
    "language": "ar"
  }'
```

### Example — subscribe to the live stream

```javascript
const es = new EventSource("/api/v1/admin/stream", { withCredentials: true });

es.addEventListener("message.inbound",  e => console.log(JSON.parse(e.data)));
es.addEventListener("approval.pending", e => console.log(JSON.parse(e.data)));
es.addEventListener("qa.scored",        e => console.log(JSON.parse(e.data)));
es.addEventListener("ticket.created",   e => console.log(JSON.parse(e.data)));
```

---

## 🗣️ Languages

Kia-Agent ships with **20 fully translated locales**. Customers pick their language on `/start`; agents detect and respond in the customer's language automatically.

| Flag | Language | Code | Dir | | Flag | Language | Code | Dir |
|:---:|---|:---:|:---:|---|:---:|---|:---:|:---:|
| 🇬🇧 | English | `en` | LTR | | 🇳🇱 | Dutch | `nl` | LTR |
| 🇸🇦 | Arabic | `ar` | **RTL** | | 🇺🇦 | Ukrainian | `uk` | LTR |
| 🇪🇸 | Spanish | `es` | LTR | | 🇸🇪 | Swedish | `sv` | LTR |
| 🇫🇷 | French | `fr` | LTR | | 🇮🇩 | Indonesian | `id` | LTR |
| 🇩🇪 | German | `de` | LTR | | 🇲🇾 | Malay | `ms` | LTR |
| 🇮🇹 | Italian | `it` | LTR | | 🇻🇳 | Vietnamese | `vi` | LTR |
| 🇵🇹 | Portuguese | `pt` | LTR | | 🇮🇱 | Hebrew | `he` | **RTL** |
| 🇹🇷 | Turkish | `tr` | LTR | | 🇷🇺 | Russian | `ru` | LTR |
| 🇨🇳 | Chinese | `zh` | LTR | | 🇯🇵 | Japanese | `ja` | LTR |
| 🇰🇷 | Korean | `ko` | LTR | | 🇮🇳 | Hindi | `hi` | LTR |

> ➕ Adding a language is a single YAML file in `app/core/i18n/locales/` — the `config-lint` CI step verifies every key is present.

---

## ☁️ Deployment

### 🐳 Docker

The multi-stage `Dockerfile` produces a slim, non-root image.

```bash
# Build
docker build -t kia-agent:20.0.0 .

# Run (expects Postgres + Redis reachable)
docker run -d --name kia-agent \
  --env-file .env \
  -p 8000:8000 \
  kia-agent:20.0.0
```

### 🧩 docker-compose (full stack)

```yaml
services:
  api:
    build: .
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    command: gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  worker:
    build: .
    env_file: .env
    depends_on: [postgres, redis]
    command: kia worker --group pipeline --concurrency 8

  scheduler:
    build: .
    env_file: .env
    depends_on: [postgres, redis]
    command: kia scheduler

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: kia
      POSTGRES_PASSWORD: kia
      POSTGRES_DB: kia_agent
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes: [redisdata:/data]

volumes:
  pgdata:
  redisdata:
```

```bash
docker compose up -d
docker compose exec api kia migrate up
docker compose exec api kia admin create --email you@company.com --role admin
```

### 🚂 Railway

Kia-Agent is Railway-native. `railway.json` defines the build, health check and start command.

1. **Create a project** → add the **PostgreSQL** and **Redis** plugins (`DATABASE_URL` and `REDIS_URL` are injected automatically).
2. **Deploy from GitHub** or `railway up` from the CLI.
3. Add secrets under **Variables** → `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `ADMIN_SECRET_KEY`, `PUBLIC_BASE_URL`, …
4. Add two more services from the same repo with custom start commands:
   - `kia worker --group pipeline --concurrency 8`
   - `kia scheduler`
5. Set `RUN_MIGRATIONS_ON_START=true` → migrations run automatically on boot.

```bash
railway login
railway init
railway add --plugin postgresql
railway add --plugin redis
railway up
railway run kia admin create --email you@company.com --role admin
```

### 🔗 Register webhooks

Once `PUBLIC_BASE_URL` is live:

```bash
kia webhooks register --channel telegram
kia webhooks register --channel whatsapp
kia webhooks register --channel instagram
kia webhooks status
```

### ✅ Production checklist

- [ ] `APP_ENV=production` · `COOKIE_SECURE=true` · `GUARD_STRICT_MODE=true`
- [ ] `ADMIN_SECRET_KEY` generated with `openssl rand -hex 32`
- [ ] `TOTP_ENABLED=true` for all admin accounts
- [ ] Postgres backups scheduled · Redis AOF persistence on
- [ ] `HITL_QUOTE_THRESHOLD` matches your commercial policy
- [ ] `REPORT_RECIPIENTS` configured
- [ ] At least **1 api · 1 worker · 1 scheduler** process running
- [ ] Webhooks registered and `kia webhooks status` is green

---

## 🧪 Testing

```bash
# Full suite with coverage
pytest --cov=app --cov-report=term-missing

# Unit tests only (no external services)
pytest tests/unit -q

# Integration tests (requires Postgres + Redis)
docker compose up -d postgres redis
pytest tests/integration -q

# A single module
pytest tests/unit/core/test_hitl.py -v
```

### Quality gates (mirrors CI)

```bash
ruff check .                     # lint
ruff format --check .            # formatting
mypy app                         # type check
python scripts/config_lint.py    # locale + YAML completeness
python scripts/secret_scan.py    # no committed secrets
bandit -r app -q                 # security lint
```

### Test layout

| Suite | Files | Covers |
|---|:---:|---|
| `tests/unit/core` | 22 | Orchestrator, agents, HITL layers, Guard, QA engine, automation rules |
| `tests/unit/channels` | 10 | Adapter normalisation, platform limits, webhook signature verification |
| `tests/unit/storage` | 7 | Repositories, Lua scripts, migrations |
| `tests/integration` | 12 | End-to-end pipeline, HITL ledger consistency, SSE stream |
| `tests/i18n` | 3 | Every key present in every locale, RTL rendering |

### CI pipeline

```text
push / PR ─▶ lint (ruff) ─▶ typecheck (mypy) ─▶ test (pytest + cov)
                                                     │
                            config-lint (i18n + YAML) ┴ secret-scan (bandit + custom)
                                                     │
                                                     ▼
                                          ✅ merge allowed
```

---

## 🛡️ Security

| Area | What we do |
|---|---|
| **Prompt injection** | 3-layer Guard on input *and* output; `GUARD_STRICT_MODE` rejects rather than sanitises |
| **Secrets** | Never in the repo — custom scanner + bandit fail the build |
| **Auth** | Argon2id passwords, optional TOTP 2FA, TWA signature verification, hardened cookies |
| **Webhooks** | Signature verification for Telegram, Meta and Twilio payloads |
| **Data at rest** | Postgres + R2 with provider-side encryption; no customer data in logs |
| **Least privilege** | Container runs as non-root; RBAC on every admin endpoint |
| **Auditability** | Append-only audit trail and HITL ledger for every mutation |

🔒 **Found a vulnerability?** Do **not** open a public issue. Email **security@kia-agent.io** — we acknowledge within 24 hours.

---

## ❓ FAQ

<details>
<summary><b>Which LLM does Kia-Agent use?</b></summary>

Any OpenAI-compatible endpoint. Default is OpenRouter with automatic failover to a second provider. You can point it at OpenAI, Anthropic (via OpenRouter), a self-hosted model, or the Hermes bridge.
</details>

<details>
<summary><b>Can the AI send a quote or refund without a human?</b></summary>

Only below the thresholds you configure. Anything above `HITL_QUOTE_THRESHOLD`, any refund, any publish action and any account change **always** waits for a human. If Redis or Postgres is unreachable, HITL fails closed — nothing is sent.
</details>

<details>
<summary><b>How does it scale?</b></summary>

Horizontally. The pipeline is Redis Streams with consumer groups — add more `kia worker` processes and throughput increases linearly. The API is stateless behind gunicorn.
</details>

<details>
<summary><b>Can I white-label it?</b></summary>

Yes. `APP_NAME`, logos, colours, email templates and all 20 locales are overridable via `config/branding.yaml`. See the white-label agreement for details.
</details>

<details>
<summary><b>Does it work without Telegram?</b></summary>

Yes. Every channel is optional — enable only the ones you configure. The admin dashboard works over HTTP regardless.
</details>

<details>
<summary><b>What happens to a message if the LLM provider is down?</b></summary>

Failover kicks in automatically. If all providers fail, the message is already persisted (stage 4) and is retried with exponential backoff; the customer receives a localised "we've received your message" acknowledgement.
</details>

---

## 🤝 Contributing

Kia-Agent is a proprietary product, but licensees and partners with repository access are welcome to contribute.

### Workflow

1. **Branch** from `main` → `feat/<scope>` · `fix/<scope>` · `docs/<scope>`
2. **Install dev deps** → `pip install -e ".[dev]"` and `pre-commit install`
3. **Write tests** for anything you change — PRs that lower coverage are blocked
4. **Run the quality gates** locally → see [Testing](#-testing)
5. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/):
   ```text
   feat(sales): add MOQ-aware quote rounding
   fix(hitl): release Redis lock on ledger write failure
   docs(readme): clarify Railway worker setup
   ```
6. **Open a PR** against `main` — fill in the template, link the issue
7. CI must be green → `lint` → `typecheck` → `test` → `config-lint` → `secret-scan`

### Ground rules

- 🚫 **Never** commit secrets, tokens, or customer data
- 🧑‍⚖️ Every new agent capability must declare its **HITL risk level**
- 🌍 Every new user-facing string must be added to **all 20 locales** (English first; machine translations acceptable if marked `# TODO:review`)
- 📝 Public API changes require a `CHANGELOG.md` entry

---

## 📄 License

**Proprietary — © 2026 Kia-Agent. All rights reserved.**

This software and its documentation are licensed, not sold. Use is governed by the Kia-Agent Commercial License Agreement delivered with your subscription, white-label agreement, or per-license contract. Redistribution, sublicensing, reverse engineering, or use outside the scope of your agreement is prohibited.

| Plan | Deployment | Branding | Support | Best for |
|---|---|---|---|---|
| ☁️ **SaaS** | Hosted by us | Kia-Agent | Standard | Fast start, no ops |
| 🏷️ **White-label** | Hosted by us or you | Your brand | Priority | Agencies & resellers |
| 🏢 **Per-license** | Your infrastructure | Your brand | Dedicated engineer | Data-sovereignty requirements |

📬 Licensing, pricing, partnerships → **sales@kia-agent.io**

---

<div align="center">

<br/>

**Kia-Agent Platform v20.0.0** · September 2026

Built with FastAPI, PostgreSQL, Redis — and a healthy respect for the humans in the loop.

<br/>

⭐ **If Kia-Agent runs your operations, we'd love to hear about it.**

<br/>

[⬆ Back to top](#-kia-agent-platform)

</div>
