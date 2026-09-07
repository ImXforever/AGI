"""Admin approval endpoints: list, get, decide (approve / reject / edit).

All mutations go through the Redis Lua scripts for atomicity,
then persist to the Postgres ``approvals`` table via an execution ledger.
409 Conflict on double-decide (already terminal).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.constants import ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.admin_api.approvals")

router = APIRouter(prefix="/approvals", tags=["admin-approvals"])


class DecideRequest(BaseModel):
    status: str  # approved | rejected | edited
    note: str = ""
    edited_payload: dict[str, Any] | None = None


class ApprovalItem(BaseModel):
    id: str
    conversation_id: str
    channel: str
    status: str
    payload: dict[str, Any]
    created_at: str
    decided_at: str | None = None
    actor: str | None = None
    note: str | None = None

    @field_validator("id", "conversation_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v: Any) -> Any:
        # asyncpg returns uuid.UUID objects for UUID columns.
        return "" if v is None else str(v)

    @field_validator("channel", "status", mode="before")
    @classmethod
    def _text_or_empty(cls, v: Any) -> Any:
        return "" if v is None else str(v)

    @field_validator("payload", mode="before")
    @classmethod
    def _payload_to_dict(cls, v: Any) -> Any:
        # jsonb arrives as a JSON *string* unless a codec is registered.
        if v is None:
            return {}
        if isinstance(v, (bytes, bytearray)):
            v = v.decode("utf-8", errors="replace")
        if isinstance(v, str):
            try:
                parsed = json.loads(v) if v.strip() else {}
            except json.JSONDecodeError:
                return {"raw": v}
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        return v if isinstance(v, dict) else {"value": v}

    @field_validator("created_at", "decided_at", mode="before")
    @classmethod
    def _ts_to_iso(cls, v: Any) -> Any:
        # asyncpg returns datetime objects for timestamptz columns.
        if v is None:
            return None
        return v.isoformat() if hasattr(v, "isoformat") else str(v)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_decision(status: str) -> str:
    if status not in ApprovalStatus.DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(ApprovalStatus.DECISIONS)}, got {status!r}",
        )
    return status


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
async def list_approvals(
    request: Request,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    where_parts: list[str] = []
    params: list[Any] = []
    idx = 1
    if status:
        where_parts.append(f"a.status = ${idx}")
        params.append(status)
        idx += 1
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    total = await pool.fetchval(f"SELECT COUNT(*) FROM approvals a {where_clause}", *params)
    rows = await pool.fetch(
        f"""SELECT a.id, a.conversation_id, a.channel, a.status, a.payload,
                   a.created_at, a.decided_at, a.actor, a.note
            FROM approvals a {where_clause}
            ORDER BY a.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}""",
        *params,
        limit,
        offset,
    )
    items = [ApprovalItem(**dict(r)).model_dump() for r in rows]
    return {"total": total, "items": items, "limit": limit, "offset": offset}


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """SELECT id, conversation_id, channel, status, payload,
                  created_at, decided_at, actor, note
           FROM approvals WHERE id = $1""",
        approval_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="approval not found")
    return ApprovalItem(**dict(row)).model_dump()


@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    req: DecideRequest,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    """Approve / reject / edit — shared path with the Telegram buttons (1.4.0).

    The 1.3.x endpoint recorded the decision but delivered the reply through a
    no-op sender, so the customer never heard back. ``app.core.hitl.decide``
    now performs the atomic claim, ledger, execution *and* the real send.
    """
    new_status = _validate_decision(req.status)
    from app.core.hitl.decide import DecisionError
    from app.core.hitl.decide import decide_approval as _decide
    from app.core.outbound import MemoryClaimStore

    store = getattr(request.app.state, "outbound_claims", None)
    if store is None:
        store = MemoryClaimStore()
        request.app.state.outbound_claims = store
    try:
        return await _decide(
            services=request.app.state.services,
            approval_id=approval_id,
            new_status=new_status,
            actor=str(admin.get("username") or "admin"),
            actor_role=str(admin.get("role") or "admin"),
            note=req.note or "",
            edited_payload=req.edited_payload,
            claim_store=store,
        )
    except DecisionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
