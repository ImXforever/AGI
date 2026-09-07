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


# ---------------------------------------------------------------------------
# 1.5.0 — attachment text (documents / PDFs / images) reaches the model
# ---------------------------------------------------------------------------

MAX_FILE_TEXT_CHARS = 6000
MAX_FILES_TEXT_TOTAL = 12000
_TEXT_MIME_PREFIXES = (
    "application/pdf",
    "image/",
    "text/",
    "application/json",
    "application/xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",  # Telegram sends many documents without a MIME
)


async def attach_file_text(
    channel: str,
    text: str,
    attachments: tuple[Any, ...],
    services: dict[str, Any] | None,
) -> tuple[str, list[dict[str, Any]]]:
    """Download inbound files (Telegram ``file_id`` in ``url``) and append their
    extracted text to the message as framed ``ATTACHED FILE … (DATA)`` blocks.

    Before 1.5.0 a customer who sent a PDF or a photo got an answer that
    ignored the file — attachments were archived but never read. The admin
    simulator uses the same framing (:func:`app.core.simulator.frame_file_text`),
    so what a manager sees in the console is what the bot does in production.
    Never raises; returns the original text when nothing could be read.
    """
    if not attachments:
        return text, []
    from app.core.ocr import extract_text
    from app.core.simulator import frame_file_text

    registry = services.get("registry") if services else None
    adapter = registry.get(channel) if registry is not None else None
    download = getattr(adapter, "download_attachment", None)
    blocks: list[str] = []
    info: list[dict[str, Any]] = []
    total = 0
    for att in attachments:
        name = str(getattr(att, "filename", "") or "file")
        mime = str(getattr(att, "content_type", "") or "").lower()
        if not mime.startswith(_TEXT_MIME_PREFIXES):
            info.append({"name": name, "content_type": mime, "chars": 0, "skipped": "type"})
            continue
        data = getattr(att, "data", b"") or b""
        if not data and download is not None and str(getattr(att, "url", "") or ""):
            try:
                data = await download(str(att.url)) or b""
            except Exception:
                data = b""
        if not data:
            info.append({"name": name, "content_type": mime, "chars": 0, "skipped": "no_data"})
            continue
        try:
            extracted = extract_text(data, filename=name) or ""
        except Exception:
            extracted = ""
        extracted = extracted[:MAX_FILE_TEXT_CHARS]
        info.append({"name": name, "content_type": mime, "chars": len(extracted)})
        framed = frame_file_text(name, extracted)
        if total + len(framed) > MAX_FILES_TEXT_TOTAL:
            # 1.6.0: budget exhausted — shrink this file to whatever is left
            # instead of silently dropping it *and every file after it*.
            room = MAX_FILES_TEXT_TOTAL - total - len(frame_file_text(name, ""))
            if room < 200:
                info[-1]["skipped"] = "budget"
                continue
            extracted = extracted[:room]
            info[-1]["chars"] = len(extracted)
            info[-1]["truncated"] = True
            framed = frame_file_text(name, extracted)
        blocks.append(framed)
        total += len(framed)
    if not blocks:
        return text, info
    joined = "\n\n".join(blocks)
    return (f"{text}\n\n{joined}" if text.strip() else joined), info


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
    from app.core.message_contract import (
        MessageContractError,
        MessageEnvelope,
        attachment_refs,
        normalize_envelope,
        sanitize_metadata,
    )

    try:
        env = normalize_envelope(
            MessageEnvelope(
                channel=channel,
                sender_id=sender_id,
                sender_name=sender_name,
                text=text,
                external_ref=external_ref,
                conversation_id=conversation_id,
                metadata=metadata,
            )
        )
    except MessageContractError as exc:
        return {
            "accepted": False,
            "conversation_id": conversation_id,
            "channel": channel,
            "reason": "contract",
            "error": str(exc),
        }

    channel = env.channel
    sender_id = env.sender_id
    sender_name = env.sender_name
    text = env.text
    external_ref = env.external_ref
    conversation_id = env.conversation_id
    meta = sanitize_metadata(env.metadata)
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

    from app.core.security_stack import audit_verdict, inspect_inbound

    security = inspect_inbound(
        text,
        attachments=attachments or (),
        rate_limited=False,
        webhook_ok=True,
    )
    audit_verdict(security, channel=channel, sender_id=sender_id)
    if not security.allowed:
        result["reason"] = f"security:{security.name}"
        result["security"] = {
            "layer": security.layer,
            "name": security.name,
            "reason": security.reason,
        }
        return result
    text = security.text or text

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

    # ── Attachment text (1.5.0) ───────────────────────────────────────
    # Read PDFs / documents / images now, while the adapter can still fetch
    # the bytes; the consumer only receives references (never bytes).
    if attachments:
        try:
            text, file_info = await attach_file_text(channel, text, attachments, services)
            meta["files"] = [f.get("name") for f in file_info][:10]
        except Exception:
            log.debug("attach_file_text_failed", exc_info=True)

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
