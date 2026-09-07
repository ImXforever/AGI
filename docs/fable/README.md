# Fable 5.1 review pack

Fable has no GitHub and must not receive long files. Use **one short paste per step**.

## Preferred: upload the skill once

Upload `skillfabale.md` (Claude Skill). New chat → wait for `BRIEF LOCKED` → type only `01` (then `02` … `16` → `WRAP`).

Same file at repo root: `/skillfabale.md`.

## How to run (no skill upload)

1. New project or chat. Paste **only** `00-BRIEF.txt` first. Wait for “BRIEF LOCKED”.
2. Same chat. Paste **one** numbered prompt (`01` … `16`). Never two modules at once.
3. Copy Fable’s answer into `CAPTURE.txt` (or a note). Bring that note back here to implement.
4. If the chat gets long, start a **new** chat: paste `00-BRIEF.txt` again, then the next number.

Do **not** paste `orchestrator.py`, `hermes_client.py`, or the zip. Contracts in the prompts are enough.

## Rules for Fable (already in the brief)

- Zenovix is a **self-hosted digital operations manager**, not an autonomous company-builder.
- Money, contract, price, delete, access, sensitive publish = **HITL only**.
- HTML is **English**. Public site ≠ admin ops.
- Security is **fail-closed**. Do not paste jailbreak / exploit samples into Fable (classifiers will swap the model).
- Output: gaps and a small design, **not** a 2000-line rewrite.

## Order (do not skip 01–06)

| # | File | Why first |
|---|---|---|
| 00 | Brief | Shared world |
| 01 | Message path | Dedup → rate → 15 layers → store |
| 02 | Orchestrator | Classify, route, honest admission |
| 03 | Security stack | 15 layers |
| 04 | Policy + HITL | Access matrix |
| 05 | Knowledge / RAG | Company brain |
| 06 | Skills runtime | Hermes, tools, sandbox |
| 07 | Email agent | Phase 1 |
| 08 | Website agent | Phase 2 |
| 09 | Social agent | Phase 3 |
| 10 | Sales agent | Phase 4 |
| 11 | Support agent | Phase 4 |
| 12 | Ops + reports | Phase 5 |
| 13 | Public web + Mini App | Customer surface |
| 14 | Admin ops | Manager surface |
| 15 | Gateway + storage | Webhooks, PG, Redis, R2 |
| 16 | Blind spots | Ideas we missed — last |

After 16, paste `WRAP.txt` so Fable ranks what to build next.
