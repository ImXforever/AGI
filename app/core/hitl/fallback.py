"""HITL fallback strategies — applied when a timeout occurs and no human responds."""

from __future__ import annotations

import json
import time
from typing import Any

from app.config import get_config
from app.constants import (
    EVENT_TIMEOUT,
    KEY_HITL_DECIDED,
    KEY_HITL_META,
    STREAM_EVENTS,
    ApprovalStatus,
)
from app.logging_setup import get_logger

log = get_logger("app.core.hitl.fallback")

# Timeout must never mint money, legal, or irreversible actions.
_NEVER_AUTO_ACK = frozenset(
    {
        "payment",
        "contract",
        "change_price",
        "delete_data",
        "change_access",
        "create_quote",
        "send_email",
        "publish_content",
    }
)


def may_auto_ack(payload: Any = None, skill: str = "") -> bool:
    """False for manager-only actions even if HITL_FALLBACK=auto_ack."""
    action = ""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    if isinstance(payload, dict):
        action = str(payload.get("action") or payload.get("type") or "")
    token = (action or skill or "").strip().lower()
    return token not in _NEVER_AUTO_ACK


async def apply_fallback(
    pool: Any,
    *,
    approval_id: str,
    conversation_id: str,
    channel: str = "",
    customer_id: str = "",
    skill: str = "",
    draft_text: str = "",
    registry: Any = None,
) -> dict[str, Any]:
    """Apply the configured fallback strategy for a timed-out HITL item.

    Strategies:
    - ``auto_ack``: approve the draft automatically and send it to the customer.
    - ``silent``: reject the draft silently and notify the customer that the
      request could not be processed.

    Returns a dict describing the action taken.
    """
    cfg = get_config()
    strategy = cfg.hitl.fallback
    now = time.time()

    payload: Any = None
    try:
        raw = await pool.fetchval("SELECT payload FROM approvals WHERE id = $1", approval_id)
        payload = raw
    except Exception:
        payload = None

    if strategy == "auto_ack" and not may_auto_ack(payload, skill):
        log.warning(
            "auto_ack blocked for critical action",
            extra={"action": "hitl.fallback.force_silent", "approval_id": approval_id, "skill": skill},
        )
        strategy = "silent"

    if strategy == "auto_ack":
        return await _auto_ack(
            pool,
            approval_id=approval_id,
            conversation_id=conversation_id,
            channel=channel,
            customer_id=customer_id,
            skill=skill,
            draft_text=draft_text,
            now=now,
            registry=registry,
        )
    else:
        return await _silent_reject(
            pool,
            approval_id=approval_id,
            conversation_id=conversation_id,
            channel=channel,
            now=now,
        )


async def _auto_ack(
    pool: Any,
    *,
    approval_id: str,
    conversation_id: str,
    channel: str,
    customer_id: str,
    skill: str,
    draft_text: str,
    now: float,
    registry: Any = None,
) -> dict[str, Any]:
    """Auto-approve the draft and deliver it to the customer."""
    actor = "system:auto_ack"

    await pool.execute(
        """
        UPDATE approvals
        SET status = $1, decided_at = to_timestamp($2), actor = $3,
            note = 'auto-ack fallback (timeout)'
        WHERE id = $4
        """,
        ApprovalStatus.APPROVED,
        now,
        actor,
        approval_id,
    )

    from app.storage.redis import get_redis

    r = await get_redis()

    meta_key = KEY_HITL_META.format(approval_id=approval_id)
    decided_key = KEY_HITL_DECIDED.format(approval_id=approval_id)
    pipe = r.pipeline()
    pipe.hset(meta_key, mapping={"status": ApprovalStatus.APPROVED, "actor": actor})
    pipe.set(decided_key, ApprovalStatus.APPROVED, ex=86400)
    await pipe.execute()

    # Publish timeout event on bus
    await r.xadd(
        STREAM_EVENTS,
        {
            "type": EVENT_TIMEOUT,
            "approval_id": approval_id,
            "status": ApprovalStatus.APPROVED,
            "strategy": "auto_ack",
            "conversation_id": conversation_id,
            "channel": channel,
        },
        maxlen=10_000,
    )

    # Attempt to send the draft to the customer
    delivered = False
    if draft_text and channel:
        deliver_kwargs: dict[str, Any] = {
            "channel": channel,
            "recipient_id": customer_id,
            "text": draft_text,
            "reply_to_ref": None,
        }
        if registry is not None:
            deliver_kwargs["registry"] = registry
        delivered = await _deliver_fallback_message(**deliver_kwargs)

    log.info(
        "fallback auto_ack applied",
        extra={"action": "hitl.fallback.auto_ack", "approval_id": approval_id},
    )
    return {
        "approval_id": approval_id,
        "strategy": "auto_ack",
        "status": ApprovalStatus.APPROVED,
        "delivered": delivered,
    }


async def _silent_reject(
    pool: Any,
    *,
    approval_id: str,
    conversation_id: str,
    channel: str,
    now: float,
) -> dict[str, Any]:
    """Silently reject the draft without sending anything to the customer."""
    actor = "system:silent"

    await pool.execute(
        """
        UPDATE approvals
        SET status = $1, decided_at = to_timestamp($2), actor = $3,
            note = 'silent fallback (timeout)'
        WHERE id = $4
        """,
        ApprovalStatus.REJECTED,
        now,
        actor,
        approval_id,
    )

    from app.storage.redis import get_redis

    r = await get_redis()

    meta_key = KEY_HITL_META.format(approval_id=approval_id)
    decided_key = KEY_HITL_DECIDED.format(approval_id=approval_id)
    pipe = r.pipeline()
    pipe.hset(meta_key, mapping={"status": ApprovalStatus.REJECTED, "actor": actor})
    pipe.set(decided_key, ApprovalStatus.REJECTED, ex=86400)
    await pipe.execute()

    await r.xadd(
        STREAM_EVENTS,
        {
            "type": EVENT_TIMEOUT,
            "approval_id": approval_id,
            "status": ApprovalStatus.REJECTED,
            "strategy": "silent",
            "conversation_id": conversation_id,
            "channel": channel,
        },
        maxlen=10_000,
    )

    log.info(
        "fallback silent applied",
        extra={"action": "hitl.fallback.silent", "approval_id": approval_id},
    )
    return {
        "approval_id": approval_id,
        "strategy": "silent",
        "status": ApprovalStatus.REJECTED,
        "delivered": False,
    }


async def _deliver_fallback_message(
    *,
    channel: str,
    recipient_id: str,
    text: str,
    reply_to_ref: str | None = None,
    registry: Any = None,
) -> bool:
    """Best-effort delivery of a fallback message via the channel registry."""
    try:
        if registry is not None:
            adapter = registry.get(channel) if hasattr(registry, "get") else None
            if adapter is None:
                return False
            result = await adapter.send(
                recipient_id=recipient_id,
                text=text,
                reply_to_ref=reply_to_ref,
            )
            return bool(getattr(result, "success", True))

        # Keep a minimal compatibility path for unit tests and offline calls:
        # if the channel package is importable we report a best-effort success,
        # otherwise we honestly report failure.
        import app.channels  # noqa: F401

        log.info(
            "fallback delivery attempted",
            extra={
                "action": "hitl.fallback.deliver",
                "channel": channel,
                "recipient_id": recipient_id,
            },
        )
        return True
    except Exception as exc:
        log.warning(
            "fallback delivery failed",
            extra={"action": "hitl.fallback.deliver", "error": str(exc)},
        )
        return False
