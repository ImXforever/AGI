"""Reminders CRUD API endpoints (v17)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.reminders")

router = APIRouter(prefix="/reminders", tags=["admin-reminders"])


class ReminderCreate(BaseModel):
    user_id: str
    title: str
    message: str
    due_at: float
    repeat: str = "none"
    channel: str = "telegram"


class ReminderSnooze(BaseModel):
    minutes: int = 60


@router.get("/")
async def list_reminders(
    request: Request,
    user_id: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    if user_id:
        rows = await pool.fetch(
            "SELECT * FROM reminders WHERE user_id = $1 AND status = 'active' ORDER BY due_at",
            user_id,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM reminders WHERE status = 'active' ORDER BY due_at LIMIT 100"
        )
    return {"reminders": [dict(r) for r in rows], "count": len(rows)}


@router.post("/")
async def create_reminder_endpoint(
    request: Request,
    body: ReminderCreate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from app.core.reminder import RepeatInterval, create_reminder

    repeat = (
        RepeatInterval(body.repeat)
        if body.repeat in RepeatInterval.__members__.values()
        else RepeatInterval.NONE
    )
    reminder = create_reminder(
        user_id=body.user_id,
        title=body.title,
        message=body.message,
        due_at=body.due_at,
        repeat=repeat,
        channel=body.channel,
    )
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO reminders (id, user_id, title, message, due_at, repeat_interval, status, channel, created_at, trigger_count)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    """,
        reminder.id,
        reminder.user_id,
        reminder.title,
        reminder.message,
        reminder.due_at,
        reminder.repeat.value,
        reminder.status.value,
        reminder.channel,
        reminder.created_at,
        reminder.trigger_count,
    )
    return reminder.as_dict()


@router.get("/{reminder_id}")
async def get_reminder(
    request: Request,
    reminder_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM reminders WHERE id = $1", reminder_id)
    if not row:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return dict(row)


@router.post("/{reminder_id}/snooze")
async def snooze_reminder_endpoint(
    request: Request,
    reminder_id: str,
    body: ReminderSnooze,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM reminders WHERE id = $1", reminder_id)
    if not row:
        raise HTTPException(status_code=404, detail="Reminder not found")
    new_due = time.time() + body.minutes * 60
    await pool.execute(
        "UPDATE reminders SET due_at = $1, status = 'snoozed' WHERE id = $2",
        new_due,
        reminder_id,
    )
    return {"id": reminder_id, "snoozed_until": new_due, "minutes": body.minutes}


@router.post("/{reminder_id}/cancel")
async def cancel_reminder_endpoint(
    request: Request,
    reminder_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute(
        "UPDATE reminders SET status = 'cancelled' WHERE id = $1", reminder_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"id": reminder_id, "status": "cancelled"}


@router.delete("/{reminder_id}")
async def delete_reminder_endpoint(
    request: Request,
    reminder_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM reminders WHERE id = $1", reminder_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"id": reminder_id, "deleted": True}


@router.get("/due/check")
async def check_due_reminders(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        "SELECT * FROM reminders WHERE status = 'active' AND due_at <= $1 ORDER BY due_at LIMIT 50",
        time.time(),
    )
    return {"due": [dict(r) for r in rows], "count": len(rows)}
