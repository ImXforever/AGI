"""Charter API — employer access matrix, domains, phases."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.admin_api.auth import require_admin
from app.core.company_charter import charter_snapshot

router = APIRouter(prefix="/charter", tags=["admin-charter"])


@router.get("")
async def get_charter(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    snap = charter_snapshot()
    snap["viewer"] = admin.get("username") or admin.get("sub") or ""
    return snap
