"""Tests for the v10 composed operations planner."""

from __future__ import annotations

from app.core.operations_orchestrator import plan_operation


def test_email_plan_composes_triage_and_task_extraction() -> None:
    plan = plan_operation(
        "Invoice payment is waiting",
        source="email",
        subject="Invoice payment",
        requested_action="send_email",
    )
    assert plan.route == "finance"
    assert plan.email is not None
    assert plan.task is not None
    assert plan.policy.requires_approval is True
    assert plan.policy.allowed is False


def test_unknown_request_has_no_side_effect_and_is_explainable() -> None:
    plan = plan_operation("سلام", requested_action="unknown_action")
    assert plan.route == "general"
    assert plan.task is None
    assert plan.policy.allowed is False
    assert plan.policy.requires_approval is True


def test_support_plan_is_routable() -> None:
    plan = plan_operation("خطا در سیستم، لطفاً پشتیبانی کنید", source="telegram")
    assert plan.route == "support"
    assert plan.task is not None
    assert plan.task.source == "telegram"
