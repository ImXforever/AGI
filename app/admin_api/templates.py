"""Fallback template management for automated responses."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_superadmin, require_writer
from app.logging_setup import get_logger

log = get_logger("app.admin_api.templates")

router = APIRouter(prefix="/templates", tags=["admin-templates"])


class TemplateCreate(BaseModel):
    key: str
    name_ar: str
    name_en: str = ""
    channel: str = ""
    subject: str = ""
    body_ar: str
    body_en: str = ""
    variables: list[str] = []
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    subject: str | None = None
    body_ar: str | None = None
    body_en: str | None = None
    variables: list[str] | None = None
    is_active: bool | None = None


@router.get("")
async def list_templates(
    request: Request,
    channel: str | None = None,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    if channel:
        rows = await pool.fetch(
            "SELECT * FROM fallback_templates WHERE channel = $1 ORDER BY key", channel
        )
    else:
        rows = await pool.fetch("SELECT * FROM fallback_templates ORDER BY key")
    items = []
    for r in rows:
        d = dict(r)
        d["variables"] = json.loads(d.get("variables") or "[]")
        items.append(d)
    return {"items": items}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM fallback_templates WHERE id = $1", template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template not found")
    d = dict(row)
    d["variables"] = json.loads(d.get("variables") or "[]")
    return d


@router.post("", status_code=201)
async def create_template(
    req: TemplateCreate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    template_id = str(uuid.uuid4())
    await pool.execute(
        """INSERT INTO fallback_templates (id, key, name_ar, name_en, channel, subject,
               body_ar, body_en, variables, is_active, created_at, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW(),NOW())""",
        template_id,
        req.key,
        req.name_ar,
        req.name_en,
        req.channel,
        req.subject,
        req.body_ar,
        req.body_en,
        json.dumps(req.variables),
        req.is_active,
    )
    log.info("template created", extra={"action": "template.create", "template_id": template_id})
    row = await pool.fetchrow("SELECT * FROM fallback_templates WHERE id = $1", template_id)
    d = dict(row)
    d["variables"] = json.loads(d.get("variables") or "[]")
    return d


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    req: TemplateUpdate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT id FROM fallback_templates WHERE id = $1", template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="template not found")

    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    for field_name in ("name_ar", "name_en", "subject", "body_ar", "body_en", "is_active"):
        val = getattr(req, field_name)
        if val is not None:
            updates.append(f"{field_name} = ${idx}")
            params.append(val)
            idx += 1
    if req.variables is not None:
        updates.append(f"variables = ${idx}")
        params.append(json.dumps(req.variables))
        idx += 1
    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")
    updates.append("updated_at = NOW()")
    params.append(template_id)
    await pool.execute(
        f"UPDATE fallback_templates SET {', '.join(updates)} WHERE id = ${idx}", *params
    )
    row = await pool.fetchrow("SELECT * FROM fallback_templates WHERE id = $1", template_id)
    d = dict(row)
    d["variables"] = json.loads(d.get("variables") or "[]")
    return d


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM fallback_templates WHERE id = $1", template_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="template not found")
    return {"ok": True}
