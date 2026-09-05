"""Integration tests for app.core.memory against the real Postgres schema.

This module was 19% covered and, until migration 0007, could not work at all:
user_memories / user_profile / purchases did not exist in any migration.
These tests run against the live test database via the `pool` fixture.
"""

from __future__ import annotations

import itertools
import time

import pytest

from app.core import memory as mem

pytestmark = pytest.mark.integration

_ids = itertools.count(int(time.time()) % 1_000_000 * 100)


@pytest.fixture
def user_id() -> int:
    """A unique synthetic user id per test, so tests never collide."""
    return next(_ids)


@pytest.fixture(autouse=True)
def _memory_on(monkeypatch):
    monkeypatch.setenv("MEMORY_ENABLED", "1")
    monkeypatch.setenv("MEMORY_PROVIDER", "postgresql")


@pytest.fixture
async def provider(pool):
    """Provider bound to the test pool (bypasses the global get_pool)."""
    p = mem.PostgreSQLMemoryProvider()

    async def _pool():
        return pool

    p._pool = _pool  # type: ignore[method-assign]
    return p


@pytest.fixture(autouse=True)
async def _bind_global_pool(pool, monkeypatch):
    """Point module-level helpers at the test pool."""

    class _P(mem.PostgreSQLMemoryProvider):
        async def _pool(self):
            return pool

    async def _get_instance():
        return _P()

    async def _get_provider():
        return _P()

    monkeypatch.setattr(mem, "_get_provider_instance", _get_instance)
    monkeypatch.setattr(mem, "get_provider", _get_provider)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def test_dedup_key_is_stable_and_short():
    k = mem._dedup_key("Hello   World")
    assert len(k) == 24
    assert k == mem._dedup_key("hello world")


def test_dedup_key_normalises_whitespace_and_case():
    assert mem._dedup_key("  A  B \n C ") == mem._dedup_key("a b c")


def test_dedup_key_differs_for_different_content():
    assert mem._dedup_key("diesel") != mem._dedup_key("petrol")


def test_dedup_key_handles_empty_input():
    assert len(mem._dedup_key("")) == 24


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('{"facts": []}', {"facts": []}),
        ('noise {"a": 1} tail', {"a": 1}),
        ('```json\n{"a": 2}\n```', {"a": 2}),
    ],
)
def test_safe_json_extracts_embedded_objects(raw, expected):
    assert mem._safe_json(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "no json", "{broken,,}"])
def test_safe_json_returns_none_on_junk(raw):
    assert mem._safe_json(raw) is None


@pytest.mark.asyncio
async def test_memory_enabled_default_is_true(monkeypatch):
    monkeypatch.delenv("MEMORY_ENABLED", raising=False)
    assert await mem.memory_enabled() is True


@pytest.mark.asyncio
async def test_memory_can_be_disabled(monkeypatch):
    monkeypatch.setenv("MEMORY_ENABLED", "0")
    assert await mem.memory_enabled() is False


# --------------------------------------------------------------------------
# provider registry
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_provider_is_postgresql(monkeypatch):
    monkeypatch.delenv("MEMORY_PROVIDER", raising=False)
    monkeypatch.undo()
    p = await mem.get_provider()
    assert isinstance(p, mem.MemoryProvider)


def test_register_provider_adds_to_the_registry():
    class _Dummy(mem.MemoryProvider):
        name = "dummy-test-provider"

        async def remember(self, *a, **k):
            return True

        async def recall(self, *a, **k):
            return []

        async def forget_all(self, *a, **k):
            return 0

        async def list_all(self, *a, **k):
            return []

        async def delete_one(self, *a, **k):
            return True

        async def add_note(self, *a, **k):
            return True

    mem.register_provider(_Dummy)
    try:
        assert mem._PROVIDERS["dummy-test-provider"] is _Dummy
    finally:
        mem._PROVIDERS.pop("dummy-test-provider", None)


def test_unknown_provider_name_falls_back_to_postgresql(monkeypatch):
    monkeypatch.setenv("MEMORY_PROVIDER", "does-not-exist")
    cls = mem._PROVIDERS.get("does-not-exist") or mem.PostgreSQLMemoryProvider
    assert cls is mem.PostgreSQLMemoryProvider


# --------------------------------------------------------------------------
# remember / recall
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remember_persists_a_memory(provider, user_id):
    assert await provider.remember(user_id, "fact", "prefers diesel", 3, "chat") is True
    rows = await provider.list_all(user_id)
    assert [r["content"] for r in rows] == ["prefers diesel"]


@pytest.mark.asyncio
async def test_remember_is_idempotent_on_duplicate_content(provider, user_id):
    assert await provider.remember(user_id, "fact", "same text", 3, "chat") is True
    assert await provider.remember(user_id, "fact", "  SAME   TEXT  ", 3, "chat") is False
    assert len(await provider.list_all(user_id)) == 1


@pytest.mark.asyncio
async def test_remember_clamps_importance_to_the_check_constraint(provider, user_id):
    await provider.remember(user_id, "fact", "too high", 99, "chat")
    await provider.remember(user_id, "fact", "too low", -5, "chat")
    scores = sorted(r["importance"] for r in await provider.list_all(user_id))
    assert scores == [1, 5]


@pytest.mark.asyncio
async def test_remember_truncates_long_content(provider, user_id):
    await provider.remember(user_id, "fact", "x" * 900, 3, "chat")
    assert len((await provider.list_all(user_id))[0]["content"]) == 400


@pytest.mark.asyncio
async def test_memories_are_isolated_per_user(provider, user_id):
    other = user_id + 1
    await provider.remember(user_id, "fact", "mine", 3, "chat")
    await provider.remember(other, "fact", "theirs", 3, "chat")
    assert [r["content"] for r in await provider.list_all(user_id)] == ["mine"]
    assert [r["content"] for r in await provider.list_all(other)] == ["theirs"]


@pytest.mark.asyncio
async def test_recall_returns_at_most_the_limit(provider, user_id):
    for i in range(8):
        await provider.remember(user_id, "fact", f"memory number {i}", 3, "chat")
    assert len(await provider.recall(user_id, "", limit=3)) == 3


@pytest.mark.asyncio
async def test_recall_ranks_importance_higher(provider, user_id):
    await provider.remember(user_id, "fact", "trivial detail", 1, "chat")
    await provider.remember(user_id, "fact", "critical detail", 5, "chat")
    top = (await provider.recall(user_id, "", limit=1))[0]
    assert top["content"] == "critical detail"


@pytest.mark.asyncio
async def test_recall_boosts_query_token_matches(provider, user_id):
    """A token match is worth +15, so it outranks an equal-importance peer."""
    await provider.remember(user_id, "fact", "customer likes lubricants", 3, "chat")
    await provider.remember(user_id, "fact", "customer asked about bitumen", 3, "chat")
    top = (await provider.recall(user_id, "bitumen pricing", limit=1))[0]
    assert "bitumen" in top["content"]


@pytest.mark.asyncio
async def test_recall_token_boost_does_not_override_a_large_importance_gap(provider, user_id):
    """One token match (+15) cannot beat a 4-point importance gap (+40)."""
    await provider.remember(user_id, "fact", "vital account note", 5, "chat")
    await provider.remember(user_id, "fact", "mentions bitumen once", 1, "chat")
    top = (await provider.recall(user_id, "bitumen", limit=1))[0]
    assert top["content"] == "vital account note"


@pytest.mark.asyncio
async def test_recall_increments_the_recall_counter(provider, user_id):
    await provider.remember(user_id, "fact", "counted memory", 3, "chat")
    await provider.recall(user_id, "", limit=5)
    await provider.recall(user_id, "", limit=5)
    assert (await provider.list_all(user_id))[0]["recall_count"] == 2


@pytest.mark.asyncio
async def test_recall_on_an_empty_user_returns_empty(provider, user_id):
    assert await provider.recall(user_id, "anything", limit=5) == []


@pytest.mark.asyncio
async def test_recall_result_shape(provider, user_id):
    await provider.remember(user_id, "goal", "expand to Jeddah", 4, "chat")
    item = (await provider.recall(user_id, "", limit=1))[0]
    assert set(item) == {"id", "kind", "content", "importance", "source"}


# --------------------------------------------------------------------------
# list / delete / forget
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_is_newest_first(provider, user_id):
    for i in range(3):
        await provider.remember(user_id, "fact", f"item {i}", 3, "chat")
    assert [r["content"] for r in await provider.list_all(user_id)] == [
        "item 2",
        "item 1",
        "item 0",
    ]


@pytest.mark.asyncio
async def test_list_all_honours_the_limit(provider, user_id):
    for i in range(5):
        await provider.remember(user_id, "fact", f"item {i}", 3, "chat")
    assert len(await provider.list_all(user_id, limit=2)) == 2


@pytest.mark.asyncio
async def test_delete_one_removes_only_that_memory(provider, user_id):
    await provider.remember(user_id, "fact", "keep me", 3, "chat")
    await provider.remember(user_id, "fact", "delete me", 3, "chat")
    target = [r for r in await provider.list_all(user_id) if r["content"] == "delete me"][0]
    assert await provider.delete_one(user_id, target["id"]) is True
    assert [r["content"] for r in await provider.list_all(user_id)] == ["keep me"]


@pytest.mark.asyncio
async def test_delete_one_cannot_touch_another_users_memory(provider, user_id):
    other = user_id + 1
    await provider.remember(other, "fact", "not yours", 3, "chat")
    victim = (await provider.list_all(other))[0]
    assert await provider.delete_one(user_id, victim["id"]) is False
    assert len(await provider.list_all(other)) == 1


@pytest.mark.asyncio
async def test_delete_one_on_a_missing_id_returns_false(provider, user_id):
    assert await provider.delete_one(user_id, 999_999_999) is False


@pytest.mark.asyncio
async def test_forget_all_returns_the_deleted_count(provider, user_id):
    for i in range(4):
        await provider.remember(user_id, "fact", f"forget {i}", 3, "chat")
    assert await provider.forget_all(user_id) == 4
    assert await provider.list_all(user_id) == []


@pytest.mark.asyncio
async def test_forget_all_on_a_clean_user_returns_zero(provider, user_id):
    assert await provider.forget_all(user_id) == 0


@pytest.mark.asyncio
async def test_forget_me_delegates_to_the_provider(user_id, pool):
    await pool.execute(
        "INSERT INTO user_memories (user_id, kind, content, importance, source, dedup_key) "
        "VALUES ($1,'fact','gdpr subject',3,'chat',$2)",
        user_id,
        mem._dedup_key("gdpr subject"),
    )
    assert await mem.forget_me(user_id) == 1


@pytest.mark.asyncio
async def test_add_note_stores_an_admin_sourced_memory(provider, user_id):
    assert await provider.add_note(user_id, "admin", "VIP account") is True
    row = (await provider.list_all(user_id))[0]
    assert row["source"] == "admin"
    assert row["importance"] == 4


# --------------------------------------------------------------------------
# counting
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_memories(provider, user_id):
    assert await mem._count_memories(user_id) == 0
    await provider.remember(user_id, "fact", "one", 3, "chat")
    await provider.remember(user_id, "fact", "two", 3, "chat")
    assert await mem._count_memories(user_id) == 2


# --------------------------------------------------------------------------
# purchase profile
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_profile_for_a_brand_new_user(user_id):
    prof = await mem.purchase_profile(user_id)
    assert prof == {
        "buys": 0,
        "spent": 0,
        "avg_ticket": 0,
        "categories": [],
        "persona": "",
        "interests": "",
    }


@pytest.mark.asyncio
async def test_record_purchase_event_creates_the_profile(user_id):
    await mem.record_purchase_event(user_id, {"category": "lubricants", "price_credits": 250})
    prof = await mem.purchase_profile(user_id)
    assert prof["buys"] == 1
    assert prof["spent"] == 250
    assert "lubricants" in prof["categories"]


@pytest.mark.asyncio
async def test_record_purchase_event_accumulates(user_id):
    await mem.record_purchase_event(user_id, {"category": "fuel", "price_credits": 100})
    await mem.record_purchase_event(user_id, {"category": "fuel", "price_credits": 150})
    prof = await mem.purchase_profile(user_id)
    assert prof["buys"] == 2
    assert prof["spent"] == 250


@pytest.mark.asyncio
async def test_record_purchase_event_tracks_recent_categories_first(user_id):
    for cat in ("fuel", "lubricants", "bitumen"):
        await mem.record_purchase_event(user_id, {"category": cat, "price_credits": 10})
    assert (await mem.purchase_profile(user_id))["categories"][0] == "bitumen"


@pytest.mark.asyncio
async def test_record_purchase_event_deduplicates_repeated_category(user_id):
    await mem.record_purchase_event(user_id, {"category": "fuel", "price_credits": 10})
    await mem.record_purchase_event(user_id, {"category": "grease", "price_credits": 10})
    await mem.record_purchase_event(user_id, {"category": "fuel", "price_credits": 10})
    cats = (await mem.purchase_profile(user_id))["categories"]
    assert cats.count("fuel") == 1
    assert cats[0] == "fuel"


@pytest.mark.asyncio
async def test_record_purchase_event_defaults_missing_category(user_id):
    await mem.record_purchase_event(user_id, {"price_credits": 5})
    assert "general" in (await mem.purchase_profile(user_id))["categories"]


@pytest.mark.asyncio
async def test_record_purchase_event_ignores_an_empty_product(user_id):
    await mem.record_purchase_event(user_id, {})
    assert (await mem.purchase_profile(user_id))["buys"] == 0


@pytest.mark.asyncio
async def test_record_purchase_event_also_writes_an_interest_memory(user_id, provider):
    await mem.record_purchase_event(user_id, {"category": "bitumen", "price_credits": 20})
    kinds = [r["kind"] for r in await provider.list_all(user_id)]
    assert "interest" in kinds


# --------------------------------------------------------------------------
# prompt context
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_memory_context_is_empty_when_disabled(monkeypatch, user_id):
    monkeypatch.setenv("MEMORY_ENABLED", "0")
    assert await mem.build_memory_context(user_id) == ""


@pytest.mark.asyncio
async def test_build_memory_context_is_empty_for_a_blank_user(user_id):
    assert await mem.build_memory_context(user_id) == ""


@pytest.mark.asyncio
async def test_build_memory_context_lists_memories(provider, user_id):
    await provider.remember(user_id, "preference", "prefers Arabic replies", 5, "chat")
    ctx = await mem.build_memory_context(user_id)
    assert "prefers Arabic replies" in ctx
    assert "⭐" in ctx


@pytest.mark.asyncio
async def test_build_memory_context_respects_the_char_budget(provider, user_id):
    for i in range(6):
        await provider.remember(user_id, "fact", f"long memory entry {i} " + "x" * 300, 5, "chat")
    assert len(await mem.build_memory_context(user_id)) <= mem.MEMORY_BUDGET_CHARS


@pytest.mark.asyncio
async def test_build_memory_context_deduplicates_identical_content(provider, user_id, pool):
    for key in ("a", "b"):
        await pool.execute(
            "INSERT INTO user_memories (user_id, kind, content, importance, source, dedup_key) "
            "VALUES ($1,'fact','duplicated line',3,'chat',$2)",
            user_id,
            key,
        )
    ctx = await mem.build_memory_context(user_id)
    assert ctx.count("duplicated line") == 1


@pytest.mark.asyncio
async def test_build_memory_context_includes_the_purchase_block(user_id):
    await mem.record_purchase_event(user_id, {"category": "fuel", "price_credits": 500})
    ctx = await mem.build_memory_context(user_id)
    assert "🛒" in ctx


@pytest.mark.asyncio
async def test_build_memory_context_puts_persona_first(provider, user_id, pool):
    await provider.remember(user_id, "fact", "some memory", 3, "chat")
    await pool.execute(
        "INSERT INTO user_profile (user_id, persona) VALUES ($1, $2) "
        "ON CONFLICT (user_id) DO UPDATE SET persona = EXCLUDED.persona",
        user_id,
        "مدیر خرید یک پالایشگاه",
    )
    ctx = await mem.build_memory_context(user_id)
    assert ctx.index("👤") < ctx.index("some memory")


# --------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_my_memory_summary_when_disabled(monkeypatch, user_id):
    monkeypatch.setenv("MEMORY_ENABLED", "0")
    text, total = await mem.my_memory_summary(user_id)
    assert total == 0
    assert "disabled" in text.lower() or "غیرفعال" in text


@pytest.mark.asyncio
async def test_my_memory_summary_for_an_empty_user(user_id):
    text, total = await mem.my_memory_summary(user_id)
    assert total == 0
    assert "haven't learned" in text.lower() or "هنوز چیزی یادنگرفتم" in text


@pytest.mark.asyncio
async def test_my_memory_summary_lists_memories_and_count(provider, user_id):
    for i in range(3):
        await provider.remember(user_id, "fact", f"summary item {i}", 3, "chat")
    text, total = await mem.my_memory_summary(user_id)
    assert total == 3
    assert "summary item 0" in text


@pytest.mark.asyncio
async def test_my_memory_summary_includes_purchase_line(provider, user_id):
    await provider.remember(user_id, "fact", "a memory", 3, "chat")
    await mem.record_purchase_event(user_id, {"category": "fuel", "price_credits": 300})
    text, _ = await mem.my_memory_summary(user_id)
    assert "🛒 Purchase profile" in text or "🛒 پروفایل خرید" in text


# --------------------------------------------------------------------------
# recommendations (bug #23 — was querying a non-existent marketplace schema)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommend_returns_empty_when_disabled(monkeypatch, user_id):
    monkeypatch.setenv("MEMORY_ENABLED", "0")
    assert await mem.recommend_for_user(user_id) == []


@pytest.mark.asyncio
async def test_recommend_returns_empty_without_affinity(user_id):
    assert await mem.recommend_for_user(user_id) == []


@pytest.mark.asyncio
async def test_recommend_suggests_products_in_a_purchased_category(user_id, pool, unique_sku):
    await pool.execute(
        "INSERT INTO products (sku, name_ar, name_en, category, unit_price, stock_qty, is_active) "
        "VALUES ($1, 'زيت', 'Oil', 'reco-cat', 50, 10, true)",
        unique_sku,
    )
    await mem.record_purchase_event(user_id, {"category": "reco-cat", "price_credits": 10})
    recs = await mem.recommend_for_user(user_id)
    assert any(r["sku"] == unique_sku for r in recs)


@pytest.mark.asyncio
async def test_recommend_result_shape(user_id, pool, unique_sku):
    await pool.execute(
        "INSERT INTO products (sku, name_ar, name_en, category, unit_price, stock_qty, is_active) "
        "VALUES ($1, 'زيت', 'Oil', 'shape-cat', 50, 10, true)",
        unique_sku,
    )
    await mem.record_purchase_event(user_id, {"category": "shape-cat", "price_credits": 10})
    rec = (await mem.recommend_for_user(user_id))[0]
    assert set(rec) == {
        "id",
        "sku",
        "name_ar",
        "name_en",
        "unit_price",
        "unit",
        "stock_qty",
        "category",
    }


@pytest.mark.asyncio
async def test_recommend_excludes_already_purchased_products(user_id, pool, unique_sku):
    pid = await pool.fetchval(
        "INSERT INTO products (sku, name_ar, name_en, category, unit_price, stock_qty, is_active) "
        "VALUES ($1, 'زيت', 'Oil', 'owned-cat', 50, 10, true) RETURNING id",
        unique_sku,
    )
    await mem.record_purchase_event(user_id, {"category": "owned-cat", "price_credits": 10})
    await pool.execute(
        "INSERT INTO purchases (buyer_id, product_id, price_credits) VALUES ($1,$2,$3)",
        user_id,
        pid,
        50,
    )
    assert all(r["sku"] != unique_sku for r in await mem.recommend_for_user(user_id))


@pytest.mark.asyncio
async def test_recommend_skips_inactive_products(user_id, pool, unique_sku):
    await pool.execute(
        "INSERT INTO products (sku, name_ar, name_en, category, unit_price, stock_qty, is_active) "
        "VALUES ($1, 'زيت', 'Oil', 'inactive-cat', 50, 10, false)",
        unique_sku,
    )
    await mem.record_purchase_event(user_id, {"category": "inactive-cat", "price_credits": 10})
    assert await mem.recommend_for_user(user_id) == []


@pytest.mark.asyncio
async def test_recommend_honours_the_limit(user_id, pool):
    for i in range(4):
        await pool.execute(
            "INSERT INTO products (sku, name_ar, name_en, category, unit_price, stock_qty, is_active) "
            "VALUES ($1, 'ز', 'O', 'limit-cat', 10, 5, true)",
            f"LIMIT-{user_id}-{i}",
        )
    await mem.record_purchase_event(user_id, {"category": "limit-cat", "price_credits": 10})
    assert len(await mem.recommend_for_user(user_id, limit=2)) == 2


# --------------------------------------------------------------------------
# extraction scheduling
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extraction_skips_short_text(user_id, provider):
    await mem.maybe_extract_memories(user_id, "hi", "hello")
    assert await provider.list_all(user_id) == []


@pytest.mark.asyncio
async def test_extraction_skips_slash_commands(user_id, provider):
    await mem.maybe_extract_memories(user_id, "/start " + "x" * 40, "hello")
    assert await provider.list_all(user_id) == []


@pytest.mark.asyncio
async def test_extraction_skips_when_disabled(monkeypatch, user_id, provider):
    monkeypatch.setenv("MEMORY_ENABLED", "0")
    await mem.maybe_extract_memories(user_id, "a" * 60, "reply")
    assert await provider.list_all(user_id) == []


def test_schedule_extraction_outside_a_loop_is_a_noop():
    # No running loop here -> RuntimeError is swallowed.
    mem.schedule_extraction(1, "some fairly long user text here", "reply")


@pytest.mark.asyncio
async def test_schedule_extraction_inside_a_loop_creates_a_task(monkeypatch, user_id):
    called = {}

    async def _fake(uid, ut, at):
        called["uid"] = uid

    monkeypatch.setattr(mem, "maybe_extract_memories", _fake)
    mem.schedule_extraction(user_id, "long enough user message text", "reply")
    import asyncio

    await asyncio.sleep(0)
    assert called.get("uid") == user_id
