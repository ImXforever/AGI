"""
Zenovix-Agent — MCP Bridge (JSON-RPC 2.0 over HTTP via FastAPI).

Exposes the bot's tool set over the Model Context Protocol so an external
agent harness can call tools the same way the internal pipeline does.

Endpoints:
    POST /mcp         — tools/list, tools/call, initialize
    GET  /mcp/healthz — liveness probe
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.admin_api.auth import require_admin
from app.config import get_config
from app.constants import APP_VERSION
from app.logging_setup import get_logger

log = get_logger("app.core.mcp_bridge")

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_schema(params: dict[str, Any]) -> dict[str, Any]:
    """Translate the registry's light param spec into a JSON-Schema object."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for name, spec in (params or {}).items():
        spec = spec if isinstance(spec, dict) else {}
        prop: dict[str, Any] = {"type": str(spec.get("type", "string"))}
        if "default" in spec:
            prop["default"] = spec["default"]
        if spec.get("description"):
            prop["description"] = str(spec["description"])
        if isinstance(spec.get("enum"), list):
            prop["enum"] = list(spec["enum"])
        props[name] = prop
        if spec.get("required"):
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def _specs() -> list[dict[str, Any]]:
    """MCP ``tools/list`` payload built from the unified tool registry.

    BUG #1 (1.3.1): this imported a non-existent ``get_tool_specs`` and the
    bare ``except`` turned the ImportError into an empty list — the bridge
    advertised 0 tools forever and ``tools/call`` used a signature that
    ``execute_tool`` never had.
    """
    from app.core.tools import ALL_TOOLS

    specs: list[dict[str, Any]] = []
    for name, tool_def in sorted(ALL_TOOLS.items()):
        specs.append(
            {
                "name": name,
                "description": str(tool_def.get("description", "")),
                "inputSchema": _json_schema(tool_def.get("params") or {}),
                "annotations": {
                    "skill": tool_def.get("skill", "general"),
                    "mutating": bool(tool_def.get("mutating", False)),
                },
            }
        )
    return specs


async def _call_tool(request: Request, name: str, args: dict[str, Any], role: str) -> str:
    """Run one registry tool with the caller's *admin* role (never a raw user_id)."""
    import json

    from app.core.tools import execute_tool

    result = await execute_tool(request, name, dict(args or {}), role=role)
    return json.dumps(result, ensure_ascii=False, default=str)


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
        return JSONResponse({"jsonrpc": "2.0", "id": rid, "result": {"tools": _specs()}})

    if method == "initialize":
        cfg = get_config()
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Zenovix-Agent", "version": APP_VERSION},
                },
            }
        )

    if method == "tools/call":
        tool = str(params.get("name", ""))
        tool_args = params.get("arguments") or {}
        if not isinstance(tool_args, dict):
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {"code": -32602, "message": "arguments must be an object"},
                }
            )
        role = str(_admin.get("role") or "viewer")
        try:
            result = await _call_tool(request, tool, tool_args, role)
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
    return JSONResponse({"ok": True, "service": "zenovix-agent-mcp", "tools": len(_specs())})
