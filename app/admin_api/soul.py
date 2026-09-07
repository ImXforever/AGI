"""Agent Soul API — read and edit who the bot is (admin console → Soul page)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.core.soul import DEFAULT_SOUL, FIELDS, load_soul, save_soul

router = APIRouter(prefix="/soul", tags=["admin-soul"])


class SoulUpdate(BaseModel):
    agent_name: str | None = Field(default=None, max_length=80)
    company_name: str | None = Field(default=None, max_length=160)
    role_title: str | None = Field(default=None, max_length=120)
    mission: str | None = Field(default=None, max_length=2000)
    personality: str | None = Field(default=None, max_length=2000)
    tone: str | None = Field(default=None, max_length=600)
    languages: str | None = Field(default=None, max_length=600)
    greeting: str | None = Field(default=None, max_length=1000)
    boundaries: str | None = Field(default=None, max_length=3000)
    style_rules: str | None = Field(default=None, max_length=2000)
    signature: str | None = Field(default=None, max_length=200)
    extra: dict[str, Any] | None = None


def _payload(soul: Any) -> dict[str, Any]:
    data = soul.as_dict()
    data["prompt_preview"] = soul.render()
    data["fields"] = list(FIELDS)
    return data


@router.get("")
async def get_soul(
    request: Request, admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    pool = request.app.state.services.get("pg")
    soul = await load_soul(pool, use_cache=False)
    return _payload(soul)


@router.get("/default")
async def get_default_soul(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return _payload(DEFAULT_SOUL)


@router.put("")
async def update_soul(
    req: SoulUpdate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    actor = str(admin.get("username") or admin.get("sub") or "manager")
    soul = await save_soul(pool, req.model_dump(exclude_none=True), updated_by=actor)
    return _payload(soul)
