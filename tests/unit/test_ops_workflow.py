"""Ops agent: tasks, manager brief, cross-domain links, future agents inactive."""

from __future__ import annotations

from app.core.agents.router import route_work
from app.core.ops_workflow import handle_ops, make_domain_links, manager_brief


def test_legal_ops_task_requires_contract() -> None:
    plan = route_work("نیاز به بررسی قرارداد داریم", requested_agent="ops")
    assert plan.agent == "ops_agent"
    assert plan.action == "contract"
    assert plan.needs_manager is True


def test_manager_brief_has_no_message_bodies() -> None:
    brief = manager_brief(
        [
            {"type": "incoming", "channel": "telegram", "text": "secret-body"},
            {"type": "approval_pending"},
            {"type": "quote_draft"},
            {"type": "safety_ticket"},
            {"type": "error"},
        ]
    )
    assert "NEEDS YOU" in brief
    assert "Approvals waiting: 1" in brief
    assert "Quotes not sent: 1" in brief
    assert "Safety tickets: 1" in brief
    assert "secret-body" not in brief
    assert "accounting_agent" in brief
    assert "INACTIVE" in brief


def test_cross_domain_links_lead_ticket_quote() -> None:
    links = make_domain_links(lead_id="L1", ticket_id="T9", quote_id="Q3")
    assert {row["kind"] for row in links} == {"lead", "ticket", "quote"}
    result = handle_ops(
        "link these",
        extras={"link": True, "lead_id": "L1", "ticket_id": "T9", "quote_id": "Q3"},
    )
    assert result.action == "create_task"
    assert result.payload["links"][0]["id"] == "L1"


def test_daily_report_is_a_task_not_a_live_agent() -> None:
    plan = route_work(
        "please send the daily report",
        requested_agent="ops",
        extras={"events": [{"type": "approval_pending"}]},
    )
    assert plan.action == "create_task"
    assert plan.auto_execute is True
    assert "NEEDS YOU" in plan.payload["brief"]


def test_future_ops_request_stays_inactive() -> None:
    result = handle_ops("run payroll close")
    assert result.action == "unknown_future"
    plan = route_work("hire someone", requested_agent="hr_agent")
    assert plan.domain == "future"
    assert plan.auto_execute is False
