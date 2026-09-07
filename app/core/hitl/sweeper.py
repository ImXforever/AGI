"""HITL sweeper — background task that times out stale approval requests."""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_config
from app.constants import KEY_HITL_META, ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.core.hitl.sweeper")

SWEEP_INTERVAL = 30  # seconds between sweep cycles


def should_timeout_without_redis(*, claimed: bool, redis_status: str | None) -> bool:
    """Redis Lua claim is authoritative when the meta key is still pending.

    Production leftover: Postgres still has ``pending`` rows whose Redis
    hash expired or was never written. Those must still leave the queue,
    otherwise the sweeper logs the same 50 rows forever.

    ``timeout`` in Redis with Postgres still pending means a previous claim
    never finished fallback — retry it.
    """
    if claimed:
        return True
    status = (redis_status or "").strip().lower()
    if status in ("", "timeout"):
        return True
    return False


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

    from app.core.hitl.fallback import apply_fallback
    from app.storage.redis import hitl_timeout_claim

    applied = 0
    skipped = 0
    for row in rows:
        approval_id = str(row["id"])
        meta_key = KEY_HITL_META.format(approval_id=approval_id)
        claimed = await hitl_timeout_claim(approval_id)
        redis_status = await redis.hget(meta_key, "status")
        if isinstance(redis_status, bytes):
            redis_status = redis_status.decode()
        if not should_timeout_without_redis(claimed=claimed, redis_status=redis_status):
            skipped += 1
            continue

        meta = await redis.hgetall(meta_key)
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
        applied += 1
        log.info(
            "sweeper fallback applied",
            extra={
                "action": "sweeper.fallback",
                "approval_id": approval_id,
                "strategy": result.get("strategy"),
                "status": result.get("status"),
                "orphan": not claimed,
            },
        )

    log.info(
        "sweeper scan",
        extra={
            "action": "sweeper.scan",
            "expired": len(rows),
            "applied": applied,
            "skipped_locked": skipped,
        },
    )
