"""Customer, support and sales task extraction (v17 — extended with due_date and reminder)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from app.core.policy import RiskLevel


class TaskKind(StrEnum):
    SUPPORT = "support"
    SALES = "sales"
    CUSTOMER = "customer"
    FINANCE = "finance"
    LEGAL = "legal"
    OTHER = "other"


@dataclass(frozen=True)
class TaskDraft:
    title: str
    kind: TaskKind
    priority: str
    due_hours: int
    requires_human: bool
    risk: RiskLevel
    source: str
    due_date: float = 0.0
    assignee: str = ""
    department: str = ""
    reminder_minutes: int = 0

    @property
    def due_timestamp(self) -> float:
        if self.due_date > 0:
            return self.due_date
        return time.time() + self.due_hours * 3600


_RULES: tuple[tuple[TaskKind, tuple[str, ...], int, str, bool, RiskLevel], ...] = (
    (TaskKind.LEGAL, ("contract", "قرارداد", "حقوقی", "قانونی"), 4, "urgent", True, RiskLevel.HIGH),
    (TaskKind.FINANCE, ("invoice", "payment", "پرداخت", "فاکتور"), 8, "high", True, RiskLevel.HIGH),
    (
        TaskKind.SUPPORT,
        ("error", "problem", "support", "خطا", "مشکل", "پشتیبانی"),
        24,
        "high",
        False,
        RiskLevel.MEDIUM,
    ),
    (
        TaskKind.SALES,
        ("price", "quote", "buy", "قیمت", "خرید", "پیش فاکتور"),
        24,
        "normal",
        False,
        RiskLevel.MEDIUM,
    ),
    (
        TaskKind.CUSTOMER,
        ("order", "delivery", "سفارش", "تحویل", "مشتری"),
        48,
        "normal",
        False,
        RiskLevel.MEDIUM,
    ),
)


def extract_task(text: str, *, source: str = "conversation") -> TaskDraft | None:
    """Create a transparent task draft from a customer or internal message.

    Returns ``None`` for messages without an actionable business signal.
    Rules are intentionally deterministic and can later be enriched by an LLM
    without weakening the risk and escalation result.
    """
    clean = " ".join(text.split())
    if not clean:
        return None
    haystack = clean.casefold()
    for kind, keywords, due_hours, priority, human, risk in _RULES:
        if any(keyword.casefold() in haystack for keyword in keywords):
            return TaskDraft(
                title=clean[:200],
                kind=kind,
                priority=priority,
                due_hours=due_hours,
                requires_human=human,
                risk=risk,
                source=source,
            )
    return None


def extract_task_with_metadata(
    text: str,
    *,
    source: str = "conversation",
    assignee: str = "",
    department: str = "",
    reminder_minutes: int = 0,
) -> TaskDraft | None:
    """Extract a task with optional metadata (v17)."""
    task = extract_task(text, source=source)
    if task is None:
        return None
    return TaskDraft(
        title=task.title,
        kind=task.kind,
        priority=task.priority,
        due_hours=task.due_hours,
        requires_human=task.requires_human,
        risk=task.risk,
        source=task.source,
        due_date=task.due_timestamp,
        assignee=assignee,
        department=department,
        reminder_minutes=reminder_minutes,
    )


def should_escalate(task: TaskDraft) -> bool:
    """Return whether the draft needs a human before external action."""
    return task.requires_human or task.risk >= RiskLevel.HIGH
