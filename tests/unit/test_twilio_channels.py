"""Twilio-first channel setup: WhatsApp via Twilio, e-mail via Twilio SendGrid."""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx
import pytest

from app.channels.base import telegram_html_to_plain
from app.channels.email import EmailAdapter
from app.channels.whatsapp import WhatsAppAdapter
from app.config import ConfigError, load_config

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

BASE_ENV: dict[str, str] = {
    "TENANT_ID": "egl",
    "TENANT_NAME_AR": "إليان جلوبال لوجستيك",
    "TENANT_NAME_EN": "Elian Global Logistics",
    "SUPPORT_CONTACT": "info@egl.co.ae",
    "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "TELEGRAM_ADMIN_IDS": "12345",
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "R2_ENDPOINT": "https://t3.storageapi.dev",
    "R2_ACCESS_KEY_ID": "testkey12345678",
    "R2_SECRET_ACCESS_KEY": "testsecret12345678",
    "R2_BUCKET": "bucket",
    "ADMIN_USERNAME": "admin",
    "ADMIN_BOOTSTRAP_PASSWORD": "StrongPassword123!",
    "CURRENCY": "USD",
    "APP_ENV": "test",
    "LLM_MODE": "mock",
}

TWILIO_ENV = {
    "WHATSAPP_ENABLED": "true",
    "WHATSAPP_PROVIDER": "twilio",
    "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "TWILIO_AUTH_TOKEN": "auth-token-0123456789abcdef",
    "TWILIO_WHATSAPP_FROM": "+14155238886",
    "EMAIL_ENABLED": "true",
    "EMAIL_PROVIDER": "sendgrid",
    "EMAIL_FROM": "info@egl.co.ae",
    "SENDGRID_API_KEY": "SG.fake",
    "EMAIL_INBOUND_PROVIDER": "imap",
    "IMAP_HOST": "imap.example.com",
    "IMAP_USER": "info@egl.co.ae",
    "IMAP_PASSWORD": "secret",
}


class _Redis:
    def __init__(self) -> None:
        self.keys: set[str] = set()

    async def set(self, key: str, *_a: Any, **_k: Any) -> bool | None:
        if key in self.keys:
            return None
        self.keys.add(key)
        return True


def _cfg(**overrides: str) -> Any:
    return load_config({**BASE_ENV, **TWILIO_ENV, **overrides})


# ---------------------------------------------------------------------------
# config contract
# ---------------------------------------------------------------------------


def test_twilio_whatsapp_plus_sendgrid_email_loads() -> None:
    cfg = _cfg()
    assert cfg.channels.whatsapp_provider == "twilio"
    assert cfg.channels.email_provider == "sendgrid"
    assert cfg.channels.email_inbound_provider == "imap"
    # Resend is not needed when SendGrid is the outbound provider
    assert cfg.channels.resend_api_key == ""


def test_sendgrid_outbound_requires_its_key() -> None:
    with pytest.raises(ConfigError, match="SENDGRID_API_KEY"):
        _cfg(SENDGRID_API_KEY="")


def test_imap_inbound_does_not_demand_a_webhook_secret() -> None:
    # regression: previously EMAIL_ENABLED=true always demanded a webhook secret
    cfg = _cfg()
    assert cfg.channels.sendgrid_webhook_public_key == ""
    assert cfg.channels.resend_webhook_secret == ""


def test_webhook_inbound_still_demands_a_secret() -> None:
    with pytest.raises(ConfigError, match="SENDGRID_WEBHOOK_PUBLIC_KEY"):
        _cfg(EMAIL_INBOUND_PROVIDER="sendgrid")


def test_resend_stays_the_default_provider() -> None:
    env = {
        **BASE_ENV,
        "EMAIL_ENABLED": "true",
        "EMAIL_FROM": "a@b.c",
        "RESEND_API_KEY": "re_x",
        "RESEND_WEBHOOK_SECRET": "whsec_x",
        "SENDGRID_API_KEY": "SG.inbound",
    }
    cfg = load_config(env)
    assert cfg.channels.email_provider == "resend"


# ---------------------------------------------------------------------------
# Telegram-HTML → plain channels
# ---------------------------------------------------------------------------


def test_html_menu_becomes_whatsapp_markdown() -> None:
    src = "⚓ <b>Welcome</b>\nDiesel <10 ppm &amp; Jet<br><code>EGL-PRD-JET</code>"
    out = telegram_html_to_plain(src, bold="*", italic="_", code="`")
    assert out == "⚓ *Welcome*\nDiesel <10 ppm & Jet\n`EGL-PRD-JET`"


def test_html_menu_becomes_plain_email_text() -> None:
    assert telegram_html_to_plain("<b>Hours:</b> Sun–Thu <i>9–18</i>") == "Hours: Sun–Thu 9–18"


# ---------------------------------------------------------------------------
# WhatsApp via Twilio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_twilio_sandbox_form_payload_is_parsed() -> None:
    wa = WhatsAppAdapter(_cfg(), _Redis())
    msg = await wa.parse_incoming(
        {
            "MessageSid": "SM123",
            "AccountSid": "ACxxx",
            "From": "whatsapp:+971544569977",
            "To": "whatsapp:+14155238886",
            "Body": "What are your working hours?",
            "ProfileName": "Ahmed",
            "NumMedia": "0",
        }
    )
    assert msg is not None
    assert msg.sender_id == "+971544569977"
    assert msg.sender_name == "Ahmed"
    assert msg.metadata["provider"] == "twilio"


@pytest.mark.asyncio
async def test_twilio_send_posts_basic_auth_form_and_converts_html() -> None:
    seen: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization", "")
        seen["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(201, json={"sid": "SM999"})

    wa = WhatsAppAdapter(_cfg(), _Redis())
    wa._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await wa.send("+971544569977", "<b>Office</b> Sun–Thu 9:00–18:00")
    assert res.success and res.external_ref == "SM999"
    assert seen["url"].endswith("/Accounts/ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx/Messages.json")
    assert seen["auth"].startswith("Basic ")
    assert seen["form"]["To"] == "whatsapp:+971544569977"
    assert seen["form"]["From"] == "whatsapp:+14155238886"
    assert seen["form"]["Body"] == "*Office* Sun–Thu 9:00–18:00"


# ---------------------------------------------------------------------------
# E-mail via Twilio SendGrid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sendgrid_send_uses_v3_mail_send() -> None:
    seen: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization", "")
        seen["json"] = json.loads(request.content)
        return httpx.Response(202, headers={"X-Message-Id": "abc123"})

    mailer = EmailAdapter(_cfg(), _Redis())
    mailer._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await mailer.send(
        "client@example.com", "<b>Thanks</b> for your enquiry.", reply_to_ref="<m1@x>"
    )
    assert res.success and res.external_ref == "abc123"
    assert seen["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert seen["auth"] == "Bearer SG.fake"
    body = seen["json"]
    assert body["from"] == {"email": "info@egl.co.ae"}
    assert body["personalizations"][0]["to"] == [{"email": "client@example.com"}]
    assert body["content"] == [{"type": "text/plain", "value": "Thanks for your enquiry."}]
    assert body["headers"]["In-Reply-To"] == "<m1@x>"
    assert body["subject"].startswith("Re: your enquiry")


@pytest.mark.asyncio
async def test_sendgrid_http_error_is_reported_not_raised() -> None:
    async def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": [{"message": "bad key"}]})

    mailer = EmailAdapter(_cfg(), _Redis())
    mailer._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await mailer.send("client@example.com", "hi")
    assert not res.success and "401" in (res.error or "")


@pytest.mark.asyncio
async def test_resend_path_is_untouched_when_provider_is_resend() -> None:
    seen: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"id": "re_1"})

    cfg = load_config(
        {
            **BASE_ENV,
            "EMAIL_ENABLED": "true",
            "EMAIL_FROM": "a@b.c",
            "RESEND_API_KEY": "re_x",
            "RESEND_WEBHOOK_SECRET": "whsec_x",
            "SENDGRID_API_KEY": "SG.inbound",
        }
    )
    mailer = EmailAdapter(cfg, _Redis())
    mailer._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await mailer.send("client@example.com", "hi", subject="s")
    assert res.success and seen["url"] == "https://api.resend.com/emails"


@pytest.mark.asyncio
async def test_imap_poller_feeds_the_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from app.channels import email as email_mod
    from app.channels.base import IncomingMessage

    mailer = EmailAdapter(_cfg(), _Redis())
    incoming = IncomingMessage(
        channel="email",
        sender_id="c@x.com",
        sender_name="C",
        text="[Subject: hi]\n\nhello",
        conversation_id="c@x.com",
        external_ref="<id1@x>",
        attachments=(),
        reply_to_ref=None,
        metadata={"provider": "imap"},
    )

    async def fake_poll() -> list[IncomingMessage]:
        return [incoming]

    ingested: list[dict[str, Any]] = []

    async def fake_ingest(**kw: Any) -> dict[str, Any]:
        ingested.append(kw)
        return {"accepted": True}

    monkeypatch.setattr(mailer, "poll_imap_once", fake_poll)
    import app.core.pipeline as pipeline

    monkeypatch.setattr(pipeline, "ingest_incoming", fake_ingest)

    task = asyncio.create_task(mailer.run_imap_poller({}))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (
        ingested and ingested[0]["external_ref"] == "<id1@x>" and ingested[0]["channel"] == "email"
    )
    assert email_mod.DEFAULT_SENDGRID_URL.startswith("https://api.sendgrid.com")
    assert dataclasses.is_dataclass(cfg := _cfg()) and cfg.channels.imap_poll_seconds >= 5
