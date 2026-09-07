from __future__ import annotations

import re

from app.core.arabic import looks_critical, normalize
from app.logging_setup import get_logger

log = get_logger(__name__)

SALES_KW = (
    "سعر",
    "عرض",
    "كمية",
    "برميل",
    "شراء",
    "توريد",
    "quote",
    "price",
    "drum",
    "order",
    "purchase",
    "tariff",
)
SUPPORT_KW = (
    "عطل",
    "تسرب",
    "تلوث",
    "شكوى",
    "تأخير",
    "leak",
    "contaminat",
    "broken",
    "defect",
    "malfunction",
    "delayed",
)
KNOW_KW = (
    "لزوجة",
    "مواصف",
    "msds",
    "tds",
    "sae",
    "api",
    "توافق",
    "viscosity",
    "spec",
    "grade",
    "flash point",
)
ANALYTICS_KW = (
    "تحليل",
    "إحصاء",
    "تقرير",
    "بيانات",
    "رسم",
    "متوسط",
    "trend",
    "analytics",
    "statistics",
    "chart",
    "report",
    "kpi",
    "dashboard",
    "average",
    "forecast",
)

_ALL_INTENT_KW: dict[str, tuple[str, ...]] = {
    "sales": SALES_KW,
    "support": SUPPORT_KW,
    "knowledge": KNOW_KW,
    "analytics": ANALYTICS_KW,
}


def heuristic_intent(text: str) -> str:
    t = normalize(text).lower()
    if looks_critical(t):
        return "support"
    scores: dict[str, int] = {}
    for intent, keywords in _ALL_INTENT_KW.items():
        scores[intent] = sum(1 for k in keywords if k in t)
    best = max(scores, key=lambda key: scores[key])
    return best if scores[best] else "other"


def score_confidence(text: str) -> float:
    t = normalize(text).lower()
    if looks_critical(t):
        return 1.0
    scores: dict[str, int] = {}
    for intent, keywords in _ALL_INTENT_KW.items():
        scores[intent] = sum(1 for k in keywords if k in t)
    total = sum(scores.values())
    if total == 0:
        return 0.0
    best_score = max(scores.values())
    return min(best_score / max(total, 1), 1.0)


_ARABIC_RANGE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_PERSIAN_RANGE = re.compile(r"[\u06F0-\u06F9\u0600-\u06FF]")
_PERSIAN_SPECIFIC = re.compile(r"[\u0629\u06CC\u06AF\u0686\u0698\u067E\u06C1\u0686]")


def detect_language(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    has_arabic = bool(_ARABIC_RANGE.search(text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))
    if has_arabic:
        has_persian = bool(_PERSIAN_SPECIFIC.search(text))
        if has_persian and not has_latin:
            return "fa"
        return "ar"
    if has_latin:
        return "en"
    return "unknown"
