"""Zenovix-Agent Platform — gateway package (webhooks + reverse proxy)."""

from __future__ import annotations

from fastapi import APIRouter

from app.gateway.public_site import router as _public_site_router
from app.gateway.router_proxy import router as _proxy_router
from app.gateway.webhooks import router as _webhooks_router

router = APIRouter()
router.include_router(_webhooks_router)
router.include_router(_proxy_router)
router.include_router(_public_site_router)

__all__ = ["router"]
