"""Expose the 15-layer security catalog to the manager console."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.admin_api.auth import require_admin
from app.core.security_stack import layers_catalog

router = APIRouter(prefix="/security", tags=["admin-security"])


@router.get("/layers")
async def get_layers(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {"count": 15, "layers": layers_catalog(), "viewer": admin.get("username") or ""}
