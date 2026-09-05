"""End-to-end tests for app.gateway.webhooks (was 16% covered).

The Telegram webhook is fully exercised against the live app: signature
verification, payload parsing, and the full ingestion path down to the
Postgres rows and the Redis event stream. WhatsApp and email are disabled in
the test environment, so those endpoints are asserted on their
service-unavailable / verification behaviour.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.integration]

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
SECRET = "integration-webhook-secret-0123456789"


def _tg_update(*, text="مرحبا، أريد عرض سعر", chat_id=None, update_id=None, first_name="Test User"):
    chat_id = chat_id or int(uuid.uuid4().int % 10**9)
    update_id = update_id or int(uuid.uuid4().int % 10**9)
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": 1788364644,
            "chat": {"id": chat_id, "type": "private", "first_name": first_name},
            "from": {"id": chat_id, "is_bot": False, "first_name": first_name},
            "text": text,
        },
    }


# --------------------------------------------------------------------------
# Telegram — verification
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_secret_header_is_forbidden(client):
    resp = await client.post("/tg/webhook", json=_tg_update())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_wrong_secret_header_is_forbidden(client):
    resp = await client.post(
        "/tg/webhook", json=_tg_update(), headers={SECRET_HEADER: "not-the-secret"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_a_near_miss_secret_is_forbidden(client):
    resp = await client.post("/tg/webhook", json=_tg_update(), headers={SECRET_HEADER: SECRET[:-1]})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_correct_secret_is_accepted(client):
    resp = await client.post("/tg/webhook", json=_tg_update(), headers={SECRET_HEADER: SECRET})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_malformed_json_is_rejected(client):
    resp = await client.post(
        "/tg/webhook",
        content=b"{not json",
        headers={SECRET_HEADER: SECRET, "content-type": "application/json"},
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------------
# Telegram — parsing
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_message_update_is_acknowledged(client):
    """A callback_query with no message must not 500."""
    payload = {"update_id": 1, "callback_query": {"id": "abc", "data": "noop"}}
    resp = await client.post("/tg/webhook", json=payload, headers={SECRET_HEADER: SECRET})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_empty_update_is_acknowledged(client):
    resp = await client.post("/tg/webhook", json={"update_id": 2}, headers={SECRET_HEADER: SECRET})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_arabic_text_is_accepted(client):
    resp = await client.post(
        "/tg/webhook",
        json=_tg_update(text="ما هو سعر الديزل اليوم؟"),
        headers={SECRET_HEADER: SECRET},
    )
    assert resp.status_code == 200


# --------------------------------------------------------------------------
# Telegram — ingestion side effects
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_message_creates_a_customer_row(client, pool):
    chat_id = int(uuid.uuid4().int % 10**9)
    await client.post(
        "/tg/webhook", json=_tg_update(chat_id=chat_id), headers={SECRET_HEADER: SECRET}
    )
    row = await pool.fetchrow(
        "SELECT id, channel FROM customers WHERE external_id = $1", str(chat_id)
    )
    assert row is not None
    assert row["channel"] == "telegram"


@pytest.mark.asyncio
async def test_message_creates_a_conversation(client, pool):
    chat_id = int(uuid.uuid4().int % 10**9)
    await client.post(
        "/tg/webhook", json=_tg_update(chat_id=chat_id), headers={SECRET_HEADER: SECRET}
    )
    count = await pool.fetchval(
        """SELECT COUNT(*) FROM conversations c
           JOIN customers cu ON cu.id = c.customer_id
           WHERE cu.external_id = $1""",
        str(chat_id),
    )
    assert count == 1


@pytest.mark.asyncio
async def test_message_body_is_persisted(client, pool):
    chat_id = int(uuid.uuid4().int % 10**9)
    text = f"طلب عرض سعر {uuid.uuid4().hex[:8]}"
    await client.post(
        "/tg/webhook", json=_tg_update(chat_id=chat_id, text=text), headers={SECRET_HEADER: SECRET}
    )
    stored = await pool.fetchval("SELECT text FROM messages WHERE text = $1", text)
    assert stored == text


@pytest.mark.asyncio
async def test_two_messages_share_one_conversation(client, pool):
    chat_id = int(uuid.uuid4().int % 10**9)
    for i in range(2):
        await client.post(
            "/tg/webhook",
            json=_tg_update(chat_id=chat_id, text=f"رسالة رقم {i}"),
            headers={SECRET_HEADER: SECRET},
        )
    count = await pool.fetchval(
        """SELECT COUNT(*) FROM conversations c
           JOIN customers cu ON cu.id = c.customer_id
           WHERE cu.external_id = $1""",
        str(chat_id),
    )
    assert count == 1


@pytest.mark.asyncio
async def test_duplicate_update_is_ingested_only_once(client, pool):
    chat_id = int(uuid.uuid4().int % 10**9)
    update_id = int(uuid.uuid4().int % 10**9)
    text = f"مكرر {uuid.uuid4().hex[:8]}"
    payload = _tg_update(chat_id=chat_id, update_id=update_id, text=text)

    first = await client.post("/tg/webhook", json=payload, headers={SECRET_HEADER: SECRET})
    second = await client.post("/tg/webhook", json=payload, headers={SECRET_HEADER: SECRET})

    # The provider must always get a 200 so it stops retrying.
    assert (first.status_code, second.status_code) == (200, 200)
    stored = await pool.fetchval("SELECT COUNT(*) FROM messages WHERE text = $1", text)
    assert stored == 1


@pytest.mark.asyncio
async def test_ingestion_publishes_onto_the_event_stream(client, app_instance):
    from app.constants import STREAM_EVENTS

    redis = app_instance.state.services["redis"]
    before = await redis.xlen(STREAM_EVENTS)
    await client.post("/tg/webhook", json=_tg_update(), headers={SECRET_HEADER: SECRET})
    assert await redis.xlen(STREAM_EVENTS) > before


@pytest.mark.asyncio
async def test_sender_name_is_captured(client, pool):
    chat_id = int(uuid.uuid4().int % 10**9)
    await client.post(
        "/tg/webhook",
        json=_tg_update(chat_id=chat_id, first_name="عبدالله"),
        headers={SECRET_HEADER: SECRET},
    )
    name = await pool.fetchval("SELECT name FROM customers WHERE external_id = $1", str(chat_id))
    assert "عبدالله" in name


# --------------------------------------------------------------------------
# WhatsApp — handshake + disabled adapter
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wa_handshake_rejects_a_wrong_token(client):
    resp = await client.get(
        "/wa/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "12345",
            "hub.verify_token": "wrong-token",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_wa_handshake_rejects_a_missing_token(client):
    resp = await client.get("/wa/webhook", params={"hub.mode": "subscribe"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_wa_post_without_a_valid_signature_is_forbidden(client):
    resp = await client.post("/wa/webhook", json={"object": "whatsapp_business_account"})
    assert resp.status_code == 403


# --------------------------------------------------------------------------
# Email — verification
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_inbound_without_a_signature_is_forbidden(client):
    resp = await client.post("/email/inbound", data={"from": "a@b.c", "text": "hi"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_email_inbound_with_a_bogus_signature_is_forbidden(client):
    resp = await client.post(
        "/email/inbound",
        data={"from": "a@b.c", "text": "hi"},
        headers={
            "X-Twilio-Email-Event-Webhook-Signature": "bogus",
            "X-Twilio-Email-Event-Webhook-Timestamp": "1788364644",
        },
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------
# _ingest guard rails
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_rejects_a_non_incoming_message(app_instance):
    from fastapi import HTTPException

    from app.gateway.webhooks import _ingest

    class _Req:
        app = app_instance

    with pytest.raises(HTTPException) as ei:
        await _ingest(_Req(), "telegram", {"not": "an IncomingMessage"})
    assert ei.value.status_code == 422


@pytest.mark.asyncio
async def test_ingest_reports_service_unavailable_without_redis(app_instance):
    from fastapi import HTTPException

    from app.channels.base import IncomingMessage
    from app.gateway.webhooks import _ingest

    services = dict(app_instance.state.services)
    services["redis"] = None

    class _State:
        pass

    class _App:
        state = _State()

    _App.state.services = services

    class _Req:
        app = _App()

    msg = IncomingMessage(
        channel="telegram",
        sender_id="1",
        sender_name="x",
        text="hi",
        conversation_id="",
        external_ref="ref-1",
    )
    with pytest.raises(HTTPException) as ei:
        await _ingest(_Req(), "telegram", msg)
    assert ei.value.status_code == 503
