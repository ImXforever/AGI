# Zenovix 1.4.0 — Client delivery pack

**Date:** 2026-09-07  
**What this is:** digital operations manager for the employer charter. Public site + Telegram Mini App + manager ops + HITL.

**1.4.0:** buying and approving made simple — Telegram main menu with sub-menus per section (Products, Quote, Support, Contact, Help); purchase flow with inline buttons category → product → quantity → request (no typing, product code works too); every product has a short customer code, image, English name, one-line title, price and translations; database reference language is English (`name_en`, `names` JSON per language) so a Turkish customer sees a Turkish list and an Arabic one an Arabic list; managers approve / reject with one tap in Telegram (buttons under the alert) or on the new **Desk** — and the customer is really told (1.3.x only recorded the decision); the admin console shrank to six doors (Ecosystem, Desk, Approvals, Catalog, Variables, Soul) in the monospace desk style; new **Catalog** editor (add product, image upload, categories, translations) and **Variables** page (company contact, bot menu switches, quote rules, alerts) saved in Postgres — no redeploy; per-person memory: the bot now stores its own replies and feeds this customer's recent turns plus long-term memory to the model; the customer mini-app (/app) shows the live per-language catalog and its buttons reach the bot (`web_app_data` was dropped before). Migration 0017, seed 006. **1.3.1:** hot-fix release — MCP bridge works again (22 tools), all four admin reports return 200, malformed UUIDs give 404 not 500, ticket severity synonyms are normalised (no more `tickets_severity_check` failures), Telegram replies over 4096 chars are chunked and the HTML→plain fallback really runs, nightly `pg_dump` no longer forces SSL, `tools/import_check.py` runs, one `APP_VERSION` constant. New option `LEAD_ALERT_ENABLED`: website enquiries are pushed to the Telegram managers instantly. **1.3.0:** public site is now a clone of the mother site egl.co.ae (real copy, navy/gold design, logo and photos shipped locally), with the Manager **Login** button kept, a quote/enquiry form that creates a lead ticket (`POST /api/public/enquiry`) and an on-page **Ask Zenovix** widget answering from the approved knowledge base (`POST /api/public/chat`) — both rate-limited, honeypot-protected and screened by the security stack. **1.2.1:** production hot-fix — repeated Telegram message_id no longer breaks ingest (503 → reply), ingest errors logged with cause, Persian half-space no longer denied, approvals API 500 fixed, audit_log columns migration 0016. **1.2.0:** agent Soul in Postgres (admin page + API), typing indicator kept alive until delivery, Markdown-free replies, English-first + USD defaults, public landing page with Login, admin themes Light/Dark/Gray/Neon + phone layout, seed/migration/log fixes. **1.1.1:** manager command palette (Ctrl+K), offline banner, Approvals nav badge, Insights JSON snapshot. Persian first-boot wizard `setup.html`. No DropAgent backend.

This file is the product contract. Older review dumps are not.

---

## 1. What we are (and are not)

Zenovix is **not** an autonomous company-builder. It does not invent a company, spend ads, or move money while the founder sleeps.

Zenovix **is** one operations manager with specialist agents (email, website, social, sales, support, ops), a shared knowledge base, and a manager record on payment, contract, price, delete, access, and sensitive publish.

That is the comparison win against Polsia-class products: ownership, HITL, audit, zero revenue share.

---

## 2. What the customer sees vs what the manager sees

| Audience | URL | What happens |
|---|---|---|
| Public / customer | `/` (`web/index.html`) | English landing. No Login. Start a conversation → Telegram. |
| Customer web app | `/app` | Telegram Mini App shell (bottom nav). |
| Customer in Telegram Web App | `/` | Same landing. Quick actions via `Telegram.WebApp.sendData`. **No Login.** |
| Manager in Telegram Web App | `/` | Probe `TELEGRAM_ADMIN_IDS` → Login → `/admin/ops/ecosystem.html`. |
| Unauthenticated `/admin/*` | anything else | HTML → `/`. API 401. Exceptions: landing, ops login, TWA, password login. |

Mini App URL: site origin `/`.

---

## 3. Page map

```text
/                              public landing (charter positioning)
└── Login (admin TWA / password)
    └── /admin/ops/ecosystem.html     3D ecosystem (first ops view)
        ├── charter.html              access matrix + phases
        ├── inbox / queue
        ├── website / social / sales / support
        ├── knowledge → brain
        └── live / insights / market / hub
```

---

## 4. Access matrix (do not change without the client)

Auto: `read_email` · `classify_email` · `reply_common` · `publish_calendar` · `create_lead` · `create_ticket` · `create_task`  
HITL always: `send_email` · `publish_content` · `change_price` · `payment` · `contract` · `delete_data` · `change_access` · `create_quote`

Code: `app/core/company_charter.py` (2.1.0) + `app/core/policy.py`. Live JSON: `GET /admin/api/charter`.

---

## 4.1 Fifteen security layers

Fail-closed on the message path (`app/core/security_stack.py`), from prompt injection through the rest of the threat surface:

1. unicode · 2. length · 3. prompt injection · 4. role smuggling · 5. indirect injection · 6. secret harvest · 7. tool smuggle · 8. attachments · 9. SSRF · 10. rate limit · 11. webhook auth · 12. policy/HITL · 13. moderation · 14. output exfil · 15. audit.

Catalog for managers: `GET /admin/api/security/layers`.

## 5. Residual (honest)

| Area | Residual |
|---|---|
| Execute | Handlers write the ledger; bank/CMS/SMTP adapters are wired per tenant after go-live. |
| Idempotency | In-process; Dockerfile `--workers 1`. |
| Multi-tenant | One `TENANT_ID` per deploy. |
| Future agents | accounting / HR / content studio / project — declared, inactive. |

---

## 6. Deploy

Fill `RAILWAY.env`. Required: Telegram token + admin ids + webhook secret, `ADMIN_USERNAME`, `ADMIN_BOOTSTRAP_PASSWORD`, **`WEB_SECRET`**, `DATABASE_URL`, `REDIS_URL`, LLM, R2.  
`APP_ENV=production` · `COOKIE_SECURE=true` · `HITL_FALLBACK=silent` recommended.

Health: `GET /healthz` · Public: `GET /` · Machine: `GET /status`
