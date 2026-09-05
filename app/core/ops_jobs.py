"""Real cron jobs for the client operating loop (phase 5)."""

from __future__ import annotations

from typing import Any

from app.core.content_calendar import get_ready_posts
from app.core.email_followup import get_escalatable, get_pending_followups
from app.core.reporting import build_daily_report_from_db, build_operational_report
from app.logging_setup import get_logger

log = get_logger("app.core.ops_jobs")


async def run_daily_report(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = list(events or [])
    report = build_daily_report_from_db(rows)
    log.info(
        "daily_report",
        extra={
            "action": "cron.daily_report",
            "messages": report.total_messages,
            "emails": report.emails_received,
            "errors": report.errors,
        },
    )
    return report.as_dict()


async def run_followup_check(entries: list[Any] | None = None) -> dict[str, Any]:
    items = list(entries or [])
    pending = get_pending_followups(items) if items else []
    escalated = get_escalatable(items) if items else []
    log.info(
        "followup_check",
        extra={
            "action": "cron.followup_check",
            "pending": len(pending),
            "escalated": len(escalated),
        },
    )
    return {"pending": len(pending), "escalated": len(escalated)}


async def run_calendar_publish(posts: list[Any] | None = None) -> dict[str, Any]:
    ready = get_ready_posts(list(posts or []))
    log.info(
        "calendar_publish",
        extra={"action": "cron.calendar_publish", "ready": len(ready)},
    )
    return {"ready": len(ready)}


async def run_ops_digest(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    report = build_operational_report(events or [])
    log.info(
        "ops_digest",
        extra={"action": "cron.ops_digest", "events": report.total_events, "errors": report.errors},
    )
    return report.as_dict()
