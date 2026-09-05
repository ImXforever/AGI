"""Kia-Agent Platform — v20 QA + automation entrypoint (final release)."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import ConfigError, as_redacted_dict, get_config, reload_config
from app.logging_setup import get_logger, setup_logging
from app.admin_api.auth import require_admin

log = get_logger("app.main")
ADMIN_DIR = Path(__file__).resolve().parent.parent / "admin"


def register_routes(app: FastAPI) -> FastAPI:
    from app.admin_api import router as admin_router
    from app.core.tools import router as tools_router
    from app.gateway import router as gateway_router
    from app.healthz import router as health_router
    from app.observability import router as observability_router

    app.include_router(health_router)
    app.include_router(observability_router)
    app.include_router(gateway_router)
    app.include_router(admin_router)
    app.include_router(tools_router)

    from app.core.mcp_bridge import router as mcp_router
    app.include_router(mcp_router)

    landing = ADMIN_DIR / "landing.html"

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    async def public_home() -> FileResponse:
        if landing.is_file():
            return FileResponse(landing, media_type="text/html; charset=utf-8")
        return FileResponse(ADMIN_DIR / "index.html", media_type="text/html; charset=utf-8")

    if ADMIN_DIR.is_dir():
        app.mount("/admin", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")
    else:
        log.warning(
            "admin UI directory missing",
            extra={"action": "app.admin_dir_missing", "path": str(ADMIN_DIR)},
        )
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await bootstrap(app)
    yield
    await shutdown(app)


def create_app() -> FastAPI:
    try:
        cfg = get_config()
    except ConfigError as exc:
        raise SystemExit(f"configuration error: {exc}") from exc

    setup_logging(cfg.ops.log_level, json_enabled=cfg.ops.log_json_enabled, tenant_id=cfg.tenant.id)

    app = FastAPI(
        title="Kia-Agent Platform",
        version="20.0.0",
        description="International AI operations platform — v20 QA + automation (final release)",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.cfg = cfg
    app.state.services = {}

    from app.admin_api.gate import AdminGateMiddleware
    from app.observability import RequestContextMiddleware

    app.add_middleware(AdminGateMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_routes(app)

    @app.exception_handler(ConfigError)
    async def _config_error(_: object, exc: ConfigError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "configuration", "detail": str(exc)})

    return app


async def _ensure_memory_tables(pg: Any) -> None:
    """Create memory tables if they don't exist (Hermes-style memory provider)."""
    await pg.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id          SERIAL PRIMARY KEY,
            user_id     BIGINT NOT NULL,
            kind        TEXT NOT NULL DEFAULT 'fact',
            content     TEXT NOT NULL,
            importance  INTEGER NOT NULL DEFAULT 3,
            source      TEXT NOT NULL DEFAULT 'chat',
            dedup_key   TEXT,
            recall_count INTEGER DEFAULT 0,
            last_recalled_at REAL,
            created_at  REAL NOT NULL DEFAULT (extract(epoch from now()))
        )
    """)
    await pg.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_memories_user_id
        ON user_memories (user_id)
    """)
    await pg.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_memories_dedup
        ON user_memories (user_id, dedup_key)
        WHERE dedup_key IS NOT NULL
    """)

    await pg.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id              BIGINT PRIMARY KEY,
            buys_count           INTEGER DEFAULT 0,
            total_spent_credits  INTEGER DEFAULT 0,
            last_categories      TEXT DEFAULT '',
            persona              TEXT DEFAULT '',
            persona_at           REAL,
            interests            TEXT DEFAULT '',
            updated_at           REAL NOT NULL DEFAULT (extract(epoch from now()))
        )
    """)
    log.info("memory tables ensured", extra={"action": "ensure_memory_tables"})


async def bootstrap(app: FastAPI) -> dict[str, Any]:
    cfg = app.state.cfg
    services: dict[str, Any] = app.state.services

    if cfg.ops.bootstrap_mode == "lite":
        log.warning(
            "bootstrap running in lite mode — external services skipped",
            extra={"action": "bootstrap", "mode": "lite"},
        )
        services.setdefault("consumers", [])
        log.info(
            "app ready", extra={"action": "bootstrap", "tenant": cfg.tenant.id, "mode": "lite"}
        )
        return services

    from app.storage.pg import connect_pg, run_migrations
    from app.storage.r2 import R2Archive
    from app.storage.redis import connect_redis, ensure_streams

    services["pg"] = await connect_pg()
    services["redis"] = await connect_redis()
    await ensure_streams()
    services["r2"] = R2Archive()
    try:
        services["r2"].ensure_bucket()
    except Exception as exc:
        log.warning(
            "R2 bucket check failed (non-critical)",
            extra={"action": "bootstrap.r2_skip", "error": str(exc)},
        )
    log.info("storage ready", extra={"action": "bootstrap"})

    await run_migrations()

    # Schema Guard: verify the code/database contract right after migrations,
    # so drift fails loudly at boot instead of as a random HTTP 500 later.
    from app.storage.schema_guard import verify_schema

    schema_report = await verify_schema(services["pg"])
    services["schema_report"] = schema_report
    if not schema_report.ok:
        log.warning(
            "schema drift detected",
            extra={"action": "bootstrap.schema_guard", "violations": schema_report.violation_count},
        )

    from app.storage.seed import load_seeds

    await load_seeds()

    await _ensure_memory_tables(services["pg"])
    log.info("memory tables ready", extra={"action": "bootstrap"})

    try:
        from app.core.identity_rl import init_tables as init_rl_tables
        await init_rl_tables()
        log.info("identity_rl ready")
    except Exception as e:
        log.warning(f"identity_rl init failed: {e}")

    from app.admin_api.auth import ensure_bootstrap_admin
    from app.channels import build_registry
    from app.core.hermes_client import HermesClient
    from app.core.llm import LLMClient

    await ensure_bootstrap_admin(services["pg"], cfg)
    services["llm"] = LLMClient(cfg)
    services["hermes"] = HermesClient(cfg, services["llm"])
    services["registry"] = build_registry(cfg, redis=services["redis"])

    try:
        from app.core.prompt_cache import get_prompt_cache

        services["prompt_cache"] = get_prompt_cache()
        log.info("prompt cache ready", extra={"action": "bootstrap"})
    except Exception:
        log.debug("prompt cache init skipped", extra={"action": "bootstrap"})

    try:
        from app.core import memory as memory_mod

        services["memory"] = memory_mod
        log.info("memory module ready", extra={"action": "bootstrap"})
    except Exception:
        log.debug("memory module init skipped", extra={"action": "bootstrap"})

    try:
        from app.core import fleet as fleet_mod

        services["fleet"] = fleet_mod
        log.info("fleet module ready", extra={"action": "bootstrap"})
    except Exception:
        log.debug("fleet module init skipped", extra={"action": "bootstrap"})

    # Loudly flag webhooks that will accept unauthenticated traffic. These are
    # shared secrets held by Telegram/Meta, so they cannot be auto-generated;
    # an empty value means anyone can POST to the endpoint.
    if not cfg.channels.telegram_webhook_secret:
        log.warning(
            "TELEGRAM_WEBHOOK_SECRET is empty — /tg/webhook accepts "
            "UNAUTHENTICATED requests. Set it and pass the same value as "
            "secret_token to setWebhook.",
            extra={"action": "bootstrap", "channel": "telegram"},
        )
    if cfg.channels.whatsapp_enabled and not cfg.channels.whatsapp_verify_token:
        log.warning(
            "WHATSAPP_VERIFY_TOKEN is empty — the Meta handshake will fail.",
            extra={"action": "bootstrap", "channel": "whatsapp"},
        )

    log.info(
        "brain + channels ready",
        extra={
            "action": "bootstrap",
            "llm_mode": cfg.llm.mode,
            "channels": ",".join(services["registry"].enabled),
        },
    )

    from app.core.hitl.sweeper import start_sweeper
    from app.core.pipeline import start_incoming_consumer
    from app.storage.archive import start_nightly_backup

    services["consumers"] = [
        asyncio.create_task(start_incoming_consumer(app), name="bus-incoming"),
        asyncio.create_task(start_sweeper(app), name="hitl-sweeper"),
        asyncio.create_task(start_nightly_backup(), name="pg-backup"),
    ]

    from app.core.cron_scheduler import get_scheduler

    scheduler = get_scheduler()
    services["cron_scheduler"] = scheduler

    from app.core.ops_jobs import run_calendar_publish, run_daily_report, run_followup_check, run_ops_digest

    async def _daily_report_job() -> None:
        await run_daily_report()

    async def _followup_check_job() -> None:
        await run_followup_check()

    async def _calendar_publish_job() -> None:
        await run_calendar_publish()

    async def _ops_digest_job() -> None:
        await run_ops_digest()

    scheduler.register("daily-report", 86400, _daily_report_job)
    scheduler.register("followup-check", 3600, _followup_check_job)
    scheduler.register("calendar-publish", 300, _calendar_publish_job)
    scheduler.register("ops-digest", 86400, _ops_digest_job)
    await scheduler.start()

    log.info("app ready", extra={"action": "bootstrap", "tenant": cfg.tenant.id})
    return services


async def shutdown(app: FastAPI) -> None:
    services: dict[str, Any] = getattr(app.state, "services", {})
    scheduler = services.get("cron_scheduler")
    if scheduler is not None:
        with contextlib.suppress(Exception):
            await scheduler.stop()
    for task in services.get("consumers", []):
        task.cancel()
    for task in services.get("consumers", []):
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
    for name in ("llm", "hermes", "registry"):
        client = services.get(name)
        closer = getattr(client, "close", None)
        if closer is not None:
            with contextlib.suppress(Exception):
                await closer()
    for name in ("pg", "redis"):
        client = services.get(name)
        if client is not None:
            with contextlib.suppress(Exception):
                await client.aclose() if name == "redis" else await client.close()
    log.info("app stopped", extra={"action": "shutdown"})


app = create_app()


@app.get("/config/snapshot", include_in_schema=False)
async def config_snapshot(
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return as_redacted_dict(get_config())


if __name__ == "__main__":
    import uvicorn

    _cfg = reload_config()
    uvicorn.run("app.main:app", host="0.0.0.0", port=_cfg.admin.web_port, proxy_headers=True)
