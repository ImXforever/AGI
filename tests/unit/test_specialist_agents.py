"""Specialist routing for sales, support and ops."""

from __future__ import annotations

from app.core.agents.router import route_work
from app.core.hitl.execute import execute_action


def test_sales_quote_is_held_for_manager() -> None:
    plan = route_work("Please send a quote for 12 drums", source="sales")
    assert plan.agent == "sales_agent"
    assert plan.action == "create_quote"
    assert plan.needs_manager is True


def test_support_ticket_is_automatic() -> None:
    plan = route_work("خطا در سیستم، لطفاً پشتیبانی کنید", source="support")
    assert plan.agent == "support_agent"
    assert plan.action == "create_ticket"
    assert plan.auto_execute is True
    assert execute_action("create_ticket", plan.payload).executed is True


def test_ops_legal_task_requires_contract_approval() -> None:
    plan = route_work("نیاز به بررسی قرارداد داریم", requested_agent="ops")
    assert plan.agent == "ops_agent"
    assert plan.action == "contract"
    assert plan.needs_manager is True
