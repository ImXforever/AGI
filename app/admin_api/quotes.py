"""Quote management endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.logging_setup import get_logger

log = get_logger("app.admin_api.quotes")

router = APIRouter(prefix="/quotes", tags=["admin-quotes"])


class QuoteItem(BaseModel):
    id: str
    customer_id: str
    conversation_id: str | None = None
    status: str
    items: list[dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    currency: str
    valid_until: str | None = None
    notes: str = ""
    created_at: str
    updated_at: str


def _row_to_dict(row: Any) -> dict[str, Any]:
    d = dict(row)
    d["items"] = json.loads(d.get("items") or "[]")
    for k in ("created_at", "updated_at", "valid_until"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


@router.get("")
async def list_quotes(
    request: Request,
    status: str | None = None,
    customer_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    where_parts: list[str] = []
    params: list[Any] = []
    idx = 1
    if status:
        where_parts.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    if customer_id:
        where_parts.append(f"customer_id = ${idx}")
        params.append(customer_id)
        idx += 1
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    total = await pool.fetchval(f"SELECT COUNT(*) FROM quotes {where_clause}", *params)
    rows = await pool.fetch(
        f"SELECT * FROM quotes {where_clause} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *params,
        limit,
        offset,
    )
    return {"total": total, "items": [_row_to_dict(r) for r in rows]}


@router.get("/{quote_id}")
async def get_quote(
    quote_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM quotes WHERE id = $1", quote_id)
    if row is None:
        raise HTTPException(status_code=404, detail="quote not found")
    return _row_to_dict(row)


@router.post("/{quote_id}/send")
async def send_quote(
    quote_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM quotes WHERE id = $1", quote_id)
    if row is None:
        raise HTTPException(status_code=404, detail="quote not found")
    await pool.execute(
        "UPDATE quotes SET status = 'sent', updated_at = NOW() WHERE id = $1", quote_id
    )
    log.info("quote sent", extra={"action": "quote.send", "quote_id": quote_id})
    return {"ok": True}


@router.post("/{quote_id}/cancel")
async def cancel_quote(
    quote_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    result = await pool.execute(
        "UPDATE quotes SET status = 'cancelled', updated_at = NOW() WHERE id = $1 AND status NOT IN ('accepted','cancelled')",
        quote_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(
            status_code=409, detail="quote cannot be cancelled in its current status"
        )
    log.info("quote cancelled", extra={"action": "quote.cancel", "quote_id": quote_id})
    return {"ok": True}
