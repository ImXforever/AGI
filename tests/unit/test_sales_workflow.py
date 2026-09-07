"""Sales agent: catalog prices, quote HITL, no payments."""

from __future__ import annotations

import pytest

from app.core.agents.router import route_work
from app.core.hitl.execute import execute_action
from app.core.sales_workflow import (
    SalesPhase,
    handle_sales,
    normalize_lead,
    quote_line_from_catalog,
)


def test_quote_is_held_and_not_sent() -> None:
    plan = route_work("Please send a quote for 12 drums", source="sales")
    assert plan.agent == "sales_agent"
    assert plan.action == "create_quote"
    assert plan.needs_manager is True
    assert plan.payload.get("sent") is False


def test_payment_is_refused() -> None:
    result = handle_sales("Please charge card / stripe pay now")
    assert result.phase == SalesPhase.REFUSE
    assert result.action == "payment"
    assert result.production is False
    plan = route_work("Please process payment", source="sales")
    assert plan.action == "payment"
    assert plan.auto_execute is False
    assert execute_action("payment").executed is False


def test_catalog_price_override_is_ignored() -> None:
    line = quote_line_from_catalog(
        product_id="sku-1",
        quantity=10,
        catalog_row={"unit_price": 50.0, "discount_tiers": [{"min_qty": 10, "discount_pct": 10}]},
        requested_unit_price=1.0,
    )
    assert line is not None
    assert line.unit_price == 50.0
    assert line.discount_pct == 10.0
    assert line.line_total == 450.0


def test_lead_fields_are_normalized() -> None:
    lead = normalize_lead(
        name="  Jane  Doe ", email=" Jane@Example.COM ", company="ACME", interest="oil"
    )
    assert lead.name == "Jane Doe"
    assert lead.email == "jane@example.com"
    plan = route_work(
        "interested",
        source="sales",
        extras={"lead": {"name": "Jane Doe", "email": "jane@example.com"}},
    )
    assert plan.action == "create_lead"
    assert plan.auto_execute is True


def test_invalid_lead_email_is_rejected() -> None:
    with pytest.raises(ValueError, match="email"):
        normalize_lead(name="Jane", email="not-an-email")
    result = handle_sales("hi", extras={"lead": {"name": "Jane", "email": "bad"}})
    assert result.phase == SalesPhase.REFUSE
    assert result.lead is None


def test_complex_deal_is_handed_off() -> None:
    result = handle_sales("We need a custom spec tender / RFP")
    assert result.phase == SalesPhase.HANDOFF
    assert result.action == "contract"
