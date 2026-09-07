"""Load the live product catalog into the reply path.

The LLM must never invent SKUs or dump tool JSON to the customer.
Read-only list/search runs here, before the model writes a word.
"""

from __future__ import annotations

import re
from typing import Any

_CATALOG_MARKERS = (
    "محصول",
    "محصولات",
    "کاتالوگ",
    "catalog",
    "چه دارید",
    "چی دارید",
    "what do you sell",
    "what do you have",
    "price list",
    "لیست قیمت",
    "lubricant",
    "روغن",
)

_NO_ACCESS = (
    "پایگاه داده محصولات",
    "امکان اتصال",
    "don't have access",
    "do not have access",
    "catalog is not",
    "no catalog",
    "database is not available",
    "using the available tools",
)

_TOOL_JSON = re.compile(r"\{[^{}]*tool[^{}]*args[^{}]*\}", re.I | re.DOTALL)
_CONVERSATION_BLOCK = re.compile(
    r"(?im)^(?:conversation|مسنجر مکالمه)\s*:?\s*",
)
_RETRIEVE_LINE = re.compile(
    r"(?i)i['’]?ll retrieve the product catalog[^\n]*",
)
_DASH_RULE = re.compile(r"(?m)^-{2,}\s*$")
_PROTOCOL_LINE = re.compile(
    r"(list_products|search_products|" + r'"tool"|' + r"'tool'|" + r'"args"|' + r"'args')",
    re.I,
)
_SKU_RE = re.compile(r"\b[A-Za-z]{2,8}-\d{2,}\b")
_PRODUCT_WORD = re.compile(r"\bproducts?\b", re.I)
_SKU_WORD = re.compile(r"\bsku\b", re.I)


def wants_catalog(text: str) -> bool:
    raw = text or ""
    hay = raw.casefold()
    if any(m.casefold() in hay for m in _CATALOG_MARKERS):
        return True
    if _PRODUCT_WORD.search(hay) or _SKU_WORD.search(hay):
        return True
    return bool(_SKU_RE.search(raw))


def leaked_tool_protocol(text: str) -> bool:
    raw = text or ""
    if '"tool"' in raw and "args" in raw:
        return True
    if "list_products" in raw:
        return True
    if "مسنجر مکالمه" in raw:
        return True
    if _RETRIEVE_LINE.search(raw):
        return True
    return False


def claims_no_catalog(text: str) -> bool:
    hay = (text or "").casefold()
    return any(m.casefold() in hay for m in _NO_ACCESS)


def strip_tool_protocol(text: str) -> str:
    """Remove leaked tool-call JSON and messenger traces from a customer reply."""
    if not text:
        return ""
    out = _TOOL_JSON.sub("", text)
    out = _RETRIEVE_LINE.sub("", out)
    kept: list[str] = []
    for line in out.splitlines():
        if _PROTOCOL_LINE.search(line):
            continue
        if _CONVERSATION_BLOCK.match(line.strip()):
            continue
        if _DASH_RULE.match(line.strip()):
            continue
        kept.append(line)
    out = "\n".join(kept)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def format_catalog_lines(products: list[dict[str, Any]], *, language: str = "en") -> str:
    """Compact per-language lines for the LLM DATA block and text channels.

    1.4.0: English is the canonical name; ``names[lang]`` is the display layer.
    Legacy ``name_ar`` is used only when the customer speaks Arabic and no
    English name exists (old rows).
    """
    from app.core.catalog_i18n import format_money, product_code, product_name, product_price

    lang = (language or "en").lower()
    lines: list[str] = []
    for row in products:
        sku = str(row.get("sku") or "").strip()
        name = product_name(row, lang)
        code = product_code(row)
        cat = str(row.get("category") or "")
        price = product_price(row)
        cur = str(row.get("currency") or "USD")
        bit = f"- {name}"
        if code and code != sku:
            bit += f" · code {code}"
        if sku:
            bit += f" · SKU {sku}"
        if cat:
            bit += f" · {cat}"
        if price > 0:
            bit += f" · {format_money(price, cur, lang)}"
        lines.append(bit)
    return "\n".join(lines)


def customer_catalog_reply(products: list[dict[str, Any]], *, language: str = "en") -> str:
    """Clean catalog answer in the customer's language (no Markdown, no JSON)."""
    from app.core.catalog_i18n import render_catalog, t

    lang = (language or "en").lower()
    if not products:
        return t(lang, "empty")
    return render_catalog(products, language=lang)


async def fetch_active_products(*, limit: int = 20) -> list[dict[str, Any]]:
    """Read active products with their per-language names (1.4.0 columns first)."""
    cap = max(1, min(int(limit), 50))
    try:
        from app.core.shop_flow import load_catalog
        from app.storage.pg import get_pool

        pool = await get_pool()
        products, _categories = await load_catalog(pool)
        if products:
            return products[:cap]
    except Exception:
        pass
    try:
        from app.storage.pg import get_pool

        pool = await get_pool()
        rows = await pool.fetch(
            """
            SELECT id, sku, code, name_ar, name_en, title_en, names, titles, category, unit,
                   currency, COALESCE(unit_price, 0) AS unit_price,
                   COALESCE(base_price, 0) AS base_price, image_url, sort_order
            FROM products
            WHERE COALESCE(is_active, TRUE) = TRUE
            ORDER BY sort_order, name_en
            LIMIT $1
            """,
            cap,
        )
        return [dict(r) for r in rows]
    except Exception:
        return []
