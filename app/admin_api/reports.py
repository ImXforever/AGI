"""Reports API endpoints (v16)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.reports")

router = APIRouter(prefix="/reports", tags=["admin-reports"])


@router.get("/daily")
async def daily_report(
    request: Request,
    date: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    target_date = date or time.strftime("%Y-%m-%d")

    rows = await pool.fetch(
        """
        SELECT type, channel, category, response_time_ms, created_at
        FROM email_logs
        WHERE to_timestamp(created_at)::date = $1::date
        ORDER BY created_at
    """,
        target_date,
    )

    from app.core.reporting import build_daily_report_from_db

    report = build_daily_report_from_db([dict(r) for r in rows], date=target_date)
    return report.as_dict()


@router.get("/weekly")
async def weekly_report(
    request: Request,
    start_date: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]

    if start_date:
        end_date_sql = "($1::date + INTERVAL '7 days')::text"
        rows = await pool.fetch(
            f"""
            SELECT type, channel, category, response_time_ms,
                   to_char(to_timestamp(created_at), 'YYYY-MM-DD') as day,
                   created_at
            FROM email_logs
            WHERE to_timestamp(created_at) >= $1::date
              AND to_timestamp(created_at) < {end_date_sql}
            ORDER BY created_at
        """,
            start_date,
        )
    else:
        rows = await pool.fetch("""
            SELECT type, channel, category, response_time_ms,
                   to_char(to_timestamp(created_at), 'YYYY-MM-DD') as day,
                   created_at
            FROM email_logs
            WHERE to_timestamp(created_at) >= (NOW() - INTERVAL '7 days')
            ORDER BY created_at
        """)

    from app.core.reporting import Counter, WeeklyReport

    day_counter: Counter[str] = Counter()
    channel_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    response_times: list[float] = []
    emails_received = emails_auto = emails_esc = 0
    tasks_created = tasks_completed = 0
    approvals_pending = approvals_completed = 0
    errors = 0

    for row in rows:
        r = dict(row)
        day = r.get("day", "")
        if day:
            day_counter[day] += 1
        ch = r.get("channel", "")
        if ch:
            channel_counter[ch] += 1
        cat = r.get("category", "")
        if cat:
            category_counter[cat] += 1
        rt = r.get("response_time_ms")
        if rt is not None:
            response_times.append(float(rt))
        event_type = r.get("type", "")
        if event_type == "email_received":
            emails_received += 1
        elif event_type == "email_auto_replied":
            emails_auto += 1
        elif event_type == "email_escalated":
            emails_esc += 1
        elif event_type == "task_created":
            tasks_created += 1
        elif event_type == "task_completed":
            tasks_completed += 1
        elif event_type == "approval_pending":
            approvals_pending += 1
        elif event_type == "approval_completed":
            approvals_completed += 1
        elif event_type in {"error", "failed"}:
            errors += 1

    avg = round(sum(response_times) / len(response_times), 1) if response_times else 0.0

    report = WeeklyReport(
        week_start=start_date or time.strftime("%Y-%m-%d", time.localtime(time.time() - 604800)),
        week_end=time.strftime("%Y-%m-%d"),
        total_messages=len(rows),
        messages_by_day=dict(day_counter),
        messages_by_channel=dict(channel_counter),
        emails_received=emails_received,
        emails_auto_replied=emails_auto,
        emails_escalated=emails_esc,
        tasks_created=tasks_created,
        tasks_completed=tasks_completed,
        approvals_pending=approvals_pending,
        approvals_completed=approvals_completed,
        errors=errors,
        average_response_ms=avg,
        top_categories=dict(category_counter),
    )
    return report.as_dict()


@router.get("/email")
async def email_report(
    request: Request,
    period: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    target = period or time.strftime("%Y-%m-%d")

    rows = await pool.fetch(
        """
        SELECT category, status, response_time_ms, auto_replied,
               CASE WHEN followup_id IS NOT NULL THEN TRUE ELSE FALSE END as followup_sent,
               created_at
        FROM email_logs
        WHERE to_timestamp(created_at)::date = $1::date
        ORDER BY created_at
    """,
        target,
    )

    from app.core.reporting import build_email_report_from_db

    report = build_email_report_from_db([dict(r) for r in rows], period=target)
    return report.as_dict()


@router.get("/website")
async def website_report(
    request: Request,
    period: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    target = period or time.strftime("%Y-%m-%d")

    rows = await pool.fetch(
        """
        SELECT event_type as type, change_type, processed, approved, created_at
        FROM website_events
        WHERE to_timestamp(created_at)::date = $1::date
        ORDER BY created_at
    """,
        target,
    )

    from app.core.reporting import build_website_report_from_db

    report = build_website_report_from_db([dict(r) for r in rows], period=target)
    return report.as_dict()


@router.get("/cron-status")
async def cron_status(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from app.core.cron_scheduler import get_scheduler

    scheduler = get_scheduler()
    return {"jobs": scheduler.get_status()}
