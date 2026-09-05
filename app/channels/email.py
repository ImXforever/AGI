"""Email channel adapter — Resend (outbound), SendGrid / IMAP (inbound)."""

from __future__ import annotations

import base64
import contextlib
import email
import email.message
import email.utils
import imaplib
import re
import ssl
from email.header import decode_header
from typing import Any

import httpx

from app.channels.base import (
    Attachment,
    IncomingMessage,
    OutboundResult,
    normalize_text,
)
from app.config import Config
from app.constants import CHANNEL_EMAIL
from app.logging_setup import get_logger

log = get_logger("app.channels.email")

__all__ = ["EmailAdapter"]

_IMAP_IDLE_TIMEOUT = 300


class EmailAdapter:
    """Manages inbound parsing and outbound delivery for email.

    Outbound uses the Resend API. Inbound is handled via either:
    - SendGrid Inbound Parse webhook (preferred)
    - IMAP polling (fallback)
    """

    channel_name = CHANNEL_EMAIL

    def __init__(self, cfg: Config, redis: Any) -> None:
        self._cfg = cfg
        self._redis = redis
        self._resend_url = cfg.channels.resend_base_url.rstrip("/")
        self._resend_key = cfg.channels.resend_api_key
        self._http = httpx.AsyncClient(timeout=30.0)
        self._imap_state: dict[str, Any] = {
            "uidvalidity": None,
            "last_uid": 0,
        }

    # ── inbound ─────────────────────────────────────────────────────

    async def parse_incoming(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse inbound email payload.

        When the inbound provider is SendGrid, ``payload`` is the JSON body
        of the Inbound Parse webhook. For Resend, it is the event payload.
        """
        if self._cfg.channels.email_inbound_provider == "sendgrid":
            return await self._parse_sendgrid(payload)
        return await self._parse_resend_event(payload)

    async def _parse_sendgrid(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse SendGrid Inbound Parse webhook body."""
        from_text = payload.get("from", "")
        subject = payload.get("subject", "")
        text_body = payload.get("text", "") or payload.get("html", "")
        message_id = payload.get("message_id", "") or payload.get("Message-ID", "")
        reply_to_id = payload.get("in_reply_to", "") or payload.get("In-Reply-To", "")

        if not message_id:
            return None

        dedup_key = f"{CHANNEL_EMAIL}:{message_id}"
        if await self._is_duplicate(dedup_key):
            log.info("duplicate email skipped", extra={"action": "dedup", "channel": CHANNEL_EMAIL})
            return None

        sender_email, sender_name = self._parse_email_address(from_text)
        attachments = self._extract_sendgrid_attachments(payload)

        # Strip quoted reply text
        clean_body = self._strip_quoted_text(text_body)

        metadata: dict[str, Any] = {
            "provider": "sendgrid",
            "subject": subject,
            "envelope": payload.get("envelope", ""),
            "charsets": payload.get("charsets", ""),
            "SPF": payload.get("SPF", ""),
        }
        if reply_to_id:
            metadata["in_reply_to"] = reply_to_id

        return IncomingMessage(
            channel=CHANNEL_EMAIL,
            sender_id=sender_email,
            sender_name=sender_name or sender_email,
            text=normalize_text(f"[Subject: {subject}]\n\n{clean_body}"),
            conversation_id=sender_email,
            external_ref=message_id,
            attachments=tuple(attachments),
            reply_to_ref=reply_to_id or None,
            metadata=metadata,
        )

    async def _parse_resend_event(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Parse a Resend email event (for forwarded inbound emails)."""
        event_type = payload.get("type", "")
        email_data = payload.get("data", {})

        if event_type != "email.received":
            return None

        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        text_body = email_data.get("text", "") or email_data.get("html", "")
        message_id = email_data.get("message_id", "")

        if not message_id:
            return None

        dedup_key = f"{CHANNEL_EMAIL}:{message_id}"
        if await self._is_duplicate(dedup_key):
            return None

        sender_email, sender_name = self._parse_email_address(from_addr)

        return IncomingMessage(
            channel=CHANNEL_EMAIL,
            sender_id=sender_email,
            sender_name=sender_name or sender_email,
            text=normalize_text(f"[Subject: {subject}]\n\n{text_body}"),
            conversation_id=sender_email,
            external_ref=message_id,
            metadata={
                "provider": "resend",
                "subject": subject,
            },
        )

    def _extract_sendgrid_attachments(self, payload: dict[str, Any]) -> list[Attachment]:
        """Extract file attachments from SendGrid inbound payload."""
        attachments: list[Attachment] = []
        files = payload.get("attachments", [])

        if isinstance(files, list):
            for att_data in files:
                if isinstance(att_data, dict):
                    content_b64 = att_data.get("content", "")
                    filename = att_data.get("filename", "attachment")
                    content_type = att_data.get("type", "application/octet-stream")
                    try:
                        content_bytes = base64.b64decode(content_b64)
                    except Exception:
                        content_bytes = b""
                    attachments.append(
                        Attachment(
                            filename=filename,
                            content_type=content_type,
                            data=content_bytes,
                        )
                    )

        return attachments

    def _strip_quoted_text(self, body: str) -> str:
        """Remove quoted reply text (lines starting with >) from email body."""
        lines = body.split("\n")
        cleaned: list[str] = []
        for line in lines:
            if line.startswith(">"):
                continue
            if re.match(r"^_{3,}$", line.strip()):
                break
            if re.match(r"^On .+ wrote:", line.strip()):
                break
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    @staticmethod
    def _parse_email_address(raw: str) -> tuple[str, str]:
        """Parse 'Name <email@example.com>' into (email, name)."""
        if "<" in raw and ">" in raw:
            match = re.match(r"^(.*?)\s*<(.+?)>", raw)
            if match:
                name = match.group(1).strip().strip('"')
                addr = match.group(2).strip()
                return addr, name
        cleaned = raw.strip().strip("<>")
        return cleaned, ""

    # ── parse RFC 822 (for IMAP raw messages) ───────────────────────

    def parse_rfc822(self, raw_bytes: bytes) -> IncomingMessage | None:
        """Parse a raw RFC 822 message (from IMAP) into IncomingMessage."""
        try:
            msg = email.message_from_bytes(raw_bytes)
        except Exception as exc:
            log.warning("rfc822 parse failed", extra={"action": "parse_rfc822", "error": str(exc)})
            return None

        from_header = msg.get("From", "")
        subject = self._decode_header_value(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")
        date_str = msg.get("Date", "")

        if not message_id:
            return None

        sender_email, sender_name = self._parse_email_address(from_header)
        body = self._extract_body_from_rfc822(msg)
        attachments = self._extract_rfc822_attachments(msg)

        # Strip quoted reply text, exactly as the SendGrid path does. Without
        # this, IMAP-ingested replies carried the entire quoted thread into the
        # prompt on every message in a conversation.
        body = self._strip_quoted_text(body)

        return IncomingMessage(
            channel=CHANNEL_EMAIL,
            sender_id=sender_email,
            sender_name=sender_name or sender_email,
            text=normalize_text(f"[Subject: {subject}]\n\n{body}"),
            conversation_id=sender_email,
            external_ref=message_id,
            attachments=tuple(attachments),
            reply_to_ref=in_reply_to or None,
            metadata={
                "provider": "imap",
                "subject": subject,
                "date": date_str,
                "message_id": message_id,
            },
        )

    @staticmethod
    def _payload_to_bytes(payload: Any) -> bytes:
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, str):
            return payload.encode("utf-8", errors="replace")
        return b""

    def _extract_body_from_rfc822(self, msg: email.message.Message) -> str:
        """Extract the plain-text body from a parsed email.Message."""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if ctype == "text/plain" and "attachment" not in disposition:
                    payload = self._payload_to_bytes(part.get_payload(decode=True))
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            return payload.decode(charset, errors="replace")
                        except (LookupError, UnicodeDecodeError):
                            return payload.decode("utf-8", errors="replace")
            # Fall back to HTML if no plain text
            for part in msg.walk():
                ctype = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if ctype == "text/html" and "attachment" not in disposition:
                    payload = self._payload_to_bytes(part.get_payload(decode=True))
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            return payload.decode(charset, errors="replace")
                        except (LookupError, UnicodeDecodeError):
                            return payload.decode("utf-8", errors="replace")
        else:
            payload = self._payload_to_bytes(msg.get_payload(decode=True))
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                try:
                    return payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    return payload.decode("utf-8", errors="replace")
        return ""

    def _extract_rfc822_attachments(self, msg: email.message.Message) -> list[Attachment]:
        """Extract attachments from a parsed RFC 822 message."""
        attachments: list[Attachment] = []
        if not msg.is_multipart():
            return attachments

        for part in msg.walk():
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition or (
                part.get_filename() and part.get_content_type() not in ("text/plain", "text/html")
            ):
                filename = self._decode_header_value(part.get_filename() or "attachment")
                content_type = part.get_content_type() or "application/octet-stream"
                payload = self._payload_to_bytes(part.get_payload(decode=True))
                if payload:
                    attachments.append(
                        Attachment(
                            filename=filename,
                            content_type=content_type,
                            data=payload,
                        )
                    )
        return attachments

    @staticmethod
    def _decode_header_value(raw: str | None) -> str:
        """Decode a MIME-encoded header value."""
        if not raw:
            return ""
        decoded_parts = decode_header(raw)
        result: list[str] = []
        for data, charset in decoded_parts:
            if isinstance(data, bytes):
                try:
                    result.append(data.decode(charset or "utf-8", errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    result.append(data.decode("utf-8", errors="replace"))
            else:
                result.append(data)
        return "".join(result)

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
        """Send an email via Resend API.

        ``recipient_id`` is the destination email address.
        ``reply_to_ref`` is the Message-ID to set in In-Reply-To / References headers.
        """
        from_addr = self._cfg.channels.email_from
        reply_to = self._cfg.channels.email_reply_to
        subject = kwargs.get("subject", "")

        payload: dict[str, Any] = {
            "from": from_addr,
            "to": [recipient_id],
            "subject": subject,
            "text": text,
        }

        if reply_to:
            payload["reply_to"] = [reply_to]

        if reply_to_ref:
            payload["headers"] = {
                "In-Reply-To": reply_to_ref,
                "References": reply_to_ref,
            }

        if attachments:
            resend_attachments: list[dict[str, Any]] = []
            for att in attachments:
                att_data: dict[str, Any] = {
                    "filename": att.filename,
                    "content": base64.b64encode(att.data).decode("ascii") if att.data else "",
                }
                if att.content_type:
                    att_data["content_type"] = att.content_type
                resend_attachments.append(att_data)
            if resend_attachments:
                payload["attachments"] = resend_attachments

        headers = {
            "Authorization": f"Bearer {self._resend_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = await self._http.post(
                f"{self._resend_url}/emails",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            email_id = data.get("id", "")
            log.info(
                "email sent", extra={"action": "send.email", "to": recipient_id, "id": email_id}
            )
            return OutboundResult(
                success=True,
                external_ref=email_id,
                metadata={"to": recipient_id, "subject": subject},
            )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text
            log.error(
                "email send failed",
                extra={
                    "action": "send.email",
                    "status": exc.response.status_code,
                    "error": error_body[:500],
                },
            )
            return OutboundResult(
                success=False,
                error=f"HTTP {exc.response.status_code}: {error_body[:200]}",
            )
        except Exception as exc:
            return OutboundResult(success=False, error=str(exc))

    # ── IMAP polling ────────────────────────────────────────────────

    async def poll_imap_once(self) -> list[IncomingMessage]:
        """Poll the IMAP inbox once and return any new messages.

        Uses ``_poll_imap_sync`` in a thread executor to avoid blocking.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._poll_imap_sync)

    def _poll_imap_sync(self) -> list[IncomingMessage]:
        """Synchronous IMAP poll — runs in a thread."""
        cfg = self._cfg.channels
        messages: list[IncomingMessage] = []

        ctx = ssl.create_default_context()
        try:
            conn = imaplib.IMAP4_SSL(
                host=cfg.imap_host,
                port=cfg.imap_port,
                ssl_context=ctx,
            )
        except Exception as exc:
            log.error("imap connect failed", extra={"action": "imap.connect", "error": str(exc)})
            return messages

        try:
            conn.login(cfg.imap_user, cfg.imap_password)
            conn.select("INBOX", readonly=True)

            status, data = conn.uid("search", "UTF-8", "UNSEEN")
            if status != "OK":
                return messages

            uid_list = data[0].split() if data[0] else []
            for uid_bytes in uid_list[-50:]:  # limit batch
                uid = uid_bytes.decode()
                uid_int = int(uid)

                if uid_int <= self._imap_state.get("last_uid", 0):
                    continue

                status, msg_data = conn.uid("fetch", uid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_bytes = msg_data[0][1]  # type: ignore[index]
                incoming = self.parse_rfc822(raw_bytes)
                if incoming:
                    messages.append(incoming)

                self._imap_state["last_uid"] = uid_int

            # Update UIDVALIDITY
            status, uid_val_data = conn.uid("search", "UTF-8", "ALL")
            if status == "OK":
                uid_validity_resp = conn.response("UIDVALIDITY")
                if uid_validity_resp:
                    self._imap_state["uidvalidity"] = uid_validity_resp[1]

        except Exception as exc:
            log.error("imap poll failed", extra={"action": "imap.poll", "error": str(exc)})
        finally:
            with contextlib.suppress(Exception):
                conn.logout()

        return messages

    # ── admin broadcast ─────────────────────────────────────────────

    async def notify_admins(self, text: str) -> None:
        """Forward an email system notification to admins via Redis pub/sub."""
        log.info(
            "admin notification (email)",
            extra={"action": "notify_admins", "channel": CHANNEL_EMAIL},
        )
        if self._redis is not None:
            try:
                await self._redis.publish(
                    "notify:admins",
                    f"[email] {text}",
                )
            except Exception:
                log.debug("email_admin_notify_failed", exc_info=True)

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
