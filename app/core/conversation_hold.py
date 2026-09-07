"""Pause the bot on a conversation while a manager is in the thread."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HOLD_NOTICE_EN = "A manager is handling this conversation. We will reply when they finish."


@dataclass(frozen=True)
class ConversationHold:
    conversation_id: str
    actor: str
    until: float
    reason: str


def hold_redis_key(conversation_id: str) -> str:
    return f"hold:{str(conversation_id or '').strip()}"


def is_held(
    *,
    until: float | None = None,
    now: float = 0.0,
    status: str = "",
    redis_value: str | None = None,
) -> bool:
    """True when a manager hold is still active."""
    if str(status or "").strip().lower() in {"held", "paused"}:
        return True
    if redis_value:
        return True
    if until is None:
        return False
    try:
        return float(until) > float(now)
    except (TypeError, ValueError):
        return False


def is_manager_sender(sender_id: str, admin_ids: list[Any] | tuple[Any, ...] | None) -> bool:
    sid = str(sender_id or "").strip()
    if not sid:
        return False
    return sid in {str(x).strip() for x in (admin_ids or ()) if str(x).strip()}


def hold_until(now: float, timeout_seconds: int) -> float:
    return float(now) + max(1, int(timeout_seconds))
