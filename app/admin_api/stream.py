"""SSE (Server-Sent Events) stream for the admin dashboard.

Events emitted:
- ``ready``              — sent once after connection is established
- ``queue``              — current pending approval count
- ``approval_created``   — new pending approval appeared
- ``approval_decided``   — an approval was decided (approve/reject/edit)
- ``heartbeat``          — every 15 seconds to keep the connection alive
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.admin_api.auth import require_admin
from app.constants import STREAM_EVENTS
from app.logging_setup import get_logger

log = get_logger("app.admin_api.stream")

router = APIRouter(tags=["admin-stream"])

HEARTBEAT_INTERVAL = 15  # seconds


async def _event_stream(request: Request, admin: dict[str, Any]) -> Any:
    """Generator that yields SSE frames from the Redis ``bus:events`` stream."""
    redis = request.app.state.services["redis"]
    pool = request.app.state.services["pg"]

    # Send initial ready frame
    yield _sse("ready", {"ts": time.time(), "user": admin.get("username", "")})

    # Send current pending count
    pending = await pool.fetchval("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
    yield _sse("queue", {"pending": pending})

    last_id = "$"
    heartbeat_at = time.time()

    try:
        while True:
            if await request.is_disconnected():
                break

            # Block-read the Redis stream for up to 2 seconds
            try:
                entries = await redis.xread(
                    {STREAM_EVENTS: last_id},
                    count=10,
                    block=2000,
                )
            except Exception:
                entries = {}

            if entries:
                for _stream_name, messages in entries.items():
                    for msg_id, fields in messages:
                        last_id = msg_id
                        event_type = fields.get("type", "unknown")
                        payload = {k: v for k, v in fields.items() if k != "type"}
                        yield _sse(event_type, payload)

            # Heartbeat
            now = time.time()
            if now - heartbeat_at >= HEARTBEAT_INTERVAL:
                yield _sse("heartbeat", {"ts": now})
                heartbeat_at = now

            # Periodically refresh pending count
            try:
                pending = await pool.fetchval(
                    "SELECT COUNT(*) FROM approvals WHERE status = 'pending'"
                )
                yield _sse("queue", {"pending": pending})
            except Exception:
                log.debug("approval_queue_count_failed", exc_info=True)

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("SSE stream error", extra={"action": "sse.error", "detail": str(exc)})
        yield _sse("error", {"detail": str(exc)})


def _sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.get("/stream")
async def stream(
    request: Request, admin: dict[str, Any] = Depends(require_admin)
) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request, admin),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/stream/stats")
async def stream_stats(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    pending = await pool.fetchval("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
    total = await pool.fetchval("SELECT COUNT(*) FROM approvals")
    return {
        "pending": pending,
        "total": total,
        "heartbeat_interval": HEARTBEAT_INTERVAL,
    }
