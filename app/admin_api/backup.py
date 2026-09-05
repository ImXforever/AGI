"""Admin backup management: manual trigger, status, and history."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.backup")

router = APIRouter(prefix="/backup", tags=["admin-backup"])

_backup_status: dict[str, Any] = {
    "last_run": None,
    "last_result": None,
    "last_error": None,
    "running": False,
}


@router.post("/trigger")
async def trigger_backup(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Manually trigger a database backup."""
    if _backup_status["running"]:
        raise HTTPException(status_code=409, detail="backup already in progress")

    from app.storage.archive import _run_single_backup
    from app.storage.r2 import R2Archive
    from app.config import get_config

    cfg = get_config()
    if not cfg.ops.backup_enabled:
        raise HTTPException(status_code=400, detail="backup is disabled in config")

    _backup_status["running"] = True
    _backup_status["last_error"] = None

    async def _run() -> None:
        try:
            r2 = R2Archive()
            r2.ensure_bucket()
            await _run_single_backup(r2, cfg.storage.pg_dump_retention_days)
            import time
            _backup_status["last_run"] = time.time()
            _backup_status["last_result"] = "success"
            log.info(
                "manual_backup_completed",
                extra={"action": "admin.backup", "admin": admin["username"]},
            )
        except Exception as exc:
            _backup_status["last_result"] = "failed"
            _backup_status["last_error"] = str(exc)[:500]
            log.exception(
                "manual_backup_failed",
                extra={"action": "admin.backup", "admin": admin["username"]},
            )
        finally:
            _backup_status["running"] = False

    asyncio.create_task(_run())

    return {"ok": True, "message": "backup started"}


@router.get("/status")
async def backup_status(
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Get backup status."""
    return _backup_status
