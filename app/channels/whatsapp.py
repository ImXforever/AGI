"""WhatsApp channel adapter — Meta Cloud API + Twilio fallback."""

from __future__ import annotations

import contextlib
from typing import Any

import httpx

from app.channels.base import (
    Attachment,
    IncomingMessage,
    OutboundResult,
    normalize_text,
)
from app.config import Config
from app.constants import CHANNEL_WHATSAPP, KEY_WA_SESSION
from app.logging_setup import get_logger

log = get_logger("app.channels.whatsapp")

__all__ = ["WhatsAppAdapter"]

# Meta Cloud API 24-hour session window (seconds)
SESSION_WINDOW_TTL = 86400


class WhatsAppAdapter:
    """Manages inbound parsing and outbound delivery for WhatsApp.

    Supports two providers:
    - ``meta``: WhatsApp Cloud API (graph.facebook.com)
    - ``twilio``: Twilio Programmable Messaging
    """

    channel_name = CHANNEL_WHATSAPP

    def __init__(self, cfg: Config, redis: Any) -> None:
        self._cfg = cfg
        self._redis = redis
        self._provider = cfg.channels.whatsapp_provider
        self._http = httpx.AsyncClient(timeout=30.0)
        self._rate_semaphore = None  # lazily bound to rate_limit_per_minute

    # ── inbound ─────────────────────────────────────────────────────

    async def parse_incoming(self, payload: dict[str, Any]) -> IncomingMessage | None:
        if self._provider == "meta":
            return await self._parse_meta(payload)
        return await self._parse_twilio(payload)

    async def _parse_meta(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse Meta Cloud API webhook payload."""
        entry = payload.get("entry", [])
        if not entry:
            return None

        for entry_item in entry:
            for change in entry_item.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if not messages:
                    continue

                msg = messages[0]
                msg_id = msg.get("id", "")
                sender_id = msg.get("from", "")
                msg_type = msg.get("type", "")

                text = ""
                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    text = msg.get("image", {}).get("caption", "")
                elif msg_type == "document":
                    text = msg.get("document", {}).get("caption", "")
                elif msg_type == "audio":
                    text = "[audio message]"
                elif msg_type == "video":
                    text = msg.get("video", {}).get("caption", "[video message]")
                elif msg_type == "sticker":
                    text = "[sticker]"
                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    if interactive.get("type") == "button_reply":
                        text = interactive.get("button_reply", {}).get("title", "")
                    elif interactive.get("type") == "list_reply":
                        text = interactive.get("list_reply", {}).get("title", "")
                elif msg_type == "location":
                    loc = msg.get("location", {})
                    text = f"Location: {loc.get('latitude', '')}, {loc.get('longitude', '')}"
                else:
                    text = f"[{msg_type}]"

                dedup_key = f"{CHANNEL_WHATSAPP}:{msg_id}"
                if await self._is_duplicate(dedup_key):
                    log.info(
                        "duplicate wa message skipped",
                        extra={"action": "dedup", "channel": CHANNEL_WHATSAPP},
                    )
                    return None

                attachments = self._extract_meta_attachments(msg, msg_type)
                conversation_id = sender_id

                contact = value.get("contacts", [{}])[0] if value.get("contacts") else {}
                sender_name = contact.get("profile", {}).get("name", sender_id)
                wa_id = contact.get("wa_id", sender_id)

                reply_to_ref = None
                context_info = msg.get("context", {})
                if context_info.get("id"):
                    reply_to_ref = context_info["id"]

                return IncomingMessage(
                    channel=CHANNEL_WHATSAPP,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    text=normalize_text(text),
                    conversation_id=conversation_id,
                    external_ref=msg_id,
                    attachments=tuple(attachments),
                    reply_to_ref=reply_to_ref,
                    metadata={
                        "provider": "meta",
                        "wa_id": wa_id,
                        "display_phone_number": value.get("metadata", {}).get(
                            "display_phone_number", ""
                        ),
                        "phone_number_id": value.get("metadata", {}).get("phone_number_id", ""),
                        "message_type": msg_type,
                        "message_timestamp": msg.get("timestamp", ""),
                    },
                )
        return None

    async def _parse_twilio(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse Twilio webhook payload."""
        sender_id = payload.get("From", "")
        text = payload.get("Body", "")
        msg_id = payload.get("MessageSid", "")
        profile_name = payload.get("ProfileName", sender_id)
        num_media = int(payload.get("NumMedia", "0"))

        if not msg_id:
            return None

        dedup_key = f"{CHANNEL_WHATSAPP}:{msg_id}"
        if await self._is_duplicate(dedup_key):
            log.info(
                "duplicate wa message skipped",
                extra={"action": "dedup", "channel": CHANNEL_WHATSAPP},
            )
            return None

        attachments: list[Attachment] = []
        for i in range(num_media):
            media_url = payload.get(f"MediaUrl{i}", "")
            media_type = payload.get(f"MediaContentType{i}", "application/octet-stream")
            if media_url:
                attachments.append(
                    Attachment(
                        filename=f"media_{i}",
                        content_type=media_type,
                        data=b"",
                        url=media_url,
                    )
                )

        # Twilio WhatsApp numbers have the "whatsapp:" prefix
        if sender_id.startswith("whatsapp:"):
            sender_id = sender_id[len("whatsapp:") :]

        conversation_id = sender_id
        # message_id for reply context
        reply_to_ref = None
        if payload.get("OriginalRepliedMessageSid"):
            reply_to_ref = payload["OriginalRepliedMessageSid"]

        return IncomingMessage(
            channel=CHANNEL_WHATSAPP,
            sender_id=sender_id,
            sender_name=profile_name,
            text=normalize_text(text),
            conversation_id=conversation_id,
            external_ref=msg_id,
            attachments=tuple(attachments),
            reply_to_ref=reply_to_ref,
            metadata={
                "provider": "twilio",
                "account_sid": payload.get("AccountSid", ""),
                "num_media": num_media,
                "message_status": payload.get("SmsStatus", ""),
            },
        )

    def _extract_meta_attachments(self, msg: dict[str, Any], msg_type: str) -> list[Attachment]:
        attachments: list[Attachment] = []
        if msg_type == "image":
            img = msg.get("image", {})
            attachments.append(
                Attachment(
                    filename=img.get("id", "image") + ".jpg",
                    content_type=img.get("mime_type", "image/jpeg"),
                    data=b"",
                    url=img.get("id", ""),
                )
            )
        elif msg_type == "document":
            doc = msg.get("document", {})
            attachments.append(
                Attachment(
                    filename=doc.get("filename", "document"),
                    content_type=doc.get("mime_type", "application/octet-stream"),
                    data=b"",
                    url=doc.get("id", ""),
                )
            )
        elif msg_type == "audio":
            aud = msg.get("audio", {})
            attachments.append(
                Attachment(
                    filename=aud.get("id", "audio") + ".ogg",
                    content_type=aud.get("mime_type", "audio/ogg"),
                    data=b"",
                    url=aud.get("id", ""),
                )
            )
        elif msg_type == "video":
            vid = msg.get("video", {})
            attachments.append(
                Attachment(
                    filename=vid.get("id", "video") + ".mp4",
                    content_type=vid.get("mime_type", "video/mp4"),
                    data=b"",
                    url=vid.get("id", ""),
                )
            )
        return attachments

    # ── outbound ────────────────────────────────────────────────────

    async def send(
        self,
        recipient_id: str,
        text: str,
        *,
        reply_to_ref: str | None = None,
        parse_mode: str | None = None,
        attachments: list[Attachment] | None = None,
        **kwargs: Any,
    ) -> OutboundResult:
        clean = normalize_text(text)
        if not clean and not attachments:
            return OutboundResult(success=False, error="empty message")

        template_name = kwargs.get("template_name")
        template_params = kwargs.get("template_params")

        if self._provider == "meta":
            return await self._send_meta(
                recipient_id,
                clean,
                reply_to_ref=reply_to_ref,
                attachments=attachments,
                template_name=template_name,
                template_params=template_params,
            )
        return await self._send_twilio(
            recipient_id,
            clean,
            reply_to_ref=reply_to_ref,
            attachments=attachments,
        )

    async def _send_meta(
        self,
        recipient_id: str,
        text: str,
        *,
        reply_to_ref: str | None = None,
        attachments: list[Attachment] | None = None,
        template_name: str | None = None,
        template_params: list[str] | None = None,
    ) -> OutboundResult:
        phone_id = self._cfg.channels.whatsapp_phone_number_id
        token = self._cfg.channels.whatsapp_api_token
        url = f"{self._cfg.channels.whatsapp_base_url}/{phone_id}/messages"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if template_name:
            body: dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "ar"},
                },
            }
            if template_params:
                body["template"]["components"] = [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "param": p} for p in template_params],
                    }
                ]
        elif (
            attachments and attachments[0].url and attachments[0].content_type.startswith("image/")
        ):
            body = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "image",
                "image": {"link": attachments[0].url},
            }
            if text:
                body["image"]["caption"] = text
        elif (
            attachments
            and attachments[0].url
            and attachments[0].content_type.startswith("document/")
        ):
            body = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "document",
                "document": {
                    "link": attachments[0].url,
                    "filename": attachments[0].filename,
                },
            }
            if text:
                body["document"]["caption"] = text
        else:
            body = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": text},
            }

        if reply_to_ref:
            body["context"] = {"message_id": reply_to_ref}

        try:
            resp = await self._http.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("messages", [])
            ext_ref = messages[0].get("id", "") if messages else ""
            return OutboundResult(
                success=True,
                external_ref=ext_ref,
                metadata={"provider": "meta"},
            )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            log.error(
                "meta send failed",
                extra={
                    "action": "send.meta",
                    "status": exc.response.status_code,
                    "error": error_body[:500],
                },
            )
            return OutboundResult(
                success=False, error=f"HTTP {exc.response.status_code}: {error_body[:200]}"
            )
        except Exception as exc:
            return OutboundResult(success=False, error=str(exc))

    async def _send_twilio(
        self,
        recipient_id: str,
        text: str,
        *,
        reply_to_ref: str | None = None,
        attachments: list[Attachment] | None = None,
    ) -> OutboundResult:
        account_sid = self._cfg.channels.twilio_account_sid
        auth_token = self._cfg.channels.twilio_auth_token
        from_number = self._cfg.channels.twilio_whatsapp_from
        url = f"{self._cfg.channels.twilio_base_url}/Accounts/{account_sid}/Messages.json"

        to_number = (
            recipient_id if recipient_id.startswith("whatsapp:") else f"whatsapp:{recipient_id}"
        )
        from_formatted = (
            from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        )

        data: dict[str, str] = {
            "To": to_number,
            "From": from_formatted,
            "Body": text,
        }

        if reply_to_ref:
            data["OriginalRepliedMessageSid"] = reply_to_ref

        if attachments:
            media_urls = [att.url for att in attachments if att.url]
            if media_urls:
                data["MediaUrl"] = ",".join(media_urls)

        try:
            resp = await self._http.post(
                url,
                data=data,
                auth=(account_sid, auth_token),
            )
            resp.raise_for_status()
            result = resp.json()
            return OutboundResult(
                success=True,
                external_ref=result.get("sid", ""),
                metadata={"provider": "twilio"},
            )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            log.error(
                "twilio send failed",
                extra={
                    "action": "send.twilio",
                    "status": exc.response.status_code,
                    "error": error_body[:500],
                },
            )
            return OutboundResult(
                success=False, error=f"HTTP {exc.response.status_code}: {error_body[:200]}"
            )
        except Exception as exc:
            return OutboundResult(success=False, error=str(exc))

    # ── session window management ───────────────────────────────────

    async def session_window_ok(self, phone: str) -> bool:
        """Check whether the 24-hour customer-initiated session window is open.

        Uses Redis key ``wa:sess:{phone}`` with TTL set by Meta/Twilio callbacks.
        """
        if self._redis is None:
            return False
        try:
            ttl = await self._redis.ttl(f"{KEY_WA_SESSION.format(phone=phone)}")
            return ttl > 0
        except Exception:
            return False

    async def mark_session_open(self, phone: str) -> None:
        """Set or refresh the session window TTL for a phone number."""
        if self._redis is None:
            return
        try:
            await self._redis.set(
                f"{KEY_WA_SESSION.format(phone=phone)}",
                "1",
                ex=SESSION_WINDOW_TTL,
            )
        except Exception as exc:
            log.warning("session mark failed", extra={"action": "session.open", "error": str(exc)})

    # ── admin broadcast ─────────────────────────────────────────────

    async def notify_admins(self, text: str) -> None:
        """Forward a WhatsApp system notification to configured Telegram admins."""

        # Import here to avoid circular dependency; registry supplies the real instance
        # In production this goes through a thin notification bus; fallback: log only.
        log.info(
            "admin notification (whatsapp)",
            extra={"action": "notify_admins", "channel": CHANNEL_WHATSAPP},
        )
        # Best-effort push to admin via configured channel
        if self._redis is not None:
            try:
                await self._redis.publish(
                    "notify:admins",
                    f"[whatsapp] {text}",
                )
            except Exception:
                log.debug("whatsapp_admin_notify_failed", exc_info=True)

    # ── internal helpers ────────────────────────────────────────────

    async def _is_duplicate(self, key: str) -> bool:
        if self._redis is None:
            return False
        try:
            was_set = await self._redis.set(key, "1", nx=True, ex=3600)
            return was_set is None
        except Exception:
            return False

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self._http.aclose()
