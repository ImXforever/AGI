"""Tests for v0.5 email triage and send approval policy."""

from __future__ import annotations

from app.core.email_workflow import (
    EmailCategory,
    risk_for_triage,
    sending_decision,
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
    assert sending_decision(approved=True, actor_role="agent").allowed is False
    assert sending_decision(approved=True, actor_role="admin").allowed is True
