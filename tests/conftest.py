"""Shared pytest fixtures.

Provides a fully booted application backed by the *real* PostgreSQL and Redis
services, so integration tests exercise the same code path production does —
migrations, schema guard, seeds, RBAC and all.

Tests that need infrastructure are skipped automatically when PostgreSQL or
Redis are unreachable, so the unit suite still runs on a bare checkout.
"""

from __future__ import annotations

import os
import socket
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Environment — must be set before app.config is first imported
# ---------------------------------------------------------------------------

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://Kia-Agent:Kia-Agent_dev@localhost:5432/Kia-Agent_test"
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/9")

_ADMIN_PASSWORD = "IntegrationTestPass123!"


def _host_port(url: str, default_port: int) -> tuple[str, int]:
    tail = url.split("//", 1)[-1]
    if "@" in tail:
        tail = tail.rsplit("@", 1)[1]
    hostport = tail.split("/", 1)[0]
    if ":" in hostport:
        host, _, port = hostport.partition(":")
        return host, int(port)
    return hostport, default_port


def _reachable(url: str, default_port: int) -> bool:
    host, port = _host_port(url, default_port)
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


PG_UP = _reachable(TEST_DB_URL, 5432)
REDIS_UP = _reachable(TEST_REDIS_URL, 6379)
INFRA_UP = PG_UP and REDIS_UP

requires_infra = pytest.mark.skipif(
    not INFRA_UP, reason="PostgreSQL and/or Redis not reachable for integration tests"
)


# ---------------------------------------------------------------------------
# Session setup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def _test_environment() -> Iterator[None]:
    """Point the app at throwaway databases before anything imports config."""
    previous = dict(os.environ)

    os.environ.update(
        {
            "APP_ENV": "test",
            "TENANT_ID": "test-tenant",
            "TENANT_NAME_AR": "شركة اختبار",
            "SUPPORT_CONTACT": "support@test.local",
            "TELEGRAM_BOT_TOKEN": "123456:TEST-token-for-integration-suite",
            "TELEGRAM_ADMIN_IDS": "1",
            "TELEGRAM_WEBHOOK_SECRET": "integration-webhook-secret-0123456789",
            "WHATSAPP_ENABLED": "0",
            "EMAIL_ENABLED": "0",
            "LLM_MODE": "mock",
            "DATABASE_URL": TEST_DB_URL,
            "REDIS_URL": TEST_REDIS_URL,
            "R2_ENDPOINT": "https://example.invalid",
            "R2_ACCESS_KEY_ID": "testkey1234567890",
            "R2_SECRET_ACCESS_KEY": "testsecret1234567890",
            "R2_BUCKET": "test-bucket",
            "ADMIN_USERNAME": "admin",
            "ADMIN_BOOTSTRAP_PASSWORD": _ADMIN_PASSWORD,
            "CURRENCY": "SAR",
            "WEB_SECRET": "integration-web-secret-0123456789abcdef",
            "SCHEMA_GUARD_MODE": "strict",
            "COOKIE_SECURE": "0",
            "BACKUP_ENABLED": "0",
        }
    )

    # Drop any config cached by an earlier import.
    try:
        import app.config as config_mod

        config_mod.config = None  # type: ignore[attr-defined]
    except Exception:
        pass

    yield

    os.environ.clear()
    os.environ.update(previous)


@pytest.fixture(scope="session", autouse=True)
def _create_test_database(_test_environment: None) -> Iterator[None]:
    """Create a dedicated ``Kia-Agent_test`` database for the run."""
    if not PG_UP:
        yield
        return

    import asyncio

    import asyncpg

    name = TEST_DB_URL.rsplit("/", 1)[-1]
    admin_url = TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"

    async def _recreate() -> None:
        conn = await asyncpg.connect(admin_url)
        try:
            await conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1", name
            )
            await conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
            await conn.execute(f'CREATE DATABASE "{name}"')
        finally:
            await conn.close()

    asyncio.run(_recreate())
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def app_instance(_create_test_database: None) -> AsyncIterator[Any]:
    """A booted FastAPI app: migrations applied, schema verified, seeds loaded."""
    if not INFRA_UP:
        pytest.skip("infrastructure unavailable")

    from app.main import bootstrap, create_app, shutdown

    application = create_app()
    await bootstrap(application)
    try:
        yield application
    finally:
        await shutdown(application)


@pytest.fixture
async def client(app_instance: Any) -> AsyncIterator[Any]:
    """HTTPX client bound directly to the ASGI app (no network hop)."""
    import httpx

    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def pool(app_instance: Any) -> Any:
    return app_instance.state.services["pg"]


# ---------------------------------------------------------------------------
# Authenticated clients per role
# ---------------------------------------------------------------------------


async def _login(client: Any, username: str, password: str) -> None:
    resp = await client.post(
        "/admin/api/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, f"login failed for {username}: {resp.text}"


async def _ensure_admin(pool: Any, username: str, role: str, password: str) -> None:
    from app.admin_api.auth import hash_password

    await pool.execute(
        """
        INSERT INTO admins (username, password_hash, role, is_active)
        VALUES ($1, $2, $3, TRUE)
        ON CONFLICT (username) DO UPDATE
            SET role = EXCLUDED.role, password_hash = EXCLUDED.password_hash, is_active = TRUE
        """,
        username,
        hash_password(password),
        role,
    )


def _new_client(app: Any) -> Any:
    import httpx

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _role_client(app: Any, pool: Any, username: str, role: str) -> AsyncIterator[Any]:
    """A dedicated client with its own cookie jar, logged in as `username`.

    Each role gets an independent client so that logging in as one role can
    never clobber the session cookie of another (fixtures share nothing).
    """
    await _ensure_admin(pool, username, role, _ADMIN_PASSWORD)
    async with _new_client(app) as ac:
        await _login(ac, username, _ADMIN_PASSWORD)
        yield ac


@pytest.fixture
async def superadmin_client(app_instance: Any, pool: Any) -> AsyncIterator[Any]:
    async for c in _role_client(app_instance, pool, "it_super", "superadmin"):
        yield c


@pytest.fixture
async def writer_client(app_instance: Any, pool: Any) -> AsyncIterator[Any]:
    async for c in _role_client(app_instance, pool, "it_writer", "admin"):
        yield c


@pytest.fixture
async def viewer_client(app_instance: Any, pool: Any) -> AsyncIterator[Any]:
    async for c in _role_client(app_instance, pool, "it_viewer", "viewer"):
        yield c


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def unique_sku() -> str:
    return f"IT-{uuid.uuid4().hex[:10].upper()}"


@pytest.fixture
async def sample_product(superadmin_client: Any, unique_sku: str) -> dict[str, Any]:
    resp = await superadmin_client.post(
        "/admin/api/catalog/products",
        json={
            "sku": unique_sku,
            "name_ar": "منتج اختبار",
            "name_en": "Test Product",
            "category": "test",
            "unit_price": 42.5,
            "currency": "SAR",
            "stock_qty": 10,
            "reorder_point": 3,
            "is_active": True,
        },
    )
    assert resp.status_code == 200, resp.text
    return {"id": resp.json()["product_id"], "sku": unique_sku}
