"""Minimal MCP (Model Context Protocol) client over stdio — no SDK needed.

Configure in data/mcp_servers.json::

    [
      {"name": "fs", "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}
    ]

Tools appear to the AI as ``mcp__<server>__<toolname>``.
"""

from __future__ import annotations

import asyncio
import json
import os

from app.logging_setup import get_logger

log = get_logger("app.core.mcp_lite")

CONFIG_PATH = os.path.join("data", "mcp_servers.json")
_servers: dict[str, dict] = {}   # name -> {"proc": ..., "tools": [...]}
_rpc_counter = 0                 # unique jsonrpc id per request


def _next_id() -> int:
    global _rpc_counter
    _rpc_counter += 1
    return _rpc_counter


def _frame(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


async def _rpc(
    proc: asyncio.subprocess.Process,
    method: str,
    params: dict,
    rpc_id: int,
    timeout: float = 15,
) -> dict:
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(
        _frame({"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}).encode()
    )
    await proc.stdin.drain()
    while True:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout)
        if not line:
            raise RuntimeError(f"MCP {method}: server closed stream")
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("id") == rpc_id:
            if "error" in obj:
                raise RuntimeError(str(obj["error"])[:200])
            return obj.get("result", {})


async def start_servers() -> dict[str, dict]:
    """Spawn configured MCP servers and cache their tool lists."""
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception as exc:
        log.warning("mcp_servers.json parse failed: %s", exc)
        return {}

    for entry in cfg[:5]:
        name = entry.get("name")
        command = entry.get("command")
        if not name or not command:
            continue
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await _rpc(
                proc,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "kia-agent", "version": "20.0"},
                },
                rpc_id=1,
            )
            assert proc.stdin is not None
            proc.stdin.write(
                _frame({"jsonrpc": "2.0", "method": "initialized"}).encode()
            )
            await proc.stdin.drain()

            tools_res = await _rpc(proc, "tools/list", {}, rpc_id=2)
            tools = tools_res.get("tools", [])
            _servers[name] = {"proc": proc, "tools": tools}
            log.info("MCP %s: %d tools", name, len(tools))
        except Exception as exc:
            log.warning("MCP %s failed: %s", name, exc)

    return _servers


def mcp_tool_specs() -> list[dict]:
    specs: list[dict] = []
    for sname, srv in _servers.items():
        for tool in srv["tools"]:
            specs.append({
                "type": "function",
                "function": {
                    "name": f"mcp__{sname}__{tool.get('name', 'tool')}",
                    "description": (tool.get("description") or "")[:300],
                    "parameters": tool.get("inputSchema") or {
                        "type": "object",
                        "properties": {},
                    },
                },
            })
    return specs


async def call_mcp_tool(full_name: str, args: dict) -> str:
    try:
        _, sname, tname = full_name.split("__", 2)
    except ValueError:
        return json.dumps({"error": "bad mcp tool name"})

    srv = _servers.get(sname)
    if not srv:
        return json.dumps({"error": "server not running"})

    try:
        res = await _rpc(
            srv["proc"],
            "tools/call",
            {"name": tname, "arguments": args},
            rpc_id=_next_id(),
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)[:300]})

    content = res.get("content") or []
    text = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    return text[:2000] or json.dumps(res)[:500]


async def stop_servers() -> None:
    """Terminate spawned MCP servers (call on shutdown to avoid zombies)."""
    for name, srv in list(_servers.items()):
        proc = srv.get("proc")
        try:
            if proc and proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
        except Exception as exc:
            log.warning("MCP %s shutdown failed: %s", name, exc)
    _servers.clear()
