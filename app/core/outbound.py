"""At-most-once outbound after a manager approval."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutboundJob:
    channel: str
    recipient_id: str
    text: str
    approval_id: str = ""
    idempotency_key: str = ""


@dataclass(frozen=True)
class DeliverResult:
    sent: bool
    duplicate: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"sent": self.sent, "duplicate": self.duplicate, "reason": self.reason}


class MemoryClaimStore:
    """SET NX stand-in for tests and in-process fallback."""

    def __init__(self) -> None:
        self._keys: set[str] = set()

    def claim(self, key: str) -> bool:
        if not key or key in self._keys:
            return False
        self._keys.add(key)
        return True

    def release(self, key: str) -> None:
        self._keys.discard(key)


def make_idempotency_key(approval_id: str, channel: str, recipient_id: str, text: str) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]
    return f"out:{approval_id or '-'}:{channel}:{recipient_id}:{digest}"


def deliver_once(
    store: MemoryClaimStore,
    job: OutboundJob,
    sender: Callable[[OutboundJob], bool],
) -> DeliverResult:
    key = job.idempotency_key or make_idempotency_key(
        job.approval_id, job.channel, job.recipient_id, job.text
    )
    if not store.claim(key):
        return DeliverResult(sent=False, duplicate=True, reason="duplicate")
    if not str(job.recipient_id or "").strip() or not str(job.text or "").strip():
        store.release(key)
        return DeliverResult(sent=False, duplicate=False, reason="empty")
    try:
        ok = bool(sender(job))
    except Exception:
        store.release(key)
        return DeliverResult(sent=False, duplicate=False, reason="send_failed")
    if not ok:
        store.release(key)
        return DeliverResult(sent=False, duplicate=False, reason="send_failed")
    return DeliverResult(sent=True, duplicate=False, reason="sent")
