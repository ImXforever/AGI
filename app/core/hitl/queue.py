"""HITL queue — enqueue approval requests into Redis streams + Postgres ledger."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, cast

from asyncpg.pool import Pool

from app.config import get_config
from app.constants import KEY_HITL_META, STREAM_HITL, ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.core.hitl.queue")


async def enqueue(
    pool: Pool,
    *,
    conversation_id: str,
    tool_name: str,
    params: dict[str, Any],
    stream: str = STREAM_HITL,
    timeout_seconds: int | None = None,
    customer_id: str = "",
    channel: str = "",
) -> str:
    """Push an approval request onto the HITL queue.

    1. Inserts a row into the ``approvals`` table (status = pending).
    2. Sets the Redis metadata hash for atomic claim/decision logic.
    3. Publishes the request onto the Redis stream so the sweeper picks it up.

    Returns the ``approval_id``.
    """
    cfg = get_config()
    if timeout_seconds is None:
        timeout_seconds = cfg.hitl.timeout_seconds

    approval_id = uuid.uuid4().hex
    now = time.time()

    # Persist to Postgres
    await pool.execute(
        """
        INSERT INTO approvals (
            id, conversation_id, channel, skill, intent,
            draft_text, status, confidence, needs_hitl,
            payload, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, to_timestamp($11))
        """,
        approval_id,
        conversation_id,
        channel,
        tool_name,
        tool_name,
        json.dumps(params, ensure_ascii=False, default=str),
        ApprovalStatus.PENDING,
        0.0,
        True,
        json.dumps(params, ensure_ascii=False, default=str),
        now,
    )

    # Set Redis metadata
    from app.storage.redis import get_redis

    r = await get_redis()
    meta_key = KEY_HITL_META.format(approval_id=approval_id)
    pipe = r.pipeline()
    pipe.hset(
        meta_key,
        mapping={
            "approval_id": approval_id,
            "status": ApprovalStatus.PENDING,
            "conversation_id": conversation_id,
            "channel": channel,
            "tool_name": tool_name,
            "customer_id": customer_id,
            "created_at": f"{now:.3f}",
            "expires_at": f"{now + timeout_seconds:.3f}",
        },
    )
    pipe.expire(meta_key, timeout_seconds + 120)
    await pipe.execute()

    # Publish to stream
    message: dict[str, Any] = {
        "approval_id": approval_id,
        "conversation_id": conversation_id,
        "channel": channel,
        "tool_name": tool_name,
        "customer_id": customer_id,
        "payload": json.dumps(params, ensure_ascii=False, default=str),
        "ts": f"{now:.3f}",
        "timeout_seconds": str(timeout_seconds),
    }
    await r.xadd(cast("str", stream), cast("Any", message), maxlen=5_000, approximate=True)

    log.info(
        "hitl enqueued",
        extra={
            "action": "hitl.enqueue",
            "approval_id": approval_id,
            "conversation_id": conversation_id,
            "tool_name": tool_name,
            "timeout": timeout_seconds,
        },
    )
    return approval_id


async def get_pending(pool: Pool, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Fetch pending approval items from Postgres."""
    total = await pool.fetchval(
        "SELECT COUNT(*) FROM approvals WHERE status = $1",
        ApprovalStatus.PENDING,
    )
    rows = await pool.fetch(
        """
        SELECT id, conversation_id, channel, skill, intent,
               draft_text, status, confidence, needs_hitl,
               payload, created_at, decided_at, actor, note
        FROM approvals
        WHERE status = $1
        ORDER BY created_at ASC
        LIMIT $2 OFFSET $3
        """,
        ApprovalStatus.PENDING,
        limit,
        offset,
    )
    return {
        "total": total,
        "items": [dict(r) for r in rows],
        "limit": limit,
        "offset": offset,
    }


async def get_approval(pool: Pool, approval_id: str) -> dict[str, Any] | None:
    """Fetch a single approval item."""
    row = await pool.fetchrow(
        """
        SELECT id, conversation_id, channel, skill, intent,
               draft_text, status, confidence, needs_hitl,
               payload, created_at, decided_at, actor, note
        FROM approvals
        WHERE id = $1
        """,
        approval_id,
    )
    return dict(row) if row else None


async def count_pending(pool: Pool) -> int:
    """Return the count of pending approvals."""
    return await pool.fetchval(
        "SELECT COUNT(*) FROM approvals WHERE status = $1",
        ApprovalStatus.PENDING,
    )
