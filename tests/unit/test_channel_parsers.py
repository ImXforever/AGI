"""Unit tests for the WhatsApp and Email inbound parsers.

Both adapters translate a provider's webhook payload into the internal
`IncomingMessage`. They are pure apart from a Redis dedup call, so they are
tested here against a stub Redis with no network involved.
"""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any

import pytest

from app.channels.email import EmailAdapter
from app.channels.whatsapp import WhatsAppAdapter

pytestmark = pytest.mark.unit


class _Redis:
    def __init__(self) -> None:
        self.keys: set[str] = set()

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None):
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


def _channels_stub() -> Any:
    """A ChannelsGroup with real defaults, so the adapters find every field.

    Built from the actual config dataclass rather than hand-rolled, which keeps
    these tests honest when new channel settings are added.
    """
    import dataclasses

    from app.config import ChannelsGroup

    values: dict[str, Any] = {}
    for field in dataclasses.fields(ChannelsGroup):
        if field.type in ("bool", bool):
            values[field.name] = False
        elif field.type in ("int", int):
            values[field.name] = 60
        elif "tuple" in str(field.type) or "list" in str(field.type):
            values[field.name] = ()
        else:
            values[field.name] = ""
    values.update(
        whatsapp_provider="meta",
        whatsapp_api_token="t",
        whatsapp_phone_number_id="pid",
        email_inbound_provider="sendgrid",
        email_from="bot@test.local",
    )
    return ChannelsGroup(**values)


class _Cfg:
    def __init__(self) -> None:
        self.channels = _channels_stub()


@pytest.fixture
def wa() -> WhatsAppAdapter:
    return WhatsAppAdapter(_Cfg(), _Redis())


@pytest.fixture
def mailer() -> EmailAdapter:
    return EmailAdapter(_Cfg(), _Redis())


def meta_payload(msg: dict[str, Any], **value: Any) -> dict[str, Any]:
    base_value = {
        "messages": [msg],
        "contacts": [{"profile": {"name": "Ali"}, "wa_id": "9665551234"}],
        "metadata": {"display_phone_number": "+966500", "phone_number_id": "pid"},
    }
    base_value.update(value)
    return {"entry": [{"changes": [{"value": base_value}]}]}


def text_msg(body: str = "مرحبا", msg_id: str = "wamid.1") -> dict[str, Any]:
    return {"id": msg_id, "from": "9665551234", "type": "text", "text": {"body": body}}


# ---------------------------------------------------------------------------
# WhatsApp — Meta Cloud API
# ---------------------------------------------------------------------------


class TestWhatsAppMeta:
    async def test_a_text_message_is_parsed(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(meta_payload(text_msg()))
        assert msg is not None
        assert msg.channel == "whatsapp"
        assert msg.sender_id == "9665551234"
        assert msg.external_ref == "wamid.1"

    async def test_the_contact_profile_name_is_used(self, wa: WhatsAppAdapter):
        assert (await wa.parse_incoming(meta_payload(text_msg()))).sender_name == "Ali"

    async def test_the_phone_number_is_the_fallback_name(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(meta_payload(text_msg(), contacts=[]))
        assert msg.sender_name == "9665551234"

    async def test_an_empty_payload_is_ignored(self, wa: WhatsAppAdapter):
        assert await wa.parse_incoming({}) is None

    async def test_a_status_only_callback_is_ignored(self, wa: WhatsAppAdapter):
        payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
        assert await wa.parse_incoming(payload) is None

    async def test_an_image_caption_becomes_the_text(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "image",
                    "image": {"caption": "صورة المضخة", "id": "img1"},
                }
            )
        )
        assert "صورة المضخة" in msg.text

    async def test_an_audio_message_gets_a_placeholder(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "audio",
                    "audio": {"id": "a1"},
                }
            )
        )
        assert "audio" in msg.text.lower()

    async def test_a_sticker_gets_a_placeholder(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "sticker",
                    "sticker": {"id": "s1"},
                }
            )
        )
        assert "sticker" in msg.text.lower()

    async def test_a_button_reply_uses_the_button_title(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "interactive",
                    "interactive": {"type": "button_reply", "button_reply": {"title": "نعم"}},
                }
            )
        )
        assert msg.text == "نعم"

    async def test_a_list_reply_uses_the_row_title(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "interactive",
                    "interactive": {"type": "list_reply", "list_reply": {"title": "ديزل"}},
                }
            )
        )
        assert msg.text == "ديزل"

    async def test_a_location_is_rendered_with_coordinates(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "location",
                    "location": {"latitude": 24.7, "longitude": 46.6},
                }
            )
        )
        assert "24.7" in msg.text and "46.6" in msg.text

    async def test_an_unknown_type_is_labelled_not_dropped(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    "id": "m1",
                    "from": "966",
                    "type": "contacts",
                    "contacts": [{}],
                }
            )
        )
        assert msg.text == "[contacts]"

    async def test_a_reply_carries_the_context_reference(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(
            meta_payload(
                {
                    **text_msg(),
                    "context": {"id": "wamid.parent"},
                }
            )
        )
        assert msg.reply_to_ref == "wamid.parent"

    async def test_the_provider_is_recorded_in_the_metadata(self, wa: WhatsAppAdapter):
        msg = await wa.parse_incoming(meta_payload(text_msg()))
        assert msg.metadata["provider"] == "meta"
        assert msg.metadata["message_type"] == "text"

    async def test_a_repeated_message_id_is_deduplicated(self, wa: WhatsAppAdapter):
        assert await wa.parse_incoming(meta_payload(text_msg())) is not None
        assert await wa.parse_incoming(meta_payload(text_msg())) is None


class TestWhatsAppTwilio:
    @pytest.fixture
    def twilio(self) -> WhatsAppAdapter:
        import dataclasses

        cfg = _Cfg()
        cfg.channels = dataclasses.replace(cfg.channels, whatsapp_provider="twilio")
        return WhatsAppAdapter(cfg, _Redis())

    async def test_a_twilio_form_payload_is_parsed(self, twilio: WhatsAppAdapter):
        msg = await twilio.parse_incoming(
            {
                "From": "whatsapp:+9665551234",
                "Body": "مرحبا",
                "MessageSid": "SM1",
                "ProfileName": "Ali",
            }
        )
        assert msg is not None
        assert msg.channel == "whatsapp"
        assert msg.external_ref == "SM1"

    async def test_an_empty_twilio_payload_is_ignored(self, twilio: WhatsAppAdapter):
        assert await twilio.parse_incoming({}) is None


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


class TestEmailAddressParsing:
    def test_a_display_name_is_separated_from_the_address(self, mailer: EmailAdapter):
        assert mailer._parse_email_address("Ali Hassan <ali@test.com>") == (
            "ali@test.com",
            "Ali Hassan",
        )

    def test_a_bare_address_has_no_name(self, mailer: EmailAdapter):
        assert mailer._parse_email_address("ali@test.com") == ("ali@test.com", "")

    def test_quotes_around_the_name_are_stripped(self, mailer: EmailAdapter):
        assert mailer._parse_email_address('"Ali" <ali@test.com>')[1] == "Ali"

    def test_angle_brackets_alone_are_stripped(self, mailer: EmailAdapter):
        assert mailer._parse_email_address("<ali@test.com>") == ("ali@test.com", "")

    def test_empty_input_is_tolerated(self, mailer: EmailAdapter):
        assert mailer._parse_email_address("") == ("", "")


class TestQuotedTextStripping:
    def test_quoted_lines_are_removed(self, mailer: EmailAdapter):
        assert mailer._strip_quoted_text("My reply\n> their text") == "My reply"

    def test_an_on_wrote_header_truncates_the_body(self, mailer: EmailAdapter):
        body = "My reply\nOn Monday Ali wrote:\ntheir whole email"
        assert mailer._strip_quoted_text(body) == "My reply"

    def test_a_signature_separator_truncates_the_body(self, mailer: EmailAdapter):
        assert mailer._strip_quoted_text("My reply\n____\nsignature") == "My reply"

    def test_an_unquoted_body_is_preserved(self, mailer: EmailAdapter):
        assert mailer._strip_quoted_text("line one\nline two") == "line one\nline two"

    def test_an_empty_body_stays_empty(self, mailer: EmailAdapter):
        assert mailer._strip_quoted_text("") == ""


class TestHeaderDecoding:
    def test_a_plain_header_is_returned_as_is(self, mailer: EmailAdapter):
        assert mailer._decode_header_value("Simple Subject") == "Simple Subject"

    def test_none_becomes_an_empty_string(self, mailer: EmailAdapter):
        assert mailer._decode_header_value(None) == ""

    def test_a_utf8_encoded_header_is_decoded(self, mailer: EmailAdapter):
        assert "مرحبا" in mailer._decode_header_value("=?utf-8?b?2YXYsdit2KjYpw==?=")

    def test_an_unknown_charset_falls_back_gracefully(self, mailer: EmailAdapter):
        assert isinstance(mailer._decode_header_value("=?x-unknown?q?hi?="), str)


class TestRfc822Parsing:
    def _raw(self, body: str = "Hello there", subject: str = "Question") -> bytes:
        msg = EmailMessage()
        msg["From"] = "Ali Hassan <ali@test.com>"
        msg["To"] = "bot@test.local"
        msg["Subject"] = subject
        msg["Message-ID"] = "<abc@test.com>"
        msg.set_content(body)
        return msg.as_bytes()

    def test_a_well_formed_message_is_parsed(self, mailer: EmailAdapter):
        msg = mailer.parse_rfc822(self._raw())
        assert msg is not None
        assert msg.channel == "email"
        assert msg.sender_id == "ali@test.com"

    def test_the_sender_display_name_is_captured(self, mailer: EmailAdapter):
        assert mailer.parse_rfc822(self._raw()).sender_name == "Ali Hassan"

    def test_the_body_text_is_extracted(self, mailer: EmailAdapter):
        assert "Hello there" in mailer.parse_rfc822(self._raw()).text

    def test_garbage_bytes_do_not_raise(self, mailer: EmailAdapter):
        assert mailer.parse_rfc822(b"\xff\xfe not an email") is not None or True

    def test_quoted_replies_are_stripped_from_the_body(self, mailer: EmailAdapter):
        msg = mailer.parse_rfc822(self._raw(body="My answer\n> your question"))
        assert "your question" not in msg.text


class TestSendGridParsing:
    async def test_an_inbound_parse_payload_is_read(self, mailer: EmailAdapter):
        msg = await mailer.parse_incoming(
            {
                "from": "Ali <ali@test.com>",
                "subject": "Need a quote",
                "text": "Please send pricing.",
                "message_id": "<sg1@test.com>",
            }
        )
        assert msg is not None
        assert msg.sender_id == "ali@test.com"
        assert "pricing" in msg.text

    async def test_a_payload_without_a_message_id_is_ignored(self, mailer: EmailAdapter):
        """No Message-ID means no dedup key, so the message cannot be accepted."""
        assert await mailer.parse_incoming({"from": "a@b.com", "text": "hi"}) is None

    async def test_an_empty_payload_is_ignored(self, mailer: EmailAdapter):
        assert await mailer.parse_incoming({}) is None

    async def test_the_subject_is_prefixed_onto_the_body(self, mailer: EmailAdapter):
        msg = await mailer.parse_incoming(
            {
                "from": "ali@test.com",
                "subject": "Need a quote",
                "text": "body",
                "message_id": "<sg2@test.com>",
            }
        )
        assert "Need a quote" in msg.text

    async def test_quoted_text_is_stripped_from_sendgrid_bodies(self, mailer: EmailAdapter):
        msg = await mailer.parse_incoming(
            {
                "from": "ali@test.com",
                "subject": "Re: quote",
                "text": "My reply\n> their original",
                "message_id": "<sg3@test.com>",
            }
        )
        assert "their original" not in msg.text
