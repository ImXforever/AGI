# Zenovix 1.2.0 — employer handoff

Paste **`RAILWAY.env`** into Railway → Variables (RAW). Fill blanks. Details: **`README.md`**.

Must set: Telegram token + admin ids + webhook secret, admin user/password, `WEB_SECRET`, Postgres, Redis, R2, LLM, `CURRENCY`.

`HITL_FALLBACK=silent`. WhatsApp stays `false` until secrets exist.

Health: `GET /healthz` · Public: `/` · Ops: `/admin/ops/ecosystem.html`
