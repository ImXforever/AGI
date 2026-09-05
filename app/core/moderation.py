"""
Content moderation — Persian/Arabic character normalisation + blocklist.

Checks text before publication to block unrealistic financial claims,
malware keywords, and illegal content.  Supports a dynamic extra-word
list stored in the database alongside a hard-coded default blocklist.
"""

from __future__ import annotations

from app.logging_setup import get_logger
from app.storage.pg import get_pool

log = get_logger("app.core.moderation")

DEFAULT_BLOCK = [
    # unrealistic financial claims
    "دوبرابر", "سود تضمینی", "درآمد تضمینی", "پول رایگان", "بی نیاز",
    # bypassing secure bot payments
    "پرداخت مستقیم", "کارت به کارت خارج", "واریز به پیج",
    # malware / intrusion
    "کرک", "کیجن", "keygen", "cracked", "rat v", "stealer", "بات نت", "botnet", "ddos",
    # illegal
    "مخدر", "شیشه", "اسلحه", "مهمات جنگی",
]

_AR2FA = str.maketrans({
    "ي": "ی", "ك": "ک", "ة": "ه", "ے": "ی", "أ": "ا", "إ": "ا", "ؤ": "و",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
})

_STRIP_CHARS = "\u200c\u200e\u200f*_.~-`'\" "


def _normalize(text: str) -> str:
    t = (text or "").translate(_AR2FA).lower()
    for ch in _STRIP_CHARS:
        t = t.replace(ch, "")
    return t


async def _words() -> list[str]:
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT value FROM settings WHERE key = 'moderation_enabled'"
        )
        enabled = (row["value"] if row else "1") == "1"
    except Exception:
        enabled = True
    if not enabled:
        return []

    extra = ""
    try:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT value FROM settings WHERE key = 'moderation_extra_words'"
        )
        extra = (row["value"] if row else "") or ""
    except Exception:
        pass

    extra_words = [w.strip() for w in extra.replace("،", ",").split(",") if w.strip()]
    return DEFAULT_BLOCK + extra_words


async def check_text(text: str) -> tuple[bool, str]:
    """Return ``(is_allowed, first_blocked_word)``."""
    if not (text or "").strip():
        return True, ""
    words = await _words()
    if not words:
        return True, ""
    t = _normalize(text)
    for w in words:
        nw = _normalize(w)
        if nw and nw in t:
            return False, w
    return True, ""
