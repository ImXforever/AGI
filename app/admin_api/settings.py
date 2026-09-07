"""Manager console — configuration variables.

* ``GET /settings`` — every *deployment* variable (env), secrets masked. Read-only.
* ``GET /settings/business`` — the *business* variables a manager may edit
  (company contact, bot menu behaviour, quote rules, notifications) with the
  field spec the console renders. 1.4.0.
* ``PUT /settings/business`` — save one or more business variables. Values
  are validated against :mod:`app.core.business_settings` and take effect on
  the bot's next message — no redeploy.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.config import as_admin_settings, get_config

router = APIRouter(prefix="/settings", tags=["admin-settings"])


class BusinessSettingsIn(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def get_settings(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    snap = as_admin_settings(get_config())
    snap["viewer"] = admin.get("username") or ""
    return snap


@router.get("/business")
async def get_business_settings(
    request: Request, admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    from app.core.business_settings import load_settings, spec_payload

    pool = request.app.state.services.get("pg")
    values = await load_settings(pool, use_cache=False)
    cfg = get_config()
    return {
        "values": values,
        "spec": spec_payload(),
        "env": {
            "currency": cfg.domain.currency,
            "tax_rate": cfg.domain.tax_rate,
            "quote_valid_days": cfg.domain.quote_valid_days,
            "support_contact": cfg.tenant.support_contact,
            "timezone": cfg.tenant.timezone,
            "hitl_timeout_seconds": cfg.hitl.timeout_seconds,
            "hitl_fallback": cfg.hitl.fallback,
            "telegram_admins": len(cfg.channels.telegram_admin_ids),
            "whatsapp_enabled": cfg.channels.whatsapp_enabled,
            "email_enabled": cfg.channels.email_enabled,
            "llm_mode": cfg.llm.mode,
        },
    }


@router.put("/business")
async def put_business_settings(
    req: BusinessSettingsIn,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    from app.core.business_settings import SettingError, save_settings

    pool = request.app.state.services.get("pg")
    if pool is None:
        raise HTTPException(status_code=503, detail="database unavailable")
    if not req.values:
        raise HTTPException(status_code=400, detail="no values")
    try:
        values = await save_settings(pool, req.values, updated_by=str(admin.get("username") or ""))
    except SettingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "values": values, "saved": sorted(req.values)}
