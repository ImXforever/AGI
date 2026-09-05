"""Manager-facing operational summaries (v16 — extended with daily/weekly/email/website reports)."""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperationalReport:
    total_events: int
    messages: int
    tasks_created: int
    approvals_pending: int
    errors: int
    by_channel: dict[str, int]
    by_category: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_events": self.total_events,
            "messages": self.messages,
            "tasks_created": self.tasks_created,
            "approvals_pending": self.approvals_pending,
            "errors": self.errors,
            "by_channel": dict(self.by_channel),
            "by_category": dict(self.by_category),
        }


def build_operational_report(events: Iterable[dict[str, Any]]) -> OperationalReport:
    """Aggregate normalized event records without exposing message contents."""
    total = messages = tasks = pending = errors = 0
    channels: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    for event in events:
        total += 1
        event_type = str(event.get("type", "")).lower()
        if event_type in {"message", "incoming", "outbound"}:
            messages += 1
        if event_type in {"task_created", "ticket_created"}:
            tasks += 1
        if event_type in {"approval_pending", "pending_approval"}:
            pending += 1
        if event_type in {"error", "failed", "tool_execution_failed"}:
            errors += 1
        channel = str(event.get("channel", "")).strip().lower()
        if channel:
            channels[channel] += 1
        category = str(event.get("category", "")).strip().lower()
        if category:
            categories[category] += 1
    return OperationalReport(
        total, messages, tasks, pending, errors, dict(channels), dict(categories)
    )


def calculate_kpis(
    *, response_times_ms: Iterable[float] = (), resolved: int = 0, received: int = 0
) -> dict[str, float | int]:
    """Calculate small, dashboard-safe KPIs with zero-denominator handling."""
    values = [float(value) for value in response_times_ms if float(value) >= 0]
    return {
        "average_response_ms": round(sum(values) / len(values), 2) if values else 0.0,
        "response_samples": len(values),
        "resolution_rate": round(resolved / received, 4) if received > 0 else 0.0,
        "received": max(0, received),
        "resolved": max(0, resolved),
    }


# ---------------------------------------------------------------------------
# v16: Extended reports
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DailyReport:
    date: str
    total_messages: int
    messages_by_channel: dict[str, int]
    messages_by_category: dict[str, int]
    emails_received: int
    emails_auto_replied: int
    emails_escalated: int
    tasks_created: int
    tasks_completed: int
    approvals_pending: int
    approvals_completed: int
    errors: int
    average_response_ms: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "total_messages": self.total_messages,
            "messages_by_channel": dict(self.messages_by_channel),
            "messages_by_category": dict(self.messages_by_category),
            "emails_received": self.emails_received,
            "emails_auto_replied": self.emails_auto_replied,
            "emails_escalated": self.emails_escalated,
            "tasks_created": self.tasks_created,
            "tasks_completed": self.tasks_completed,
            "approvals_pending": self.approvals_pending,
            "approvals_completed": self.approvals_completed,
            "errors": self.errors,
            "average_response_ms": self.average_response_ms,
        }

    def to_text(self) -> str:
        return (
            f"Daily Report — {self.date}\n"
            f"{'=' * 40}\n"
            f"Messages: {self.total_messages}\n"
            f"  Telegram: {self.messages_by_channel.get('telegram', 0)}\n"
            f"  WhatsApp: {self.messages_by_channel.get('whatsapp', 0)}\n"
            f"  Email: {self.messages_by_channel.get('email', 0)}\n"
            f"Emails: {self.emails_received} received, "
            f"{self.emails_auto_replied} auto-replied, "
            f"{self.emails_escalated} escalated\n"
            f"Tasks: {self.tasks_created} created, {self.tasks_completed} completed\n"
            f"Approvals: {self.approvals_pending} pending, {self.approvals_completed} completed\n"
            f"Errors: {self.errors}\n"
            f"Avg Response: {self.average_response_ms:.0f}ms"
        )


@dataclass(frozen=True)
class WeeklyReport:
    week_start: str
    week_end: str
    total_messages: int
    messages_by_day: dict[str, int]
    messages_by_channel: dict[str, int]
    emails_received: int
    emails_auto_replied: int
    emails_escalated: int
    tasks_created: int
    tasks_completed: int
    approvals_pending: int
    approvals_completed: int
    errors: int
    average_response_ms: float
    top_categories: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "total_messages": self.total_messages,
            "messages_by_day": dict(self.messages_by_day),
            "messages_by_channel": dict(self.messages_by_channel),
            "emails_received": self.emails_received,
            "emails_auto_replied": self.emails_auto_replied,
            "emails_escalated": self.emails_escalated,
            "tasks_created": self.tasks_created,
            "tasks_completed": self.tasks_completed,
            "approvals_pending": self.approvals_pending,
            "approvals_completed": self.approvals_completed,
            "errors": self.errors,
            "average_response_ms": self.average_response_ms,
            "top_categories": dict(self.top_categories),
        }

    def to_text(self) -> str:
        cats = ", ".join(
            f"{k}: {v}" for k, v in sorted(self.top_categories.items(), key=lambda x: -x[1])[:5]
        )
        return (
            f"Weekly Report — {self.week_start} to {self.week_end}\n"
            f"{'=' * 40}\n"
            f"Total Messages: {self.total_messages}\n"
            f"By Channel: {self.messages_by_channel}\n"
            f"Emails: {self.emails_received} received, "
            f"{self.emails_auto_replied} auto-replied, "
            f"{self.emails_escalated} escalated\n"
            f"Tasks: {self.tasks_created} created, {self.tasks_completed} completed\n"
            f"Approvals: {self.approvals_pending} pending, {self.approvals_completed} completed\n"
            f"Errors: {self.errors}\n"
            f"Avg Response: {self.average_response_ms:.0f}ms\n"
            f"Top Categories: {cats}"
        )


@dataclass(frozen=True)
class EmailReport:
    period: str
    total_received: int
    total_sent: int
    auto_replied: int
    escalated: int
    pending: int
    by_category: dict[str, int]
    average_response_ms: float
    followups_sent: int
    followups_completed: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "total_received": self.total_received,
            "total_sent": self.total_sent,
            "auto_replied": self.auto_replied,
            "escalated": self.escalated,
            "pending": self.pending,
            "by_category": dict(self.by_category),
            "average_response_ms": self.average_response_ms,
            "followups_sent": self.followups_sent,
            "followups_completed": self.followups_completed,
        }

    def to_text(self) -> str:
        cats = ", ".join(
            f"{k}: {v}" for k, v in sorted(self.by_category.items(), key=lambda x: -x[1])
        )
        return (
            f"Email Report — {self.period}\n"
            f"{'=' * 40}\n"
            f"Received: {self.total_received}\n"
            f"Sent: {self.total_sent}\n"
            f"Auto-replied: {self.auto_replied}\n"
            f"Escalated: {self.escalated}\n"
            f"Pending: {self.pending}\n"
            f"By Category: {cats}\n"
            f"Avg Response: {self.average_response_ms:.0f}ms\n"
            f"Follow-ups: {self.followups_sent} sent, {self.followups_completed} completed"
        )


@dataclass(frozen=True)
class WebsiteReport:
    period: str
    contact_forms_received: int
    contact_forms_processed: int
    contact_forms_pending: int
    content_changes: int
    content_changes_approved: int
    content_changes_pending: int
    products_updated: int
    errors_detected: int
    by_change_type: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "contact_forms_received": self.contact_forms_received,
            "contact_forms_processed": self.contact_forms_processed,
            "contact_forms_pending": self.contact_forms_pending,
            "content_changes": self.content_changes,
            "content_changes_approved": self.content_changes_approved,
            "content_changes_pending": self.content_changes_pending,
            "products_updated": self.products_updated,
            "errors_detected": self.errors_detected,
            "by_change_type": dict(self.by_change_type),
        }

    def to_text(self) -> str:
        types = ", ".join(
            f"{k}: {v}" for k, v in sorted(self.by_change_type.items(), key=lambda x: -x[1])
        )
        return (
            f"Website Report — {self.period}\n"
            f"{'=' * 40}\n"
            f"Contact Forms: {self.contact_forms_received} received, "
            f"{self.contact_forms_processed} processed, "
            f"{self.contact_forms_pending} pending\n"
            f"Content Changes: {self.content_changes} total, "
            f"{self.content_changes_approved} approved, "
            f"{self.content_changes_pending} pending\n"
            f"Products Updated: {self.products_updated}\n"
            f"Errors Detected: {self.errors_detected}\n"
            f"By Change Type: {types}"
        )


def build_daily_report_from_db(rows: list[dict[str, Any]], *, date: str = "") -> DailyReport:
    """Build a daily report from database query results."""
    channels: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    emails_received = emails_auto = emails_esc = 0
    tasks_created = tasks_completed = 0
    approvals_pending = approvals_completed = 0
    errors = 0
    response_times: list[float] = []
    total_messages = 0

    for row in rows:
        event_type = str(row.get("type", "")).lower()
        if event_type in {"message", "incoming", "outbound", "reply"}:
            total_messages += 1
            ch = str(row.get("channel", "")).lower()
            if ch:
                channels[ch] += 1
            cat = str(row.get("category", "")).lower()
            if cat:
                categories[cat] += 1
        if event_type == "email_received":
            emails_received += 1
        if event_type == "email_auto_replied":
            emails_auto += 1
        if event_type == "email_escalated":
            emails_esc += 1
        if event_type == "task_created":
            tasks_created += 1
        if event_type == "task_completed":
            tasks_completed += 1
        if event_type == "approval_pending":
            approvals_pending += 1
        if event_type == "approval_completed":
            approvals_completed += 1
        if event_type in {"error", "failed"}:
            errors += 1
        rt = row.get("response_time_ms")
        if rt is not None:
            response_times.append(float(rt))

    avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0.0

    return DailyReport(
        date=date or time.strftime("%Y-%m-%d"),
        total_messages=total_messages,
        messages_by_channel=dict(channels),
        messages_by_category=dict(categories),
        emails_received=emails_received,
        emails_auto_replied=emails_auto,
        emails_escalated=emails_esc,
        tasks_created=tasks_created,
        tasks_completed=tasks_completed,
        approvals_pending=approvals_pending,
        approvals_completed=approvals_completed,
        errors=errors,
        average_response_ms=avg_response,
    )


def build_email_report_from_db(rows: list[dict[str, Any]], *, period: str = "") -> EmailReport:
    """Build an email-specific report from database rows."""
    categories: Counter[str] = Counter()
    received = sent = auto = escalated = pending = 0
    response_times: list[float] = []
    followups_sent = followups_completed = 0

    for row in rows:
        cat = str(row.get("category", "")).lower()
        if cat:
            categories[cat] += 1
        status = str(row.get("status", "")).lower()
        if status == "received":
            received += 1
        elif status == "sent":
            sent += 1
        elif status == "auto_replied":
            auto += 1
        elif status == "escalated":
            escalated += 1
        elif status == "pending":
            pending += 1
        rt = row.get("response_time_ms")
        if rt is not None:
            response_times.append(float(rt))
        if row.get("followup_sent"):
            followups_sent += 1
        if row.get("followup_completed"):
            followups_completed += 1

    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else 0.0

    return EmailReport(
        period=period or time.strftime("%Y-%m-%d"),
        total_received=received,
        total_sent=sent,
        auto_replied=auto,
        escalated=escalated,
        pending=pending,
        by_category=dict(categories),
        average_response_ms=avg_response,
        followups_sent=followups_sent,
        followups_completed=followups_completed,
    )


def build_website_report_from_db(rows: list[dict[str, Any]], *, period: str = "") -> WebsiteReport:
    """Build a website-specific report from database rows."""
    change_types: Counter[str] = Counter()
    forms_received = forms_processed = forms_pending = 0
    changes_total = changes_approved = changes_pending = 0
    products_updated = errors = 0

    for row in rows:
        event_type = str(row.get("type", "")).lower()
        if event_type == "contact_form":
            forms_received += 1
            if row.get("processed"):
                forms_processed += 1
            else:
                forms_pending += 1
        if event_type == "content_change":
            changes_total += 1
            ct = str(row.get("change_type", "")).lower()
            if ct:
                change_types[ct] += 1
            if row.get("approved"):
                changes_approved += 1
            else:
                changes_pending += 1
        if event_type == "product_updated":
            products_updated += 1
        if event_type in {"error", "website_error"}:
            errors += 1

    return WebsiteReport(
        period=period or time.strftime("%Y-%m-%d"),
        contact_forms_received=forms_received,
        contact_forms_processed=forms_processed,
        contact_forms_pending=forms_pending,
        content_changes=changes_total,
        content_changes_approved=changes_approved,
        content_changes_pending=changes_pending,
        products_updated=products_updated,
        errors_detected=errors,
        by_change_type=dict(change_types),
    )
