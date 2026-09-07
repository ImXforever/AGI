"""Load company knowledge (FAQ, troubleshooting, approved docs) into the reply path.

Mirrors ``catalog_context``: read-only retrieval runs *before* the model writes a
word, and the result is framed as DATA (never instructions) via ``inspect_data``.

Sources, in order:
1. ``faq``              — Postgres, keyword match on question/answer/tags
2. ``troubleshooting``  — Postgres, keyword match on title/problem/solution
3. ``product/knowledge/*.md`` — approved Markdown docs (frontmatter-governed),
   scored by keyword overlap. Only ``public`` docs reach a customer channel.

Everything is best-effort: any failure returns an empty block and the agent
falls back to its honest-admission path instead of crashing the reply.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.arabic import extract_keywords
from app.core.security_stack import inspect_data
from app.logging_setup import get_logger

log = get_logger("app.core.knowledge_context")

_KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent.parent / "product" / "knowledge"
_MAX_KEYWORDS = 8
_MAX_BLOCK_CHARS = 3500
_DOC_SNIPPET_CHARS = 900

# Persian / English filler that extract_keywords does not drop.
_EXTRA_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "you",
        "your",
        "with",
        "what",
        "how",
        "can",
        "are",
        "does",
        "about",
        "please",
        "have",
        "there",
        "this",
        "that",
        "من",
        "به",
        "از",
        "که",
        "را",
        "با",
        "در",
        "چه",
        "چی",
        "آیا",
        "شما",
        "برای",
        "است",
        "هست",
        "چیه",
        "چطور",
        "چطوری",
        "لطفا",
        "لطفاً",
        "میشه",
        "می‌شه",
        "دارید",
        "کنید",
        "هل",
        "ما",
        "كيف",
        "هي",
        "هو",
        "لدي",
        "لديكم",
        "عن",
        "أن",
    }
)

# Domain synonyms so a Persian/English question still hits Arabic/English rows.
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "ساعت": ("hours", "ساعات"),
    "ساعات": ("hours",),
    "کاری": ("hours", "working"),
    "آدرس": ("office", "address", "عنوان"),
    "دفتر": ("office",),
    "تماس": ("contact", "phone", "تواصل"),
    "قیمت": ("price", "quote", "سعر"),
    "هزینه": ("price", "quote"),
    "پیش‌فاکتور": ("quote",),
    "استعلام": ("quote",),
    "خدمات": ("services", "خدمات"),
    "انبار": ("storage", "tank", "تخزين"),
    "مخزن": ("storage", "tank"),
    "ذخیره": ("storage",),
    "سوخت": ("fuel", "bunker", "وقود"),
    "بانکرینگ": ("bunker",),
    "کشتی": ("vessel", "charter", "سفينة"),
    "اجاره": ("charter",),
    "نفت": ("crude", "oil", "نفط"),
    "گازوئیل": ("diesel",),
    "دیزل": ("diesel",),
    "بنزین": ("gasoline",),
    "سوخت هواپیما": ("jet",),
    "ایمنی": ("hse", "safety", "سلامة"),
    "مدارک": ("documents", "tsa", "tsr"),
    "سند": ("document", "tsa", "tsr"),
    "تایید": ("verification", "verify"),
    "شرکت": ("company", "who", "شركة"),
    "کجا": ("location", "office"),
    "زبان": ("language",),
    "فوری": ("emergency",),
    "اضطراری": ("emergency",),
    "نشت": ("spill", "leak"),
    "whatsapp": ("contact",),
    "email": ("contact",),
    "phone": ("contact",),
    "address": ("location", "office"),
    "where": ("location",),
    "who": ("company",),
    "cost": ("price", "quote"),
    "rate": ("price", "quote"),
    "rates": ("price", "quote"),
    "tank": ("storage",),
    "tanks": ("storage",),
    "ship": ("vessel", "charter"),
    "tanker": ("charter", "vessel"),
    "سعر": ("price", "quote"),
    "أسعار": ("price", "quote"),
    "تخزين": ("storage",),
    "تموين": ("bunker",),
    "تأجير": ("charter",),
    "عنوان": ("location", "office"),
    "موقع": ("location",),
}


def keywords_for(text: str, *, limit: int = _MAX_KEYWORDS) -> list[str]:
    """Normalised search terms: base keywords + domain synonyms, filler removed."""
    base = [k for k in extract_keywords(text or "", max_keywords=limit * 2) if k not in _EXTRA_STOP]
    out: list[str] = []
    seen: set[str] = set()
    for tok in base:
        clean = tok.strip("؟?!.,:;\"'()[]{}")
        if len(clean) < 2:
            continue
        for cand in (clean, *_SYNONYMS.get(clean, ())):
            c = cand.casefold()
            if c not in seen:
                seen.add(c)
                out.append(c)
    return out[:limit]


def _patterns(keywords: list[str]) -> list[str]:
    return [f"%{k}%" for k in keywords]


async def fetch_faq(keywords: list[str], *, limit: int = 4) -> list[dict[str, Any]]:
    if not keywords:
        return []
    try:
        from app.storage.pg import get_pool

        pool = await get_pool()
        rows = await pool.fetch(
            """
            SELECT question_en, answer_en, question_ar, answer_ar, category,
                   (
                     (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE question_en ILIKE p) * 3
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE question_ar ILIKE p) * 3
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE tags::text ILIKE p) * 2
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE answer_en ILIKE p)
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE answer_ar ILIKE p)
                   ) AS score
            FROM faq
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND (
                    question_en ILIKE ANY($1) OR question_ar ILIKE ANY($1)
                 OR answer_en   ILIKE ANY($1) OR answer_ar   ILIKE ANY($1)
                 OR tags::text  ILIKE ANY($1)
              )
            ORDER BY score DESC, updated_at DESC
            LIMIT $2
            """,
            _patterns(keywords),
            max(1, min(int(limit), 10)),
        )
        return [dict(r) for r in rows]
    except Exception as exc:  # pragma: no cover - DB down / schema drift
        log.warning(
            "faq lookup failed", extra={"action": "knowledge_context.faq", "error": str(exc)}
        )
        return []


async def fetch_troubleshooting(keywords: list[str], *, limit: int = 2) -> list[dict[str, Any]]:
    if not keywords:
        return []
    try:
        from app.storage.pg import get_pool

        pool = await get_pool()
        rows = await pool.fetch(
            """
            SELECT title_en, title_ar, problem_en, problem_ar, solution_en, solution_ar,
                   category, severity,
                   (
                     (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE title_en ILIKE p) * 3
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE title_ar ILIKE p) * 3
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE tags::text ILIKE p) * 2
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE problem_en ILIKE p)
                   + (SELECT COUNT(*) FROM unnest($1::text[]) p WHERE problem_ar ILIKE p)
                   ) AS score
            FROM troubleshooting
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND (
                    title_en ILIKE ANY($1) OR title_ar ILIKE ANY($1)
                 OR problem_en ILIKE ANY($1) OR problem_ar ILIKE ANY($1)
                 OR tags::text ILIKE ANY($1)
              )
            ORDER BY score DESC, severity DESC
            LIMIT $2
            """,
            _patterns(keywords),
            max(1, min(int(limit), 5)),
        )
        return [dict(r) for r in rows]
    except Exception as exc:  # pragma: no cover
        log.warning(
            "troubleshooting lookup failed",
            extra={"action": "knowledge_context.troubleshooting", "error": str(exc)},
        )
        return []


@lru_cache(maxsize=1)
def _approved_docs() -> tuple[Any, ...]:
    """Approved public/internal docs, parsed once per process."""
    try:
        from app.core.knowledge_base import load_documents

        docs, errors = load_documents(_KNOWLEDGE_ROOT)
        if errors:
            log.warning(
                "knowledge docs skipped",
                extra={"action": "knowledge_context.docs", "errors": errors[:5]},
            )
        return tuple(docs)
    except Exception as exc:  # pragma: no cover
        log.warning(
            "knowledge docs unavailable",
            extra={"action": "knowledge_context.docs", "error": str(exc)},
        )
        return ()


def reload_docs() -> int:
    """Drop the doc cache (e.g. after an admin edits product/knowledge)."""
    _approved_docs.cache_clear()
    return len(_approved_docs())


def _split_sections(text: str) -> list[str]:
    parts = re.split(r"\n(?=#{1,3}\s)", text)
    return [p.strip() for p in parts if p.strip()]


def search_docs(
    keywords: list[str], *, limit: int = 2, access_level: str = "public"
) -> list[dict[str, Any]]:
    """Score approved doc sections by keyword overlap; customer channels see only public docs."""
    if not keywords:
        return []
    allowed = {"public"} if access_level == "public" else {"public", "internal"}
    hits: list[tuple[int, str, str, int]] = []
    for doc in _approved_docs():
        if doc.sensitivity not in allowed:
            continue
        for section in _split_sections(doc.text):
            hay = section.casefold()
            score = sum(hay.count(k) for k in keywords)
            if score:
                hits.append((score, doc.title, section[:_DOC_SNIPPET_CHARS], int(doc.version)))
    hits.sort(key=lambda h: h[0], reverse=True)
    return [
        {"title": title, "version": version, "text": snippet, "score": score}
        for score, title, snippet, version in hits[:limit]
    ]


def _pick(row: dict[str, Any], en_key: str, ar_key: str, language: str) -> str:
    en = str(row.get(en_key) or "").strip()
    ar = str(row.get(ar_key) or "").strip()
    if language == "ar":
        return ar or en
    return en or ar


def format_knowledge_block(
    faq_rows: list[dict[str, Any]],
    issue_rows: list[dict[str, Any]],
    doc_hits: list[dict[str, Any]],
    *,
    language: str = "en",
) -> str:
    """Framed DATA block for the prompt. Empty string when nothing was found."""
    lang = (language or "en").lower()
    parts: list[str] = []
    for r in faq_rows:
        qq = _pick(r, "question_en", "question_ar", lang)
        aa = _pick(r, "answer_en", "answer_ar", lang)
        if qq and aa:
            parts.append(f"FAQ · {r.get('category') or 'general'}\nQ: {qq}\nA: {aa}")
    for r in issue_rows:
        title = _pick(r, "title_en", "title_ar", lang)
        sol = _pick(r, "solution_en", "solution_ar", lang)
        if title and sol:
            parts.append(
                f"GUIDE · {r.get('category') or 'support'} · severity {r.get('severity')}\n{title}\n{sol}"
            )
    for h in doc_hits:
        parts.append(f"DOC · {h['title']} v{h['version']}\n{h['text']}")
    if not parts:
        return ""
    body = "\n\n".join(parts)
    if len(body) > _MAX_BLOCK_CHARS:
        body = body[:_MAX_BLOCK_CHARS].rsplit("\n", 1)[0] + "\n…"
    framed = inspect_data(body, source="company knowledge base")
    return framed.text or ""


def citation_for(faq_rows: list[dict[str, Any]], doc_hits: list[dict[str, Any]]) -> str:
    """Short human label for the 📎 source line (never a URL)."""
    if doc_hits:
        return f"{doc_hits[0]['title']} v{doc_hits[0]['version']}"[:80]
    if faq_rows:
        return "Company FAQ"
    return ""


async def build_knowledge_context(
    user_text: str,
    *,
    language: str = "en",
    access_level: str = "public",
) -> dict[str, Any]:
    """One call for the skill runner: {'block', 'citation', 'hits', 'keywords'}."""
    keywords = keywords_for(user_text)
    if not keywords:
        return {"block": "", "citation": "", "hits": 0, "keywords": []}
    faq_rows = await fetch_faq(keywords)
    issue_rows = await fetch_troubleshooting(keywords)
    doc_hits = search_docs(keywords, access_level=access_level)
    block = format_knowledge_block(faq_rows, issue_rows, doc_hits, language=language)
    hits = len(faq_rows) + len(issue_rows) + len(doc_hits)
    log.info(
        "knowledge context",
        extra={
            "action": "knowledge_context.build",
            "keywords": keywords,
            "faq": len(faq_rows),
            "guides": len(issue_rows),
            "docs": len(doc_hits),
        },
    )
    return {
        "block": block,
        "citation": citation_for(faq_rows, doc_hits) if hits else "",
        "hits": hits,
        "keywords": keywords,
    }
