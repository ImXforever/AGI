"""
Kia-Agent — MCP Bridge (JSON-RPC 2.0 over HTTP via FastAPI).

Exposes the bot's tool set over the Model Context Protocol so an external
agent harness can call tools the same way the internal pipeline does.

Endpoints:
    POST /mcp         — tools/list, tools/call, initialize
    GET  /mcp/healthz — liveness probe
"""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.admin_api.auth import require_admin
from app.config import get_config
from app.logging_setup import get_logger

log = get_logger("app.core.mcp_bridge")

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _specs() -> list[dict[str, Any]]:
    try:
        from app.core.tools import get_tool_specs

        return get_tool_specs()
    except Exception:
        return []


async def _call_tool(name: str, args: dict[str, Any], user_id: int) -> str:
    from app.core.tools import execute_tool

    return await execute_tool(name, args, user_id)


# ---------------------------------------------------------------------------
# JSON-RPC handler
# ---------------------------------------------------------------------------


@router.post("")
async def handle_rpc(
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin),
) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "parse error"},
                "id": None,
            },
            status_code=400,
        )

    rid = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}

    if method == "tools/list":
        return JSONResponse(
            {"jsonrpc": "2.0", "id": rid, "result": {"tools": _specs()}}
        )

    if method == "initialize":
        cfg = get_config()
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Kia-Agent", "version": getattr(cfg, "version", "20.0")},
                },
            }
        )

    if method == "tools/call":
        tool = params.get("name", "")
        tool_args = params.get("arguments", {})
        uid = int(params.get("user_id", 0) or 0)
        try:
            result = await _call_tool(tool, tool_args, uid)
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {"content": [{"type": "text", "text": result}]},
                }
            )
        except Exception as exc:
            log.exception(
                "mcp.tools.call failed",
                extra={"action": "mcp.tools.call", "tool": tool},
            )
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {
                        "code": -32603,
                        "message": str(exc)[:300],
                        "data": traceback.format_exc()[:1000],
                    },
                }
            )

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": rid,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }
    )


@router.get("/healthz")
async def health() -> JSONResponse:
    return JSONResponse(
        {"ok": True, "service": "kia-agent-mcp", "tools": len(_specs())}
    )
