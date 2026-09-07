"""Tests for v0.5 email triage and send approval policy."""

from __future__ import annotations

from app.core.agents.router import route_work
from app.core.email_workflow import (
    EmailCategory,
    EmailPhase,
    handle_inbound_email,
    is_bounce,
    make_thread_id,
    queue_approval,
    risk_for_triage,
    sending_decision,
    sla_hours_for,
    triage_email,
)
from app.core.policy import RiskLevel


def test_finance_email_is_high_priority_and_human_reviewed() -> None:
    result = triage_email("Invoice payment", "Please process the bank payment.")
    assert result.category == EmailCategory.FINANCE
    assert result.priority == "high"
    assert result.requires_human is True
    assert risk_for_triage(result) == RiskLevel.HIGH


def test_support_email_is_classified_transparently() -> None:
    result = triage_email("خطا در سفارش", "پشتیبانی لطفاً مشکل را بررسی کنید")
    assert result.category == EmailCategory.SUPPORT
    assert result.confidence >= 0.55
    assert result.reason == "support content"


def test_spam_is_not_sent_for_automatic_reply() -> None:
    result = triage_email("Unsubscribe", "casino offer")
    assert result.category == EmailCategory.SPAM
    assert result.requires_human is False
    assert sending_decision().allowed is False


def test_unknown_email_is_escalated_instead_of_guessed() -> None:
    result = triage_email("Hello", "A message without a known business intent.")
    assert result.category == EmailCategory.OTHER
    assert result.requires_human is True
    assert result.confidence < 0.5


def test_only_explicit_manager_approval_allows_sending() -> None:
    assert sending_decision().requires_approval is True
    assert sending_decision(approved=True, actor_role="agent", approval_id="rec-1").allowed is False
    assert sending_decision(approved=True, actor_role="admin", approval_id="rec-1").allowed is True


def test_confidential_mail_is_held() -> None:
    result = triage_email("NDA review", "This is confidential.")
    assert result.category == EmailCategory.CONFIDENTIAL
    assert result.requires_human is True
    assert risk_for_triage(result) == RiskLevel.HIGH
    decision = handle_inbound_email("NDA review", "This is confidential.")
    assert decision.phase == EmailPhase.QUEUE_APPROVAL
    assert decision.action == "send_email"


def test_bounce_is_dropped_with_no_outbound() -> None:
    assert is_bounce("Undeliverable: hello", "", sender="MAILER-DAEMON@example.com") is True
    decision = handle_inbound_email(
        "Mail delivery failed",
        "Diagnostic-Code: smtp; 550",
        sender="mailer-daemon@example.net",
        message_id="<bounce-1@ex>",
    )
    assert decision.phase == EmailPhase.DROP
    assert decision.bounce is True
    assert decision.action == "classify_email"
    assert decision.draft is None


def test_thread_id_prefers_in_reply_to() -> None:
    tid = make_thread_id(
        message_id="<new@ex>",
        in_reply_to="<root@ex>",
        references="<older@ex> <root@ex>",
    )
    assert tid == "root@ex"


def test_common_pricing_is_auto_reply() -> None:
    decision = handle_inbound_email("Price inquiry", "What is the price of lubricant oil?")
    assert decision.phase == EmailPhase.SEND_COMMON
    assert decision.action == "reply_common"
    assert decision.draft is not None
    plan = route_work(
        "What is the price of lubricant oil?",
        source="email",
        subject="Price inquiry",
    )
    assert plan.auto_execute is True
    assert plan.action == "reply_common"


def test_finance_never_auto_sends() -> None:
    decision = handle_inbound_email("Invoice payment", "Please process the bank payment.")
    assert decision.phase == EmailPhase.QUEUE_APPROVAL
    assert queue_approval().allowed is False
    assert sla_hours_for(decision.triage) == 1.0
    plan = route_work(
        "Please process the bank payment.",
        source="email",
        subject="Invoice payment",
    )
    assert plan.needs_manager is True
    assert plan.action == "send_email"


def test_unknown_mail_is_drafted_not_sent() -> None:
    decision = handle_inbound_email("Hello", "A message without a known business intent.")
    assert decision.phase == EmailPhase.DRAFT
    assert decision.action == "create_draft"
