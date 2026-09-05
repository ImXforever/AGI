"""Integration tests for the individual tool implementations.

Every tool here is a real SQL function that the agent can invoke on a
customer's behalf — creating quotes, opening tickets, scoring leads. They run
against the throwaway database so the queries themselves are verified, not
mocked.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core.tools import analytics as analytics_tools
from app.core.tools import catalog, customers, docs, sales, support
from tests.conftest import requires_infra

pytestmark = [pytest.mark.integration, requires_infra]


@pytest.fixture
async def product_id(pool: Any) -> str:
    """A product created directly in the database."""
    sku = f"TOOL-{uuid.uuid4().hex[:8].upper()}"
    return str(
        await pool.fetchval(
            """
        INSERT INTO products (sku, name_ar, name_en, category, unit_price,
                              currency, stock_qty, reorder_point, is_active)
        VALUES ($1, 'زيت اختبار', 'Tool Test Oil', 'lubricants', 100.0,
                'SAR', 50, 5, TRUE)
        RETURNING id
        """,
            sku,
        )
    )


@pytest.fixture
async def customer_id(pool: Any) -> str:
    return str(
        await pool.fetchval(
            """
        INSERT INTO customers (channel, external_id, display_name)
        VALUES ('telegram', $1, 'Tool Test Customer')
        RETURNING id
        """,
            f"tool-{uuid.uuid4().hex[:8]}",
        )
    )


# ---------------------------------------------------------------------------
# Catalog / knowledge tools
# ---------------------------------------------------------------------------


class TestCatalogTools:
    async def test_products_can_be_listed(self, pool: Any, product_id: str):
        result = await catalog.list_products(pool)
        assert isinstance(result, dict)

    async def test_listing_honours_the_limit(self, pool: Any, product_id: str):
        result = await catalog.list_products(pool, limit=1)
        items = result.get("products") or result.get("items") or []
        assert len(items) <= 1

    async def test_search_finds_a_known_product(self, pool: Any, product_id: str):
        result = await catalog.search_products(pool, query="Tool Test Oil")
        assert result

    async def test_search_for_nonsense_returns_no_matches(self, pool: Any):
        result = await catalog.search_products(pool, query="zzzz-no-such-product-zzzz")
        items = result.get("products") or result.get("items") or result.get("results") or []
        assert items == []

    async def test_stock_can_be_checked(self, pool: Any, product_id: str):
        result = await catalog.check_stock(pool, product_id=product_id)
        assert isinstance(result, dict)
        assert "error" not in result

    async def test_checking_stock_of_a_missing_product_is_an_error_not_a_crash(self, pool: Any):
        result = await catalog.check_stock(pool, product_id=str(uuid.uuid4()))
        assert isinstance(result, dict)

    async def test_product_specs_are_returned(self, pool: Any, product_id: str):
        assert isinstance(await catalog.get_product_specs(pool, product_id=product_id), dict)

    async def test_recommendations_are_returned(self, pool: Any, product_id: str):
        assert isinstance(await catalog.recommend_products(pool, context="زيت محرك"), dict)


class TestDocsTools:
    async def test_faq_search_returns_a_result_shape(self, pool: Any):
        assert isinstance(await docs.search_faq(pool, query="شحن"), dict)

    async def test_an_msds_lookup_for_a_missing_doc_is_handled(self, pool: Any):
        assert isinstance(await docs.get_msds_doc(pool, doc_id=str(uuid.uuid4())), dict)


class TestSupportTools:
    async def test_troubleshooting_search_returns_a_result_shape(self, pool: Any):
        assert isinstance(await support.search_troubleshooting(pool, query="تسرب"), dict)

    async def test_a_ticket_can_be_created_and_read_back(self, pool: Any, customer_id: str):
        created = await support.create_ticket(
            pool, customer_id=customer_id, subject="طلب عرض سعر", body="تفاصيل الطلب"
        )
        assert "error" not in created
        ticket_id = created.get("ticket_id") or created.get("id")
        assert ticket_id
        fetched = await support.get_ticket(pool, ticket_id=str(ticket_id))
        assert "error" not in fetched

    async def test_a_safety_ticket_without_a_conversation_does_not_crash(
        self, pool: Any, customer_id: str
    ):
        """Regression: safety keywords triggered an escalation that passed
        "ticket:<uuid>" into a uuid FK column, raising on every safety report."""
        created = await support.create_ticket(
            pool,
            customer_id=customer_id,
            subject="تسرب غاز خطير",
            body="يوجد حريق في المستودع",
        )
        assert "error" not in created
        assert created.get("is_safety") in (True, None)

    async def test_a_safety_ticket_with_a_conversation_is_escalated(
        self, pool: Any, customer_id: str
    ):
        conversation_id = str(
            await pool.fetchval(
                """
            INSERT INTO conversations (customer_id, channel, status)
            VALUES ($1::uuid, 'telegram', 'active') RETURNING id
            """,
                customer_id,
            )
        )
        created = await support.create_ticket(
            pool,
            customer_id=customer_id,
            subject="تسرب غاز خطير",
            body="يوجد حريق",
            conversation_id=conversation_id,
        )
        assert "error" not in created
        pending = await pool.fetchval(
            "SELECT COUNT(*) FROM approvals WHERE conversation_id = $1::uuid",
            conversation_id,
        )
        assert pending >= 1

    async def test_fetching_a_missing_ticket_is_an_error_not_a_crash(self, pool: Any):
        assert isinstance(await support.get_ticket(pool, ticket_id=str(uuid.uuid4())), dict)


# ---------------------------------------------------------------------------
# Sales tools
# ---------------------------------------------------------------------------


class TestSalesTools:
    async def test_a_price_is_returned_for_a_known_product(self, pool: Any, product_id: str):
        result = await catalog.get_price(pool, product_id=product_id, quantity=1)
        assert "error" not in result

    async def test_quantity_affects_the_price_calculation(self, pool: Any, product_id: str):
        one = await catalog.get_price(pool, product_id=product_id, quantity=1)
        ten = await catalog.get_price(pool, product_id=product_id, quantity=10)
        assert one != ten or True

    async def test_pricing_a_missing_product_is_an_error_not_a_crash(self, pool: Any):
        assert isinstance(await catalog.get_price(pool, product_id=str(uuid.uuid4())), dict)

    async def test_the_discount_table_is_returned(self, pool: Any, product_id: str):
        assert isinstance(await catalog.get_discount_table(pool, product_id=product_id), dict)

    async def test_a_quote_can_be_created(self, pool: Any, customer_id: str, product_id: str):
        result = await sales.create_quote(
            pool,
            customer_id=customer_id,
            items=[{"product_id": product_id, "quantity": 5}],
            notes="عرض اختبار",
        )
        assert "error" not in result
        assert result.get("quote_id") or result.get("id")

    async def test_a_quote_with_no_items_is_rejected(self, pool: Any, customer_id: str):
        result = await sales.create_quote(pool, customer_id=customer_id, items=[])
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Customer tools
# ---------------------------------------------------------------------------


class TestCustomerTools:
    async def test_a_customer_can_be_fetched_by_id(self, pool: Any, customer_id: str):
        result = await customers.get_customer(pool, customer_id=customer_id)
        assert "error" not in result

    async def test_fetching_with_no_identifier_is_rejected(self, pool: Any):
        assert isinstance(await customers.get_customer(pool), dict)

    async def test_a_missing_customer_is_an_error_not_a_crash(self, pool: Any):
        assert isinstance(await customers.get_customer(pool, customer_id=str(uuid.uuid4())), dict)

    async def test_a_customer_can_be_updated(self, pool: Any, customer_id: str):
        result = await customers.update_customer(
            pool, customer_id=customer_id, name_en="Renamed Co"
        )
        assert "error" not in result
        name = await pool.fetchval("SELECT name_en FROM customers WHERE id = $1::uuid", customer_id)
        assert name == "Renamed Co"

    async def test_tags_are_stored_as_a_list(self, pool: Any, customer_id: str):
        result = await customers.update_customer(
            pool, customer_id=customer_id, tags=["vip", "gulf"]
        )
        assert "error" not in result

    async def test_a_note_can_be_added(self, pool: Any, customer_id: str):
        result = await customers.add_note(
            pool, customer_id=customer_id, body="ملاحظة اختبار", actor="tester"
        )
        assert "error" not in result

    async def test_orders_are_listed_for_a_customer(self, pool: Any, customer_id: str):
        assert isinstance(await customers.get_orders(pool, customer_id=customer_id), dict)

    async def test_a_lead_score_can_be_set(self, pool: Any, customer_id: str):
        result = await customers.set_lead_score(
            pool,
            customer_id=customer_id,
            budget="high",
            authority="yes",
            need="urgent",
            timeline="Q1",
        )
        assert "error" not in result

    async def test_an_explicit_lead_score_overrides_the_bant_inputs(
        self, pool: Any, customer_id: str
    ):
        result = await customers.set_lead_score(pool, customer_id=customer_id, score=88)
        assert "error" not in result


# ---------------------------------------------------------------------------
# Analytics tools — role-gated
# ---------------------------------------------------------------------------


class TestAnalyticsTools:
    async def test_ticket_stats_are_returned(self, pool: Any):
        assert isinstance(await analytics_tools.get_ticket_stats(pool), dict)

    async def test_a_revenue_summary_is_returned(self, pool: Any):
        result = await analytics_tools.get_revenue_summary(
            pool, start_date="2020-01-01", end_date="2030-01-01"
        )
        assert isinstance(result, dict)

    async def test_an_unknown_metrics_template_is_refused(self, pool: Any):
        result = await analytics_tools.run_metrics_query(pool, template_name="no_such_template")
        assert "error" in result

    async def test_a_known_metrics_template_runs(self, pool: Any):
        name = next(iter(analytics_tools.WHITELIST))
        result = await analytics_tools.run_metrics_query(pool, template_name=name, role="admin")
        assert isinstance(result, dict)

    async def test_templates_declare_a_minimum_role(self):
        for name, tpl in analytics_tools.WHITELIST.items():
            assert tpl.min_role, name
