"""Smart reminder system (v17).

Create, list, and check reminders with configurable repeat intervals.
Reminders are persisted in Redis for fast access and PostgreSQL for durability.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.reminder")

REDIS_KEY_PREFIX = "reminder:"
REDIS_INDEX_KEY = "reminders:active"


class RepeatInterval(StrEnum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReminderStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SNOOZED = "snoozed"


@dataclass
class Reminder:
    id: str
    user_id: str
    title: str
    message: str
    due_at: float
    repeat: RepeatInterval
    status: ReminderStatus
    channel: str
    created_at: float
    last_triggered_at: float | None
    trigger_count: int
    snooze_until: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "due_at": self.due_at,
            "repeat": self.repeat,
            "status": self.status,
            "channel": self.channel,
            "created_at": self.created_at,
            "last_triggered_at": self.last_triggered_at,
            "trigger_count": self.trigger_count,
            "snooze_until": self.snooze_until,
        }


def _gen_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


def create_reminder(
    user_id: str,
    title: str,
    message: str,
    due_at: float,
    *,
    repeat: RepeatInterval = RepeatInterval.NONE,
    channel: str = "telegram",
) -> Reminder:
    """Create a new reminder."""
    return Reminder(
        id=_gen_id(),
        user_id=user_id,
        title=title,
        message=message,
        due_at=due_at,
        repeat=repeat,
        status=ReminderStatus.ACTIVE,
        channel=channel,
        created_at=time.time(),
        last_triggered_at=None,
        trigger_count=0,
    )


def is_due(reminder: Reminder) -> bool:
    """Check if a reminder should fire now."""
    if reminder.status != ReminderStatus.ACTIVE:
        return False
    now = time.time()
    if reminder.snooze_until and now < reminder.snooze_until:
        return False
    return now >= reminder.due_at


def trigger_reminder(reminder: Reminder) -> Reminder:
    """Mark a reminder as triggered and schedule next occurrence."""
    now = time.time()
    reminder.last_triggered_at = now
    reminder.trigger_count += 1
    reminder.snooze_until = None

    if reminder.repeat == RepeatInterval.NONE:
        reminder.status = ReminderStatus.COMPLETED
    elif reminder.repeat == RepeatInterval.DAILY:
        reminder.due_at = now + 86400
    elif reminder.repeat == RepeatInterval.WEEKLY:
        reminder.due_at = now + 604800
    elif reminder.repeat == RepeatInterval.MONTHLY:
        reminder.due_at = now + 2592000

    return reminder


def snooze_reminder(reminder: Reminder, minutes: int = 60) -> Reminder:
    """Snooze a reminder for N minutes."""
    reminder.snooze_until = time.time() + minutes * 60
    reminder.status = ReminderStatus.SNOOZED
    return reminder


def cancel_reminder(reminder: Reminder) -> Reminder:
    """Cancel a reminder."""
    reminder.status = ReminderStatus.CANCELLED
    return reminder


def format_reminder_text(reminder: Reminder) -> str:
    """Format a reminder for display."""
    import datetime

    due = datetime.datetime.fromtimestamp(reminder.due_at)
    due_str = due.strftime("%Y-%m-%d %H:%M")
    repeat_str = (
        f" (repeats {reminder.repeat.value})" if reminder.repeat != RepeatInterval.NONE else ""
    )
    return f"Reminder: {reminder.title}\n{reminder.message}\nDue: {due_str}{repeat_str}"


def get_due_reminders(reminders: list[Reminder]) -> list[Reminder]:
    """Filter reminders that are due now."""
    return [r for r in reminders if is_due(r)]


def get_user_reminders(reminders: list[Reminder], user_id: str) -> list[Reminder]:
    """Filter reminders for a specific user."""
    return [r for r in reminders if r.user_id == user_id and r.status == ReminderStatus.ACTIVE]
