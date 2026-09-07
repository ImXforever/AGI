"""Automation rules API endpoints (v20)."""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.automation")

router = APIRouter(prefix="/automation", tags=["admin-automation"])


class RuleCreate(BaseModel):
    name: str
    description: str
    trigger: str
    conditions: dict[str, Any]
    actions: list[dict[str, Any]]
    priority: int = 0


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    conditions: dict[str, Any] | None = None
    actions: list[dict[str, Any]] | None = None
    enabled: bool | None = None
    priority: int | None = None


@router.get("/rules")
async def list_rules(
    request: Request,
    trigger: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    if trigger:
        rows = await pool.fetch(
            "SELECT * FROM automation_rules WHERE trigger_type = $1 ORDER BY priority DESC", trigger
        )
    else:
        rows = await pool.fetch("SELECT * FROM automation_rules ORDER BY priority DESC")
    return {"rules": [dict(r) for r in rows], "count": len(rows)}


@router.post("/rules")
async def create_rule_endpoint(
    request: Request,
    body: RuleCreate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    import hashlib
    import os

    rule_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO automation_rules (id, name, description, trigger_type, conditions, actions, enabled, priority, created_at, trigger_count)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7, $8, 0)
    """,
        rule_id,
        body.name,
        body.description,
        body.trigger,
        json.dumps(body.conditions),
        json.dumps(body.actions),
        body.priority,
        time.time(),
    )
    return {"id": rule_id, "created": True}


@router.get("/rules/{rule_id}")
async def get_rule(
    request: Request,
    rule_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM automation_rules WHERE id = $1", rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    return dict(row)


@router.put("/rules/{rule_id}")
async def update_rule_endpoint(
    request: Request,
    rule_id: str,
    body: RuleUpdate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM automation_rules WHERE id = $1", rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    if body.name is not None:
        updates.append(f"name = ${idx}")
        params.append(body.name)
        idx += 1
    if body.description is not None:
        updates.append(f"description = ${idx}")
        params.append(body.description)
        idx += 1
    if body.conditions is not None:
        updates.append(f"conditions = ${idx}")
        params.append(json.dumps(body.conditions))
        idx += 1
    if body.actions is not None:
        updates.append(f"actions = ${idx}")
        params.append(json.dumps(body.actions))
        idx += 1
    if body.enabled is not None:
        updates.append(f"enabled = ${idx}")
        params.append(body.enabled)
        idx += 1
    if body.priority is not None:
        updates.append(f"priority = ${idx}")
        params.append(body.priority)
        idx += 1
    if updates:
        params.append(rule_id)
        await pool.execute(
            f"UPDATE automation_rules SET {', '.join(updates)} WHERE id = ${idx}", *params
        )
    return {"id": rule_id, "updated": True}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(
    request: Request,
    rule_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT enabled FROM automation_rules WHERE id = $1", rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    new_state = not row["enabled"]
    await pool.execute("UPDATE automation_rules SET enabled = $1 WHERE id = $2", new_state, rule_id)
    return {"id": rule_id, "enabled": new_state}


@router.delete("/rules/{rule_id}")
async def delete_rule_endpoint(
    request: Request,
    rule_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM automation_rules WHERE id = $1", rule_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"id": rule_id, "deleted": True}


@router.get("/templates")
async def list_templates(
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from app.core.automation_engine import TEMPLATES

    return {"templates": list(TEMPLATES.keys())}


@router.post("/templates/{template_key}/create")
async def create_from_template(
    request: Request,
    template_key: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from app.core.automation_engine import create_from_template

    rule = create_from_template(template_key)
    if not rule:
        raise HTTPException(status_code=404, detail="Template not found")
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO automation_rules (id, name, description, trigger_type, conditions, actions, enabled, priority, created_at, trigger_count)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7, $8, 0)
    """,
        rule.id,
        rule.name,
        rule.description,
        rule.trigger.value,
        json.dumps(rule.conditions),
        json.dumps(rule.actions),
        rule.priority,
        rule.created_at,
    )
    return {"id": rule.id, "created": True, "template": template_key}


@router.get("/stats")
async def automation_stats(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        "SELECT trigger_type, COUNT(*) as count, SUM(trigger_count) as total_fires FROM automation_rules GROUP BY trigger_type"
    )
    return {"by_trigger": [dict(r) for r in rows]}
