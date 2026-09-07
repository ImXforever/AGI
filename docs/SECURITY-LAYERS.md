# Fifteen security layers

Every inbound Telegram/email/web message and every outbound model reply goes through `app.core.security_stack`. A deny at any layer stops the work. Denies are logged (layer 15) and never silent.

| # | Name | What it stops |
|---|---|---|
| 1 | unicode | Bidi / zero-width overlays, homoglyphs (NFKC) |
| 2 | length | Messages over 4000 characters |
| 3 | prompt_injection | Jailbreaks (“ignore previous instructions”, …) |
| 4 | role_smuggling | Chat-template / system-role markup in user text |
| 5 | indirect_injection | Commands hidden in retrieved docs or web data |
| 6 | secret_harvest | “show api key”, private keys, token-shaped strings |
| 7 | tool_smuggle | `rm -rf`, SQL, path traversal, pipe-to-shell |
| 8 | attachments | MIME allowlist, 10 MB cap, safe filenames |
| 9 | ssrf | Private IPs, localhost, cloud metadata, non-http |
| 10 | rate_limit | Per-sender window at ingest (Redis) |
| 11 | webhook_auth | Channel signatures at the gateway |
| 12 | policy_hitl | Payment / contract / price / delete need a manager |
| 13 | moderation | Fraud / malware / illegal terms |
| 14 | output_exfil | Prompt leaks, secrets, suspicious links in replies |
| 15 | audit | Structured log for every verdict |

Wiring: `ingest_incoming` (before store) and `handle_incoming` (before the LLM). Outbound: `_apply_guard_output`.
