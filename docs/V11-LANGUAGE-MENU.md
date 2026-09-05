# Kia-Agent v11.0.0 â€” International Language Menu

## Ù‡Ø¯Ù

Ù†Ø³Ø®Ù‡â€ŒÛŒ 11 Ù…Ù†ÙˆÛŒ Telegram Ø±Ø§ Ø¨Ø§ Û±Û² Ø²Ø¨Ø§Ù† Ø¨ÛŒÙ†â€ŒØ§Ù„Ù…Ù„Ù„ÛŒ Ø¬Ø¯ÛŒØ¯ ØªÙˆØ³Ø¹Ù‡ Ù…ÛŒâ€ŒØ¯Ù‡Ø¯. Ø²Ø¨Ø§Ù†â€ŒÙ‡Ø§ÛŒ Arabic Ùˆ English Ù‚Ø¨Ù„Ø§Ù‹ ÙˆØ¬ÙˆØ¯ Ø¯Ø§Ø´ØªÙ†Ø¯Ø› Ø¯Ø± Ù…Ø¬Ù…ÙˆØ¹ Ù…Ù†Ùˆ Ø§Ú©Ù†ÙˆÙ† Û±Û´ Ø²Ø¨Ø§Ù† Ø¯Ø§Ø±Ø¯.

## Û±Û² Ø²Ø¨Ø§Ù† Ø§Ø¶Ø§ÙÙ‡â€ŒØ´Ø¯Ù‡

```text
Spanish     es    EspaÃ±ol
French      fr    FranÃ§ais
German      de    Deutsch
Italian     it    Italiano
Portuguese  pt    PortuguÃªs
Turkish     tr    TÃ¼rkÃ§e
Russian     ru    Ð ÑƒÑÑÐºÐ¸Ð¹
Chinese     zh    ä¸­æ–‡
Japanese    ja    æ—¥æœ¬èªž
Korean      ko    í•œêµ­ì–´
Hindi       hi    à¤¹à¤¿à¤¨à¥à¤¦à¥€
Dutch       nl    Nederlands
```

## Ù…Ø¹Ù…Ø§Ø±ÛŒ

ÙÙ‡Ø±Ø³Øª Ø²Ø¨Ø§Ù†â€ŒÙ‡Ø§ Ø¯Ø± `app/core/languages.py` Ø¨Ù‡â€ŒØµÙˆØ±Øª ÛŒÚ© catalog Ù…Ø±Ú©Ø²ÛŒ Ù†Ú¯Ù‡â€ŒØ¯Ø§Ø±ÛŒ Ù…ÛŒâ€ŒØ´ÙˆØ¯. Ù…Ù†ÙˆÛŒ Telegram Ø§Ø² Ù‡Ù…ÛŒÙ† catalog Ø¯Ú©Ù…Ù‡â€ŒÙ‡Ø§ Ùˆ callbackÙ‡Ø§ÛŒ Ù¾Ø§ÛŒØ¯Ø§Ø± `lang_<code>` Ø±Ø§ Ù…ÛŒâ€ŒØ³Ø§Ø²Ø¯Ø› Ø¨Ù†Ø§Ø¨Ø±Ø§ÛŒÙ† ØªØ±ØªÛŒØ¨ Ùˆ Ú©Ø¯Ù‡Ø§ Ø¯Ø± Ù†Ù‚Ø§Ø· Ù…Ø®ØªÙ„Ù Ø¯ÙˆØ¨Ø§Ø±Ù‡ ØªØ¹Ø±ÛŒÙ Ù†Ù…ÛŒâ€ŒØ´ÙˆÙ†Ø¯.

Ø¯Ø± v11 Ø§Ù†ØªØ®Ø§Ø¨ Ø²Ø¨Ø§Ù† Ø¯Ø± Ù…Ù†Ùˆ Ùˆ callback handling Ø§Ø¶Ø§ÙÙ‡ Ø´Ø¯Ù‡ Ø§Ø³Øª. ØªØ±Ø¬Ù…Ù‡â€ŒÛŒ Ú©Ø§Ù…Ù„ Ù¾Ø§Ø³Ø®â€ŒÙ‡Ø§ÛŒ business Ùˆ ØªØ´Ø®ÛŒØµ Ø²Ø¨Ø§Ù† ØªÙˆÙ„ÛŒØ¯ÛŒ Ø¯Ø± Ù†Ø³Ø®Ù‡â€ŒÙ‡Ø§ÛŒ Ø¨Ø¹Ø¯ÛŒ Ø§Ù†Ø¬Ø§Ù… Ù…ÛŒâ€ŒØ´ÙˆØ¯Ø› ÙØ¹Ù„Ø§Ù‹ fallback Ø§Ù…Ù† Ø¹Ø±Ø¨ÛŒ/Ø§Ù†Ú¯Ù„ÛŒØ³ÛŒ Ø­ÙØ¸ Ø´Ø¯Ù‡ Ø§Ø³Øª.

## ØªØ³Øª

```bash
.venv/bin/pytest tests/unit/ -q
.venv/bin/python tools/import_check.py
.venv/bin/python -m compileall -q app tests tools provision
```
