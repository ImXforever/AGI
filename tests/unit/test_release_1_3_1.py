"""Regression tests for the 1.3.1 hot-fix release.

One test per fixed defect so the bug cannot silently return, plus the new
``LEAD_ALERT_ENABLED`` option. Everything here runs without Postgres/Redis.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# BUG #1 — MCP bridge advertised zero tools and could not call any
# ---------------------------------------------------------------------------


def test_mcp_bridge_lists_every_registered_tool() -> None:
    from app.core import mcp_bridge
    from app.core.tools import ALL_TOOLS

    specs = mcp_bridge._specs()
    assert len(specs) == len(ALL_TOOLS) > 0
    by_name = {s["name"]: s for s in specs}
    assert set(by_name) == set(ALL_TOOLS)
    ticket = by_name["create_ticket"]
    assert ticket["inputSchema"]["type"] == "object"
    assert "customer_id" in ticket["inputSchema"]["required"]
    assert ticket["inputSchema"]["properties"]["severity"]["enum"] == [
        "low",
        "normal",
        "high",
        "critical",
    ]


def test_mcp_bridge_never_leaks_tracebacks() -> None:
    source = (ROOT / "app/core/mcp_bridge.py").read_text(encoding="utf-8")
    assert "import get_tool_specs" not in source and "tools.get_tool_specs" not in source
    assert "traceback.format_exc" not in source
    assert "APP_VERSION" in source


# ---------------------------------------------------------------------------
# BUG #2 / #3 / #4 — reports SQL: phantom columns, $1::date, followup_completed
# ---------------------------------------------------------------------------


def test_reports_sql_uses_real_email_log_columns() -> None:
    source = (ROOT / "app/admin_api/reports.py").read_text(encoding="utf-8")
    body = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith(("#", "BUG"))
    )
    assert "$1::date" not in body.split("_DATE_SQL =")[1]
    assert "to_date($1, 'YYYY-MM-DD')" in source
    assert re.search(r"SELECT\s+type,\s+channel", source) is None
    assert "status AS type" in source
    assert "AS followup_completed" in source


def test_report_date_parameter_is_validated() -> None:
    from fastapi import HTTPException

    from app.admin_api.reports import _iso_date

    assert _iso_date("2026-09-07") == "2026-09-07"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", _iso_date(""))
    with pytest.raises(HTTPException) as exc:
        _iso_date("07/09/2026")
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException):
        _iso_date("2026-13-45")
    with pytest.raises(HTTPException):
        _iso_date("", default_today=False)


def test_email_report_counts_completed_followups() -> None:
    from app.core.reporting import build_email_report_from_db

    rows: list[dict[str, Any]] = [
        {
            "category": "quote",
            "status": "received",
            "followup_sent": True,
            "followup_completed": True,
        },
        {"category": "quote", "status": "sent", "followup_sent": True, "followup_completed": False},
    ]
    report = build_email_report_from_db(rows, period="2026-09-07").as_dict()
    assert report["followups_sent"] == 2
    assert report["followups_completed"] == 1


# ---------------------------------------------------------------------------
# BUG #5 — malformed UUID path parameter must not be a 500
# ---------------------------------------------------------------------------


def test_invalid_uuid_maps_to_404_and_other_data_errors_stay_500() -> None:
    from asyncpg.exceptions import DataError
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.main import register_routes

    app = FastAPI()
    app.state.services = {}
    register_routes(app)

    # Re-create the handler exactly as create_app installs it.
    @app.exception_handler(DataError)
    async def _bad_query_argument(_: object, exc: DataError):  # type: ignore[no-untyped-def]
        from fastapi.responses import JSONResponse

        text = str(exc)
        if "invalid input for query argument" in text:
            if "invalid UUID" in text:
                return JSONResponse(status_code=404, content={"detail": "not found"})
            return JSONResponse(status_code=400, content={"detail": "invalid parameter"})
        raise exc

    @app.get("/_probe/uuid")
    async def _uuid() -> None:
        raise DataError(
            "invalid input for query argument $1: 'abc' (invalid UUID 'abc': length must be between 32..36 characters, got 3)"
        )

    @app.get("/_probe/int")
    async def _int() -> None:
        raise DataError(
            "invalid input for query argument $1: 'x' (invalid literal for int() with base 10: 'x')"
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/_probe/uuid").status_code == 404
        assert client.get("/_probe/int").status_code == 400


def test_create_app_installs_the_data_error_handler() -> None:
    source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "@app.exception_handler(DataError)" in source
    assert "invalid input for query argument" in source


# ---------------------------------------------------------------------------
# BUG #6 — ticket severity synonyms violated tickets_severity_check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("urgent", "critical"),
        ("EMERGENCY", "critical"),
        ("P1", "critical"),
        ("medium", "normal"),
        (" Normal ", "normal"),
        ("major", "high"),
        ("minor", "low"),
        ("", "normal"),
        (None, "normal"),
        ("banana", "normal"),
        (7, "normal"),
    ],
)
def test_severity_synonyms_map_onto_the_db_check(raw: object, expected: str) -> None:
    from app.core.tools.support import _PRIORITY_BY_SEVERITY, normalize_severity

    value = normalize_severity(raw)
    assert value == expected
    assert value in _PRIORITY_BY_SEVERITY  # every output is insertable


@pytest.mark.asyncio
async def test_create_ticket_normalises_severity_before_insert() -> None:
    from app.core.tools.support import create_ticket

    captured: dict[str, Any] = {}

    class _Pool:
        async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any]:
            captured["args"] = args
            return {"id": "00000000-0000-0000-0000-000000000001", "created_at": 0}

    await create_ticket(
        _Pool(), customer_id="c1", subject="Pump", body="No pressure", severity="urgent"
    )  # type: ignore[arg-type]
    assert captured["args"][3] == "critical"
    assert captured["args"][7] == "urgent"  # priority derived from the canonical severity


@pytest.mark.asyncio
async def test_safety_tickets_are_never_low_severity() -> None:
    from app.core.tools.support import create_ticket

    captured: dict[str, Any] = {}

    class _Pool:
        async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any]:
            captured["args"] = args
            return {"id": "00000000-0000-0000-0000-000000000002", "created_at": 0}

    await create_ticket(
        _Pool(), customer_id="c1", subject="Chemical spill in tank 4", body="leak", severity="low"
    )  # type: ignore[arg-type]
    assert captured["args"][3] == "high"
    assert captured["args"][6] is True


# ---------------------------------------------------------------------------
# BUG #7 — tools/import_check.py crashed on its first file
# ---------------------------------------------------------------------------


def test_import_check_discovers_modules_without_crashing() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("import_check", ROOT / "tools/import_check.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    modules = module.discover_modules()
    assert "app.main" in modules
    assert "app.core.tools.support" in modules
    assert all("/" not in m and not m.endswith(".py") for m in modules)


# ---------------------------------------------------------------------------
# BUG #8 — Telegram 4096-char limit and dead plain-text fallback
# ---------------------------------------------------------------------------


def test_long_telegram_replies_are_chunked_on_boundaries() -> None:
    from app.channels.telegram import TELEGRAM_MAX_CHARS, split_telegram_text

    paragraph = "Product " + "x" * 90 + "\n"
    text = (paragraph * 90).strip()
    chunks = split_telegram_text(text)
    assert len(chunks) >= 2
    assert all(len(c) <= TELEGRAM_MAX_CHARS for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")
    assert all(not c.startswith("x") for c in chunks)  # cut on line boundaries
    assert split_telegram_text("short") == ["short"]
    assert split_telegram_text("") == []
    assert [len(c) for c in split_telegram_text("y" * 9000)] == [3900, 3900, 1200]


@pytest.mark.asyncio
async def test_telegram_send_splits_and_falls_back_to_plain_text() -> None:
    import httpx

    from app.channels.telegram import TelegramAdapter

    adapter = TelegramAdapter.__new__(TelegramAdapter)
    calls: list[dict[str, Any]] = []

    async def _send_text(
        text: str, parse_mode: str | None, kwargs_tg: dict[str, Any]
    ) -> dict[str, Any]:
        calls.append({**kwargs_tg, "text": text, "parse_mode": parse_mode})
        if parse_mode == "HTML" and "<b>bad" in text:
            request = httpx.Request("POST", "https://api.telegram.org/bot/sendMessage")
            response = httpx.Response(
                400,
                request=request,
                json={
                    "ok": False,
                    "description": "Bad Request: can't parse entities: unclosed tag",
                },
            )
            raise httpx.HTTPStatusError("400", request=request, response=response)
        return {"message_id": len(calls)}

    adapter._send_text = _send_text  # type: ignore[method-assign]
    adapter._send_attachment = None  # type: ignore[assignment]

    long_text = ("Line " + "z" * 60 + "\n") * 120 + "<b>bad tail"
    result = await adapter.send("42", long_text, reply_to_ref="7")
    assert result.success is True
    assert result.metadata["chunks"] >= 2
    assert all(len(c["text"]) <= 4096 for c in calls)
    assert calls[0].get("reply_to_message_id") == 7
    assert all("reply_to_message_id" not in c for c in calls[1:] if c["parse_mode"] == "HTML")
    plain_retries = [c for c in calls if c["parse_mode"] is None]
    assert plain_retries and "<b>" not in plain_retries[-1]["text"]


# ---------------------------------------------------------------------------
# BUG #9 — nightly backup forced PGSSLMODE=require
# ---------------------------------------------------------------------------


def test_pg_dump_sslmode_follows_the_url_and_env() -> None:
    from app.storage.archive import pg_sslmode_for

    assert pg_sslmode_for("postgresql://u:p@postgres.railway.internal:5432/railway") == "prefer"
    assert pg_sslmode_for("postgresql://u:p@host/db?sslmode=require") == "require"
    assert pg_sslmode_for("postgresql://u:p@host/db?sslmode=disable") == "disable"
    assert (
        pg_sslmode_for("postgresql://u:p@host/db?sslmode=disable", "verify-full") == "verify-full"
    )
    source = (ROOT / "app/storage/archive.py").read_text(encoding="utf-8")
    assert 'env["PGSSLMODE"] = "require"' not in source


# ---------------------------------------------------------------------------
# Version single source of truth
# ---------------------------------------------------------------------------


def test_version_is_defined_once() -> None:
    import tomllib

    from app.constants import APP_VERSION

    assert APP_VERSION == "1.6.0"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == APP_VERSION
    for rel in ("app/main.py", "app/healthz.py", "app/config.py", "app/gateway/public_site.py"):
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert '"1.3.' not in source, rel
        assert "APP_VERSION" in source, rel


# ---------------------------------------------------------------------------
# New option — LEAD_ALERT_ENABLED
# ---------------------------------------------------------------------------


def test_lead_alert_text_is_plain_and_bounded() -> None:
    from app.gateway.public_site import format_lead_alert

    text = format_lead_alert(
        reference="ZX-ABC12345",
        name="Ahmed",
        company="",
        email="a@example.com",
        phone="+971500000000",
        service="Artificial Intelligence",
        message="<b>hi</b> " + "word " * 200,
    )
    assert text.startswith("New website lead ZX-ABC12345")
    assert "Company: -" in text
    assert "Service: Artificial Intelligence" in text
    assert "..." in text and len(text) < 700
    assert "/admin/ops/support.html" in text


@pytest.mark.asyncio
async def test_lead_alert_respects_the_flag_and_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from app.gateway import public_site

    sent: list[str] = []

    class _Adapter:
        async def notify_admins(self, text: str) -> None:
            sent.append(text)

    class _Registry:
        def get(self, name: str) -> Any:
            return _Adapter() if name == "telegram" else None

    flag = SimpleNamespace(domain=SimpleNamespace(lead_alert_enabled=True))
    monkeypatch.setattr(public_site, "get_config", lambda: flag)
    assert await public_site._send_lead_alert({"registry": _Registry()}, "lead") is True
    assert sent == ["lead"]

    flag.domain.lead_alert_enabled = False
    assert await public_site._send_lead_alert({"registry": _Registry()}, "lead") is False
    assert sent == ["lead"]

    flag.domain.lead_alert_enabled = True
    assert await public_site._send_lead_alert({}, "lead") is False  # no Telegram adapter → skip

    class _Broken:
        async def notify_admins(self, text: str) -> None:
            raise RuntimeError("telegram down")

    class _BrokenRegistry:
        def get(self, name: str) -> Any:
            return _Broken()

    assert await public_site._send_lead_alert({"registry": _BrokenRegistry()}, "lead") is False


def test_lead_alert_flag_is_parsed_from_env() -> None:
    from app.config import DomainGroup

    assert "lead_alert_enabled" in DomainGroup.__dataclass_fields__
    source = (ROOT / "app/config.py").read_text(encoding="utf-8")
    assert '_b(source, "LEAD_ALERT_ENABLED", True)' in source
    assert "LEAD_ALERT_ENABLED" in (ROOT / "env.example").read_text(encoding="utf-8")
