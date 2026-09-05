"""Unit tests for app.core.context (was 0% covered).

context.build() lazily imports repository helpers inside the function body, so
they are monkeypatched on app.core.repository directly.
"""

from __future__ import annotations

import pytest

from app.core import context

pytestmark = pytest.mark.asyncio


class _FakePool:
    """Marker object — the repository functions are patched, not the pool."""


def _patch_repo(monkeypatch, *, customer=None, history=None, catalog=None):
    from app.core import repository

    async def _get_customer(pg, customer_id):
        return customer

    async def _get_history(pg, conversation_id, limit=10):
        return history or []

    async def _search_catalog(pg, query, limit=20):
        return catalog or []

    monkeypatch.setattr(repository, "get_customer", _get_customer)
    monkeypatch.setattr(repository, "get_conversation_history", _get_history)
    monkeypatch.setattr(repository, "search_catalog", _search_catalog)


# --------------------------------------------------------------------------
# build() — base fields
# --------------------------------------------------------------------------


async def test_build_without_pg_returns_only_static_fields():
    ctx = await context.build(conversation_id="c1", customer_id="cu1", channel="telegram")
    assert ctx["conversation_id"] == "c1"
    assert ctx["customer_id"] == "cu1"
    assert ctx["channel"] == "telegram"
    assert ctx["language"] == "ar"
    assert "customer_name" not in ctx
    assert "history" not in ctx


async def test_build_pulls_currency_and_style_from_config():
    from app.config import get_config

    cfg = get_config()
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web")
    assert ctx["currency"] == cfg.domain.currency
    assert ctx["numeral_style"] == cfg.domain.numeral_style
    assert ctx["reply_language_policy"] == cfg.domain.reply_language_policy


async def test_build_language_override():
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", language="en")
    assert ctx["language"] == "en"


# --------------------------------------------------------------------------
# build() — customer + history enrichment
# --------------------------------------------------------------------------


async def test_build_injects_customer_profile(monkeypatch):
    _patch_repo(
        monkeypatch,
        customer={
            "display_name": "Acme Petro",
            "channel": "whatsapp",
            "tags": ["vip", "wholesale"],
            "lead_score": 82,
        },
    )
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", pg=_FakePool())
    assert ctx["customer_name"] == "Acme Petro"
    assert ctx["customer_channel"] == "whatsapp"
    assert ctx["customer_tags"] == ["vip", "wholesale"]
    assert ctx["customer_lead_score"] == 82


async def test_build_tolerates_a_sparse_customer_row(monkeypatch):
    """A row present but missing optional columns must use safe defaults."""
    _patch_repo(monkeypatch, customer={"id": "x"})
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", pg=_FakePool())
    assert ctx["customer_name"] == ""
    assert ctx["customer_tags"] == []
    assert ctx["customer_lead_score"] == 0


async def test_build_skips_customer_fields_for_an_empty_row(monkeypatch):
    """An empty dict is falsy, so no customer_* keys are added."""
    _patch_repo(monkeypatch, customer={})
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", pg=_FakePool())
    assert "customer_name" not in ctx


async def test_build_skips_customer_fields_when_row_missing(monkeypatch):
    _patch_repo(monkeypatch, customer=None)
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", pg=_FakePool())
    assert "customer_name" not in ctx


async def test_build_normalises_history_to_role_content(monkeypatch):
    _patch_repo(
        monkeypatch,
        history=[
            {"role": "user", "content": "price?", "extra": "dropped"},
            {"content": "no role key"},
        ],
    )
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", pg=_FakePool())
    assert ctx["history"] == [
        {"role": "user", "content": "price?"},
        {"role": "user", "content": "no role key"},
    ]


async def test_build_omits_history_key_when_empty(monkeypatch):
    _patch_repo(monkeypatch, history=[])
    ctx = await context.build(conversation_id="c", customer_id="x", channel="web", pg=_FakePool())
    assert "history" not in ctx


# --------------------------------------------------------------------------
# build() — memory injection
# --------------------------------------------------------------------------


class _Memory:
    def __init__(self, result="remembered facts", exc=None):
        self.result = result
        self.exc = exc
        self.seen: list[tuple] = []

    async def build_memory_context(self, user_id, query=""):
        self.seen.append((user_id, query))
        if self.exc:
            raise self.exc
        return self.result


async def test_memory_context_is_injected():
    mem = _Memory()
    ctx = await context.build(conversation_id="c", customer_id="42", channel="web", memory=mem)
    assert ctx["memory_context"] == "remembered facts"


async def test_numeric_customer_id_is_passed_through_as_int():
    mem = _Memory()
    await context.build(conversation_id="c", customer_id="42", channel="web", memory=mem)
    assert mem.seen[0][0] == 42


async def test_non_numeric_customer_id_is_hashed_to_positive_int():
    mem = _Memory()
    await context.build(
        conversation_id="c", customer_id="a-uuid-like-value", channel="web", memory=mem
    )
    user_id = mem.seen[0][0]
    assert isinstance(user_id, int)
    assert 0 <= user_id <= 0x7FFFFFFF


async def test_query_is_taken_from_extra():
    mem = _Memory()
    await context.build(
        conversation_id="c",
        customer_id="1",
        channel="web",
        memory=mem,
        extra={"query": "diesel spec"},
    )
    assert mem.seen[0][1] == "diesel spec"


async def test_query_defaults_to_empty_without_extra():
    mem = _Memory()
    await context.build(conversation_id="c", customer_id="1", channel="web", memory=mem)
    assert mem.seen[0][1] == ""


async def test_empty_memory_result_is_not_injected():
    ctx = await context.build(
        conversation_id="c", customer_id="1", channel="web", memory=_Memory(result="")
    )
    assert "memory_context" not in ctx


async def test_memory_failure_is_swallowed():
    mem = _Memory(exc=RuntimeError("vector store down"))
    ctx = await context.build(conversation_id="c", customer_id="1", channel="web", memory=mem)
    assert "memory_context" not in ctx
    assert ctx["conversation_id"] == "c"


async def test_memory_object_without_the_hook_is_ignored():
    ctx = await context.build(conversation_id="c", customer_id="1", channel="web", memory=object())
    assert "memory_context" not in ctx


# --------------------------------------------------------------------------
# build() — extra merge
# --------------------------------------------------------------------------


async def test_extra_fields_are_merged():
    ctx = await context.build(
        conversation_id="c",
        customer_id="1",
        channel="web",
        extra={"skill": "sales", "intent": "quote"},
    )
    assert ctx["skill"] == "sales" and ctx["intent"] == "quote"


async def test_extra_overrides_computed_fields():
    ctx = await context.build(
        conversation_id="c",
        customer_id="1",
        channel="web",
        extra={"language": "fr"},
    )
    assert ctx["language"] == "fr"


# --------------------------------------------------------------------------
# catalog_hints()
# --------------------------------------------------------------------------


async def test_catalog_hints_without_pg_returns_empty():
    assert await context.catalog_hints("diesel") == []


async def test_catalog_hints_projects_only_prompt_safe_fields(monkeypatch):
    _patch_repo(
        monkeypatch,
        catalog=[
            {
                "sku": "D-100",
                "name_ar": "ديزل",
                "name_en": "Diesel",
                "unit_price": 12.5,
                "unit": "L",
                "category": "fuel",
                "internal_cost": 9.0,
                "supplier": "secret",
            }
        ],
    )
    hints = await context.catalog_hints("diesel", pg=_FakePool())
    assert hints == [
        {
            "sku": "D-100",
            "name_ar": "ديزل",
            "name_en": "Diesel",
            "unit_price": 12.5,
            "unit": "L",
            "category": "fuel",
        }
    ]
    assert "internal_cost" not in hints[0]
    assert "supplier" not in hints[0]


async def test_catalog_hints_fills_defaults_for_missing_columns(monkeypatch):
    _patch_repo(monkeypatch, catalog=[{"sku": "X"}])
    hints = await context.catalog_hints("x", pg=_FakePool())
    assert hints[0] == {
        "sku": "X",
        "name_ar": "",
        "name_en": "",
        "unit_price": 0,
        "unit": "",
        "category": "",
    }


async def test_catalog_hints_empty_result(monkeypatch):
    _patch_repo(monkeypatch, catalog=[])
    assert await context.catalog_hints("nothing", pg=_FakePool()) == []


async def test_catalog_hints_forwards_the_limit(monkeypatch):
    from app.core import repository

    seen = {}

    async def _search(pg, query, limit=20):
        seen["query"] = query
        seen["limit"] = limit
        return []

    monkeypatch.setattr(repository, "search_catalog", _search)
    await context.catalog_hints("grease", pg=_FakePool(), limit=3)
    assert seen == {"query": "grease", "limit": 3}
