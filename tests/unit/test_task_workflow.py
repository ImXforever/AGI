"""Tests for v0.6 task extraction and escalation."""

from __future__ import annotations

from app.core.policy import RiskLevel
from app.core.task_workflow import TaskKind, extract_task, should_escalate


def test_support_request_becomes_high_priority_task() -> None:
    task = extract_task("خطا در سفارش و نیاز به پشتیبانی", source="email")
    assert task is not None
    assert task.kind == TaskKind.SUPPORT
    assert task.priority == "high"
    assert task.due_hours == 24
    assert task.source == "email"
    assert should_escalate(task) is False


def test_legal_request_is_escalated() -> None:
    task = extract_task("لطفاً قرارداد را بررسی کنید")
    assert task is not None
    assert task.kind == TaskKind.LEGAL
    assert task.risk == RiskLevel.HIGH
    assert task.requires_human is True
    assert should_escalate(task) is True


def test_finance_is_more_urgent_than_general_customer_request() -> None:
    finance = extract_task("invoice payment is waiting")
    customer = extract_task("please check my delivery")
    assert finance is not None and customer is not None
    assert finance.priority == "high"
    assert finance.due_hours < customer.due_hours


def test_unknown_message_does_not_create_noise_task() -> None:
    assert extract_task("سلام، روز خوبی داشته باشید") is None


def test_task_title_is_bounded_and_whitespace_is_cleaned() -> None:
    task = extract_task("  price   request " + "x" * 300)
    assert task is not None
    assert len(task.title) == 200
    assert "  " not in task.title
