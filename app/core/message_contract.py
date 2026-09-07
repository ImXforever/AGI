"""Canonical validation and normalization for inbound message envelopes.

v0.2 makes the message boundary explicit. Channel adapters may differ in their
provider payloads, but the pipeline only accepts this small, validated contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.channels.base import normalize_text
from app.constants import CHANNELS

_MAX_META_KEYS = 32
_MAX_META_KEY = 64
_MAX_META_VAL = 500


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
        metadata=sanitize_metadata(envelope.metadata),
    )


def sanitize_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Drop nested blobs and cap keys so adapters cannot poison Redis/Postgres."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if len(out) >= _MAX_META_KEYS:
            break
        name = str(key).strip()[:_MAX_META_KEY]
        if not name or isinstance(value, (dict, list, bytes, bytearray)):
            continue
        if value is None or isinstance(value, bool):
            out[name] = value
            continue
        if isinstance(value, (int, float)):
            out[name] = value
            continue
        text = str(value)
        out[name] = text if len(text) <= _MAX_META_VAL else text[:_MAX_META_VAL]
    return out


def attachment_refs(
    attachments: tuple[Any, ...] | list[Any] = (), r2_keys: list[str] | None = None
) -> list[dict[str, Any]]:
    """Bytes never go on the Redis stream — only filename, type, size, url, r2 key."""
    keys = list(r2_keys or [])
    refs: list[dict[str, Any]] = []
    for i, att in enumerate(attachments or ()):
        if isinstance(att, dict):
            filename = str(att.get("filename") or "file")
            content_type = str(att.get("content_type") or "application/octet-stream")
            size = int(att.get("size") or 0)
            url = att.get("url")
        else:
            filename = str(getattr(att, "filename", None) or "file")
            content_type = str(getattr(att, "content_type", None) or "application/octet-stream")
            size = int(getattr(att, "size", None) or 0)
            url = getattr(att, "url", None)
        refs.append(
            {
                "filename": filename[:180],
                "content_type": content_type[:120],
                "size": size,
                "url": str(url)[:500] if url else None,
                "r2_key": keys[i] if i < len(keys) else None,
            }
        )
    return refs
