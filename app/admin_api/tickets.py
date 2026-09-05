"""Ticket management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.logging_setup import get_logger

log = get_logger("app.admin_api.tickets")

router = APIRouter(prefix="/tickets", tags=["admin-tickets"])


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    note: str | None = None


@router.get("")
async def list_tickets(
    request: Request,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    where_parts: list[str] = []
    params: list[Any] = []
    idx = 1
    if status:
        where_parts.append(f"t.status = ${idx}")
        params.append(status)
        idx += 1
    if priority:
        where_parts.append(f"t.priority = ${idx}")
        params.append(priority)
        idx += 1
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    total = await pool.fetchval(f"SELECT COUNT(*) FROM tickets t {where_clause}", *params)
    rows = await pool.fetch(
        f"""SELECT t.*, c.name AS customer_name
            FROM tickets t
            LEFT JOIN customers c ON c.id = t.customer_id
            {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}""",
        *params,
        limit,
        offset,
    )
    return {"total": total, "items": [dict(r) for r in rows]}


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    result = dict(row)

    # Fetch notes
    notes = await pool.fetch(
        "SELECT * FROM ticket_notes WHERE ticket_id = $1 ORDER BY created_at", ticket_id
    )
    result["notes"] = [dict(n) for n in notes]
    return result


@router.put("/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    req: TicketUpdate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT id FROM tickets WHERE id = $1", ticket_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    for field_name in ("status", "priority", "assigned_to"):
        val = getattr(req, field_name)
        if val is not None:
            updates.append(f"{field_name} = ${idx}")
            params.append(val)
            idx += 1

    if updates:
        updates.append("updated_at = NOW()")
        params.append(ticket_id)
        await pool.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = ${idx}", *params)

    if req.note:
        await pool.execute(
            """INSERT INTO ticket_notes (id, ticket_id, author, content, created_at)
               VALUES ($1, $2, $3, $4, NOW())""",
            str(__import__("uuid").uuid4()),
            ticket_id,
            admin["username"],
            req.note,
        )

    log.info("ticket updated", extra={"action": "ticket.update", "ticket_id": ticket_id})
    row = await pool.fetchrow("SELECT * FROM tickets WHERE id = $1", ticket_id)
    return dict(row)
