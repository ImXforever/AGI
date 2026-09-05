"""FastAPI router — inbound webhook endpoints for all channels."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_config
from app.constants import (
    CHANNEL_EMAIL,
    CHANNEL_TELEGRAM,
    CHANNEL_WHATSAPP,
)
from app.gateway.verify import (
    verify_meta_handshake,
    verify_meta_signature,
    verify_sendgrid_signature,
    verify_telegram,
    verify_twilio_signature,
)
from app.logging_setup import get_logger

log = get_logger("app.gateway.webhooks")

router = APIRouter(tags=["gateway"])


async def _get_redis(request: Request):
    return request.app.state.services.get("redis")


async def _get_registry(request: Request):
    return request.app.state.services.get("registry")


async def _ingest(request: Request, channel: str, incoming_msg) -> Response:
    """Push a verified incoming message onto the event stream."""
    from app.channels.base import IncomingMessage

    if not isinstance(incoming_msg, IncomingMessage):
        raise HTTPException(status_code=422, detail="failed to parse incoming message")

    redis = await _get_redis(request)
    registry = await _get_registry(request)

    if redis is None:
        log.error("redis unavailable", extra={"action": "ingest", "channel": channel})
        raise HTTPException(status_code=503, detail="service unavailable")

    # Delegate to the ingestion pipeline: dedup, rate limiting, customer /
    # conversation / message persistence, then publish onto the event stream.
    # (Previously this handler wrote straight to Redis, so nothing was ever
    # persisted and ingest_incoming() was dead code.)
    from app.core.pipeline import ingest_incoming

    try:
        result = await ingest_incoming(
            channel=channel,
            sender_id=incoming_msg.sender_id,
            sender_name=incoming_msg.sender_name,
            text=incoming_msg.text,
            external_ref=incoming_msg.external_ref,
            conversation_id=incoming_msg.conversation_id,
            attachments=incoming_msg.attachments,
            reply_to_ref=incoming_msg.reply_to_ref,
            metadata=dict(incoming_msg.metadata or {}),
            services=request.app.state.services,
        )
    except Exception as exc:
        log.error(
            "ingest failed", extra={"action": "ingest", "channel": channel, "error": str(exc)}
        )
        raise HTTPException(status_code=503, detail="ingestion unavailable") from exc

    if not result.get("accepted"):
        # Duplicates and rate-limited senders are acknowledged so the channel
        # provider does not retry.
        log.info(
            "message not accepted",
            extra={"action": "ingest", "channel": channel, "reason": result.get("reason", "")},
        )
        return Response(status_code=200)

    log.info(
        "message ingested",
        extra={
            "action": "ingest",
            "channel": channel,
            "conversation_id": result.get("conversation_id", ""),
            "external_ref": incoming_msg.external_ref,
        },
    )

    return Response(status_code=200)


# ── Telegram ───────────────────────────────────────────────────────


@router.post("/tg/webhook")
async def tg_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> Response:
    """Receive Telegram updates via webhook."""
    cfg = get_config()
    body = await request.body()

    if cfg.channels.telegram_webhook_secret:
        vr = verify_telegram(
            cfg.channels.telegram_webhook_secret,
            x_telegram_bot_api_secret_token,
        )
        if not vr.ok:
            log.warning(
                "telegram verify failed", extra={"action": "webhook.verify", "reason": vr.reason}
            )
            raise HTTPException(status_code=403, detail="forbidden")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    registry = await _get_registry(request)
    if registry is None:
        raise HTTPException(status_code=503, detail="service unavailable")

    adapter = registry.get(CHANNEL_TELEGRAM)
    if adapter is None:
        raise HTTPException(status_code=503, detail="telegram adapter not configured")

    incoming = await adapter.parse_incoming(payload)
    if incoming is None:
        # Non-message update (e.g. callback_query with no text) — acknowledge silently
        return Response(status_code=200)

    return await _ingest(request, CHANNEL_TELEGRAM, incoming)


# ── WhatsApp (Meta + Twilio) ──────────────────────────────────────


@router.get("/wa/webhook")
async def wa_webhook_verify(
    request: Request,
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
) -> Response:
    """Meta webhook verification GET endpoint."""
    cfg = get_config()
    vr = verify_meta_handshake(
        cfg.channels.whatsapp_verify_token,
        hub_mode,
        hub_challenge,
        hub_verify_token,
    )
    if not vr.ok:
        log.warning("wa handshake failed", extra={"action": "webhook.verify", "reason": vr.reason})
        raise HTTPException(status_code=403, detail="forbidden")

    challenge = vr.data.get("challenge", "") if vr.data else ""
    return PlainTextResponse(content=challenge)


@router.post("/wa/webhook")
async def wa_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_hub_signature: str | None = Header(None),
    x_twilio_signature: str | None = Header(None),
) -> Response:
    """Receive WhatsApp inbound messages (Meta or Twilio)."""
    cfg = get_config()
    body = await request.body()

    if cfg.channels.whatsapp_provider == "meta":
        vr = verify_meta_signature(
            cfg.channels.whatsapp_app_secret,
            body,
            x_hub_signature,
            x_hub_signature_256,
        )
        if not vr.ok:
            log.warning(
                "wa meta verify failed", extra={"action": "webhook.verify", "reason": vr.reason}
            )
            raise HTTPException(status_code=403, detail="forbidden")
    else:
        # Twilio verification
        form_data = await request.form()
        twilio_params = {k: v for k, v in form_data.items() if isinstance(v, str)}
        url_str = str(request.url)
        vr = verify_twilio_signature(
            cfg.channels.twilio_auth_token,
            url_str,
            twilio_params,
            x_twilio_signature,
        )
        if not vr.ok:
            log.warning(
                "wa twilio verify failed", extra={"action": "webhook.verify", "reason": vr.reason}
            )
            raise HTTPException(status_code=403, detail="forbidden")

    try:
        if cfg.channels.whatsapp_provider == "meta":
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid body")

    registry = await _get_registry(request)
    if registry is None:
        raise HTTPException(status_code=503, detail="service unavailable")

    adapter = registry.get(CHANNEL_WHATSAPP)
    if adapter is None:
        raise HTTPException(status_code=503, detail="whatsapp adapter not configured")

    incoming = await adapter.parse_incoming(payload)
    if incoming is None:
        return Response(status_code=200)

    # Mark session window open for this sender
    if hasattr(adapter, "mark_session_open"):
        await adapter.mark_session_open(incoming.sender_id)

    return await _ingest(request, CHANNEL_WHATSAPP, incoming)


# ── Email (SendGrid inbound parse) ─────────────────────────────────


@router.post("/email/inbound")
async def email_inbound(
    request: Request,
    x_twilio_email_event_webhook_signature: str | None = Header(None),
    x_twilio_email_event_webhook_timestamp: str | None = Header(None),
    x_twilio_email_event_webhook_nonce: str | None = Header(None),
    svix_id: str | None = Header(None),
    svix_timestamp: str | None = Header(None),
    svix_signature: str | None = Header(None),
) -> Response:
    """Receive inbound email via SendGrid Inbound Parse or Resend webhook."""
    cfg = get_config()
    body = await request.body()

    # Verify signature — try SendGrid first, then Svix
    verified = False

    if cfg.channels.sendgrid_webhook_public_key:
        vr = verify_sendgrid_signature(
            cfg.channels.sendgrid_webhook_public_key,
            body,
            x_twilio_email_event_webhook_timestamp,
            x_twilio_email_event_webhook_nonce,
            x_twilio_email_event_webhook_signature,
        )
        if vr.ok:
            verified = True

    if not verified and cfg.channels.resend_webhook_secret:
        from app.gateway.verify import verify_svix_signature

        vr = verify_svix_signature(
            cfg.channels.resend_webhook_secret,
            body,
            svix_id,
            svix_timestamp,
            svix_signature,
        )
        if vr.ok:
            verified = True

    if not verified:
        log.warning(
            "email verify failed", extra={"action": "webhook.verify", "channel": CHANNEL_EMAIL}
        )
        raise HTTPException(status_code=403, detail="forbidden")

    # Parse the payload
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        # SendGrid Inbound Parse sends form-encoded data
        form_data = await request.form()
        payload = dict(form_data)

    registry = await _get_registry(request)
    if registry is None:
        raise HTTPException(status_code=503, detail="service unavailable")

    adapter = registry.get(CHANNEL_EMAIL)
    if adapter is None:
        raise HTTPException(status_code=503, detail="email adapter not configured")

    incoming = await adapter.parse_incoming(payload)
    if incoming is None:
        return Response(status_code=200)

    return await _ingest(request, CHANNEL_EMAIL, incoming)
