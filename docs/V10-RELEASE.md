# Kia-Agent v10.0.0 â€” Composed Operations Release

## Ù‡Ø¯Ù

Ù†Ø³Ø®Ù‡â€ŒÛŒ 10.0.0 Ù†Ù‚Ø·Ù‡â€ŒÛŒ Ø§ØªØµØ§Ù„ workflowÙ‡Ø§ÛŒ ØªØ³Øªâ€ŒØ´Ø¯Ù‡â€ŒÛŒ Ù†Ø³Ø®Ù‡â€ŒÙ‡Ø§ÛŒ Ù‚Ø¨Ù„ÛŒ Ø§Ø³Øª. Orchestrator Ø¯Ø± Ø§ÛŒÙ† Ù†Ø³Ø®Ù‡ Ø§Ø¨ØªØ¯Ø§ ÛŒÚ© plan ØªÙˆØ¶ÛŒØ­â€ŒÙ¾Ø°ÛŒØ± Ù…ÛŒâ€ŒØ³Ø§Ø²Ø¯ Ùˆ Ù‚Ø¨Ù„ Ø§Ø² Ù‡Ø± side effect Ø¢Ù† Ø±Ø§ Ø¨Ù‡ Policy Engine Ù…ÛŒâ€ŒØ³Ù¾Ø§Ø±Ø¯.

## Ù‚Ø§Ø¨Ù„ÛŒØªâ€ŒÙ‡Ø§

- ØªØ±Ú©ÛŒØ¨ Email Triage Ù†Ø³Ø®Ù‡â€ŒÛŒ 0.5
- ØªØ±Ú©ÛŒØ¨ Task Workflow Ù†Ø³Ø®Ù‡â€ŒÛŒ 0.6
- ØªØ±Ú©ÛŒØ¨ Website/Social/Knowledge/Policy foundations
- route Ù‚Ø§Ø¨Ù„â€ŒØªÙˆØ¶ÛŒØ­ Ø¨Ø±Ø§ÛŒ financeØŒ supportØŒ salesØŒ customer Ùˆ general
- ØªÙˆÙ„ÛŒØ¯ `OperationPlan` Ø¨Ø¯ÙˆÙ† Ø§Ø¬Ø±Ø§ÛŒ Ù…Ø³ØªÙ‚ÛŒÙ… Ø¹Ù…Ù„ÛŒØ§Øª Ø®Ø§Ø±Ø¬ÛŒ
- fail-closed Ø¨Ø±Ø§ÛŒ action Ù†Ø§Ø´Ù†Ø§Ø®ØªÙ‡
- approval gate Ù‚Ø¨Ù„ Ø§Ø² sendØŒ publishØŒ payment Ùˆ delete
- Ø­ÙØ¸ reporting Ùˆ health check Ù†Ø³Ø®Ù‡â€ŒÙ‡Ø§ÛŒ Ù‚Ø¨Ù„ÛŒ

## Ø¬Ø±ÛŒØ§Ù† Ù†Ù‡Ø§ÛŒÛŒ

```text
input
  â†’ channel/message contract
  â†’ email/task triage
  â†’ OperationPlan
  â†’ Policy Engine
  â†’ approval when needed
  â†’ external connector
  â†’ audit/report
```

## Ø§ØµÙ„ Ù…Ù‡Ù…

`plan_operation` Ø¹Ù…Ø¯Ø§Ù‹ side effect Ù†Ø¯Ø§Ø±Ø¯. Ø¨Ø±Ù†Ø§Ù…Ù‡ Ø§Ø¨ØªØ¯Ø§ Ù‚Ø§Ø¨Ù„ Ù†Ù…Ø§ÛŒØ´ØŒ ØªØ³Øª Ùˆ ØªØ£ÛŒÛŒØ¯ Ø§Ø³ØªØ› Ù…Ø±Ø­Ù„Ù‡â€ŒÛŒ Ø§Ø¬Ø±Ø§ÛŒ connector Ø¨Ø§ÛŒØ¯ Ø¨Ø¹Ø¯ Ø§Ø² policy Ùˆ approval ØµØ±ÛŒØ­ Ø§Ù†Ø¬Ø§Ù… Ø´ÙˆØ¯.

## ØªØ³Øª release

```bash
.venv/bin/pytest tests/unit/ -q
.venv/bin/python tools/import_check.py
.venv/bin/python -m compileall -q app tests tools provision
.venv/bin/python tools/config_lint.py
```

ØªØ³Øª production ÙˆØ§Ù‚Ø¹ÛŒ Ø¨Ø§ credentialÙ‡Ø§ØŒ providerÙ‡Ø§ÛŒ Ø¨ÛŒØ±ÙˆÙ†ÛŒ Ùˆ PostgreSQL/Redis Ø¨Ø§ÛŒØ¯ Ø¯Ø± Ù…Ø­ÛŒØ· staging Ø¬Ø¯Ø§ Ø§Ù†Ø¬Ø§Ù… Ø´ÙˆØ¯.
