"""Pipeline — incoming message ingestion, dedup, storage, and stream consumer."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from app.config import get_config
from app.constants import (
    CONSUMER_PREFIX,
    EVENT_INCOMING,
    GROUP_EVENTS,
    STREAM_EVENTS,
)
from app.logging_setup import get_logger
from app.storage.redis import check_dedup, check_rate_limit, get_redis, publish_event

_CONV_NS = uuid.UUID("6f1d1a10-3f52-4d0b-9a3e-1f8a7c2b4d55")

log = get_logger("app.core.pipeline")

_CONSUMER_SUFFIX = "incoming"


async def ingest_incoming(
    *,
    channel: str,
    sender_id: str,
    sender_name: str,
    text: str,
    external_ref: str,
    conversation_id: str = "",
    attachments: tuple[Any, ...] = (),
    reply_to_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    services: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """End-to-end ingestion of an incoming message.

    Deduplication → rate limit → customer/conversation upsert → attachment
    archival → message storage → event publish → hand off to orchestrator.

    Returns a summary dict consumed by the gateway adapter.
    """
    t0 = time.perf_counter()
    cfg = get_config()
    meta = dict(metadata or {})
    result: dict[str, Any] = {
        "accepted": False,
        "conversation_id": conversation_id,
        "channel": channel,
        "reason": "",
    }

    # ── Dedup ─────────────────────────────────────────────────────────
    redis = services.get("redis") if services else None
    if redis is None:
        from app.storage.redis import get_redis as _get_redis

        redis = await _get_redis()

    is_dup = await check_dedup(channel, external_ref)
    if is_dup:
        result["reason"] = "duplicate"
        log.info(
            "ingest_dedup", extra={"action": "ingest", "channel": channel, "ext_ref": external_ref}
        )
        return result

    # ── Rate limit ────────────────────────────────────────────────────
    allowed, remaining, retry_after = await check_rate_limit(
        channel,
        sender_id,
        window=60,
        limit=cfg.channels.rate_limit_per_minute,
    )
    if not allowed:
        result["reason"] = "rate_limited"
        log.warning(
            "ingest_rate_limited",
            extra={
                "action": "ingest",
                "channel": channel,
                "sender_id": sender_id,
                "retry_after": retry_after,
            },
        )
        return result

    # ── Customer & conversation ───────────────────────────────────────
    pg = services.get("pg") if services else None
    if pg is None:
        from app.storage.pg import get_pool

        pg = await get_pool()

    from app.core.repository import get_or_create_conversation, get_or_create_customer

    customer = await get_or_create_customer(
        pg,
        channel=channel,
        sender_id=sender_id,
        sender_name=sender_name,
    )
    customer_id = customer.get("id", "")

    if not conversation_id:
        # conversations.id is a UUID column — derive a deterministic one from
        # the channel/sender pair instead of a composite string.
        conversation_id = str(uuid.uuid5(_CONV_NS, f"{channel}:{sender_id}"))
    else:
        try:
            uuid.UUID(conversation_id)
        except (ValueError, AttributeError, TypeError):
            conversation_id = str(uuid.uuid5(_CONV_NS, f"{channel}:{conversation_id}"))

    conv = await get_or_create_conversation(
        pg,
        conversation_id=conversation_id,
        customer_id=customer_id,
        channel=channel,
    )
    result["conversation_id"] = conversation_id
    meta["customer_id"] = customer_id

    # ── Conversation history ──────────────────────────────────────────
    from app.core.repository import get_conversation_history

    history = await get_conversation_history(pg, conversation_id, limit=10)
    meta["conversation_history"] = [
        {"role": m.get("role", "user"), "content": m.get("content", "")} for m in history
    ]

    # ── Attachment archival ───────────────────────────────────────────
    r2 = services.get("r2") if services else None
    attachment_keys: list[str] = []
    if attachments and r2 is not None:
        for att in attachments:
            try:
                key = r2.write_attachment(
                    conversation_id,
                    att.filename,
                    att.data,
                    content_type=att.content_type,
                )
                attachment_keys.append(key)
            except Exception as exc:
                log.warning(
                    "attachment_archive_failed", extra={"action": "ingest", "error": str(exc)}
                )
    meta["attachment_keys"] = attachment_keys

    # ── Message storage ───────────────────────────────────────────────
    from app.core.repository import store_message

    await store_message(
        pg,
        conversation_id=conversation_id,
        role="user",
        content=text,
        channel=channel,
        external_ref=external_ref,
        metadata=meta,
    )

    # ── Publish to event stream ───────────────────────────────────────
    event_payload = {
        "channel": channel,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "text": text,
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "external_ref": external_ref,
        "reply_to_ref": reply_to_ref,
        "metadata": meta,
    }
    msg_id = await publish_event(
        EVENT_INCOMING,
        event_payload,
        conversation_id=conversation_id,
        channel=channel,
    )

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    result["accepted"] = True
    result["event_msg_id"] = msg_id
    result["latency_ms"] = latency_ms

    log.info(
        "ingest_complete",
        extra={
            "action": "ingest",
            "channel": channel,
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "latency_ms": latency_ms,
        },
    )
    return result


async def start_incoming_consumer(app: Any) -> None:
    """Redis stream consumer loop for the ``bus:events`` stream.

    Reads events of type ``incoming`` and dispatches them to the orchestrator.
    Designed to run as a long-lived ``asyncio.Task``.
    """
    cfg = get_config()
    redis = await get_redis()
    consumer_name = f"{CONSUMER_PREFIX}:{_CONSUMER_SUFFIX}"

    # Ensure consumer group exists
    try:
        await redis.xgroup_create(STREAM_EVENTS, GROUP_EVENTS, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            log.error(
                "stream_group_create_failed",
                extra={"action": "start_incoming_consumer", "error": str(exc)},
            )

    log.info(
        "incoming_consumer_started",
        extra={"action": "start_incoming_consumer", "consumer": consumer_name},
    )

    while True:
        try:
            entries = await redis.xreadgroup(
                GROUP_EVENTS,
                consumer_name,
                {STREAM_EVENTS: ">"},
                count=5,
                block=5000,
            )
        except asyncio.CancelledError:
            log.info("incoming_consumer_cancelled", extra={"action": "start_incoming_consumer"})
            break
        except Exception as exc:
            log.error(
                "incoming_consumer_read_error",
                exc_info=exc,
                extra={"action": "start_incoming_consumer", "error": str(exc)},
            )
            await asyncio.sleep(1)
            continue

        if not entries:
            continue

        entries_any: Any = entries
        for entry in entries_any:
            _stream_name, messages = entry
            messages_any: Any = messages
            for message_entry in messages_any:
                msg_id, fields = message_entry
                if not isinstance(fields, dict):
                    await redis.xack(STREAM_EVENTS, GROUP_EVENTS, msg_id)
                    continue
                event_type = fields.get("type", "")
                if event_type != EVENT_INCOMING:
                    await redis.xack(STREAM_EVENTS, GROUP_EVENTS, msg_id)
                    continue

                try:
                    await _dispatch_incoming(fields, app)
                except Exception as exc:
                    log.exception(
                        "incoming_dispatch_error",
                        extra={
                            "action": "start_incoming_consumer",
                            "msg_id": msg_id,
                            "error": str(exc),
                        },
                    )
                    continue
                finally:
                    await redis.xack(STREAM_EVENTS, GROUP_EVENTS, msg_id)


async def _dispatch_incoming(fields: dict[str, str], app: Any) -> None:
    """Parse an incoming event and route it to the orchestrator."""
    import json as _json

    payload_raw = fields.get("payload", "{}")
    try:
        payload = _json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
    except _json.JSONDecodeError:
        log.error("invalid_event_payload", extra={"action": "dispatch_incoming"})
        return

    if not isinstance(payload, dict):
        log.error("invalid_event_payload_type", extra={"action": "dispatch_incoming"})
        return

    from app.channels.base import Attachment, IncomingMessage

    channel = payload.get("channel", "")
    sender_id = payload.get("sender_id", "")
    sender_name = payload.get("sender_name", "")
    text = payload.get("text", "")
    conversation_id = payload.get("conversation_id", "")
    external_ref = payload.get("external_ref", "")
    reply_to_ref = payload.get("reply_to_ref")
    meta = payload.get("metadata", {})

    attachments_raw = payload.get("attachments", [])
    attachments: list[Attachment] = []
    for att in attachments_raw:
        try:
            attachments.append(
                Attachment(
                    filename=att.get("filename", "file"),
                    content_type=att.get("content_type", "application/octet-stream"),
                    data=b"",
                    size=att.get("size", 0),
                    url=att.get("url"),
                )
            )
        except Exception:
            log.debug("incoming_attachment_parse_failed", exc_info=True)
            continue

    message = IncomingMessage(
        channel=channel,
        sender_id=sender_id,
        sender_name=sender_name,
        text=text,
        conversation_id=conversation_id,
        external_ref=external_ref,
        attachments=tuple(attachments),
        reply_to_ref=reply_to_ref,
        metadata=meta,
    )

    services: dict[str, Any] = getattr(app.state, "services", {})
    from app.core.orchestrator import handle_incoming

    await handle_incoming(message, services)
