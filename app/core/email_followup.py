"""Automated email follow-up system (v16).

Tracks unanswered emails and sends follow-up reminders at configurable intervals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.email_followup")


class FollowUpStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


@dataclass
class FollowUpRule:
    name: str
    hours_before_first: int
    hours_between: int
    max_followups: int
    escalate_after: int
    channels: tuple[str, ...] = ("email",)


DEFAULT_RULES: list[FollowUpRule] = [
    FollowUpRule(
        name="standard",
        hours_before_first=24,
        hours_between=48,
        max_followups=3,
        escalate_after=72,
    ),
    FollowUpRule(
        name="urgent",
        hours_before_first=4,
        hours_between=12,
        max_followups=5,
        escalate_after=24,
    ),
    FollowUpRule(
        name="sales",
        hours_before_first=24,
        hours_between=72,
        max_followups=2,
        escalate_after=168,
    ),
]


@dataclass
class FollowUpEntry:
    id: str
    email_id: str
    sender: str
    recipient: str
    subject: str
    category: str
    rule_name: str
    status: FollowUpStatus
    created_at: float
    last_followup_at: float | None
    followup_count: int
    next_followup_at: float
    escalation_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email_id": self.email_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": self.subject,
            "category": self.category,
            "rule_name": self.rule_name,
            "status": self.status,
            "created_at": self.created_at,
            "last_followup_at": self.last_followup_at,
            "followup_count": self.followup_count,
            "next_followup_at": self.next_followup_at,
            "escalation_at": self.escalation_at,
        }


def get_rule(category: str = "standard") -> FollowUpRule:
    """Get the follow-up rule for a given email category."""
    for rule in DEFAULT_RULES:
        if rule.name == category:
            return rule
    return DEFAULT_RULES[0]


def create_followup(
    email_id: str,
    sender: str,
    recipient: str,
    subject: str,
    category: str = "standard",
    *,
    rule: FollowUpRule | None = None,
) -> FollowUpEntry:
    """Create a new follow-up entry for an unanswered email."""
    import hashlib
    import os

    rule = rule or get_rule(category)
    now = time.time()
    entry_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]

    return FollowUpEntry(
        id=entry_id,
        email_id=email_id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        category=category,
        rule_name=rule.name,
        status=FollowUpStatus.ACTIVE,
        created_at=now,
        last_followup_at=None,
        followup_count=0,
        next_followup_at=now + rule.hours_before_first * 3600,
        escalation_at=now + rule.escalate_after * 3600,
    )


def should_followup(entry: FollowUpEntry) -> bool:
    """Check if a follow-up should be sent now."""
    if entry.status != FollowUpStatus.ACTIVE:
        return False
    now = time.time()
    if now < entry.next_followup_at:
        return False
    rule = get_rule(entry.rule_name)
    if entry.followup_count >= rule.max_followups:
        return False
    return True


def should_escalate(entry: FollowUpEntry) -> bool:
    """Check if the entry should be escalated to a human."""
    if entry.status != FollowUpStatus.ACTIVE:
        return False
    return time.time() >= entry.escalation_at


def mark_followup_sent(entry: FollowUpEntry) -> FollowUpEntry:
    """Mark that a follow-up was sent and schedule the next one."""
    import time as _time

    rule = get_rule(entry.rule_name)
    entry.followup_count += 1
    entry.last_followup_at = _time.time()
    entry.next_followup_at = _time.time() + rule.hours_between * 3600

    if entry.followup_count >= rule.max_followups:
        entry.status = FollowUpStatus.ESCALATED

    return entry


def mark_completed(entry: FollowUpEntry) -> FollowUpEntry:
    """Mark the follow-up as completed (email was replied to)."""
    entry.status = FollowUpStatus.COMPLETED
    return entry


def mark_cancelled(entry: FollowUpEntry) -> FollowUpEntry:
    """Cancel the follow-up."""
    entry.status = FollowUpStatus.CANCELLED
    return entry


def build_followup_message(
    entry: FollowUpEntry, *, company_name: str = "Our Company"
) -> dict[str, str]:
    """Build the follow-up email message."""
    followup_number = entry.followup_count + 1

    if followup_number == 1:
        body = (
            f"Dear {entry.sender},\n\n"
            f"This is a friendly follow-up regarding your email with subject:\n"
            f'"{entry.subject}"\n\n'
            f"We wanted to make sure your inquiry was received and is being processed. "
            f"If you have any additional questions, please don't hesitate to reply.\n\n"
            f"Best regards,\n{company_name} Team"
        )
    elif followup_number == 2:
        body = (
            f"Dear {entry.sender},\n\n"
            f"We are following up again on your email regarding:\n"
            f'"{entry.subject}"\n\n'
            f"We haven't heard back from you and want to ensure "
            f"your needs are addressed. Please let us know if you "
            f"still need assistance.\n\n"
            f"Best regards,\n{company_name} Team"
        )
    else:
        body = (
            f"Dear {entry.sender},\n\n"
            f"This is our final follow-up regarding:\n"
            f'"{entry.subject}"\n\n'
            f"If we don't hear from you, we will assume your inquiry "
            f"has been resolved. You can always reach us again via email.\n\n"
            f"Best regards,\n{company_name} Team"
        )

    return {
        "to": entry.sender,
        "from": entry.recipient,
        "subject": f"Follow-up #{followup_number}: {entry.subject}",
        "body": body,
    }


def get_pending_followups(entries: list[FollowUpEntry]) -> list[FollowUpEntry]:
    """Filter entries that need a follow-up sent now."""
    return [e for e in entries if should_followup(e)]


def get_escalatable(entries: list[FollowUpEntry]) -> list[FollowUpEntry]:
    """Filter entries that should be escalated to a human."""
    return [e for e in entries if should_escalate(e)]
