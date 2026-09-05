"""Canonical validation and normalization for inbound message envelopes.

v0.2 makes the message boundary explicit. Channel adapters may differ in their
provider payloads, but the pipeline only accepts this small, validated contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.channels.base import normalize_text
from app.constants import CHANNELS


class MessageContractError(ValueError):
    """Raised when an inbound message cannot safely enter the pipeline."""


@dataclass(frozen=True)
class MessageEnvelope:
    channel: str
    sender_id: str
    sender_name: str
    text: str
    external_ref: str
    conversation_id: str = ""
    metadata: dict[str, Any] | None = None


def normalize_envelope(envelope: MessageEnvelope) -> MessageEnvelope:
    """Validate and normalize an inbound envelope before persistence.

    Empty text is allowed for attachment-only messages. An external reference
    is mandatory because deduplication cannot be safe without one.
    """
    channel = envelope.channel.strip().lower()
    if channel not in CHANNELS:
        raise MessageContractError(f"unsupported channel: {channel!r}")

    sender_id = envelope.sender_id.strip()
    if not sender_id:
        raise MessageContractError("sender_id must not be empty")

    external_ref = envelope.external_ref.strip()
    if not external_ref:
        raise MessageContractError("external_ref must not be empty")

    text = normalize_text(envelope.text or "")
    sender_name = normalize_text(envelope.sender_name or sender_id)
    if len(text) > 100_000:
        raise MessageContractError("message text exceeds 100000 characters")

    return MessageEnvelope(
        channel=channel,
        sender_id=sender_id,
        sender_name=sender_name,
        text=text,
        external_ref=external_ref,
        conversation_id=envelope.conversation_id.strip(),
        metadata=dict(envelope.metadata or {}),
    )
