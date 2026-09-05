"""Kia-Agent Platform — tools package.

FastAPI router that exposes tool execution endpoints, plus helpers for
running tool sequences from the Hermes skill runner.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.constants import AUTO_ALLOWED_TOOLS, MUTATING_TOOLS
from app.logging_setup import get_logger

log = get_logger("app.core.tools")

router = APIRouter(prefix="/tools", tags=["tools"])

# ---------------------------------------------------------------------------
# Tool registry — aggregate REGISTRY dicts from every tool module
# ---------------------------------------------------------------------------

from app.core.tools.analytics import REGISTRY as _ANALYTICS_REG
from app.core.tools.catalog import REGISTRY as _CATALOG_REG
from app.core.tools.customers import REGISTRY as _CUSTOMERS_REG
from app.core.tools.docs import REGISTRY as _DOCS_REG
from app.core.tools.sales import REGISTRY as _SALES_REG
from app.core.tools.support import REGISTRY as _SUPPORT_REG

TOOLS_BY_SKILL: dict[str, dict[str, dict[str, Any]]] = {}
ALL_TOOLS: dict[str, dict[str, Any]] = {}

for _reg in (_ANALYTICS_REG, _CATALOG_REG, _CUSTOMERS_REG, _DOCS_REG, _SALES_REG, _SUPPORT_REG):
    for tool_name, tool_def in _reg.items():
        ALL_TOOLS[tool_name] = tool_def
        skill = tool_def.get("skill", "general")
        TOOLS_BY_SKILL.setdefault(skill, {})[tool_name] = tool_def

del _reg, _ANALYTICS_REG, _CATALOG_REG, _CUSTOMERS_REG, _DOCS_REG, _SALES_REG, _SUPPORT_REG

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ToolRequest(BaseModel):
    """A single tool invocation request."""

    tool: str = Field(..., description="Registered tool name")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    role: str = Field(default="viewer", description="Caller role for access control")


class ToolSequenceRequest(BaseModel):
    """Execute multiple tools in order. Fails fast on first error unless ``continue_on_error`` is set."""

    steps: list[ToolRequest]
    continue_on_error: bool = False


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------


async def execute_tool(
    request: Request,
    tool_name: str,
    params: dict[str, Any],
    *,
    role: str = "viewer",
) -> dict[str, Any]:
    """Execute a single tool by name.

    Resolves the function from the unified registry, binds the Postgres
    pool from application state, and returns the tool's result dict.
    """
    t0 = time.perf_counter()
    tool_def = ALL_TOOLS.get(tool_name)
    if tool_def is None:
        return {"error": "unknown_tool", "tool": tool_name, "available": sorted(ALL_TOOLS.keys())}

    required_role = tool_def.get("min_role")
    if required_role:
        # Use the canonical ranks from app.admin_api.rbac. The old table lived
        # in app.core.tools.analytics with the vocabulary viewer/editor/admin,
        # which ranked a real "superadmin" at 0 — i.e. below a viewer — so the
        # highest-privilege role was denied every guarded tool.
        from app.admin_api.rbac import has_role

        if not has_role(role, required_role):
            return {"error": "insufficient_role", "required": required_role, "caller": role}

    fn = tool_def["fn"]
    pool = request.app.state.services.get("pg")
    if pool is None:
        return {"error": "database_unavailable"}

    try:
        result = await fn(pool, **params)
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000, 1)
        log.error(
            "tool execution failed",
            extra={
                "action": "execute_tool",
                "tool": tool_name,
                "error": str(exc),
                "latency_ms": latency,
            },
        )
        return {"error": "tool_execution_failed", "tool": tool_name, "detail": str(exc)}

    latency = round((time.perf_counter() - t0) * 1000, 1)
    log.info(
        "tool executed", extra={"action": "execute_tool", "tool": tool_name, "latency_ms": latency}
    )
    return result


async def run_tool_sequence(
    request: Request,
    steps: list[ToolRequest],
    *,
    continue_on_error: bool = False,
    role: str | None = None,
) -> list[dict[str, Any]]:
    """Execute a sequence of tool calls in order.

    If *continue_on_error* is ``True``, errors are recorded in the result
    list but do not abort the remaining steps.
    """
    results: list[dict[str, Any]] = []
    for step in steps:
        result = await execute_tool(
            request,
            step.tool,
            step.params,
            # A session role, when supplied, overrides whatever the payload claims.
            role=role if role is not None else step.role,
        )
        results.append(result)
        if result.get("error") and not continue_on_error:
            break
    return results


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/catalog")
async def tool_catalog(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Return the full tool registry grouped by skill."""
    catalog: dict[str, list[dict[str, Any]]] = {}
    for skill, tools in TOOLS_BY_SKILL.items():
        catalog[skill] = [
            {
                "name": name,
                "description": defn.get("description", ""),
                "mutating": defn.get("mutating", False),
                "approval_required": defn.get("approval_required", False),
                "params": defn.get("params", {}),
            }
            for name, defn in tools.items()
        ]
    return {"total": len(ALL_TOOLS), "by_skill": catalog}


@router.post("/execute")
async def execute_tool_endpoint(
    req: ToolRequest,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Execute a single tool (admin-only endpoint).

    The effective role is taken from the *authenticated session*, never from
    the request body: trusting ``req.role`` let any signed-in viewer escalate
    to superadmin by simply saying so in the JSON payload.
    """
    result = await execute_tool(
        request, req.tool, req.params, role=str(admin.get("role") or "viewer")
    )
    return result


@router.post("/sequence")
async def execute_sequence_endpoint(
    req: ToolSequenceRequest,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Execute a sequence of tool calls (admin-only endpoint)."""
    results = await run_tool_sequence(
        request,
        req.steps,
        continue_on_error=req.continue_on_error,
        role=str(admin.get("role") or "viewer"),
    )
    return {"results": results, "count": len(results)}


@router.get("/mutating")
async def list_mutating_tools(
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    """Return the list of tools that mutate state and require HITL approval."""
    mutating = [
        {
            "name": name,
            "description": ALL_TOOLS[name].get("description", ""),
            "skill": ALL_TOOLS[name].get("skill", ""),
            "approval_required": ALL_TOOLS[name].get("approval_required", name in MUTATING_TOOLS),
        }
        for name in sorted(MUTATING_TOOLS)
        if name in ALL_TOOLS
    ]
    return {"mutating": mutating, "auto_allowed": sorted(AUTO_ALLOWED_TOOLS)}
