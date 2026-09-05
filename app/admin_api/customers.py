"""Customer management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.logging_setup import get_logger

log = get_logger("app.admin_api.customers")

router = APIRouter(prefix="/customers", tags=["admin-customers"])


class CustomerUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    phone: str | None = None
    email: str | None = None
    lead_score: int | None = None
    tags: list[str] | None = None


@router.get("")
async def list_customers(
    request: Request,
    search: str = "",
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    params: list[Any] = []
    where = ""
    idx = 1
    if search:
        where = f"WHERE name ILIKE ${idx} OR company ILIKE ${idx} OR phone ILIKE ${idx}"
        params.append(f"%{search}%")
        idx += 1

    total = await pool.fetchval(f"SELECT COUNT(*) FROM customers {where}", *params)
    rows = await pool.fetch(
        f"SELECT * FROM customers {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *params,
        limit,
        offset,
    )
    return {"total": total, "items": [dict(r) for r in rows]}


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return dict(row)


@router.put("/{customer_id}")
async def update_customer(
    customer_id: str,
    req: CustomerUpdate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT id FROM customers WHERE id = $1", customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="customer not found")

    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    for field_name in ("name", "company", "phone", "email", "lead_score"):
        val = getattr(req, field_name)
        if val is not None:
            updates.append(f"{field_name} = ${idx}")
            params.append(val)
            idx += 1
    if req.tags is not None:
        import json

        updates.append(f"tags = ${idx}")
        params.append(json.dumps(req.tags))
        idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    params.append(customer_id)
    await pool.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id = ${idx}", *params)
    log.info("customer updated", extra={"action": "customer.update", "customer_id": customer_id})
    row = await pool.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
    return dict(row)


@router.get("/{customer_id}/conversations")
async def customer_conversations(
    customer_id: str,
    request: Request,
    limit: int = 20,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        """SELECT id, channel, status, created_at, updated_at
           FROM conversations WHERE customer_id = $1
           ORDER BY updated_at DESC LIMIT $2""",
        customer_id,
        limit,
    )
    return {"items": [dict(r) for r in rows]}
