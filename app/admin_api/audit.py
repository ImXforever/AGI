"""Audit log query endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.audit")

router = APIRouter(prefix="/audit", tags=["admin-audit"])


@router.get("")
async def list_audit_entries(
    request: Request,
    actor: str | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    where_parts: list[str] = []
    params: list[Any] = []
    idx = 1
    if actor:
        where_parts.append(f"actor = ${idx}")
        params.append(actor)
        idx += 1
    if action:
        where_parts.append(f"action ILIKE ${idx}")
        params.append(f"%{action}%")
        idx += 1
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    total = await pool.fetchval(f"SELECT COUNT(*) FROM audit_log {where_clause}", *params)
    rows = await pool.fetch(
        f"SELECT * FROM audit_log {where_clause} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *params,
        limit,
        offset,
    )
    items = []
    for r in rows:
        d = dict(r)
        if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        items.append(d)
    return {"total": total, "items": items}
