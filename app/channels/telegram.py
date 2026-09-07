"""Telegram channel adapter — aiogram 3 + raw httpx fallback."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import aiogram
import httpx

from app.channels.base import (
    Attachment,
    IncomingMessage,
    OutboundResult,
    escape_html,
    normalize_text,
    telegram_html_to_plain,
)
from app.config import Config
from app.constants import CHANNEL_TELEGRAM
from app.logging_setup import get_logger

log = get_logger("app.channels.telegram")

__all__ = ["TelegramAdapter"]


# Telegram hard-limits a single sendMessage to 4096 characters and rejects the
# whole call otherwise (HTTP 400 "message is too long"). We cut a little below
# the limit on paragraph / line / sentence / word boundaries.
TELEGRAM_MAX_CHARS = 4096
TELEGRAM_CHUNK_CHARS = 3900


def split_telegram_text(text: str, limit: int = TELEGRAM_CHUNK_CHARS) -> list[str]:
    """Split *text* into Telegram-sized chunks without cutting words.

    BUG #8 (1.3.1): 1.3.0 posted the full reply in one call; long answers
    (a product list, an MSDS excerpt, a multi-step guide) were rejected by
    Telegram and silently lost — the user saw the typing indicator stop and
    nothing arrive.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while len(text) > limit:
        cut = -1
        for sep in ("\n\n", "\n", ". ", "؟ ", "! ", " "):
            idx = text.rfind(sep, 0, limit)
            if idx > limit // 2:
                cut = idx + len(sep)
                break
        if cut <= 0:
            cut = limit
        chunk = text[:cut].rstrip()
        if chunk:
            chunks.append(chunk)
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def _web_app_command(raw: str) -> str:
    """``{"v":1,"action":"products","code":"203"}`` → ``/prod_203`` (or ``/shop``)."""
    import json as _json

    try:
        data = _json.loads(raw)
    except (ValueError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    action = str(data.get("action") or "").strip().lower()
    code = "".join(ch for ch in str(data.get("code") or "") if ch.isalnum() or ch in "-_")[:12]
    if action == "products":
        return f"/prod_{code}" if code else "/shop"
    if action == "support":
        return "/menu_support"
    if action == "quote":
        return "/menu_quote"
    return ""


def _telegram_error_description(exc: BaseException) -> str:
    """Best-effort extraction of Telegram's ``description`` from an HTTP error."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("description"):
                return str(body["description"])
        except Exception:  # noqa: BLE001 - non-JSON error body
            pass
        try:
            return str(response.text)
        except Exception:  # noqa: BLE001
            pass
    return str(exc)


def _is_parse_error(description: str) -> bool:
    lowered = description.lower()
    return (
        "can't parse" in lowered
        or "parse entities" in lowered
        or "unsupported start tag" in lowered
    )


@dataclass
class _ChunkResult:
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class TelegramAdapter:
    """Manages inbound parsing and outbound delivery for Telegram."""

    channel_name = CHANNEL_TELEGRAM

    def __init__(self, cfg: Config, redis: Any) -> None:
        self._cfg = cfg
        self._redis = redis
        self._token = cfg.channels.telegram_bot_token
        self._admin_ids = list(cfg.channels.telegram_admin_ids)
        self._secret = cfg.channels.telegram_webhook_secret.encode()
        api_base = (
            getattr(cfg.channels, "telegram_api_base", "") or "https://api.telegram.org"
        ).rstrip("/")
        if api_base != "https://api.telegram.org":
            from aiogram.client.session.aiohttp import AiohttpSession
            from aiogram.client.telegram import TelegramAPIServer

            session = AiohttpSession(api=TelegramAPIServer.from_base(api_base))
            self._bot = aiogram.Bot(token=self._token, session=session)
        else:
            self._bot = aiogram.Bot(token=self._token)
        self._api_base = api_base.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=f"{api_base}/bot{self._token}",
            timeout=30.0,
        )

    # ── inbound ─────────────────────────────────────────────────────

    async def parse_incoming(self, payload: dict[str, Any]) -> IncomingMessage | None:
        """Convert a Telegram update dict into a normalised IncomingMessage."""
        # Handle callback_query (inline keyboard button press)
        callback_query = payload.get("callback_query")
        if callback_query:
            return self._parse_callback_query(callback_query)

        message = payload.get("message") or payload.get("edited_message")
        if message is None:
            return None

        chat = message.get("chat", {})
        sender = message.get("from", {})
        chat_id = str(chat.get("id", ""))
        sender_id = str(sender.get("id", ""))
        text = message.get("text", "") or message.get("caption", "") or ""

        # 1.4.0: the customer mini-app (/app) sends {"v":1,"action":"products","code":"203"}
        # through Telegram.WebApp.sendData — it arrives as message.web_app_data and was
        # silently dropped before. Map it onto the same commands the inline buttons use.
        web_app = message.get("web_app_data")
        if not text and isinstance(web_app, dict) and web_app.get("data"):
            text = _web_app_command(str(web_app.get("data") or ""))

        if not text and not message.get("photo") and not message.get("document"):
            return None

        dedup_key = f"{CHANNEL_TELEGRAM}:{message.get('message_id', '')}"
        if await self._is_duplicate(dedup_key):
            log.info(
                "duplicate telegram message skipped",
                extra={"action": "dedup", "channel": CHANNEL_TELEGRAM},
            )
            return None

        attachments = tuple(self._extract_attachments(message))
        conversation_id = chat_id
        sender_name = " ".join(
            filter(None, [sender.get("first_name"), sender.get("last_name")])
        ) or sender.get("username", sender_id)

        reply_to_ref = None
        reply_to = message.get("reply_to_message")
        if reply_to:
            reply_to_ref = str(reply_to.get("message_id", ""))

        return IncomingMessage(
            channel=CHANNEL_TELEGRAM,
            sender_id=sender_id,
            sender_name=sender_name,
            text=normalize_text(text),
            conversation_id=conversation_id,
            external_ref=str(message.get("message_id", "")),
            attachments=attachments,
            reply_to_ref=reply_to_ref,
            metadata={
                "chat_id": chat_id,
                "chat_type": chat.get("type", ""),
                "is_group": chat.get("type", "") in ("group", "supergroup"),
                "language_code": sender.get("language_code", ""),
            },
        )

    def _parse_callback_query(self, cq: dict[str, Any]) -> IncomingMessage | None:
        """Convert a callback_query into an IncomingMessage."""
        from_app = cq.get("from", {})
        chat = cq.get("message", {}).get("chat", {})
        data = cq.get("data", "")
        if not data:
            return None

        sender_id = str(from_app.get("id", ""))
        chat_id = str(chat.get("id", "")) or sender_id
        sender_name = " ".join(
            filter(None, [from_app.get("first_name"), from_app.get("last_name")])
        ) or from_app.get("username", sender_id)

        log.info(
            "callback_query_received",
            extra={"action": "parse_callback", "data": data, "sender_id": sender_id},
        )

        return IncomingMessage(
            channel=CHANNEL_TELEGRAM,
            sender_id=sender_id,
            sender_name=sender_name,
            text=f"/{data}",
            conversation_id=chat_id,
            external_ref=str(cq.get("id", "")),
            attachments=(),
            reply_to_ref=None,
            metadata={
                "chat_id": chat_id,
                "callback_data": data,
                "callback_query_id": str(cq.get("id", "")),
                # 1.4.0: id of the message that carried the pressed button, so
                # the bot can edit it (Approve/Reject → receipt, menus → next step).
                "callback_message_id": str(cq.get("message", {}).get("message_id", "")),
                "is_callback": True,
                "language_code": from_app.get("language_code", ""),
            },
        )

    def _extract_attachments(self, message: dict[str, Any]) -> list[Attachment]:
        attachments: list[Attachment] = []

        photo = message.get("photo")
        if photo and isinstance(photo, list) and photo:
            best = max(photo, key=lambda p: p.get("file_size", 0))
            attachments.append(
                Attachment(
                    filename=best.get("file_id", "photo") + ".jpg",
                    content_type="image/jpeg",
                    data=b"",
                    url=best.get("file_id", ""),
                )
            )

        document = message.get("document")
        if document:
            file_name = document.get("file_name", "document")
            mime = document.get("mime_type", "application/octet-stream")
            attachments.append(
                Attachment(
                    filename=file_name,
                    content_type=mime,
                    data=b"",
                    url=document.get("file_id", ""),
                )
            )

        voice = message.get("voice")
        if voice:
            attachments.append(
                Attachment(
                    filename="voice.ogg",
                    content_type=voice.get("mime_type", "audio/ogg"),
                    data=b"",
                    url=voice.get("file_id", ""),
                )
            )

        video = message.get("video")
        if video:
            attachments.append(
                Attachment(
                    filename=video.get("file_name", "video.mp4"),
                    content_type=video.get("mime_type", "video/mp4"),
                    data=b"",
                    url=video.get("file_id", ""),
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
        if not clean:
            return OutboundResult(success=False, error="empty message")

        parsed_mode = parse_mode or "HTML"
        kwargs_tg: dict[str, Any] = {
            "chat_id": recipient_id,
            "parse_mode": parsed_mode,
        }
        if reply_to_ref:
            try:
                kwargs_tg["reply_to_message_id"] = int(reply_to_ref)
            except (ValueError, TypeError):
                pass

        # BUG #8 (1.3.1): chunk long replies; only the first chunk quotes the
        # original message so the thread stays readable.
        chunks = split_telegram_text(clean)
        sent: dict[str, Any] = {}
        for index, chunk in enumerate(chunks):
            chunk_kwargs = dict(kwargs_tg)
            if index > 0:
                chunk_kwargs.pop("reply_to_message_id", None)
            result = await self._send_chunk(chunk, parsed_mode, chunk_kwargs)
            if result.error is not None:
                return OutboundResult(
                    success=False,
                    error=result.error,
                    metadata={"chat_id": recipient_id, "chunks_sent": index, "chunks": len(chunks)},
                )
            sent = result.payload

        if attachments:
            for att in attachments:
                await self._send_attachment(recipient_id, att, reply_to_ref)

        msg_id = str(sent.get("message_id", "")) if isinstance(sent, dict) else ""
        return OutboundResult(
            success=True,
            external_ref=msg_id,
            metadata={"chat_id": recipient_id, "chunks": len(chunks)},
        )

    async def _send_chunk(
        self, chunk: str, parse_mode: str, kwargs_tg: dict[str, Any]
    ) -> _ChunkResult:
        """Send one chunk; on an HTML parse error resend it as *plain text*.

        1.3.0 caught ``aiogram.exceptions.TelegramBadRequest`` here, but the
        adapter talks to Telegram through ``httpx`` which raises
        ``httpx.HTTPStatusError`` — so the plain-text fallback was dead code
        and any reply with an unbalanced tag failed outright. The fallback
        also re-sent the *HTML string* (tags visible to the customer); we now
        strip it with ``telegram_html_to_plain``.
        """
        try:
            payload = await self._send_text(chunk, parse_mode, kwargs_tg)
            return _ChunkResult(payload=payload)
        except (httpx.HTTPStatusError, aiogram.exceptions.TelegramBadRequest) as exc:
            description = _telegram_error_description(exc)
            if not _is_parse_error(description):
                return _ChunkResult(error=description)
            log.info(
                "parse fallback to plain text",
                extra={"action": "send.fallback", "channel": CHANNEL_TELEGRAM},
            )
            try:
                plain = telegram_html_to_plain(chunk) if parse_mode.upper() == "HTML" else chunk
                payload = await self._send_text(plain or chunk, None, kwargs_tg)
                return _ChunkResult(payload=payload)
            except Exception as retry_exc:  # noqa: BLE001 - reported to caller
                return _ChunkResult(error=_telegram_error_description(retry_exc))
        except Exception as exc:  # noqa: BLE001 - reported to caller
            return _ChunkResult(error=str(exc))

    async def _send_text(
        self, text: str, parse_mode: str | None, kwargs_tg: dict[str, Any]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": kwargs_tg["chat_id"],
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if "reply_to_message_id" in kwargs_tg:
            payload["reply_to_message_id"] = kwargs_tg["reply_to_message_id"]

        resp = await self._http.post("/sendMessage", json=payload)
        resp.raise_for_status()
        return resp.json().get("result", {})

    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        """Acknowledge a callback query to dismiss the loading indicator."""
        try:
            await self._http.post(
                "/answerCallbackQuery",
                json={
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": False,
                },
            )
        except Exception as exc:
            log.warning(
                "answer_callback_failed", extra={"action": "answer_callback", "error": str(exc)}
            )

    async def _send_attachment(
        self, recipient_id: str, att: Attachment, reply_to_ref: str | None
    ) -> None:
        if att.url:
            try:
                if att.content_type.startswith("image/"):
                    await self._bot.send_photo(
                        chat_id=recipient_id,
                        photo=att.url,
                        caption=att.filename,
                    )
                else:
                    await self._bot.send_document(
                        chat_id=recipient_id,
                        document=att.url,
                    )
            except Exception as exc:
                log.warning(
                    "attachment send failed", extra={"action": "send.attachment", "error": str(exc)}
                )
        elif att.data:
            file_obj = aiogram.types.BufferedInputFile(att.data, filename=att.filename)
            try:
                await self._bot.send_document(
                    chat_id=recipient_id,
                    document=file_obj,
                )
            except Exception as exc:
                log.warning(
                    "attachment send failed", extra={"action": "send.attachment", "error": str(exc)}
                )

    # ── inline keyboards (1.4.0 order flow + one-tap approvals) ─────────

    @staticmethod
    def inline_keyboard(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
        """``[[(label, callback_data), …], …]`` → Bot API ``reply_markup``.

        Labels are clipped to 64 chars and callback data to Telegram's 64-byte
        limit so a long product name can never break the whole keyboard.
        """
        keyboard: list[list[dict[str, str]]] = []
        for row in rows:
            line = []
            for label, data in row:
                data_bytes = str(data).encode("utf-8")[:64]
                line.append(
                    {
                        "text": str(label)[:64] or "·",
                        "callback_data": data_bytes.decode("utf-8", errors="ignore") or "noop",
                    }
                )
            if line:
                keyboard.append(line)
        return {"inline_keyboard": keyboard}

    async def send_with_buttons(
        self,
        chat_id: str,
        text: str,
        rows: list[list[tuple[str, str]]],
        *,
        photo_url: str | None = None,
        photo_bytes: bytes | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """Send text (or a photo with caption) plus an inline keyboard.

        Plain text by default — menus generated from the database must never
        fail on an unbalanced tag. Falls back to a text-only send when the
        photo is rejected (bad URL, too large, private bucket…), and finally
        to :meth:`send` so the customer always gets an answer.
        """
        markup = self.inline_keyboard(rows)
        body = normalize_text(text)
        if photo_bytes:
            try:
                file_obj = aiogram.types.BufferedInputFile(photo_bytes, filename="product.jpg")
                msg = await self._bot.send_photo(
                    chat_id=int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id,
                    photo=file_obj,
                    caption=body[:1024],
                    reply_markup=aiogram.types.InlineKeyboardMarkup.model_validate(markup),
                )
                return {"message_id": msg.message_id, "photo": True}
            except Exception as exc:
                log.info(
                    "photo bytes rejected, sending text",
                    extra={"action": "send.photo", "error": str(exc)[:200]},
                )
        if photo_url:
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": body[:1024],
                "reply_markup": markup,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            try:
                resp = await self._http.post("/sendPhoto", json=payload)
                resp.raise_for_status()
                result = resp.json().get("result", {})
                return {"message_id": result.get("message_id"), "photo": True}
            except Exception as exc:
                log.info(
                    "photo url rejected, sending text",
                    extra={"action": "send.photo", "error": _telegram_error_description(exc)[:200]},
                )
        payload = {"chat_id": chat_id, "text": body[:4096], "reply_markup": markup}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            resp = await self._http.post("/sendMessage", json=payload)
            resp.raise_for_status()
            result = resp.json().get("result", {})
            return {"message_id": result.get("message_id"), "photo": False}
        except Exception as exc:
            log.warning(
                "keyboard send failed, plain fallback",
                extra={"action": "send.keyboard", "error": _telegram_error_description(exc)[:200]},
            )
            await self.send(recipient_id=chat_id, text=body)
            return {"message_id": None, "photo": False}

    async def edit_message_text(
        self,
        chat_id: str,
        message_id: int | str,
        text: str,
        rows: list[list[tuple[str, str]]] | None = None,
    ) -> bool:
        """Replace an earlier bot message (used to turn Approve/Reject into a receipt)."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": int(message_id),
            "text": normalize_text(text)[:4096],
        }
        payload["reply_markup"] = self.inline_keyboard(rows or [])
        try:
            resp = await self._http.post("/editMessageText", json=payload)
            resp.raise_for_status()
            return True
        except Exception as exc:
            # Photo messages have a caption, not text.
            try:
                payload.pop("text", None)
                payload["caption"] = normalize_text(text)[:1024]
                resp = await self._http.post("/editMessageCaption", json=payload)
                resp.raise_for_status()
                return True
            except Exception:
                log.info(
                    "edit message failed",
                    extra={
                        "action": "edit_message",
                        "error": _telegram_error_description(exc)[:200],
                    },
                )
                return False

    async def answer_callback_alert(self, callback_query_id: str, text: str) -> None:
        """Pop-up (alert) answer — used for errors the customer must notice."""
        try:
            await self._http.post(
                "/answerCallbackQuery",
                json={
                    "callback_query_id": callback_query_id,
                    "text": text[:200],
                    "show_alert": True,
                },
            )
        except Exception as exc:
            log.warning(
                "answer_callback_failed", extra={"action": "answer_callback", "error": str(exc)}
            )

    # ── admin broadcast ─────────────────────────────────────────────

    async def notify_admins(self, text: str) -> None:
        """Send a notification to all configured admin chat IDs."""
        clean = escape_html(normalize_text(text))
        for admin_id in self._admin_ids:
            try:
                await self._bot.send_message(
                    chat_id=admin_id,
                    text=clean,
                    parse_mode="HTML",
                )
            except Exception as exc:
                log.warning(
                    "admin notify failed",
                    extra={"action": "notify_admins", "target": admin_id, "error": str(exc)},
                )

    # ── attachment download ─────────────────────────────────────────

    async def download_attachment(self, file_id: str) -> bytes | None:
        """Download a file from Telegram servers by file_id."""
        try:
            file_info = await self._bot.get_file(file_id)
            file_path = str(file_info.file_path or "").lstrip("/")
            if not file_path:
                return None
            # 1.5.0 fix: the client's base_url already ends in ``/bot<token>``,
            # so a relative ``/file/bot<token>/…`` produced
            # ``/bot<token>/file/bot<token>/…`` (404) — files were never read.
            url = f"{self._api_base}/file/bot{self._token}/{file_path}"
            resp = await self._http.get(url)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            log.warning(
                "download failed",
                extra={"action": "download", "file_id": file_id, "error": str(exc)},
            )
            return None

    # ── webhook management ──────────────────────────────────────────

    async def set_webhook(self, webhook_url: str) -> bool:
        """Register the webhook URL with Telegram."""
        try:
            resp = await self._http.post(
                "/setWebhook",
                json={
                    "url": webhook_url,
                    "secret_token": self._secret.decode(),
                    "allowed_updates": ["message", "edited_message", "callback_query"],
                    "drop_pending_updates": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            ok = data.get("ok", False)
            log.info("webhook set", extra={"action": "webhook.set", "ok": ok, "url": webhook_url})
            return ok
        except Exception as exc:
            log.error("webhook set failed", extra={"action": "webhook.set", "error": str(exc)})
            return False

    # ── Telegram Web App (TWA) helpers ─────────────────────────────

    def verify_twa_init_data(self, init_data: str) -> dict[str, Any] | None:
        """Verify Telegram Web App initData using HMAC-SHA256.

        Returns parsed data dict or None if verification fails.
        """
        parsed = dict(item.split("=", 1) for item in init_data.split("&") if "=" in item)
        auth_date = parsed.get("auth_date", "")
        hash_val = parsed.get("hash", "")

        if not hash_val or not auth_date:
            return None

        try:
            auth_ts = int(auth_date)
        except (ValueError, TypeError):
            return None
        if abs(time.time() - auth_ts) > 86400:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items()) if k not in ("hash",)
        )
        secret_key = hmac.new(b"WebAppData", self._token.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed, hash_val):
            return None

        return {k: v for k, v in parsed.items() if k != "hash"}

    def build_twa_init_data(self, user_id: int, user_name: str) -> str:
        """Build a TWA init data string for testing purposes."""
        auth_date = str(int(time.time()))
        data_check_string = f"auth_date={auth_date}\nuser={user_id}"
        secret_key = hmac.new(b"WebAppData", self._token.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        params = {
            "auth_date": auth_date,
            "user": user_id,
            "hash": computed,
        }
        return urlencode(params)

    async def open_queue_web_app(self, user_id: int | str, queue_id: str) -> str:
        """Build a deep link URL to open the TWA for a specific queue."""
        bot_username = ""
        try:
            me = await self._bot.get_me()
            bot_username = me.username or ""
        except Exception:
            log.debug("telegram_get_me_failed", exc_info=True)
        base = f"https://t.me/{bot_username}" if bot_username else "https://t.me"
        return f"{base}?start=queue_{queue_id}"

    # ── internal helpers ────────────────────────────────────────────

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        """Send a chat action (typing, upload_photo, etc.) to Telegram."""
        try:
            await self._bot.send_chat_action(chat_id=int(chat_id), action=action)
        except Exception:
            pass

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
        with contextlib.suppress(Exception):
            await self._bot.session.close()
