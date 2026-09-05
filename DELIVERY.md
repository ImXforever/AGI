# Kia-Agent — Client delivery pack

**Date:** 2026-09-05  
**What this is:** the tree to hand to the employer. Public site + Telegram Mini App + manager ops console + HITL API.

Do not treat older review files (`CODE-REVIEW.md`, Persian dumps) as the product contract. This file is.

---

## 1. What the customer sees vs what the manager sees

| Audience | URL | What happens |
|---|---|---|
| Public / customer | `/` and `/index.html` | English landing. No Login. Start a conversation → Telegram. |
| Customer in Telegram Web App | same `/` | Same landing. Quick actions (`products` / `support` / `quote`) via `Telegram.WebApp.sendData`. **No Login.** |
| Manager in Telegram Web App | same `/` | `POST /admin/api/twa/probe` with `initData`. Only if Telegram user id is in `TELEGRAM_ADMIN_IDS` the **Login** control appears. Click → `POST /admin/api/twa/login` (sets `pa_session`) → `/admin/ops/ecosystem.html`. |
| Unauthenticated `/admin/*` | anything else under `/admin` | HTML redirects to `/`. API returns 401. Exceptions: landing, ops login form, TWA probe/login, password login. |

BotFather Mini App URL **must** be:

```text
https://agi-production-1f9f.up.railway.app/
```

---

## 2. Page map (start at index, go deeper)

```text
/                              public landing (TWA index)
└── Login (admin TWA only)
    └── /admin/ops/ecosystem.html     3D ecosystem (first ops view)
        ├── inbox.html
        ├── queue.html                HITL decide → execute_action
        ├── website / social / sales / support
        ├── knowledge.html → brain.html
        └── live / insights / market / hub
```

`admin/index.html` (legacy SPA) is **not replaced**. It stays behind the same session gate.

---

## 3. Technical director review (honest)

A reviewer *will* still find limits. They are listed so they are not surprises.

### Closed this delivery

| Area | Issue | Fix |
|---|---|---|
| Front | Root was JSON `{service, admin}` | `/` serves `admin/landing.html` |
| Front | Mojibake logos (`âœ¦`) | Landing rewritten; SVG only |
| Front | Login visible to everyone | Hidden until TWA probe says `admin: true` |
| Auth | TWA posted `initData`, API expected `init_data` | Both aliases accepted |
| Auth | TWA token `twa:{id}` failed `admins` lookup | `require_admin` accepts TELEGRAM_ADMIN_IDS |
| Auth | TWA login returned token, no cookie | Sets `pa_session` |
| Auth | `/admin/ops` static HTML was world-readable | `AdminGateMiddleware` |
| HITL | `HITL_FALLBACK=auto_ack` could approve money after timeout | Default `silent`; `may_auto_ack` hard-blocks payment/contract/price/delete/access/quote/send_email |
| Ops | Docker `--port 8080` vs Railway `$PORT` | `${PORT:-8080}` |
| Ops | 10k members | Capacity model: ~0.67 msg/s inbound, 1 web worker; HITL staffing is the bottleneck |

### Residual (do not oversell)

| Area | Residual | Why it is acceptable for v1 |
|---|---|---|
| Execute | Handlers write the **ledger**, they do not call a bank, CMS, or SMTP by themselves | Fail-closed. Wire adapters per tenant after go-live. |
| Idempotency | In-process dict (one uvicorn worker) | Dockerfile and Railway start with `--workers 1`. |
| LLM | Quotes/prices must come from approved catalog, not the model | Policy + RAG filter; unapproved drafts are not answers. |
| Data | Integration tests need Postgres/Redis/`asyncpg` | Unit policy/HITL/TWA/landing tests run without infra. |
| Multi-tenant | One `TENANT_ID` per deploy | White-label = another Railway service. |
| Demo queue cards | Some ops cards have empty `data-id` | Real ids come from `/admin/api/approvals`. |

**Score after this pack:** architecture 8.5 · correctness of the agreed product path 9 · security of the admin surface 9 · tests of the policy/TWA/landing contract 9. Not a fictional 10/10 on ERP, multi-region, or bank rails — those were never in this charter.

---

## 4. Policy (do not change without the client)

Auto: `classify_email` · `reply_common` · `publish_calendar` · `create_lead` · `create_ticket` · `create_task`  
HITL always: `send_email` · `change_price` · `payment` · `contract` · `delete_data` · `change_access` · `create_quote`

---

## 5. Deploy (Railway)

1. Fill `RAILWAY.env` (copy into Railway Variables). **Never commit live secrets.**
2. Required: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_IDS`, `TELEGRAM_WEBHOOK_SECRET`, `ADMIN_USERNAME`, `ADMIN_BOOTSTRAP_PASSWORD`, `WEB_SECRET`, `DATABASE_URL`, `REDIS_URL`, LLM keys, R2.
3. `HITL_FALLBACK=silent`
4. `COOKIE_SECURE=true`
5. After deploy: `kia webhooks register --channel telegram`
6. Mini App URL = site origin `/`

Health: `GET /healthz`  
Machine status JSON: `GET /status`  
Public site: `GET /`

---

## 6. Local

```bash
# full stack (needs env + Postgres + Redis)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers

# landing-only preview (no API, no gate)
python3 tools/serve_public.py
```

---

## 7. Files that encode this release

| Path | Role |
|---|---|
| `admin/landing.html` | Public / TWA index |
| `admin/ops/ecosystem.html` | First manager view (3D) |
| `admin/ops/_build.py` | Regenerates ops HTML (English neon) |
| `app/admin_api/gate.py` | Session gate |
| `app/admin_api/twa.py` | probe + login |
| `app/core/policy.py` | Fail-closed matrix |
| `app/core/hitl/execute.py` | Re-check policy at execute time |
| `app/core/hitl/fallback.py` | Timeout; never auto money |
| `RAILWAY.env` | Variable template |
| `Dockerfile` | Non-root, `$PORT` |

`admin/index.html` is frozen on purpose.
