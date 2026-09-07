"""Catalog fetch + outbound tool-JSON strip for Telegram."""

from __future__ import annotations

from app.core.catalog_context import (
    claims_no_catalog,
    customer_catalog_reply,
    leaked_tool_protocol,
    strip_tool_protocol,
    wants_catalog,
)
from app.core.postprocess import run as postprocess_run
from app.core.security_stack import inspect_outbound

LEAK = (
    "I'll retrieve the product catalog using the available tools.\n\n"
    "---\n\n"
    "مسنجر مکالمه:\n"
    'conversation: { "tool": "list_products", "args": {} }\n'
)

NO_DB = "متأسفانه در حال حاضر امکان اتصال به پایگاه داده محصولات فراهم نیست."

SAMPLE = [
    {
        "sku": "PET-001",
        "name_ar": "زيت تشحيم أساسي G50",
        "name_en": "Base Lubricant Oil G50",
        "category": "lubricants",
        "unit_price": 85.0,
        "currency": "SAR",
    }
]


def test_wants_catalog_persian_question() -> None:
    assert wants_catalog("چه محصولاتی دارید")
    assert wants_catalog("what products do you have")
    assert wants_catalog("PET-001")
    assert not wants_catalog("سلام، ساعت کار چیست؟")
    assert not wants_catalog("production outage on line 3")


def test_strip_tool_protocol_drops_list_products() -> None:
    cleaned = strip_tool_protocol(LEAK)
    assert "list_products" not in cleaned
    assert "مسنجر مکالمه" not in cleaned
    assert "I'll retrieve" not in cleaned


def test_postprocess_strips_tool_json() -> None:
    from app.core import postprocess as pp

    class _Cfg:
        class _Domain:
            numeral_style = "western"

        domain = _Domain()

    report = pp.run(LEAK, config=_Cfg())  # type: ignore[arg-type]
    assert "list_products" not in report.text
    assert "strip_tool_protocol" in report.fixes_applied


def test_inspect_outbound_does_not_send_tool_json() -> None:
    verdict = inspect_outbound(LEAK)
    assert "list_products" not in (verdict.text or "")
    assert "args" not in (verdict.text or "")


def test_claims_no_catalog() -> None:
    assert claims_no_catalog(NO_DB)
    assert leaked_tool_protocol(LEAK)


def test_customer_catalog_reply_lists_sku() -> None:
    fa = customer_catalog_reply(SAMPLE, language="fa")
    assert "PET-001" in fa
    assert "list_products" not in fa
    assert "tool" not in fa
