"""Tenant business hours. Used for OOO copy — never auto-approves HITL."""

from __future__ import annotations

from datetime import UTC, datetime, time


def parse_hours(spec: str = "09:00-17:00") -> tuple[time, time]:
    raw = (spec or "09:00-17:00").strip()
    start_s, _, end_s = raw.partition("-")
    sh, sm = (int(p) for p in start_s.split(":")[:2])
    eh, em = (int(p) for p in (end_s or "17:00").split(":")[:2])
    return time(sh, sm), time(eh, em)


def is_open(
    now: datetime | None = None,
    *,
    hours: str = "09:00-17:00",
    weekdays_only: bool = True,
) -> bool:
    current = now or datetime.now(UTC)
    if weekdays_only and current.weekday() >= 5:
        return False
    start, end = parse_hours(hours)
    check = current.time().replace(tzinfo=None)
    if start <= end:
        return start <= check <= end
    return check >= start or check <= end


def ooo_notice(*, open_now: bool) -> str:
    if open_now:
        return ""
    return "We are outside business hours. A manager will reply when the office opens."
