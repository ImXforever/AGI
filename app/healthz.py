"""Deep health probe: /healthz reports every dependency the app needs."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])
STARTED_AT = time.time()


async def _check_pg(pool: Any) -> dict[str, Any]:
    if pool is None:
        return {"ok": False, "detail": "pool not initialised"}
    started = time.perf_counter()
    async with pool.acquire() as conn:
        value = await conn.fetchval("SELECT 1")
    return {"ok": value == 1, "latency_ms": round((time.perf_counter() - started) * 1000, 1)}


async def _check_redis(redis: Any) -> dict[str, Any]:
    if redis is None:
        return {"ok": False, "detail": "client not initialised"}
    started = time.perf_counter()
    pong = await redis.ping()
    return {"ok": bool(pong), "latency_ms": round((time.perf_counter() - started) * 1000, 1)}


async def _check_r2(r2: Any) -> dict[str, Any]:
    if r2 is None:
        return {"ok": False, "detail": "client not initialised"}
    started = time.perf_counter()
    exists = await asyncio.to_thread(r2.bucket_exists)
    return {"ok": bool(exists), "latency_ms": round((time.perf_counter() - started) * 1000, 1)}


async def _check_http(
    base_url: str, path: str, headers: dict[str, str] | None = None, timeout: float = 5.0
) -> dict[str, Any]:
    import httpx

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url.rstrip('/')}{path}", headers=headers or {})
        return {
            "ok": response.status_code < 500,
            "status": response.status_code,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except Exception as exc:
        return {
            "ok": False,
            "detail": type(exc).__name__,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }


@router.get("/healthz")
async def healthz(request: Request) -> dict[str, Any]:
    from app.config import config as cfg

    state: dict[str, Any] = getattr(request.app.state, "services", None) or {}
    deep = request.query_params.get("deep", "1") != "0"
    checks: dict[str, Any] = {}

    if deep:
        results = await asyncio.gather(
            _check_pg(state.get("pg")),
            _check_redis(state.get("redis")),
            _check_r2(state.get("r2")),
            return_exceptions=True,
        )
        for name, result in zip(("postgres", "redis", "r2"), results, strict=True):
            payload = result if isinstance(result, dict) else {"ok": False, "detail": str(result)}
            if name == "r2":
                payload = {**payload, "critical": False}
            checks[name] = payload
        if cfg is not None:
            if cfg.llm.hermes_base_url and "http://hermes:3000" not in cfg.llm.hermes_base_url:
                hermes = await _check_http(cfg.llm.hermes_base_url, "/health", timeout=2.0)
                checks["hermes"] = {**hermes, "critical": False}
            else:
                checks["hermes"] = {
                    "ok": True,
                    "critical": False,
                    "detail": f"inline (LLM_MODE={cfg.llm.mode})",
                }
            if cfg.llm.mode == "router":
                checks["router"] = {
                    **await _check_http(cfg.llm.router_base_url.replace("/v1", ""), "/v1/models", timeout=2.0),
                    "critical": False,
                }
            else:
                checks["router"] = {
                    "ok": True,
                    "critical": False,
                    "detail": f"skipped (LLM_MODE={cfg.llm.mode})",
                }

    schema_report = state.get("schema_report")
    if schema_report is not None:
        detail = schema_report.as_dict()
        # Drift is reported but never blocks readiness in warn mode — strict
        # mode already prevented the app from starting at all.
        checks["schema"] = {
            "ok": detail["ok"],
            "critical": detail["mode"] == "strict",
            **detail,
        }

    critical = [check for check in checks.values() if check.get("critical", True)]
    ready = all(check.get("ok") for check in critical) if critical else True
    return {
        "status": "ok" if ready else "degraded",
        "tenant": cfg.tenant.id if cfg else "",
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "ready": ready,
        "checks": checks,
    }


@router.get("/status")
async def root() -> dict[str, str]:
    from app.config import config as cfg

    return {
        "service": "Kia-Agent-app",
        "tenant": cfg.tenant.id if cfg else "",
        "health": "/healthz",
        "public": "/",
        "admin": "/admin/ops/ecosystem.html",
        "ops": "/admin/ops/",
        "agent": "/agent.json",
    }


@router.get("/agent.json")
@router.get("/.well-known/agent.json")
async def agent_card() -> dict[str, Any]:
    """A2A discovery card — DropAgent/radius pattern, Kia identity."""
    from app.config import config as cfg

    tenant = cfg.tenant.id if cfg else "kia"
    return {
        "name": "Kia-Agent",
        "description": "Multi-channel operations agent with human-in-the-loop gates.",
        "url": "/admin/api",
        "version": "20.0.3",
        "provider": {"organization": tenant},
        "capabilities": {
            "streaming": True,
            "hitl": True,
            "channels": ["telegram", "whatsapp", "email", "instagram", "twitter"],
        },
        "authentication": {"schemes": ["Bearer"]},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
    }


@router.get("/buildinfo")
async def buildinfo() -> dict[str, Any]:
    """Static build/uptime facts.

    NOTE: this used to be mounted at /metrics but returned no real metrics.
    Prometheus exposition now lives in app.observability at /metrics.
    """
    return {
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "service": "Kia-Agent-app",
        "version": "20.0.3",
    }


@router.get("/system/info")
async def system_info(request: Request) -> dict[str, Any]:
    """Detailed system information for debugging and monitoring."""
    import sys

    from app.config import config as cfg

    state: dict[str, Any] = getattr(request.app.state, "services", None) or {}

    channels = {}
    if cfg:
        channels = {
            "telegram": bool(cfg.channels.telegram_bot_token),
            "whatsapp": cfg.channels.whatsapp_enabled,
            "email": cfg.channels.email_enabled,
            "instagram": cfg.channels.instagram_enabled,
            "twitter": cfg.channels.twitter_enabled,
        }

    return {
        "version": "20.0.3",
        "python": sys.version.split()[0],
        "tenant": cfg.tenant.id if cfg else "",
        "app_env": cfg.ops.app_env if cfg else "",
        "llm_mode": cfg.llm.mode if cfg else "",
        "channels": channels,
        "modules": {
            "memory": cfg.memory.enabled if cfg else False,
            "fleet": cfg.fleet.enabled if cfg else False,
            "calendar": cfg.calendar.enabled if cfg else False,
            "backup": cfg.ops.backup_enabled if cfg else False,
        },
        "uptime_s": round(time.time() - STARTED_AT, 1),
    }
