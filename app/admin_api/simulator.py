"""Admin API — bot simulator (1.5.0).

A 100 % clone of the customer bot inside the admin console: every message is
routed through :func:`app.core.orchestrator.handle_incoming` on the WhatsApp
channel with a capturing adapter (see :mod:`app.core.simulator`). Files can be
dropped in and removed per session; their extracted text travels with the
next message exactly as the production pipeline frames documents.

Endpoints (prefix ``/admin/api/simulator``):

* ``POST   /message``               → run one turn, returns the bot replies
* ``GET    /history?session=``      → stored turns for a session
* ``GET    /files?session=``        → files attached to a session
* ``POST   /files?session=``        → multipart upload (≤ 10 MB, allow-listed MIME)
* ``DELETE /files/{file_id}``       → remove one file
* ``DELETE /session``               → forget files, language and stored turns
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_writer
from app.core import simulator as sim
from app.core.business_settings import LANGUAGE_CODES
from app.logging_setup import get_logger

log = get_logger("app.admin_api.simulator")

router = APIRouter(prefix="/simulator", tags=["admin-simulator"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class SimMessage(BaseModel):
    text: str = Field(default="", max_length=4000)
    session: str = Field(default="default", max_length=64)
    language: str = Field(default="", max_length=8)
    use_files: bool = True
    sender_name: str = Field(default="Simulator", max_length=80)


def _services(request: Request) -> dict[str, Any]:
    return getattr(request.app.state, "services", {}) or {}


def _actor(admin: dict[str, Any]) -> str:
    return str(admin.get("username") or admin.get("sub") or "manager")


@router.post("/message")
async def post_message(
    req: SimMessage, request: Request, admin: dict[str, Any] = Depends(require_writer)
) -> dict[str, Any]:
    services = _services(request)
    if req.language and req.language.lower() not in LANGUAGE_CODES:
        raise HTTPException(status_code=422, detail="unsupported language")
    try:
        out = await sim.run_turn(
            services,
            session=req.session,
            text=req.text,
            sender_name=req.sender_name or "Simulator",
            language=req.language.lower(),
            use_files=req.use_files,
            actor=_actor(admin),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.error(
            "simulator_turn_failed: %s: %s",
            type(exc).__name__,
            str(exc)[:300],
            exc_info=exc,
            extra={"action": "simulator", "error": str(exc)},
        )
        raise HTTPException(status_code=503, detail="simulator unavailable") from exc
    try:
        from app.storage.pg import audit

        await audit(
            action="simulator.message",
            actor=_actor(admin),
            entity="simulator",
            entity_id=out.get("session", ""),
            details={"chars": len(req.text), "files": len(out.get("files_used", []))},
            conversation_id=out.get("conversation_id"),
            channel="whatsapp",
        )
    except Exception:
        log.debug("simulator_audit_failed", exc_info=True)
    return out


@router.get("/history")
async def get_history(
    request: Request,
    session: str = Query(default="default", max_length=64),
    limit: int = Query(default=60, ge=1, le=200),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    services = _services(request)
    try:
        turns = await sim.history(services, session, limit=limit)
    except Exception:
        log.debug("simulator_history_failed", exc_info=True)
        turns = []
    return {
        "ok": True,
        "session": sim.sanitize_session(session),
        "conversation_id": sim.conversation_id_for(session),
        "turns": turns,
    }


@router.get("/files")
async def get_files(
    request: Request,
    session: str = Query(default="default", max_length=64),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    files = await sim.list_files(_services(request).get("redis"), session)
    return {
        "ok": True,
        "session": sim.sanitize_session(session),
        "files": [sim.public_file(f) for f in files],
        "limits": {"max_files": sim.MAX_FILES_PER_SESSION, "max_bytes": MAX_UPLOAD_BYTES},
    }


@router.post("/files", status_code=201)
async def upload_file(
    request: Request,
    session: str = Query(default="default", max_length=64),
    file: UploadFile = File(...),
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    redis = _services(request).get("redis")
    if redis is None:
        raise HTTPException(status_code=503, detail="redis unavailable")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 10 MB)")
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    try:
        entry = await sim.add_file(
            redis,
            session,
            name=file.filename or "file",
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    return {"ok": True, "session": sim.sanitize_session(session), "file": sim.public_file(entry)}


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    session: str = Query(default="default", max_length=64),
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    redis = _services(request).get("redis")
    removed = await sim.remove_file(redis, session, file_id) if redis is not None else False
    if not removed:
        raise HTTPException(status_code=404, detail="file not found")
    return {"ok": True, "removed": file_id}


@router.delete("/session")
async def delete_session(
    request: Request,
    session: str = Query(default="default", max_length=64),
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    return await sim.reset(_services(request), session)
