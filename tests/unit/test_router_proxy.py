"""Unit tests for app.gateway.router_proxy (was 22% covered).

Focus is the session-validation gate (a security boundary: it decides who may
reach the 9router dashboard) plus the upstream header/error handling in
_proxy_request. httpx is stubbed; no network is used.
"""

from __future__ import annotations

import hashlib
import hmac
import time

import httpx
import pytest
from fastapi import HTTPException

from app.gateway import router_proxy as rp

SECRET = "unit-test-web-secret-value"


def _sign(ts: int, secret: str = SECRET) -> str:
    sig = hmac.new(secret.encode(), str(ts).encode(), hashlib.sha256).hexdigest()[:32]
    return f"{ts}:{sig}"


# --------------------------------------------------------------------------
# _validate_admin_session
# --------------------------------------------------------------------------


def test_valid_fresh_token_is_accepted():
    assert rp._validate_admin_session(_sign(int(time.time())), SECRET) is True


def test_missing_token_is_rejected():
    assert rp._validate_admin_session(None, SECRET) is False


def test_empty_token_is_rejected():
    assert rp._validate_admin_session("", SECRET) is False


def test_token_without_a_separator_is_rejected():
    assert rp._validate_admin_session("nosignaturehere", SECRET) is False


def test_token_with_a_non_numeric_timestamp_is_rejected():
    assert rp._validate_admin_session("notanumber:deadbeef", SECRET) is False


def test_token_signed_with_the_wrong_secret_is_rejected():
    token = _sign(int(time.time()), "a-totally-different-secret")
    assert rp._validate_admin_session(token, SECRET) is False


def test_tampered_signature_is_rejected():
    ts = int(time.time())
    good = _sign(ts)
    tampered = good[:-1] + ("0" if good[-1] != "0" else "1")
    assert rp._validate_admin_session(tampered, SECRET) is False


def test_tampered_timestamp_invalidates_the_signature():
    ts = int(time.time())
    _, sig = _sign(ts).split(":")
    assert rp._validate_admin_session(f"{ts + 1}:{sig}", SECRET) is False


def test_token_older_than_24h_is_rejected():
    assert rp._validate_admin_session(_sign(int(time.time()) - 86_401), SECRET) is False


def test_token_just_inside_24h_is_accepted():
    assert rp._validate_admin_session(_sign(int(time.time()) - 86_000), SECRET) is True


def test_token_from_the_far_future_is_rejected():
    """abs() means clock-skewed future tokens are bounded too."""
    assert rp._validate_admin_session(_sign(int(time.time()) + 86_401), SECRET) is False


def test_signature_is_truncated_to_32_hex_chars():
    ts = int(time.time())
    full = hmac.new(SECRET.encode(), str(ts).encode(), hashlib.sha256).hexdigest()
    assert rp._validate_admin_session(f"{ts}:{full}", SECRET) is False
    assert rp._validate_admin_session(f"{ts}:{full[:32]}", SECRET) is True


# --------------------------------------------------------------------------
# _target_base_url
# --------------------------------------------------------------------------


def test_target_base_url_strips_v1_and_trailing_slash(monkeypatch):
    class _LLM:
        router_base_url = "https://router.example.com/v1/"

    class _Cfg:
        llm = _LLM()

    monkeypatch.setattr(rp, "get_config", lambda: _Cfg())
    assert rp._target_base_url() == "https://router.example.com"


def test_target_base_url_without_v1_is_unchanged(monkeypatch):
    class _Cfg:
        llm = type("L", (), {"router_base_url": "http://localhost:9000"})()

    monkeypatch.setattr(rp, "get_config", lambda: _Cfg())
    assert rp._target_base_url() == "http://localhost:9000"


# --------------------------------------------------------------------------
# _proxy_request
# --------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, method="GET", headers=None, body=b"", query=""):
        self.method = method
        self.headers = headers or {}
        self._body = body
        self.url = type("U", (), {"query": query})()

    async def body(self):
        return self._body


def _patch_config(monkeypatch, access_key="router-key-123"):
    class _Cfg:
        llm = type(
            "L",
            (),
            {
                "router_base_url": "http://up/v1",
                "router_access_key": access_key,
            },
        )()

    monkeypatch.setattr(rp, "get_config", lambda: _Cfg())


def _patch_client(monkeypatch, *, response=None, exc=None, captured=None):
    class _Client:
        def __init__(self, timeout=None):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def request(self, **kw):
            if captured is not None:
                captured.update(kw)
            if exc:
                raise exc
            return response

    monkeypatch.setattr(rp.httpx, "AsyncClient", _Client)


def _resp(status=200, content=b"ok", headers=None):
    return httpx.Response(
        status_code=status,
        content=content,
        headers=headers or {"content-type": "application/json"},
    )


@pytest.mark.asyncio
async def test_proxy_returns_upstream_status_and_body(monkeypatch):
    _patch_config(monkeypatch)
    _patch_client(monkeypatch, response=_resp(201, b'{"ok":true}'))
    out = await rp._proxy_request(_FakeRequest(), "http://up/models")
    assert out.status_code == 201
    assert out.body == b'{"ok":true}'


@pytest.mark.asyncio
async def test_proxy_injects_the_router_access_key(monkeypatch):
    _patch_config(monkeypatch, access_key="secret-key")
    captured: dict = {}
    _patch_client(monkeypatch, response=_resp(), captured=captured)
    await rp._proxy_request(_FakeRequest(), "http://up/models")
    assert captured["headers"]["Authorization"] == "Bearer secret-key"


@pytest.mark.asyncio
async def test_proxy_forwards_only_whitelisted_request_headers(monkeypatch):
    _patch_config(monkeypatch, access_key="")
    captured: dict = {}
    _patch_client(monkeypatch, response=_resp(), captured=captured)
    req = _FakeRequest(
        headers={
            "content-type": "application/json",
            "accept": "text/event-stream",
            "cookie": "petro_session=leaky",
            "x-forwarded-for": "1.2.3.4",
        }
    )
    await rp._proxy_request(req, "http://up/x")
    assert set(captured["headers"]) == {"content-type", "accept"}
    assert "cookie" not in captured["headers"]


@pytest.mark.asyncio
async def test_proxy_forwards_method_body_and_query(monkeypatch):
    _patch_config(monkeypatch)
    captured: dict = {}
    _patch_client(monkeypatch, response=_resp(), captured=captured)
    req = _FakeRequest(method="POST", body=b'{"a":1}', query="page=2")
    await rp._proxy_request(req, "http://up/x")
    assert captured["method"] == "POST"
    assert captured["content"] == b'{"a":1}'
    assert captured["params"] == "page=2"


@pytest.mark.asyncio
async def test_proxy_sends_no_content_for_an_empty_body(monkeypatch):
    _patch_config(monkeypatch)
    captured: dict = {}
    _patch_client(monkeypatch, response=_resp(), captured=captured)
    await rp._proxy_request(_FakeRequest(body=b""), "http://up/x")
    assert captured["content"] is None


@pytest.mark.asyncio
async def test_proxy_strips_hop_by_hop_response_headers(monkeypatch):
    _patch_config(monkeypatch)
    _patch_client(
        monkeypatch,
        response=_resp(
            headers={
                "content-type": "text/plain",
                "transfer-encoding": "chunked",
                "connection": "keep-alive",
                "x-custom": "kept",
            }
        ),
    )
    out = await rp._proxy_request(_FakeRequest(), "http://up/x")
    assert out.headers.get("x-custom") == "kept"
    assert "transfer-encoding" not in out.headers
    assert "connection" not in out.headers


@pytest.mark.asyncio
async def test_proxy_timeout_becomes_504(monkeypatch):
    _patch_config(monkeypatch)
    _patch_client(monkeypatch, exc=httpx.TimeoutException("slow"))
    with pytest.raises(HTTPException) as ei:
        await rp._proxy_request(_FakeRequest(), "http://up/x")
    assert ei.value.status_code == 504


@pytest.mark.asyncio
async def test_proxy_connect_error_becomes_502(monkeypatch):
    _patch_config(monkeypatch)
    _patch_client(monkeypatch, exc=httpx.ConnectError("refused"))
    with pytest.raises(HTTPException) as ei:
        await rp._proxy_request(_FakeRequest(), "http://up/x")
    assert ei.value.status_code == 502


@pytest.mark.asyncio
async def test_proxy_unexpected_error_becomes_502(monkeypatch):
    _patch_config(monkeypatch)
    _patch_client(monkeypatch, exc=RuntimeError("boom"))
    with pytest.raises(HTTPException) as ei:
        await rp._proxy_request(_FakeRequest(), "http://up/x")
    assert ei.value.status_code == 502


# --------------------------------------------------------------------------
# router_proxy endpoint gate
# --------------------------------------------------------------------------


def _patch_admin_config(monkeypatch):
    class _Cfg:
        llm = type(
            "L",
            (),
            {
                "router_base_url": "http://up/v1",
                "router_access_key": "k",
            },
        )()
        admin = type("A", (), {"web_secret": SECRET})()

    monkeypatch.setattr(rp, "get_config", lambda: _Cfg())


@pytest.mark.asyncio
async def test_endpoint_rejects_a_missing_cookie(monkeypatch):
    _patch_admin_config(monkeypatch)
    with pytest.raises(HTTPException) as ei:
        await rp.router_proxy(_FakeRequest(), "dashboard", petro_session=None)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_rejects_a_forged_cookie(monkeypatch):
    _patch_admin_config(monkeypatch)
    forged = _sign(int(time.time()), "attacker-secret")
    with pytest.raises(HTTPException) as ei:
        await rp.router_proxy(_FakeRequest(), "dashboard", petro_session=forged)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_forwards_a_valid_session_to_the_right_url(monkeypatch):
    _patch_admin_config(monkeypatch)
    seen: dict = {}

    async def _fake_proxy(request, target_url):
        seen["target"] = target_url
        return httpx.Response(200, content=b"proxied")

    monkeypatch.setattr(rp, "_proxy_request", _fake_proxy)
    out = await rp.router_proxy(
        _FakeRequest(), "admin/models", petro_session=_sign(int(time.time()))
    )
    assert seen["target"] == "http://up/admin/models"
    assert out.status_code == 200
