"""Unit tests for the Telegram adapter's inbound parsing and TWA auth.

`parse_incoming` is the translation layer between Telegram's update format and
the internal `IncomingMessage`, and `verify_twa_init_data` authenticates Web App
sessions with HMAC-SHA256. Neither needs the network, so both are tested here
against a real adapter instance with a stub Redis.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import pytest

from app.channels.telegram import TelegramAdapter

pytestmark = pytest.mark.unit

TOKEN = "123456:TEST-token-for-integration-suite"


class _Redis:
    """Minimal Redis stub implementing SET NX semantics."""

    def __init__(self) -> None:
        self.keys: set[str] = set()

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


class _Channels:
    telegram_bot_token = TOKEN
    telegram_admin_ids = (1, 2)
    telegram_webhook_secret = "webhook-secret-0123456789abcdef"


class _Cfg:
    channels = _Channels()


@pytest.fixture
def adapter() -> TelegramAdapter:
    return TelegramAdapter(_Cfg(), _Redis())


def update(**message: Any) -> dict[str, Any]:
    base = {
        "message_id": 100,
        "chat": {"id": 555, "type": "private"},
        "from": {"id": 42, "first_name": "Ali", "language_code": "ar"},
    }
    base.update(message)
    return {"message": base}


# ---------------------------------------------------------------------------
# Inbound parsing
# ---------------------------------------------------------------------------


class TestParseIncoming:
    async def test_a_plain_text_message_is_normalised(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(update(text="مرحبا"))
        assert msg is not None
        assert msg.channel == "telegram"
        assert msg.sender_id == "42"
        assert msg.conversation_id == "555"
        assert msg.external_ref == "100"

    async def test_an_update_without_a_message_is_ignored(self, adapter: TelegramAdapter):
        assert await adapter.parse_incoming({}) is None

    async def test_an_edited_message_is_accepted(self, adapter: TelegramAdapter):
        payload = {"edited_message": update(text="edited")["message"]}
        assert await adapter.parse_incoming(payload) is not None

    async def test_a_message_with_neither_text_nor_media_is_ignored(self, adapter: TelegramAdapter):
        assert await adapter.parse_incoming(update()) is None

    async def test_a_caption_is_used_when_there_is_no_text(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(caption="تعليق", document={"file_name": "a.pdf", "file_id": "f1"})
        )
        assert msg is not None and "تعليق" in msg.text

    async def test_the_sender_name_joins_first_and_last(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(text="hi", **{"from": {"id": 42, "first_name": "Ali", "last_name": "Hassan"}})
        )
        assert msg.sender_name == "Ali Hassan"

    async def test_the_username_is_used_when_no_real_name_is_present(
        self, adapter: TelegramAdapter
    ):
        msg = await adapter.parse_incoming(
            update(text="hi", **{"from": {"id": 42, "username": "ali_h"}})
        )
        assert msg.sender_name == "ali_h"

    async def test_group_chats_are_flagged_in_the_metadata(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(text="hi", chat={"id": 555, "type": "supergroup"})
        )
        assert msg.metadata["is_group"] is True

    async def test_private_chats_are_not_flagged_as_groups(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(update(text="hi"))
        assert msg.metadata["is_group"] is False

    async def test_a_reply_carries_the_parent_reference(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(update(text="hi", reply_to_message={"message_id": 99}))
        assert msg.reply_to_ref == "99"

    async def test_a_non_reply_has_no_parent_reference(self, adapter: TelegramAdapter):
        assert (await adapter.parse_incoming(update(text="hi"))).reply_to_ref is None

    async def test_the_same_message_is_only_accepted_once(self, adapter: TelegramAdapter):
        """Telegram retries deliveries; the dedup key must suppress the repeat."""
        assert await adapter.parse_incoming(update(text="hi")) is not None
        assert await adapter.parse_incoming(update(text="hi")) is None

    async def test_a_different_message_id_is_not_deduplicated(self, adapter: TelegramAdapter):
        assert await adapter.parse_incoming(update(text="hi", message_id=1)) is not None
        assert await adapter.parse_incoming(update(text="hi", message_id=2)) is not None

    async def test_dedup_is_disabled_when_redis_is_absent(self):
        adapter = TelegramAdapter(_Cfg(), None)
        assert await adapter._is_duplicate("k") is False

    async def test_a_failing_redis_does_not_drop_messages(self, adapter: TelegramAdapter):
        class Broken:
            async def set(self, *a, **k):
                raise RuntimeError("redis down")

        adapter._redis = Broken()
        assert await adapter._is_duplicate("k") is False


class TestAttachments:
    async def test_a_photo_becomes_a_jpeg_attachment(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(
                text="look",
                photo=[
                    {"file_id": "small", "file_size": 100},
                    {"file_id": "large", "file_size": 900},
                ],
            )
        )
        assert len(msg.attachments) == 1
        assert msg.attachments[0].content_type == "image/jpeg"

    async def test_the_largest_photo_variant_is_chosen(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(
                text="look",
                photo=[
                    {"file_id": "small", "file_size": 100},
                    {"file_id": "large", "file_size": 900},
                ],
            )
        )
        assert msg.attachments[0].url == "large"

    async def test_a_document_keeps_its_filename_and_mime(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(
                text="doc",
                document={"file_name": "msds.pdf", "mime_type": "application/pdf", "file_id": "d1"},
            )
        )
        assert msg.attachments[0].filename == "msds.pdf"
        assert msg.attachments[0].content_type == "application/pdf"

    async def test_a_voice_note_is_captured(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(text="v", voice={"file_id": "v1", "mime_type": "audio/ogg"})
        )
        assert msg.attachments[0].filename == "voice.ogg"

    async def test_a_video_is_captured(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(text="v", video={"file_id": "vid1", "mime_type": "video/mp4"})
        )
        assert msg.attachments[0].content_type == "video/mp4"

    async def test_several_media_types_are_all_captured(self, adapter: TelegramAdapter):
        msg = await adapter.parse_incoming(
            update(
                text="all",
                photo=[{"file_id": "p", "file_size": 1}],
                document={"file_name": "d.pdf", "file_id": "d"},
                voice={"file_id": "v"},
            )
        )
        assert len(msg.attachments) == 3

    async def test_a_text_message_has_no_attachments(self, adapter: TelegramAdapter):
        assert (await adapter.parse_incoming(update(text="hi"))).attachments == ()


# ---------------------------------------------------------------------------
# Telegram Web App auth
# ---------------------------------------------------------------------------


class TestTwaInitData:
    def _sign(self, params: dict[str, Any]) -> str:
        check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
        digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        return urlencode({**params, "hash": digest})

    def test_a_correctly_signed_payload_verifies(self, adapter: TelegramAdapter):
        data = self._sign({"auth_date": str(int(time.time())), "user": "42"})
        assert adapter.verify_twa_init_data(data) is not None

    def test_the_hash_is_stripped_from_the_result(self, adapter: TelegramAdapter):
        data = self._sign({"auth_date": str(int(time.time())), "user": "42"})
        assert "hash" not in adapter.verify_twa_init_data(data)

    def test_a_tampered_field_fails_verification(self, adapter: TelegramAdapter):
        data = self._sign({"auth_date": str(int(time.time())), "user": "42"})
        assert adapter.verify_twa_init_data(data.replace("user=42", "user=99")) is None

    def test_a_forged_hash_fails_verification(self, adapter: TelegramAdapter):
        data = urlencode({"auth_date": str(int(time.time())), "user": "42", "hash": "deadbeef"})
        assert adapter.verify_twa_init_data(data) is None

    def test_a_missing_hash_fails_verification(self, adapter: TelegramAdapter):
        assert adapter.verify_twa_init_data("auth_date=123&user=42") is None

    def test_a_missing_auth_date_fails_verification(self, adapter: TelegramAdapter):
        assert adapter.verify_twa_init_data("user=42&hash=abc") is None

    def test_a_non_numeric_auth_date_fails_verification(self, adapter: TelegramAdapter):
        assert adapter.verify_twa_init_data("auth_date=abc&user=42&hash=x") is None

    def test_a_day_old_session_is_refused(self, adapter: TelegramAdapter):
        old = str(int(time.time()) - 90_000)
        assert adapter.verify_twa_init_data(self._sign({"auth_date": old, "user": "42"})) is None

    def test_empty_input_fails_verification(self, adapter: TelegramAdapter):
        assert adapter.verify_twa_init_data("") is None

    def test_the_builder_produces_data_the_verifier_accepts(self, adapter: TelegramAdapter):
        """build_twa_init_data and verify_twa_init_data must agree."""
        assert adapter.verify_twa_init_data(adapter.build_twa_init_data(42, "Ali")) is not None
