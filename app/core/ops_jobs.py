"""Real cron jobs for the client operating loop (phase 5)."""

from __future__ import annotations

from typing import Any

from app.core.content_calendar import calendar_post_from_row, get_ready_posts
from app.core.email_followup import followup_from_row, get_escalatable, get_pending_followups
from app.core.ops_workflow import manager_brief
from app.core.reporting import build_daily_report_from_db, build_operational_report
from app.logging_setup import get_logger

log = get_logger("app.core.ops_jobs")


async def _get_pg(pg: Any | None) -> Any | None:
    if pg is not None:
        return pg
    try:
        from app.storage.pg import get_pool

        return await get_pool()
    except Exception:
        return None


async def load_followups(pg: Any | None = None) -> list[Any]:
    pool = await _get_pg(pg)
    if pool is None:
        return []
    try:
        rows = await pool.fetch("SELECT * FROM email_followups WHERE status = 'active' LIMIT 500")
    except Exception as exc:
        log.warning("followup_load_failed", extra={"action": "cron.load", "error": str(exc)[:200]})
        return []
    return [followup_from_row(dict(r)) for r in rows]


async def load_calendar_posts(pg: Any | None = None) -> list[Any]:
    pool = await _get_pg(pg)
    if pool is None:
        return []
    try:
        rows = await pool.fetch(
            "SELECT * FROM content_calendar WHERE status = 'scheduled' LIMIT 500"
        )
    except Exception as exc:
        log.warning("calendar_load_failed", extra={"action": "cron.load", "error": str(exc)[:200]})
        return []
    return [calendar_post_from_row(dict(r)) for r in rows]


async def load_report_events(pg: Any | None = None) -> list[dict[str, Any]]:
    """Compact count-rows for reports (no message bodies)."""
    pool = await _get_pg(pg)
    if pool is None:
        return []
    events: list[dict[str, Any]] = []
    try:
        rows = await pool.fetch(
            """
            SELECT c.channel AS channel, COUNT(*) AS n
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.created_at >= now() - interval '1 day'
            GROUP BY c.channel
            """
        )
        for row in rows:
            events.append(
                {"type": "incoming", "channel": str(row["channel"] or ""), "count": int(row["n"])}
            )
    except Exception as exc:
        log.warning("events_load_failed", extra={"action": "cron.load", "error": str(exc)[:200]})
    try:
        pending = await pool.fetchval("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
        if pending:
            events.append({"type": "approval_pending", "count": int(pending)})
    except Exception:
        pass
    return events


async def run_daily_report(
    events: list[dict[str, Any]] | None = None, *, pg: Any | None = None
) -> dict[str, Any]:
    rows = list(events) if events is not None else await load_report_events(pg)
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


async def run_followup_check(
    entries: list[Any] | None = None, *, pg: Any | None = None
) -> dict[str, Any]:
    items = list(entries) if entries is not None else await load_followups(pg)
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


async def run_calendar_publish(
    posts: list[Any] | None = None, *, pg: Any | None = None
) -> dict[str, Any]:
    items = list(posts) if posts is not None else await load_calendar_posts(pg)
    ready = get_ready_posts(items)
    log.info(
        "calendar_publish",
        extra={"action": "cron.calendar_publish", "ready": len(ready)},
    )
    return {"ready": len(ready), "published": 0}


async def run_ops_digest(
    events: list[dict[str, Any]] | None = None, *, pg: Any | None = None
) -> dict[str, Any]:
    rows = list(events) if events is not None else await load_report_events(pg)
    report = build_operational_report(rows)
    brief = manager_brief(rows)
    log.info(
        "ops_digest",
        extra={"action": "cron.ops_digest", "events": report.total_events, "errors": report.errors},
    )
    out = report.as_dict()
    out["brief"] = brief
    return out
