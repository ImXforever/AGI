"""HITL sweeper — background task that times out stale approval requests."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.config import get_config
from app.constants import KEY_HITL_META, ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.core.hitl.sweeper")

SWEEP_INTERVAL = 30  # seconds between sweep cycles


async def start_sweeper(app: Any) -> None:
    """Background loop that scans for timed-out HITL items and applies fallbacks.

    This coroutine **never** returns.  It is launched as an asyncio task at
    application startup (see ``app.main.bootstrap``).
    """
    log.info("hitl_sweeper_started", extra={"action": "sweeper.start"})

    while True:
        try:
            await _sweep_once(app)
        except asyncio.CancelledError:
            log.info("hitl_sweeper_cancelled", extra={"action": "sweeper.cancel"})
            break
        except Exception as exc:
            log.exception(
                "hitl_sweeper_error",
                extra={"action": "sweeper.error", "error": str(exc)},
            )

        await asyncio.sleep(SWEEP_INTERVAL)


async def _sweep_once(app: Any) -> None:
    """Single sweep cycle: find timed-out items and apply fallbacks."""
    services: dict[str, Any] = getattr(app.state, "services", {})
    pg = services.get("pg")
    redis = services.get("redis")

    if pg is None or redis is None:
        return

    now = time.time()

    # Find pending approvals that have expired
    rows = await pg.fetch(
        """
        SELECT id, conversation_id, channel, skill, intent,
               draft_text, payload, created_at
        FROM approvals
        WHERE status = $1
          AND created_at < NOW() - INTERVAL '1 second' * $2
        ORDER BY created_at ASC
        LIMIT 50
        """,
        ApprovalStatus.PENDING,
        get_config().hitl.timeout_seconds,
    )

    if not rows:
        return

    log.info(
        "sweeper found expired items",
        extra={"action": "sweeper.scan", "count": len(rows)},
    )

    from app.core.hitl.fallback import apply_fallback

    for row in rows:
        approval_id = row["id"]

        # Atomically try to claim the timeout via Redis Lua script
        from app.storage.redis import hitl_timeout_claim

        claimed = await hitl_timeout_claim(approval_id)

        if not claimed:
            continue

        # Read the metadata for fallback context
        meta = await redis.hgetall(KEY_HITL_META.format(approval_id=approval_id))
        conversation_id = (meta or {}).get("conversation_id", row["conversation_id"])
        channel = (meta or {}).get("channel", row["channel"] or "")
        customer_id = (meta or {}).get("customer_id", "")
        skill = (meta or {}).get("skill", row["skill"] or "")
        draft_text = row["draft_text"] or ""

        result = await apply_fallback(
            pg,
            approval_id=approval_id,
            conversation_id=conversation_id,
            channel=channel,
            customer_id=customer_id,
            skill=skill,
            draft_text=draft_text,
            registry=services.get("registry"),
        )

        log.info(
            "sweeper fallback applied",
            extra={
                "action": "sweeper.fallback",
                "approval_id": approval_id,
                "strategy": result.get("strategy"),
                "status": result.get("status"),
            },
        )
