"""Base channel data structures, protocol and text helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "Attachment",
    "IncomingMessage",
    "OutboundResult",
    "ChannelAdapter",
    "normalize_text",
]


@dataclass(frozen=True)
class Attachment:
    """A single file attachment carried on a message."""

    filename: str
    content_type: str
    data: bytes
    size: int = 0
    url: str | None = None

    def __post_init__(self) -> None:
        if self.size == 0:
            object.__setattr__(self, "size", len(self.data))


@dataclass(frozen=True)
class IncomingMessage:
    """Normalized inbound message from any channel."""

    channel: str
    sender_id: str
    sender_name: str
    text: str
    conversation_id: str
    external_ref: str
    attachments: tuple[Attachment, ...] = ()
    reply_to_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundResult:
    """Result of sending a message through a channel adapter."""

    success: bool
    external_ref: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ChannelAdapter(Protocol):
    """Interface that every channel adapter must satisfy."""

    channel_name: str

    async def send(
        self,
        recipient_id: str,
        text: str,
        *,
        reply_to_ref: str | None = None,
        parse_mode: str | None = None,
        attachments: list[Attachment] | None = None,
        **kwargs: Any,
    ) -> OutboundResult: ...

    async def parse_incoming(self, payload: dict[str, Any]) -> IncomingMessage | None: ...

    async def notify_admins(self, text: str) -> None: ...

    async def close(self) -> None: ...


_EXTENDED_ESCAPE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
}


def normalize_text(text: str) -> str:
    """Collapse whitespace and strip control characters for safe channel delivery.

    - Replace runs of whitespace with a single space.
    - Strip ASCII control characters (except newlines and tabs).
    - Strip RTL / bidi override characters that can cause rendering issues.
    """
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069]", "", text)
    cleaned = re.sub(r"[^\S\n]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return cleaned.strip()


def escape_html(text: str) -> str:
    """Escape text for Telegram's HTML parse mode."""
    result = text
    for char, entity in _EXTENDED_ESCAPE.items():
        result = result.replace(char, entity)
    return result


def strip_html(text: str) -> str:
    """Best-effort removal of HTML tags."""
    return re.sub(r"<[^>]+>", "", text)
