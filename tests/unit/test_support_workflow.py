"""Support agent: tickets, SLA, safety vs knowledge."""

from __future__ import annotations

from app.core.agents.router import route_work
from app.core.hitl.execute import execute_action
from app.core.support_workflow import (
    CustomerTicketStatus,
    SupportPhase,
    TicketSeverity,
    handle_support,
    is_safety_text,
)


def test_normal_issue_opens_ticket_automatically() -> None:
    plan = route_work("خطا در سیستم، لطفاً پشتیبانی کنید", source="support")
    assert plan.agent == "support_agent"
    assert plan.action == "create_ticket"
    assert plan.auto_execute is True
    assert execute_action("create_ticket", plan.payload).executed is True
    assert plan.payload["customer_status"] == CustomerTicketStatus.OPEN.value
    assert plan.payload["sla_hours"] == 2.0


def test_safety_escalates_and_hides_internal_pending() -> None:
    result = handle_support("There is a fire in the warehouse")
    assert result.phase == SupportPhase.ESCALATE
    assert result.ticket is not None
    assert result.ticket.is_safety is True
    assert result.ticket.severity == TicketSeverity.CRITICAL
    assert result.ticket.customer_status == CustomerTicketStatus.ESCALATED
    assert result.ticket.sla_hours == 0.0
    assert result.payload["escalate"] is True
    plan = route_work("There is a fire in the warehouse", source="support")
    assert plan.action == "create_ticket"
    assert plan.payload["is_safety"] is True


def test_safety_does_not_match_substring_leak() -> None:
    assert is_safety_text("please leak") is True
    assert is_safety_text("bleak weather today") is False
    assert is_safety_text("fireplace catalog") is False


def test_faq_uses_knowledge_instead_of_ticket() -> None:
    result = handle_support("how do i reset password")
    assert result.phase == SupportPhase.ANSWER
    assert result.action == "search_knowledge"
    assert result.ticket is None
    plan = route_work("how do i reset password", source="support")
    assert plan.action == "search_knowledge"
    assert plan.auto_execute is True


def test_followup_is_a_task() -> None:
    result = handle_support("still waiting", extras={"followup": True})
    assert result.phase == SupportPhase.FOLLOWUP
    assert result.action == "create_task"
