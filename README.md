<div align="center">

<br/>

# Zenovix 1.6.0

### Digital operations manager for **one** company.  
You own the code, the data, the keys, and the Railway.

<br/>

[![Version](https://img.shields.io/badge/version-1.6.0-8A3FE6?style=for-the-badge)](#)
[![Charter](https://img.shields.io/badge/charter-2.1.0-ff2bd6?style=for-the-badge)](#-access-matrix)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Workers](https://img.shields.io/badge/uvicorn--workers-1-1f2937?style=for-the-badge)](#️-deployment)
[![HITL](https://img.shields.io/badge/HITL-locked-8b5cf6?style=for-the-badge)](#-human-in-the-loop)
[![License](https://img.shields.io/badge/license-Proprietary-0b0d0e?style=for-the-badge)](#-license)

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.app/)
[![R2](https://img.shields.io/badge/object%20store-R2%20%2F%20S3-F38020?style=flat-square)](#-environment-variables)
[![Security](https://img.shields.io/badge/inbound-15%20layers-22c55e?style=flat-square)](#️-security)

<br/>

Zenovix answers customers on **Telegram** and **WhatsApp** (email optional), uses **your services catalogue and knowledge base** as knowledge, drafts quotes and tickets, and **asks a manager before anything important**.

It is **not** an autonomous company. It does not invent a business, spend ads, or move money while the founder sleeps. **No revenue share.**

<br/>

[Quick start](#-quick-start) · [Charter](#what-zenovix-is) · [Architecture](#️-architecture) · [Railway](#️-deployment) · [Variables](#-environment-variables) · [API](#-api) · [FAQ](#-faq)

<br/>

</div>

---

## Why this, not an “AI company in a box”

<table>
<tr>
<td width="50%" valign="top">

### Autonomous SaaS

- The platform owns the sandbox company
- Money and contracts often auto-execute
- Subscription **plus** a cut of revenue / ads
- Knowledge is a generated landing page
- Human is a spectator of a loop

</td>
<td width="50%" valign="top">

### Zenovix (this pack)

- **You** own code, data, keys, Railway
- Payment / contract / price / delete **never** without a manager record
- **Zero** revenue share
- Knowledge is **your** catalog, FAQ, tone, prices
- Human is the **manager of exceptions**

</td>
</tr>
</table>

> Built for one self-hosted tenant. Capabilities turn on from **Railway Variables** — not from a second product backend.

---

## Table of contents

<details>
<summary><b>Open</b></summary>

- [What Zenovix is](#what-zenovix-is)
- [Surfaces](#-surfaces)
- [Access matrix](#-access-matrix)
- [Features](#-features)
- [Architecture](#️-architecture)
- [Quick start](#-quick-start)
- [Environment variables](#-environment-variables)
- [API](#-api)
- [Languages](#-languages)
- [Deployment](#️-deployment)
- [Testing](#-testing)
- [Security](#️-security)
- [Do not](#-do-not)
- [FAQ](#-faq)
- [License](#-license)

</details>

---

## What Zenovix is

You are deploying a **digital operations manager** with six specialist agents and a shared knowledge base.

| Agent | Domain | Phase | Does |
|---|---|:---:|---|
| `email_agent` | Email | 1 | Classify, auto-reply under rules, draft sensitive mail, follow up, escalate finance/legal |
| `website_agent` | Website | 2 | Forms → leads, prepare pages, **hold** price / legal / delete |
| `social_agent` | Social | 3 | Calendar, captions, auto-publish **ordinary** posts, hold claims |
| `sales_agent` | Sales | 4 | First-line answers, leads, **quotes (HITL before send)** |
| `support_agent` | Support | 4 | First-line, tickets, SLA, safety → human |
| `ops_agent` | Ops | 5 | Tasks, reminders, daily / weekly report, cross-domain |

**Declared, inactive:** `accounting_agent` · `hr_agent` · `content_studio_agent` · `project_agent`  
Routing them returns `domain=future` and `auto_execute=false`. Do not turn them on.

Charter in code: `app/core/company_charter.py` (2.1.0) · live JSON: `GET /admin/api/charter`

---

## Surfaces

| Who | URL | Rule |
|---|---|---|
| Public / customer | `/` | English landing. **No Login.** |
| Customer Mini App | `/app` | Telegram Web App shell. **No Login.** |
| Manager (after login) | `/admin/ops/ecosystem.html` | **3D ecosystem first** |
| Unauthenticated `/admin/*` | anything else | HTML → `/`. API **401**. Exceptions: ops login, TWA, password login |

Admin login: `TELEGRAM_ADMIN_IDS` (Telegram Web App) **or** `ADMIN_USERNAME` / `ADMIN_BOOTSTRAP_PASSWORD`.

### Ops chrome (1.1.1)

- **Ctrl+K** (or `/`) command palette — jump every ops page
- Offline banner; Approvals **badge** on the rail
- Insights **JSON snapshot**
- Variables page: every loaded config key, **secrets masked**, bot token never required in chat

First-boot wizard: **`setup.html`** (Persian). **Every other HTML page is English.**

Manager path: Login → ecosystem → HITL queue → decide.

---

## What's new in 1.6.0 (Zenovix identity · simulator · database · Telegram admin · fixes)

**Identity — Kia → Zenovix (zenovix.ae)**

- Agent, company and tenant are **Zenovix — AI & Digital Technology (Dubai)**: soul defaults, business-settings defaults (`ZX` reference prefix, `+971 4570 1100`, `wa.me/97145701100`, `studio@zenovix.com`, Mon–Fri 9:00–18:00 GST), translations in all 8 languages, public landing page, customer app, console chrome, e-mail replies.
- **Data is Zenovix**: six services `ZX-SVC-{AI,CLOUD,WEB,AUTOMATION,DATA,3D}` (codes 101–106, price on request), 24 FAQ, 8 troubleshooting guides, soul, knowledge docs (`product/knowledge/*.md`). Regenerate with `python3 db/seed_packs/zenovix_build.py`. The old EGL pack is preserved under `db/seed_packs/egl/` + `product/knowledge_packs/egl/` (optional, not loaded).
- `env.example` and `railway-variables-ZENOVIX.env` carry the Zenovix defaults (`TENANT_ID=zenovix`, `ADMIN_USERNAME=zenovix-admin`, `R2_PREFIX=tenants/zenovix`).

**Simulator — the real bot inside the console** (`/admin/ops/simulator.html`)

- A WhatsApp-style chat box that runs **the production pipeline** (`orchestrator.handle_incoming` on channel `whatsapp`, sender `sim:<session>`) with a capturing adapter: same 15-layer guard, command router, catalogue flow, skills, output guard, HITL queueing and memory. Nothing is re-implemented.
- **Drop files** (PDF, images, DOCX, XLSX, CSV, JSON, TXT · ≤ 10 MB · 8 per session) on the chat or paste them; they are read (`app/core/ocr.py`) and travel with the next message as framed `ATTACHED FILE … (DATA)` blocks — exactly how Telegram / WhatsApp documents are handled in production. Delete a file and it is gone from the next message.
- Per-session history, language override, "Last turn" debug panel (handled / guard / held / approval id / classification / files used / latency), *New session* and *Forget session*.
- API: `POST /admin/api/simulator/message`, `GET /history`, `GET|POST /files`, `DELETE /files/{id}`, `DELETE /session`.

**Database — whole database from the panel, JSON-versioned** (`/admin/ops/database.html`)

- Browse / search / add / edit / delete rows of 21 business tables (catalogue, knowledge, agent soul & settings, CRM, tickets, quotes, orders, approvals, memory). `admins` and `audit_log` are never exposed; secret-like columns are hidden. Deletes need a superadmin. Every write is audited.
- **Export** one table or everything as `zenovix-db-json/1` files (version, table, key, timestamp, rows); **import** them back — upsert on the natural key (`products.sku`, `settings.key`, …), same semantics as the seed loader, so a JSON export is a faithful, re-loadable snapshot. Settings / soul caches are invalidated on write.
- API: `GET /admin/api/database/tables`, `GET|POST /{table}`, `PUT|DELETE /{table}/{pk}`, `GET /{table}/export`, `GET /export/all`, `POST /{table}/import`, `POST /import`.

**Telegram admin commands** (managers in `TELEGRAM_ADMIN_IDS`)

- `/admin` help · `/vars [group]` · `/get <key>` · `/set <key> <value>` · `/reset <key>` · `/soul [field] [text]` · `/status` · `/approvals` · `/reload`. Same validation as the console's Variables and Soul pages; changes apply to the next customer message, no redeploy. Audited as `telegram.settings.*` / `telegram.soul.*`.

**Console** — 3D background (three.js, theme-aware, `Ctrl+Shift+B` to toggle, respects reduced-motion, 2D fallback; admin panel only, vendored at `/admin/ops/vendor/three.min.js`), new *Simulator* and *Database* doors in the Command nav and the `Ctrl+K` palette.

**Bugs fixed in 1.6.0** (all verified locally against Postgres + Redis + fake Telegram/LLM)

1. **Attachment text rejected by the input guard** — a 2-page PDF made the whole message fail layer 2 ("over 4000 chars"), and any document containing a phrase like "ignore previous…" was refused as prompt injection. `security_stack.inspect_inbound` now splits the `ATTACHED FILE` block off, sanitises it line by line (`paksazi_dade`), caps it (16k) and re-attaches it after the customer's own text passed every layer.
2. **Telegram files were never read** — `download_attachment` built `/bot<token>/file/bot<token>/…` (404) since the first release.
3. **WhatsApp media was never read** — the WhatsApp adapter had no `download_attachment`; Meta media ids and Twilio `MediaUrl`s are now fetched (authenticated) and read like Telegram documents.
4. **`pypdf` missing from the production image** — PDFs could not be read on Railway at all; added to `pyproject.toml` and `Dockerfile`.
5. **DOCX / XLSX / CSV / JSON / TXT were accepted but only their *name* reached the model** — `ocr.extract_text` reads them now (no new dependencies).
6. **Database page: edit / delete failed with 400 on bigint-key tables** (`kb_notes`, `user_memories`, `user_profile`) — the path id was bound as text; keys are now bound with the column's real type, garbage ids give 404.
7. **Database page: duplicate SKU / rule violations crashed with 500** — integrity errors map to 422 with a readable reason; deleting a referenced row gives 409 instead of a stack trace; insert echoes the *stored* row (generated ids, defaults).
8. **Telegram admin replies lost their `<key> <value>` hints** — the adapter's HTML parse mode swallowed them (or failed the send); admin replies are escaped.
9. **Manager-approved answers were not remembered** — `hitl/decide.py` delivered the text but never stored the agent turn, so the next message contradicted what the manager had just sent.
10. Persian and Arabic *Request a quote* menus still described fuel / vessel services from the old tenant; `healthz` fell back to tenant `kia`; `setup.html` title.

Tests: `tests/unit/test_release_1_6_0.py` (simulator helpers, database helpers, file-block security, OCR readers, admin commands, console build, seeds, identity).

## What's new in 1.4.0 (buy in three taps · approve in one)

**For customers (Telegram)**

- Main menu → **sub-menus** per section: Products & Prices, Quote (shop / my requests / talk to sales), Support (new ticket / FAQ / emergency), Contact (call / e-mail / location / hours), Help. Every sub-menu has a Back button.
- **Purchase flow with inline buttons**: category → product card (image, code, title, price) → quantity presets or a typed amount → confirm → request. Typing a product code (`203`) opens the product directly.
- **Per-language display**: the database keeps English as the reference (`name_en`, `title_en`) and translations in `names` / `titles` JSON; a Turkish customer sees a Turkish list, an Arabic customer an Arabic one, with clean plain-text formatting (the messy `/prices` output is gone).
- **My requests**: status of the customer's own quote requests; the customer is told when a manager approves or rejects.
- **Memory**: the bot stores its own replies and gives the model this person's recent turns plus long-term memory.

**For managers**

- **One-tap approvals in Telegram**: every HITL alert carries ✅ Approve / ✖ Reject buttons; the message turns into a receipt and the customer is notified. The console's `/decide` uses the same path (`app/core/hitl/decide.py`) and now really sends.
- **Simpler console**: six doors — Ecosystem, **Desk** (today's numbers, what needs you, latest conversations, traffic, system), Approvals, **Catalog**, **Variables**, Soul. Everything else sits under *More*. Monospace "desk" panels, four themes, phone layout.
- **Catalog editor**: add a product with code, English name, one-line title, category, unit, price, stock, image (upload ≤ 2 MB, stored in Postgres and sent by the bot), translations per language; categories with icons and translations.
- **Variables page**: all business variables (company contact, bot menu switches, quote rules, alert switches) saved in the `settings` table — the bot reads them on the next message, no redeploy. Deployment variables stay read-only and masked.
- Customer mini-app `/app` shows the live catalog in the visitor's language (`GET /api/public/catalog?lang=`) and its buttons now reach the bot (`web_app_data`).

Schema: migration `0017_catalog_i18n_orders.sql` (products: `code`, `title_en`, `names`, `titles`, `image_url`, `sort_order`; `product_images`; `catalog_categories`; `customers.preferred_language`; quotes: `reference`, `channel`, `approval_id`, `language`), seed `006_catalog_categories.json`. New admin API: `/admin/api/desk`, `/admin/api/catalog/categories`, `/admin/api/catalog/products/{id}/image`, `/admin/api/settings/business`.

## What's new in 1.3.1 (hot-fix + one option)

Nine defects found in a live review of 1.3.0 are fixed without touching the project structure:

1. **MCP bridge** — `tools/list` returned `[]` and every `tools/call` failed (imported a non-existent `get_tool_specs`, wrong `execute_tool` signature, tracebacks leaked to clients). Now lists all 22 registry tools with JSON-Schema, validates `arguments` (`-32602`), reports the real version.
2. **Reports 500** — `email_logs` has no `type`/`channel` columns; `daily`/`weekly` now select real columns.
3. **Reports `$1::date`** — asyncpg refused the string date (`'str' object has no attribute 'toordinal'`); all four report queries use `to_date($1,'YYYY-MM-DD')` and the parameter is validated (400 on a bad date instead of 500).
4. **E-mail report** counted `followup_completed` but never selected it (always 0) — joined `email_followups`.
5. **Malformed UUID in a path** (`/admin/api/customers/abc`) → 500 with a traceback; now a clean 404 (other bad parameters → 400) via one `asyncpg.DataError` handler in `app/main.py`.
6. **Ticket severity** — the planner/MCP/`/tools/execute` passed `urgent`, `medium`, `P1`… and hit `tickets_severity_check`, dropping the customer's issue. `normalize_severity()` maps every synonym onto `low|normal|high|critical`; safety tickets are never below `high`; the tool schema now advertises the enum.
7. **`tools/import_check.py`** crashed on its first file (`str(rel).with_suffix`) — the CI import gate never ran. Fixed; 144 modules verified.
8. **Telegram** — replies longer than 4096 chars were rejected by Telegram and lost; the plain-text fallback caught the wrong exception type (dead code) and re-sent raw HTML. Replies are now chunked on paragraph/line boundaries (`split_telegram_text`), the fallback catches `httpx.HTTPStatusError` and strips tags.
9. **Nightly backup** forced `PGSSLMODE=require`, so `pg_dump` failed against Railway's internal endpoint / compose / local Postgres. `pg_sslmode_for()` follows `PGSSLMODE` → `?sslmode=` → `prefer`.

Also: one `APP_VERSION` constant (`app/constants.py`) replaces seven hand-copied version strings; mypy is clean with the strict default flags; six None-unsafe spots hardened.

**New option — `LEAD_ALERT_ENABLED` (default `true`).** Every website enquiry (`POST /api/public/enquiry`) is pushed to the managers in `TELEGRAM_ADMIN_IDS` as a plain-text Telegram alert (reference, name, company, e-mail, phone, service, first 300 chars of the message, link to the support page). The alert never blocks or breaks the form; the response carries `"alerted": true|false`. Set `LEAD_ALERT_ENABLED=false` to switch it off.

---

## What's new in 1.3.0 (public website)

- **Landing page = clone of the mother site.** `/` now renders the Elian Global Logistics website (egl.co.ae): same copy, section order, navy/gold palette, logo and photography. Assets live in `web/assets/` — nothing is loaded from egl.co.ae at runtime except the optional Arabic link.
- **Login kept.** The header, mobile menu and footer carry the Manager **Login** button (`/admin/ops/login.html` → `/admin/ops/ecosystem.html`); Telegram one-tap admin login still works through `data-admin-login`.
- **Enquiry form → lead.** `POST /api/public/enquiry` creates/updates a `web` customer and opens a ticket (`channel=web`, subject "Website enquiry — <service>"), writes an audit row and returns an `EGL-XXXXXXXX` reference. Honeypot field `website`, 6 requests/hour/IP, fail-closed on Redis outage.
- **Ask Zenovix on the website.** `POST /api/public/chat` runs the knowledge skill inline (no admin tools), screens input/output with the 15-layer security stack, strips Markdown, 10 messages/minute/IP.
- `GET /api/public/site` — non-secret tenant facts for the page. `web/_build_site.py` regenerates `web/index.html` from the site data.

## What's new in 1.2.1 (production hot-fix)

Fixes observed in the live 1.2.0 Railway logs — no new features.

- **Second Telegram message got no reply** — `store_message` raised `UniqueViolation` on `idx_messages_conv_extref` when a Telegram `message_id` repeated for the same chat (new bot token on an existing database, or a Redis flush followed by a Telegram retry). The webhook answered 503, Telegram retried, the retry was dropped as a duplicate. Colliding refs are now stored under a salvaged unique ref and answered normally.
- **`ingest failed` without a cause** — the exception is now part of the log message (`ingest failed: <Type>: <detail>`) so Railway shows it.
- **Persian half-space (ZWNJ, U+200C) denied as a bidi attack** — ordinary messages such as «می‌خوام» were silently rejected by security layer 1. ZWNJ/ZWJ are allowed (and stripped only for the pattern checks, so `ig\u200cnore` cannot evade them); genuine bidi overrides remain denied.
- **`/admin/api/approvals` 500** — rows are coerced (UUID → str, timestamptz → ISO, jsonb text → dict) via pydantic validators.
- **`audit_write_failed`** — migration `0016_audit_log_columns.sql` adds the `entity / details / conversation_id / channel` columns `audit()` writes; schema guard updated.
- 14 regression tests (`tests/unit/test_release_121_regressions.py`); 1,265 unit + 297 integration tests green against a real PostgreSQL 17 + Redis.

## What's new in 1.2.0 (English-first release)

- **Agent Soul in Postgres** (`db/migrations/0015_agent_soul.sql`, `app/core/soul.py`, `/admin/api/soul`, admin page **Soul**): name, company, role, mission, personality, tone, languages, greeting, boundaries and style rules are stored in the database, editable from the console without a redeploy, and rendered at the top of **every** system prompt (inline skills + fleet synthesis). The bot now knows who it is.
- **Typing indicator that stays on** (`app/core/typing_keepalive.py`): Telegram `typing` is re-sent every 4 s from the moment a message arrives until the reply is delivered (or 3 min), so customers never see the bot go silent while the model works.
- **Plain-text replies** (`app/core/reply_format.py`, wired into `postprocess.run`): Markdown from the model (`**bold**`, `## headings`, `---`, tables, code fences, links) is converted to channel-safe Telegram HTML (`<b>`, `•`) — WhatsApp / e-mail adapters keep converting that to `*bold*` / plain text. Prompts also carry an explicit "no Markdown, no JSON" output contract.
- **English-first + USD**: `CURRENCY` defaults to `USD` (no longer required), numerals default to `western`, `REPLY_LANGUAGE_POLICY=english-first`, `TENANT_NAME_EN` is the primary tenant name (`TENANT_NAME_AR` optional), catalog seed in USD, migration re-denominates unpriced rows to USD.
- **Landing page at `/`** (`web/index.html`): English marketing page with an always-visible **Login** button → `/admin/ops/login.html` → console. `/admin/index.html` redirects to the same login. Hero, login and soul graphics are inline base64 JPEGs (no external assets).
- **Admin console**: four themes — **Light, Dark, Gray, Neon** (switcher in the top bar, `Alt+T` cycles, persisted in `localStorage`), full phone layout (drawer nav, stacked grids, touch targets, no horizontal overflow), crisper nav icons, Soul page with prompt preview.
- **Boot and log fixes seen in production**: seeds upsert by natural key (`sku` / `key` / `id`) instead of failing on `fallback_templates_key_key`; migration checksum drift is a warning unless `MIGRATION_CHECKSUM_STRICT=true`; uvicorn access/error logs go through the JSON logger with their real severity; IMAP poller stays quiet until credentials are set; output guard removes only tainted sentences and keeps line breaks; QA rewrite no longer flattens paragraphs.
- **Tests**: `test_reply_format.py`, `test_typing_keepalive.py`, `test_soul.py`, seed / guard regressions — CI (ruff, bandit, mypy, pytest, secret scan, config lint, Docker) stays green.

---

## What's new in 1.1.1 (EGL tenant)

- **CI is green**: ruff lint + format across the tree, bandit (Medium+ gate, `nosec` only on SSRF blocklists / container bind), mypy, 1,227 unit tests, secret scanner (fixed directory skipping, `PASTE_` placeholders allow-listed), Docker builds with lowercase tags; `Dockerfile.hermes` now builds the Python bridge that actually ships in `deploy/hermes_bridge/`.

- **Company knowledge wired into replies** (`app/core/knowledge_context.py`): FAQ + troubleshooting (Postgres) + `product/knowledge/*.md` (6 approved EGL docs) load **before** the model, framed as DATA via `inspect_data`. Customer channels see `public` docs only. Persian / English synonyms included. Prices are never invented — unknown prices route to a HITL quote.
- **EGL dataset**: 11 products/services (USD, `unit_price=0`), 23 FAQ, 7 troubleshooting guides, 6 templates from `egl.co.ae`. Migration `0014_retire_sample_dataset.sql` deactivates the old sample rows (PET-001…) so they never answer customers.
- **Twilio-first channels**: WhatsApp via Twilio (`WHATSAPP_PROVIDER=twilio`, Basic-auth form post, Telegram-HTML → `*bold*` markdown) with Meta still supported. Email outbound via Twilio SendGrid (`EMAIL_PROVIDER=sendgrid`, v3 `/mail/send`), inbound via IMAP poller (`EMAIL_INBOUND_PROVIDER=imap`, 60s). Resend path untouched.
- **EGL defaults** in `env.example`: `TENANT_ID=egl` · `CURRENCY=USD` · `Asia/Dubai` · `09:00-18:00` · SendGrid/IMAP/Twilio keys present. Deploy guide: `DEPLOY-EGL-FA.md` + `railway-variables-ZENOVIX.env`.
- **20 new tests**: `tests/unit/test_knowledge_context.py` (7) + `tests/unit/test_twilio_channels.py` (13).

---

## Access matrix

Do not change without the employer.

| Action | Mode |
|---|---|
| `read_email` `classify_email` `reply_common` | **AUTO** |
| `publish_calendar` | **AUTO** |
| `create_lead` `create_ticket` `create_task` | **AUTO** |
| `send_email` (sensitive) `publish_content` `create_quote` | **HITL always** |
| `change_price` `payment` `contract` `delete_data` `change_access` | **HITL always** |
| Unknown action | **deny** |

Production recommendation: `HITL_FALLBACK=silent` — on timeout Zenovix may send a **courtesy line**, never the draft.

`HITL_FALLBACK=auto_ack` is a loaded option. Do **not** use it for quotes, sensitive email, publish, payment, or contracts.

---

## Features

### Channels

| Channel | Default | Notes |
|---|---|---|
| Telegram | **Required** | Webhook HMAC. Empty secret in production = **boot reject** |
| WhatsApp | Off | Meta or Twilio. Disabled = **404** (not 200) |
| Email | Off | Resend outbound + SendGrid or IMAP inbound |
| Instagram | Off | Graph API |
| X / Twitter | Off | API v2 |
| Google Calendar | Off | Ordinary calendar publish only when enabled |

### Knowledge & brain

- Catalog / FAQ / MSDS / troubleshooting in Postgres
- RAG answers grounded in **approved** documents
- Long-term memory + persona (optional sizes in env)
- Fleet teams optional (`FLEET_ENABLED`) — still HITL-bound
- 3D **knowledge atom** and **ecosystem sim** live in ops (English neon)

### HITL ledger

- Pending draft in Postgres
- Redis Lua **consume-once** claim
- Telegram ping to `TELEGRAM_ADMIN_IDS` on every queued item
- Conversation **hold** while a manager is in the thread
- At-most-once outbound after approve (`--workers 1`)

### Ops jobs

| Job | Interval | May auto? |
|---|---|---|
| `followup-check` | 1h | Open tasks only |
| `calendar-publish` | 5m | Ordinary calendar posts |
| `daily-report` | 24h | Compile only |
| `ops-digest` | 24h | Compile only |
| Nightly `pg_dump` → R2 | `BACKUP_HOUR` UTC | List in ops. **Live restore is a drill** — never `pg_restore` without a new approval |

---

## Architecture

Event-driven on **Redis Streams**. Persist **before** the LLM. Mutating tools never skip HITL.

```text
  Telegram · WhatsApp · Email · Instagram · X · Website form
                         │
                         ▼
              HMAC / signature verify
                         │
                         ▼
     ingest → dedup → rate-limit → 15-layer security_stack
                         │
                         ▼
              Postgres  (message stored)
                         │
                         ▼
              Redis stream → orchestrator
           email · website · social · sales · support · ops
                         │
              RAG · memory · LLM (DIRECT_* or router)
                         │
                         ▼
              output guard  →  policy
           AUTO reply_common / publish_calendar / create_*
           HITL  payment · contract · price · delete · quote send
                         │
                         ▼
              manager decide  →  at-most-once send
```

### How a message travels

| # | Stage | What happens |
|:---:|---|---|
| 1 | Verify | Telegram `secret_token` / Meta / Twilio / email webhook. Empty Telegram secret in production **does not boot** |
| 2 | Ingest | Adapter → `Message`. Dedup + per-user rate limit |
| 3 | Security | 15 fail-closed layers (see [Security](#️-security)) |
| 4 | Store | Postgres **before** any model call |
| 5 | Route | Orchestrator → specialist. Future agents: hold |
| 6 | Draft | Catalog-grounded. Prices are not invented |
| 7 | Policy | AUTO vs HITL vs deny |
| 8 | Decide | Manager in ops queue or Telegram. Lua claim, 409 on double-decide |
| 9 | Send | At-most-once. `--workers 1` is the idempotency contract |

---

## Quick start

Employer path is **Railway**. Local is optional.

### 1. First-boot (Persian wizard)

Open `setup.html` in a browser. It explains every variable and where it comes from. **Do not paste live secrets into that page.**

### 2. Railway

1. New project → add **PostgreSQL** + **Redis** (`DATABASE_URL`, `REDIS_URL`).
2. Deploy this repo (`railway.json` → `Dockerfile`, health `/healthz`, **1 worker**).
3. Variables → RAW Editor → paste **`RAILWAY.env`** (same keys as `env.example`).
4. Fill blanks. Generate `WEB_SECRET`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

5. After the public URL exists, register Telegram with the **same** secret you set (never invent a second one):

```text
https://api.telegram.org/bot<TOKEN>/setWebhook
  ?url=https://YOUR_HOST/tg/webhook
  &secret_token=<TELEGRAM_WEBHOOK_SECRET>
```

### 3. Verify

| Check | URL |
|---|---|
| Health | `GET /healthz` |
| Public | `GET /` |
| Mini App | `GET /app` |
| Machine | `GET /status` |
| OpenAPI | `/api/docs` |
| Ops | login → `/admin/ops/ecosystem.html` |

### Local (optional)

```bash
cp env.example .env    # fill secrets; never commit .env
# Postgres + Redis running
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1 --proxy-headers
```

---

## Environment variables

All configuration is read **only** by `app/config.py`. Names not loaded there do nothing.

Paste file: **`RAILWAY.env`**. Details: **`setup.html`**.

`PORT` is set by Railway.

Production: `APP_ENV=production` · `COOKIE_SECURE=true` · `HITL_FALLBACK=silent`.

### Must set (production will not boot without these)

| Variable | What it is |
|---|---|
| `TENANT_ID` | Short slug (stored lowercase) |
| `TENANT_NAME_EN` / `TENANT_NAME_AR` | Company name |
| `SUPPORT_CONTACT` | Public support contact |
| `TELEGRAM_BOT_TOKEN` | BotFather. **Never paste in chat.** |
| `TELEGRAM_ADMIN_IDS` | Comma-separated Telegram user ids |
| `TELEGRAM_WEBHOOK_SECRET` | ≥16 chars. **Never empty in production. Never auto-generated.** |
| `ADMIN_USERNAME` | Ops login |
| `ADMIN_BOOTSTRAP_PASSWORD` | First admin password |
| `WEB_SECRET` | ≥16 chars cookie signer |
| `DATABASE_URL` / `REDIS_URL` | Railway plugins |
| `R2_ENDPOINT` `R2_ACCESS_KEY_ID` `R2_SECRET_ACCESS_KEY` `R2_BUCKET` | Object storage |
| `CURRENCY` | e.g. `EUR` / `SAR` |
| LLM | `LLM_MODE=direct` + `DIRECT_BASE_URL` `DIRECT_API_KEY` `DIRECT_MODEL` — or `LLM_MODE=router` + `ROUTER_*` |

### Turn a capability on

| Capability | Flags | Also required |
|---|---|---|
| Telegram | token + admin ids + webhook secret | `setWebhook` with the **same** secret |
| WhatsApp Meta | `WHATSAPP_ENABLED=true` `WHATSAPP_PROVIDER=meta` | `WHATSAPP_APP_SECRET` `WHATSAPP_PHONE_NUMBER_ID` `WHATSAPP_API_TOKEN` `WHATSAPP_VERIFY_TOKEN` |
| WhatsApp Twilio | `WHATSAPP_ENABLED=true` `WHATSAPP_PROVIDER=twilio` | `TWILIO_ACCOUNT_SID` `TWILIO_AUTH_TOKEN` `TWILIO_WHATSAPP_FROM` |
| Email | `EMAIL_ENABLED=true` | `EMAIL_FROM` `RESEND_API_KEY` **and** `SENDGRID_WEBHOOK_PUBLIC_KEY` or `RESEND_WEBHOOK_SECRET`; IMAP extras if `EMAIL_INBOUND_PROVIDER=imap` |
| Instagram | `INSTAGRAM_ENABLED=true` | `INSTAGRAM_ACCESS_TOKEN` `INSTAGRAM_BUSINESS_ACCOUNT_ID` |
| X | `TWITTER_ENABLED=true` | API key/secret + access token/secret or bearer |
| Calendar | `CALENDAR_ENABLED=true` | `GOOGLE_CALENDAR_CREDENTIALS` `GOOGLE_CALENDAR_ID` |
| Nightly backup | `BACKUP_ENABLED=true` | `BACKUP_HOUR` (0–23 UTC) `PG_DUMP_RETENTION_DAYS` |
| HITL Telegram ping | `HITL_PING_TELEGRAM=true` | default on |
| Memory / fleet | `MEMORY_ENABLED` `FLEET_ENABLED` | optional sizes / timeouts |
| Brand | `BRAND_PRIMARY_COLOR` `BRAND_LOGO_URL` | ops UI |
| Hours | `TENANT_TIMEZONE` `BUSINESS_HOURS` | e.g. `Europe/Amsterdam` `09:00-17:00` |
| Quotes | `TAX_RATE` `QUOTE_VALID_DAYS` `LEAD_SCORING_ENABLED` | catalog still HITL for price |
| Website lead alert (1.3.1) | `LEAD_ALERT_ENABLED=true` | every `/api/public/enquiry` is pushed to `TELEGRAM_ADMIN_IDS` |
| Rate limit | `RATE_LIMIT_PER_MINUTE` | ingest window 60s |
| 2FA | `TOTP_ENABLED=true` | admin accounts |
| LLM aliases | `OPENAI_API_KEY` / `OPENAI_BASE_URL` | mapped onto `DIRECT_*` |

Disabled WhatsApp = **404**. Empty webhook secrets = **reject**.

<details>
<summary><b>Full key list (loaded by config.py)</b></summary>

Tenant · brand · hours: `TENANT_ID` `TENANT_NAME_AR` `TENANT_NAME_EN` `SUPPORT_CONTACT` `BRAND_LOGO_URL` `BRAND_PRIMARY_COLOR` `TENANT_TIMEZONE` `BUSINESS_HOURS`

Telegram: `TELEGRAM_BOT_TOKEN` `TELEGRAM_ADMIN_IDS` `TELEGRAM_WEBHOOK_SECRET`

WhatsApp: `WHATSAPP_ENABLED` `WHATSAPP_PROVIDER` `WHATSAPP_VERIFY_TOKEN` `WHATSAPP_APP_SECRET` `WHATSAPP_PHONE_NUMBER_ID` `WHATSAPP_API_TOKEN` `WHATSAPP_BASE_URL` `TWILIO_ACCOUNT_SID` `TWILIO_AUTH_TOKEN` `TWILIO_WHATSAPP_FROM` `TWILIO_BASE_URL`

Email: `EMAIL_ENABLED` `EMAIL_FROM` `EMAIL_REPLY_TO` `EMAIL_INBOUND_PROVIDER` `RESEND_API_KEY` `RESEND_BASE_URL` `RESEND_WEBHOOK_SECRET` `SENDGRID_API_KEY` `SENDGRID_WEBHOOK_PUBLIC_KEY` `IMAP_HOST` `IMAP_PORT` `IMAP_USER` `IMAP_PASSWORD` `IMAP_POLL_SECONDS`

Social: `INSTAGRAM_ENABLED` `INSTAGRAM_ACCESS_TOKEN` `INSTAGRAM_BUSINESS_ACCOUNT_ID` `TWITTER_ENABLED` `TWITTER_API_KEY` `TWITTER_API_SECRET` `TWITTER_ACCESS_TOKEN` `TWITTER_ACCESS_SECRET` `TWITTER_BEARER_TOKEN`

Calendar: `CALENDAR_ENABLED` `GOOGLE_CALENDAR_CREDENTIALS` `GOOGLE_CALENDAR_ID` `DEFAULT_REMINDER_MINUTES`

LLM: `LLM_MODE` `DIRECT_BASE_URL` `DIRECT_API_KEY` `DIRECT_MODEL` `LLM_MODEL_FAST` `LLM_MODEL_STANDARD` `LLM_TEMPERATURE` `OPENAI_API_KEY` `OPENAI_BASE_URL` `ROUTER_BASE_URL` `ROUTER_ACCESS_KEY` `ROUTER_TIMEOUT` `ROUTER_FALLBACK_TO_DIRECT` `HERMES_BASE_URL` `HERMES_SERVICE_TOKEN` `HERMES_TIMEOUT`

Storage: `DATABASE_URL` `REDIS_URL` `R2_ENDPOINT` `R2_ACCESS_KEY_ID` `R2_SECRET_ACCESS_KEY` `R2_BUCKET` `R2_PREFIX` `R2_SIGNED_URL_TTL` `ARCHIVE_FINAL_OUTPUTS` `PG_DUMP_RETENTION_DAYS` `HOT_DATA_DAYS` `BACKUP_ENABLED` `BACKUP_HOUR`

Admin / ops: `ADMIN_USERNAME` `ADMIN_BOOTSTRAP_PASSWORD` `WEB_SECRET` `WEB_PORT` `COOKIE_SECURE` `TOTP_ENABLED` `APP_ENV` `BOOTSTRAP_MODE` `LOG_LEVEL` `LOG_JSON_ENABLED` `LOG_TO_DB`

Domain / HITL / memory: `CURRENCY` `TAX_RATE` `QUOTE_VALID_DAYS` `LEAD_SCORING_ENABLED` `LEAD_ALERT_ENABLED` `NUMERAL_STYLE` `REPLY_LANGUAGE_POLICY` `RATE_LIMIT_PER_MINUTE` `HITL_TIMEOUT_SECONDS` `HITL_FALLBACK` `HITL_PING_TELEGRAM` `MEMORY_ENABLED` `MEMORY_EXTRACT_EVERY` `MEMORY_BUDGET_CHARS` `MEMORY_PERSONA_THRESHOLD` `FLEET_ENABLED` `FLEET_MAX_TEAM_SIZE` `FLEET_TEAM_TIMEOUT`

</details>

---

## API

Interactive docs: **`/api/docs`** · OpenAPI: **`/api/openapi.json`**.  
Admin JSON lives under **`/admin/api`**. Cookie session or TWA. Secrets in `/settings` are **masked**.

### Public / health

| Method | Path | Auth | What |
|---|---|:---:|---|
| `GET` | `/` | — | English landing |
| `GET` | `/app` | — | Customer Mini App |
| `GET` | `/healthz` | — | Deep health (`?deep=0` skips deps) |
| `GET` | `/status` | — | Service map |
| `GET` | `/buildinfo` | — | Version + uptime |
| `GET` | `/agent.json` | — | A2A discovery card |

### Webhooks

| Method | Path | Gate |
|---|---|---|
| `POST` | `/tg/webhook` | `TELEGRAM_WEBHOOK_SECRET` |
| `GET`/`POST` | `/wa/webhook` | Off = **404** |
| `POST` | `/email/inbound` | SendGrid / Resend signature |

### Admin (session)

| Module | Base | Typical |
|---|---|---|
| Auth | `/admin/api/auth` | `POST /login` `POST /logout` `GET /session` |
| Approvals | `/admin/api/approvals` | `GET /` `POST /{id}/decide` |
| Settings | `/admin/api/settings` | Full config, secrets masked |
| Charter | `/admin/api/charter` | Access matrix as JSON |
| Security | `/admin/api/security` | 15-layer catalog |
| Stream | `/admin/api/stream` | Live stats / SSE |
| Catalog | `/admin/api/catalog` | Products, FAQ, MSDS |
| Customers / quotes / tickets | `/admin/api/customers` `/quotes` `/tickets` | CRM surfaces |
| CMS / content | `/admin/api/cms` `/content` | Pages and calendar — publish still HITL |
| Reports / audit / QA | `/admin/api/reports` `/audit` `/qa` | Manager trail |
| Automation / backup / team | `/admin/api/automation` `/backup` `/team` | Rules; backup **list**; restore is a drill |
| TWA | `/admin/api/twa` | Telegram Web App manager login |

### Example — decide a held item

```bash
curl -X POST https://YOUR_HOST/admin/api/approvals/APPROVAL_ID/decide \
  -H "Content-Type: application/json" \
  --cookie "session=…" \
  -d '{"status":"approved","note":"ops console"}'
```

`status`: `approved` | `rejected` | `edited`. Already terminal → **409**.

---

## Languages

Customer **menu** codes in `app/core/languages.py` (21, including Persian / Arabic / Hebrew RTL). Agents detect and reply in the customer’s language when possible (`REPLY_LANGUAGE_POLICY`).

**Product HTML (landing + ops) is English.** The only Persian HTML exception is `setup.html`.

---

## Deployment

### Dockerfile (what Railway runs)

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers
```

Health: `GET /healthz`. User: non-root `zenovix`. Python 3.12-slim.

**Do not** raise worker count. HITL consume-once and outbound at-most-once assume **one** process.

### Production checklist

- [ ] `APP_ENV=production` · `COOKIE_SECURE=true`
- [ ] `TELEGRAM_WEBHOOK_SECRET` ≥16 and **identical** to `setWebhook`
- [ ] `WEB_SECRET` generated, not empty
- [ ] `HITL_FALLBACK=silent` for go-live
- [ ] WhatsApp stays `false` until Meta/Twilio secrets exist
- [ ] `BACKUP_ENABLED=true` once R2 is confirmed
- [ ] Login → `/admin/ops/ecosystem.html` → Approvals works
- [ ] Accounting / HR / studio / project remain **off**

### Residual (honest)

| Area | Residual |
|---|---|
| Execute | Handlers write the ledger; bank / CMS / SMTP adapters are wired **per tenant** after go-live |
| Idempotency | In-process; Dockerfile `--workers 1` |
| Multi-tenant | One `TENANT_ID` per deploy |
| Future agents | Declared, inactive |

---

## Testing

Charter / ops / public slice (no live FastAPI app required):

```bash
python -m pytest \
  tests/unit/test_week_two.py \
  tests/unit/test_config.py \
  tests/unit/test_client_spec.py \
  tests/unit/test_public_web.py \
  tests/unit/test_admin_ops.py -q
```

Full unit tree needs FastAPI in the environment. Gateway tests import `verify.py` / `body.py` via importlib.

---

## Security

Fail-closed on the message path (`app/core/security_stack.py`):

1. unicode · 2. length · 3. prompt injection · 4. role smuggling · 5. indirect injection · 6. secret harvest · 7. tool smuggle · 8. attachments · 9. SSRF · 10. rate limit · 11. webhook auth · 12. policy / HITL · 13. moderation · 14. output exfil · 15. audit

Manager catalog: `GET /admin/api/security/layers`.

| Area | Contract |
|---|---|
| Webhook secrets | Never invented. Empty Telegram secret in production = **reject at boot** |
| Cookies | Signed with `WEB_SECRET`. `COOKIE_SECURE` in production |
| Passwords | Argon2id |
| Settings UI | Secrets masked; admin ids are **not** treated as secrets |
| Backup restore | New HITL approval. Not a silent `pg_restore` |
| Container | Non-root |

---

## Do not

- Invent `TELEGRAM_WEBHOOK_SECRET`
- Run extra uvicorn workers
- Set `HITL_FALLBACK=auto_ack` for quotes / email / publish / payment
- Enable WhatsApp without Meta or Twilio secrets
- Turn on accounting / HR / studio / project agents
- Spend ads or take payments **inside** Zenovix
- Dump another product’s backend into this tenant
- Put live tokens in `setup.html` or in chat

---

## FAQ

<details>
<summary><b>Is this an autonomous company?</b></summary>

No. Zenovix is a **HITL operations manager** for one employer tenant. Comparison wins are ownership, audit, and zero revenue share — not “it runs the business while you sleep.”
</details>

<details>
<summary><b>Can it send a quote or a payment alone?</b></summary>

Quotes: draft yes, send **no** until a manager record exists. Payment, contract, price change, delete, and access change: **never** auto.
</details>

<details>
<summary><b>Why only one worker?</b></summary>

Redis Lua claim + outbound at-most-once are in-process. Extra workers split that contract. Scale channels and Postgres, not uvicorn replicas.
</details>

<details>
<summary><b>Why was my WhatsApp URL 404?</b></summary>

`WHATSAPP_ENABLED=false` is a hard 404 by design. Enable only with provider secrets.
</details>

<details>
<summary><b>Where do I put the bot token?</b></summary>

Railway Variables only. Never in chat, never in `setup.html`, never in ops HTML.
</details>

<details>
<summary><b>Persian UI?</b></summary>

`setup.html` is Persian. Landing and ops are English. The agent may reply in the customer’s language.
</details>

---

## License

Proprietary. Delivered to the employer for **one self-hosted tenant**. The employer owns the deployment.

Not SaaS. Not white-label marketplace. Not a revenue-share autonomous company.

---

<div align="center">

**Zenovix 1.4.0** · charter 2.1.0 · September 2026

FastAPI · PostgreSQL · Redis · R2 · `--workers 1` · manager on the exceptions.

[Back to top](#zenovix-160)

</div>
