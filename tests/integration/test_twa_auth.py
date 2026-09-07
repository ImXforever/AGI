"""Regression tests for Telegram Mini App (TWA) admin authorisation.

Guards bug #27: ``/twa/login`` compared TELEGRAM_ADMIN_IDS against the raw
``user`` JSON blob and then against the free-text ``username``. That made a
genuine admin unable to log in, while anyone whose Telegram username happened
to equal an admin's numeric id was granted an admin token.

Authorisation must depend on the immutable numeric ``user["id"]`` only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import pytest

# Must match tests/conftest.py session env.
BOT_TOKEN = "123456:TEST-token-for-integration-suite"
ADMIN_ID = "1"


def _sign_init_data(user: dict[str, Any], *, auth_date: int | None = None) -> str:
    """Build a genuinely HMAC-signed ``initData`` string, as Telegram would."""
    parsed = {
        "user": json.dumps(user),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAF_test_query",
    }
    check_string = "\n".join(sorted(f"{k}={v}" for k, v in parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    parsed["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{k}={v}" for k, v in parsed.items())


async def _login(client: Any, init_data: str) -> Any:
    return await client.post("/admin/api/twa/login", json={"init_data": init_data})


@pytest.mark.anyio
async def test_genuine_admin_can_log_in(client: Any) -> None:
    """The real fix: an admin listed in TELEGRAM_ADMIN_IDS is accepted."""
    init_data = _sign_init_data({"id": int(ADMIN_ID), "username": "realadmin"})
    resp = await _login(client, init_data)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["token"]
    assert body["username"] == ADMIN_ID


@pytest.mark.anyio
async def test_username_spoofing_is_rejected(client: Any) -> None:
    """A non-admin whose *username* equals an admin id must NOT get in."""
    init_data = _sign_init_data({"id": 999999, "username": ADMIN_ID})
    resp = await _login(client, init_data)
    assert resp.status_code == 403, resp.text
    assert "not authorized" in resp.json()["detail"]


@pytest.mark.anyio
async def test_ordinary_user_is_rejected(client: Any) -> None:
    init_data = _sign_init_data({"id": 424242, "username": "someone"})
    resp = await _login(client, init_data)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_forged_signature_is_rejected(client: Any) -> None:
    """Tampering with the payload after signing must break the HMAC."""
    init_data = _sign_init_data({"id": 999999, "username": "attacker"})
    forged = init_data.replace('"id": 999999', f'"id": {ADMIN_ID}')
    resp = await _login(client, forged)
    assert resp.status_code == 403
    assert "verification failed" in resp.json()["detail"]


@pytest.mark.anyio
async def test_expired_init_data_is_rejected(client: Any) -> None:
    stale = int(time.time()) - 3600
    init_data = _sign_init_data({"id": int(ADMIN_ID)}, auth_date=stale)
    resp = await _login(client, init_data)
    assert resp.status_code == 403
    assert "expired" in resp.json()["detail"]


@pytest.mark.anyio
async def test_missing_hash_is_rejected(client: Any) -> None:
    resp = await _login(client, "user=%7B%22id%22%3A1%7D&auth_date=1")
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_malformed_user_payload_is_rejected(client: Any) -> None:
    """A signed but non-JSON ``user`` field must not slip past the id check."""
    init_data = _sign_init_data_raw({"user": ADMIN_ID, "auth_date": str(int(time.time()))})
    resp = await _login(client, init_data)
    assert resp.status_code == 403


def _sign_init_data_raw(parsed: dict[str, str]) -> str:
    check_string = "\n".join(sorted(f"{k}={v}" for k, v in parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    signed = dict(parsed)
    signed["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{k}={v}" for k, v in signed.items())
