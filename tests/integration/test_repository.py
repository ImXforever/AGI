"""Integration tests for the data-access layer.

`app.core.repository` is the only module that writes conversations, messages
and approvals, and every SQL string in it is unverified until it actually hits
PostgreSQL. These tests run against the real throwaway database so that column
names, jsonb casts and RETURNING semantics are all exercised for real.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core import repository as repo
from tests.conftest import requires_infra

pytestmark = [pytest.mark.integration, requires_infra]


@pytest.fixture
async def customer(pool: Any) -> dict[str, Any]:
    return await repo.get_or_create_customer(
        pool, channel="telegram", sender_id=f"u-{uuid.uuid4().hex[:8]}", sender_name="Test User"
    )


@pytest.fixture
async def conversation(pool: Any, customer: dict[str, Any]) -> dict[str, Any]:
    return await repo.get_or_create_conversation(
        pool,
        conversation_id=str(uuid.uuid4()),
        customer_id=customer["id"],
        channel="telegram",
    )


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


class TestCustomers:
    async def test_create_then_fetch_round_trip(self, pool: Any, customer: dict[str, Any]):
        fetched = await repo.get_customer(pool, customer["id"])
        assert fetched is not None
        assert fetched["external_id"] == customer["external_id"]
        assert fetched["channel"] == "telegram"

    async def test_get_or_create_is_idempotent(self, pool: Any, customer: dict[str, Any]):
        again = await repo.get_or_create_customer(
            pool, channel="telegram", sender_id=customer["external_id"]
        )
        assert again["id"] == customer["id"]

    async def test_same_external_id_on_another_channel_is_a_different_customer(self, pool: Any):
        ext = f"u-{uuid.uuid4().hex[:8]}"
        a = await repo.get_or_create_customer(pool, channel="telegram", sender_id=ext)
        b = await repo.get_or_create_customer(pool, channel="whatsapp", sender_id=ext)
        assert a["id"] != b["id"]

    async def test_unknown_customer_is_none(self, pool: Any):
        assert await repo.get_customer(pool, str(uuid.uuid4())) is None

    async def test_update_writes_the_field(self, pool: Any, customer: dict[str, Any]):
        assert await repo.update_customer(pool, customer["id"], {"display_name": "Renamed"}) is True
        assert (await repo.get_customer(pool, customer["id"]))["display_name"] == "Renamed"

    async def test_update_with_no_fields_is_a_noop(self, pool: Any, customer: dict[str, Any]):
        assert await repo.update_customer(pool, customer["id"], {}) is False

    async def test_update_of_a_missing_row_reports_failure(self, pool: Any):
        assert await repo.update_customer(pool, str(uuid.uuid4()), {"display_name": "x"}) is False


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class TestConversations:
    async def test_create_then_fetch_round_trip(self, pool: Any, conversation: dict[str, Any]):
        fetched = await repo.get_conversation(pool, conversation["id"])
        assert fetched is not None and fetched["status"] == "active"

    async def test_get_or_create_is_idempotent(self, pool: Any, conversation: dict[str, Any]):
        again = await repo.get_or_create_conversation(
            pool,
            conversation_id=conversation["id"],
            customer_id=conversation["customer_id"],
            channel="telegram",
        )
        assert again["id"] == conversation["id"]

    async def test_unknown_conversation_is_none(self, pool: Any):
        assert await repo.get_conversation(pool, str(uuid.uuid4())) is None

    async def test_status_can_be_changed(self, pool: Any, conversation: dict[str, Any]):
        assert await repo.set_conversation_status(pool, conversation["id"], "closed") is True
        assert (await repo.get_conversation(pool, conversation["id"]))["status"] == "closed"

    async def test_status_change_on_missing_row_reports_failure(self, pool: Any):
        assert await repo.set_conversation_status(pool, str(uuid.uuid4()), "closed") is False

    async def test_fetch_conversation_is_an_alias(self, pool: Any, conversation: dict[str, Any]):
        assert (await repo.fetch_conversation(pool, conversation["id"]))["id"] == conversation["id"]

    async def test_listing_filters_by_customer(self, pool: Any, conversation: dict[str, Any]):
        rows = await repo.list_conversations(pool, customer_id=conversation["customer_id"])
        assert [str(r["id"]) for r in rows] == [str(conversation["id"])]

    async def test_listing_filters_by_status(self, pool: Any, conversation: dict[str, Any]):
        rows = await repo.list_conversations(
            pool, customer_id=conversation["customer_id"], status="active"
        )
        assert len(rows) == 1
        none_left = await repo.list_conversations(
            pool, customer_id=conversation["customer_id"], status="archived"
        )
        assert none_left == []

    async def test_limit_is_honoured(self, pool: Any, customer: dict[str, Any]):
        for _ in range(3):
            await repo.get_or_create_conversation(
                pool,
                conversation_id=str(uuid.uuid4()),
                customer_id=customer["id"],
                channel="telegram",
            )
        assert len(await repo.list_conversations(pool, customer_id=customer["id"], limit=2)) == 2


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class TestMessages:
    async def test_stored_message_comes_back_in_history(
        self, pool: Any, conversation: dict[str, Any]
    ):
        mid = await repo.store_message(
            pool, conversation_id=conversation["id"], role="user", content="مرحبا"
        )
        assert mid
        history = await repo.get_conversation_history(pool, conversation["id"])
        assert [h["content"] for h in history] == ["مرحبا"]
        assert history[0]["role"] == "user"

    async def test_metadata_is_stored_as_jsonb(self, pool: Any, conversation: dict[str, Any]):
        """asyncpg will not coerce a dict into jsonb by itself — this proves the
        repository does the json.dumps that the raw driver requires."""
        mid = await repo.store_message(
            pool,
            conversation_id=conversation["id"],
            role="user",
            content="hi",
            metadata={"nested": {"a": 1}, "list": [1, 2]},
        )
        raw = await pool.fetchval("SELECT metadata FROM messages WHERE id = $1", mid)
        assert '"nested"' in raw

    async def test_history_is_returned_in_chronological_order(
        self, pool: Any, conversation: dict[str, Any]
    ):
        for i in range(3):
            await repo.store_message(
                pool, conversation_id=conversation["id"], role="user", content=f"m{i}"
            )
        history = await repo.get_conversation_history(pool, conversation["id"])
        assert [h["content"] for h in history] == ["m0", "m1", "m2"]

    async def test_history_limit_keeps_the_most_recent(
        self, pool: Any, conversation: dict[str, Any]
    ):
        for i in range(5):
            await repo.store_message(
                pool, conversation_id=conversation["id"], role="user", content=f"m{i}"
            )
        history = await repo.get_conversation_history(pool, conversation["id"], limit=2)
        assert [h["content"] for h in history] == ["m3", "m4"]

    async def test_empty_conversation_has_empty_history(
        self, pool: Any, conversation: dict[str, Any]
    ):
        assert await repo.get_conversation_history(pool, conversation["id"]) == []

    async def test_outbound_message_is_recorded_as_sent(
        self, pool: Any, conversation: dict[str, Any]
    ):
        mid = await repo.create_outbound_message(
            pool,
            conversation_id=conversation["id"],
            channel="telegram",
            recipient_id="42",
            content="الرد",
            metadata={"k": "v"},
        )
        status = await pool.fetchval("SELECT status FROM outbound_messages WHERE id = $1", mid)
        assert status == "sent"


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


class TestAttachments:
    async def test_attachment_round_trip(self, pool: Any, conversation: dict[str, Any]):
        aid = await repo.store_attachment(
            pool,
            conversation_id=conversation["id"],
            message_id=None,
            filename="msds.pdf",
            content_type="application/pdf",
            r2_key="tenants/t/x.pdf",
            size=1024,
        )
        row = await pool.fetchrow("SELECT * FROM attachments WHERE id = $1", aid)
        assert row["filename"] == "msds.pdf" and row["size"] == 1024


# ---------------------------------------------------------------------------
# Approvals (HITL)
# ---------------------------------------------------------------------------


@pytest.fixture
async def approval(pool: Any, conversation: dict[str, Any]) -> str:
    return await repo.create_approval(
        pool,
        conversation_id=conversation["id"],
        customer_id=conversation["customer_id"],
        skill="sales_agent",
        intent="price_request",
        draft_text="السعر 300 ريال",
        confidence=0.8,
    )


class TestApprovals:
    async def test_new_approval_starts_pending(self, pool: Any, approval: str):
        row = await repo.get_approval(pool, approval)
        assert row is not None
        assert row["status"] == "pending"
        assert row["needs_hitl"] is True
        assert row["decided_at"] is None

    async def test_unknown_approval_is_none(self, pool: Any):
        assert await repo.get_approval(pool, str(uuid.uuid4())) is None

    async def test_approval_can_be_listed_by_status(self, pool: Any, approval: str):
        rows = await repo.list_approvals(pool, status="pending")
        assert approval in [str(r["id"]) for r in rows]

    async def test_listing_by_skill(self, pool: Any, approval: str):
        rows = await repo.list_approvals(pool, skill="sales_agent")
        assert approval in [str(r["id"]) for r in rows]

    async def test_listing_by_a_skill_with_no_rows_is_empty(self, pool: Any, approval: str):
        assert await repo.list_approvals(pool, skill="no_such_agent") == []

    async def test_pagination_does_not_crash_on_offset(self, pool: Any, approval: str):
        assert isinstance(await repo.list_approvals(pool, limit=1, offset=1), list)

    async def test_decision_records_actor_and_timestamp(self, pool: Any, approval: str):
        assert (
            await repo.update_approval_status(
                pool, approval, "approved", actor="alice", note="looks good"
            )
            is True
        )
        row = await repo.get_approval(pool, approval)
        assert row["status"] == "approved"
        assert row["actor"] == "alice"
        assert row["note"] == "looks good"
        assert row["decided_at"] is not None

    async def test_decision_can_carry_an_edited_draft(self, pool: Any, approval: str):
        assert (
            await repo.update_approval_status(
                pool, approval, "approved", actor="alice", edited_text="السعر 350 ريال"
            )
            is True
        )
        assert (await repo.get_approval(pool, approval))["edited_text"] == "السعر 350 ريال"

    async def test_decision_on_a_missing_approval_reports_failure(self, pool: Any):
        assert await repo.update_approval_status(pool, str(uuid.uuid4()), "approved") is False

    async def test_tool_execution_is_journalled(self, pool: Any, approval: str):
        await repo.mark_tool_executed(pool, approval, "create_quote", {"quote_id": "Q-1"})
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM tool_executions WHERE approval_id = $1", approval
        )
        assert count == 1


# ---------------------------------------------------------------------------
# Catalog & analytics
# ---------------------------------------------------------------------------


class TestCatalogAndAnalytics:
    async def test_catalog_items_are_returned_as_dicts(self, pool: Any):
        items = await repo.get_catalog_items(pool, limit=5)
        assert isinstance(items, list)
        assert all(isinstance(i, dict) for i in items)

    async def test_catalog_search_returns_a_list(self, pool: Any):
        assert isinstance(await repo.search_catalog(pool, "zzz-no-match"), list)

    async def test_sales_summary_has_the_expected_shape(self, pool: Any):
        summary = await repo.get_sales_summary(pool, days=30)
        assert {"total_sales", "order_count", "avg_order_value"} <= set(summary)

    async def test_ticket_stats_have_the_expected_shape(self, pool: Any):
        stats = await repo.get_ticket_stats(pool)
        assert {"total", "open_count", "resolved_count", "high_priority"} <= set(stats)
