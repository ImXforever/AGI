"""Admin approval endpoints: list, get, decide (approve / reject / edit).

All mutations go through the Redis Lua scripts for atomicity,
then persist to the Postgres ``approvals`` table via an execution ledger.
409 Conflict on double-decide (already terminal).
"""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.constants import ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.admin_api.approvals")

router = APIRouter(prefix="/approvals", tags=["admin-approvals"])

LUA_CLAIM_DECISION = None  # loaded at startup from storage/lua


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


def _load_lua(redis: Any) -> str:
    from pathlib import Path

    lua_path = (
        Path(__file__).resolve().parents[2] / "app" / "storage" / "lua" / "hitl_claim_decision.lua"
    )
    return lua_path.read_text(encoding="utf-8")


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
    new_status = _validate_decision(req.status)
    pool = request.app.state.services["pg"]
    redis = request.app.state.services["redis"]

    # Check current status
    row = await pool.fetchrow(
        "SELECT status, payload FROM approvals WHERE id = $1", approval_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="approval not found")

    current_status = row["status"]
    if current_status in ApprovalStatus.TERMINAL:
        raise HTTPException(
            status_code=409,
            detail=f"approval {approval_id} is already {current_status!r} — cannot decide again",
        )

    if current_status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"approval {approval_id} has status {current_status!r}, expected pending",
        )

    now = time.time()
    actor = admin["username"]

    # Try atomic Redis claim first
    meta_key = f"hitl:meta:{approval_id}"
    decided_key = f"hitl:decided:{approval_id}"
    lua_script = _load_lua(redis)
    edited_json = json.dumps(req.edited_payload, ensure_ascii=False) if req.edited_payload else ""

    result = await redis.eval(
        lua_script,
        2,
        meta_key,
        decided_key,
        ApprovalStatus.PENDING,
        new_status,
        actor,
        str(int(now)),
        edited_json,
        req.note,
    )

    if int(result) == 0:
        raise HTTPException(
            status_code=409,
            detail=f"approval {approval_id} was decided concurrently (409)",
        )

    # Persist to Postgres execution ledger
    await pool.execute(
        """INSERT INTO approval_execution_ledger
               (approval_id, decided_status, actor, decided_at, edited_payload, note)
           VALUES ($1, $2, $3, to_timestamp($4), $5, $6)
           ON CONFLICT (approval_id) DO UPDATE SET
               decided_status = EXCLUDED.decided_status,
               actor = EXCLUDED.actor,
               decided_at = EXCLUDED.decided_at,
               edited_payload = EXCLUDED.edited_payload,
               note = EXCLUDED.note""",
        approval_id,
        new_status,
        actor,
        now,
        json.dumps(req.edited_payload, ensure_ascii=False) if req.edited_payload else None,
        req.note or None,
    )

    # Update the approvals table status
    await pool.execute(
        """UPDATE approvals SET status = $1, decided_at = to_timestamp($2),
                  actor = $3, note = $4
           WHERE id = $5""",
        new_status,
        now,
        actor,
        req.note or None,
        approval_id,
    )

    # Publish event on bus
    await redis.xadd(
        "bus:events",
        {"type": "approval-decided", "approval_id": approval_id, "status": new_status},
        maxlen=10000,
    )

    log.info(
        "approval decided",
        extra={
            "action": "approval.decide",
            "approval_id": approval_id,
            "status": new_status,
            "actor": actor,
        },
    )

    execution: dict[str, Any] | None = None
    if new_status in {"approved", "edited"}:
        raw = row["payload"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}
        payload = dict(raw or {}) if isinstance(raw, dict) else {}
        action_name = str(payload.get("action") or payload.get("type") or "")
        if action_name:
            from app.core.hitl.execute import execute_action

            outcome = execute_action(
                action_name,
                payload,
                actor_role=str(admin.get("role") or "admin"),
                approved=True,
                context={"approval_id": approval_id, "channel": payload.get("channel")},
                idempotency_key=approval_id,
            )
            execution = outcome.as_dict()

    return {
        "ok": True,
        "approval_id": approval_id,
        "status": new_status,
        "execution": execution,
    }
