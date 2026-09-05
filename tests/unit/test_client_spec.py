"""Acceptance tests for the client digital-operations charter.

Every row of the access matrix and every specialist domain must stay true.
"""

from __future__ import annotations

import time

from app.core.agents.router import route_work
from app.core.company_charter import (
    ACCESS_MATRIX,
    ACTIVE_DOMAINS,
    BUILDING_BLOCKS,
    FUTURE_AGENTS,
    charter_snapshot,
    system_prompt,
)
from app.core.hitl.execute import execute_action, reset_idempotency
from app.core.policy import auto_actions, evaluate_action, registered_actions
from app.core.social_workflow import prepare_post


def test_charter_covers_five_live_domains() -> None:
    keys = {d.key for d in ACTIVE_DOMAINS}
    assert keys == {"email", "website", "social", "sales", "support", "ops"}
    assert "llm_brain" in BUILDING_BLOCKS
    assert "accounting_agent" in FUTURE_AGENTS
    prompt = system_prompt(language="fa")
    assert "تأیید" in prompt
    snap = charter_snapshot()
    assert snap["version"]
    assert len(snap["access_matrix"]) == len(ACCESS_MATRIX)


def test_access_matrix_matches_policy() -> None:
    for action, mode, _label in ACCESS_MATRIX:
        decision = evaluate_action(action)
        if mode == "auto":
            assert decision.allowed is True, action
            assert decision.requires_approval is False, action
        else:
            assert decision.allowed is False, action
            assert decision.requires_approval is True, action
            manager = evaluate_action(action, actor_role="admin", approved=True)
            assert manager.allowed is True, action


def test_common_email_reply_is_automatic() -> None:
    plan = route_work(
        "Please send your product catalog and price list",
        source="email",
        subject="Catalog request",
        sender="buyer@example.com",
    )
    assert plan.agent == "email_agent"
    assert plan.auto_execute is True
    assert plan.action == "reply_common"
    assert execute_action(plan.action, plan.payload).executed is True


def test_finance_email_requires_manager() -> None:
    plan = route_work(
        "Please process the bank payment.",
        source="email",
        subject="Invoice payment",
        sender="ap@example.com",
    )
    assert plan.needs_manager is True
    assert plan.action == "send_email"
    blocked = execute_action(plan.action, plan.payload, context=plan.audit["context"])
    assert blocked.executed is False
    allowed = execute_action(
        plan.action,
        plan.payload,
        actor_role="admin",
        approved=True,
        context=plan.audit["context"],
    )
    assert allowed.executed is True


def test_website_form_creates_lead_automatically() -> None:
    plan = route_work(
        "Need product information",
        source="website",
        extras={"form": {"name": "Jane Doe", "email": "jane@example.com", "message": "Need product information"}},
    )
    assert plan.agent == "website_agent"
    assert plan.action == "create_lead"
    assert plan.auto_execute is True


def test_price_change_on_site_requires_manager() -> None:
    plan = route_work(
        "99.00",
        source="cms",
        extras={"field": "price", "before": "80.00", "after": "99.00"},
    )
    assert plan.action == "change_price"
    assert plan.needs_manager is True
    assert execute_action("change_price").executed is False
    assert execute_action("change_price", actor_role="admin", approved=True).executed is True


def test_ordinary_calendar_post_is_automatic() -> None:
    when = time.time() + 3600
    post = prepare_post(platform="instagram", caption="Weekly product update", scheduled_at=when)
    assert post.requires_approval is False
    plan = route_work(
        "Weekly product update",
        source="social",
        extras={"platform": "instagram", "caption": "Weekly product update", "scheduled_at": when},
    )
    assert plan.auto_execute is True
    assert plan.action == "publish_calendar"


def test_sensitive_social_claim_is_held() -> None:
    when = time.time() + 3600
    plan = route_work(
        "Guaranteed best price",
        source="social",
        extras={"platform": "instagram", "caption": "Guaranteed best price", "scheduled_at": when},
    )
    assert plan.needs_manager is True


def test_payment_and_delete_never_auto() -> None:
    for action in ("payment", "contract", "delete_data", "change_access"):
        assert action not in auto_actions()
        assert evaluate_action(action, actor_role="agent", approved=True).allowed is False
        assert evaluate_action(action, actor_role="admin", approved=True).allowed is True


def test_future_agents_are_inactive() -> None:
    plan = route_work("hire someone", requested_agent="hr_agent")
    assert plan.domain == "future"
    assert plan.auto_execute is False


def test_execution_is_idempotent() -> None:
    reset_idempotency()
    first = execute_action("reply_common", {"k": 1}, idempotency_key="r1")
    second = execute_action("reply_common", {"k": 2}, idempotency_key="r1")
    assert first.executed is True
    assert second.result == first.result


def test_legal_site_change_uses_contract_gate() -> None:
    plan = route_work(
        "Updated refund terms",
        source="cms",
        extras={"field": "refund_policy", "before": "old", "after": "new"},
    )
    assert plan.action == "contract"
    assert plan.needs_manager is True


def test_hermes_tool_plan_follows_charter() -> None:
    import asyncio

    from app.core.hermes_client import plan_inline_tools

    catalog = asyncio.run(
        plan_inline_tools(
            "email_agent",
            "Please send your product catalog and price list",
            {"source": "email", "subject": "Catalog request", "sender": "buyer@example.com"},
        )
    )
    assert catalog and catalog[0]["name"] == "reply_common"
    assert catalog[0]["auto"] is True

    payment = asyncio.run(
        plan_inline_tools(
            "email_agent",
            "Please process the bank payment.",
            {"source": "email", "subject": "Invoice payment", "sender": "ap@example.com"},
        )
    )
    assert payment and payment[0]["name"] == "send_email"
    assert payment[0]["requires_approval"] is True

    quote = asyncio.run(plan_inline_tools("sales_agent", "Please send a quote for 12 drums", {}))
    assert quote and quote[0]["name"] == "create_quote"
    assert quote[0]["requires_approval"] is True


def test_unknown_action_fail_closed() -> None:
    decision = evaluate_action("wire_money_offshore")
    assert decision.allowed is False
    assert "reply_common" in registered_actions()
    assert "publish_calendar" in registered_actions()
    assert "contract" in registered_actions()
