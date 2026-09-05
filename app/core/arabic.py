from __future__ import annotations

import re

from app.logging_setup import get_logger

log = get_logger(__name__)

_TATWEEL = "\u0640"
_ALEF = dict.fromkeys(list("أإآٱ"), "ا")
_WS = re.compile(r"\s+")

_ARABIC_STOP = frozenset(
    [
        "من",
        "على",
        "إلى",
        "في",
        "عن",
        "مع",
        "ذلك",
        "هذه",
        "ليس",
        "ثم",
        "أو",
        "كل",
        "ما",
        "قد",
        "لكن",
        "بعد",
    ]
)


def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.replace(_TATWEEL, "")
    for src, dst in _ALEF.items():
        text = text.replace(src, dst)
    return _WS.sub(" ", text).strip()


def truncate(text: str, max_len: int = 4000) -> str:
    text = text or ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


CRITICAL_MARKERS = (
    "حريق",
    "انفجار",
    "إصابة",
    "اصابة",
    "تسرب نفطي",
    "تسرّب",
    "تلوث",
    " انهيار",
    "غرق",
    "اختناق",
    "نزيف",
    "سكتة قلبية",
    " hemorrhage",
    "burn",
    "scald",
    "chemical exposure",
    "toxic release",
    "blowout",
    "kick",
    "lost circulation",
    "stuck pipe",
    "well control",
    "H2S",
    "hydrogen sulfide",
    "oil spill",
    "gas leak",
    "pipeline rupture",
    "equipment failure",
    "fatality",
    "near miss",
    "evacuate",
    "shutdown",
    "arrêt durgence",
    "incendie",
    "explosion",
    "blessure",
    "déversement",
    "fuite de gaz",
    "effondrement",
)


def looks_critical(text: str) -> bool:
    t = (text or "").lower()
    return any(m.lower() in t for m in CRITICAL_MARKERS)


def normalize_numbers(text: str) -> str:
    if not text:
        return ""
    result: list[str] = []
    for ch in text:
        if "\u0660" <= ch <= "\u0669":
            result.append(chr(ord("0") + ord(ch) - 0x0660))
        elif "\u06f0" <= ch <= "\u06f9":
            result.append(chr(ord("0") + ord(ch) - 0x06F0))
        else:
            result.append(ch)
    return "".join(result)


def extract_keywords(text: str, max_keywords: int = 20) -> list[str]:
    text = normalize_numbers(normalize(text))
    tokens = re.findall(r"[\w\u0600-\u06FF]+", text.lower())
    keywords: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        if len(tok) < 2 or tok in _ARABIC_STOP or tok in seen:
            continue
        seen.add(tok)
        keywords.append(tok)
        if len(keywords) >= max_keywords:
            break
    return keywords


_POSITIVE_AR = frozenset(
    ("ممتاز", "رائع", "جيد", "شكراً", "شكرا", "مقدّر", "مقدر", "حلو", "أحسنت", "أفضل", "متفوق")
)
_NEGATIVE_AR = frozenset(
    (
        "سيء",
        "سيئ",
        "مشكلة",
        "بطيء",
        "مرتفع",
        "غالي",
        "مرفوض",
        "لا أريد",
        "disappointed",
        "poor",
        "bad",
        "slow",
        "refund",
        "bumped",
        "grinding",
    )
)
_URGENT_AR = frozenset(("عاجل", "فوراً", "الآن", "مستعجل", "سريع"))


def sentiment_hint(text: str) -> str:
    t = normalize_numbers(normalize(text)).lower()
    pos = sum(1 for w in _POSITIVE_AR if w in t)
    neg = sum(1 for w in _NEGATIVE_AR if w in t)
    urg = sum(1 for w in _URGENT_AR if w in t)
    if urg >= 2 or neg >= 3:
        return "negative"
    if pos >= 2:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"
