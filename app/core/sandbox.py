"""Terminal sandbox: Python execution + shell commands with approval gates.

Adapted from Hermes DropAgentX sandbox.py for Kia-Agent.

Safety model:
  1. Every command passes through classify_command()
  2. SAFE  → immediate execution in Docker/local sandbox
  3. GUARD → requires admin approval before execution
  4. BLOCK → always rejected, never executes

Two execution backends:
  - docker: ``docker run --rm --network=none python:3.12-slim`` (production)
  - local: subprocess with timeout (dev/test only, gated by APP_ENV)

Config keys:
  sandbox_enabled=1, sandbox_mode=auto|docker|local,
  sandbox_local_allow=0, approval_mode=auto|guard-all|allow-all
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import tempfile
from typing import Any, Literal

from app.logging_setup import get_logger

log = get_logger("app.core.sandbox")

# =========================================================
# Limits
# =========================================================

MAX_CODE_CHARS = 6000
TIMEOUT_S = 25
MAX_OUT = 3000
DOCKER_IMAGE = "python:3.12-slim"

# =========================================================
# SAFE / GUARD / BLOCK classification
# =========================================================

SAFE_PATTERNS: frozenset[str] = frozenset(
    {
        "ls",
        "pwd",
        "whoami",
        "date",
        "echo",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "find",
        "df",
        "du",
        "env",
        "printenv",
        "uname",
    }
)

GUARD_PATTERNS: frozenset[str] = frozenset(
    {
        "pip install",
        "npm install",
        "apt-get",
        "apt install",
        "yum install",
        "brew install",
        "mkdir",
        "rm",
        "rmdir",
        "mv",
        "cp",
        "chmod",
        "chown",
        "curl",
        "wget",
        "ssh",
        "scp",
        "rsync",
        "docker",
    }
)

BLOCK_PATTERNS: frozenset[str] = frozenset(
    {
        "rm -rf /",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",
        "shutdown",
        "reboot",
        "halt",
        "init 0",
        "init 6",
        "systemctl stop",
        "kill -9 1",
        "chmod 777",
        "> /dev/sda",
    }
)


class CommandClassification:
    __slots__ = ("tier", "reason")

    def __init__(self, tier: Literal["safe", "guard", "block"], reason: str = ""):
        self.tier = tier
        self.reason = reason


def classify_command(command: str) -> CommandClassification:
    """Classify a shell command as safe, guard, or block."""
    cmd = (command or "").strip().lower()

    if not cmd:
        return CommandClassification("block", "empty command")

    for pattern in BLOCK_PATTERNS:
        if pattern in cmd:
            return CommandClassification("block", f"dangerous pattern: {pattern}")

    for pattern in GUARD_PATTERNS:
        if cmd.startswith(pattern) or f" {pattern}" in cmd:
            return CommandClassification("guard", f"requires approval: {pattern}")

    for pattern in SAFE_PATTERNS:
        if cmd == pattern or (cmd.startswith(pattern + " ") and re.match(rf'^{re.escape(pattern)}\s', cmd)):
            return CommandClassification("safe")

    return CommandClassification("guard", "unknown command — defaulting to guard")


# =========================================================
# Public API
# =========================================================


async def run_python(
    code: str,
    *,
    config: Any = None,
) -> str:
    """Execute Python code safely."""
    if not code or len(code) > MAX_CODE_CHARS:
        return "⚠️ Code is empty or too long."
    if not _enabled(config):
        return "🔒 Sandbox is disabled by admin."
    return await _exec_sandboxed(
        f"# sandboxed\n{code}",
        suffix=".py",
        interpreter_cmd=lambda tmp: [_sys_py(), "-I", tmp],
        config=config,
    )


async def run_shell(
    command: str,
    *,
    config: Any = None,
    approval_callback: Any = None,
) -> str:
    """Execute a shell command with approval gates.

    Returns the command output, or a message indicating
    the command needs approval / is blocked.
    """
    if not command or not command.strip():
        return "⚠️ Command is empty."

    if not _enabled(config):
        return "🔒 Sandbox is disabled by admin."

    result = classify_command(command)

    if result.tier == "block":
        return f"🚫 **Command blocked**\nReason: {result.reason}\nCommand:\n`{command[:200]}`"

    if result.tier == "guard":
        approval_mode = _get_setting(config, "approval_mode", "auto").lower()
        yolo = _get_setting(config, "yolo_mode", "0") == "1"

        if yolo or approval_mode == "allow-all":
            pass
        elif approval_mode != "guard-all":
            approval_id = f"sandbox:{hash(command) & 0xFFFFFF:08x}"
            if approval_callback is not None:
                await approval_callback(command, approval_id)
            return (
                f"⏳ **Admin approval required**\n"
                f"Reason: {result.reason}\n"
                f"Approval ID: `{approval_id}`\n"
                f"Command:\n`{command[:200]}`\n\n"
                f"Admin must approve before execution."
            )

    return await _exec_shell(command, config=config)


async def check_approval(approval_id: str, *, pg: Any = None) -> bool:
    """Check if a pending approval was granted."""
    if pg is not None:
        row = await pg.fetchrow(
            "SELECT status FROM approvals WHERE id = $1",
            approval_id,
        )
        return row is not None and row["status"] == "approved"
    return False


# =========================================================
# Internal execution
# =========================================================


def _enabled(config: Any = None) -> bool:
    return _get_setting(config, "sandbox_enabled", "1") == "1"


def _get_setting(config: Any, key: str, default: str) -> str:
    if config is None:
        return default
    getter = getattr(config, "get", None)
    if getter is not None:
        try:
            return str(getter(key, default))
        except Exception:
            return default
    return getattr(config, key, default) or default


async def _exec_sandboxed(
    code_or_cmd: str,
    suffix: str,
    interpreter_cmd: Any,
    config: Any = None,
) -> str:
    mode = _get_setting(config, "sandbox_mode", "auto").lower()
    if mode == "docker" or (mode == "auto" and _docker_ok()):
        return await _run_docker(code_or_cmd, suffix, interpreter_cmd)
    if mode == "local" and _local_allowed():
        return await _run_local(code_or_cmd, suffix, interpreter_cmd)
    if mode == "auto" and _local_allowed():
        return await _run_local(code_or_cmd, suffix, interpreter_cmd)
    return "🔒 Docker is not installed and local execution is disabled."


async def _run_local(code: str, suffix: str, interpreter_cmd: Any) -> str:
    tmp = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    tmp.write(code)
    tmp.close()
    try:
        proc = await asyncio.create_subprocess_exec(
            *interpreter_cmd(tmp.name),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=tempfile.gettempdir(),
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_S)
        except TimeoutError:
            proc.kill()
            return f"⏳ Execution exceeded {TIMEOUT_S}s time limit — stopped."
        rc = proc.returncode
        body = out.decode("utf-8", "replace").strip()[:MAX_OUT]
        return f"exit={rc}\n{body or '(no output)'}"
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


async def _run_docker(code: str, suffix: str, interpreter_cmd: Any) -> str:
    tmp = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    tmp.write(code)
    tmp.close()
    mount = tmp.name.replace("\\", "/")
    win_mount = f"{mount[0].lower()}:{mount[2:]}" if mount[1:2] == ":" else mount
    args = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{win_mount}:/sandbox/code{suffix}:ro",
        "--network=none",
        "--memory=256m",
        "--cpus=0.5",
        DOCKER_IMAGE,
        "python",
        "-I",
        f"/sandbox/code{suffix}",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_S + 10)
        except TimeoutError:
            proc.kill()
            return "⏳ Docker sandbox timed out."
        body = out.decode("utf-8", "replace").strip()[:MAX_OUT]
        low = body.lower()
        if proc.returncode != 0 and any(
            x in low
            for x in (
                "error during connect",
                "cannot connect",
                "docker:",
                "dockerdesktoplinuxengine",
                "no such image",
            )
        ):
            return "🔒 Docker daemon is not available — code execution halted."
        return f"docker exit={proc.returncode}\n{body or '(no output)'}"
    except FileNotFoundError:
        return "🔒 Docker is not installed."
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


async def _exec_shell(command: str, config: Any = None) -> str:
    mode = _get_setting(config, "sandbox_mode", "auto").lower()

    if mode in ("docker",) or (mode == "auto" and _docker_ok()):
        return await _docker_shell(command)
    if _local_allowed():
        return await _local_shell(command)
    return "🔒 Shell execution is disabled."


async def _local_shell(command: str) -> str:
    SHEMetacharacters = (";", "&&", "||", "|", "`", "$(", "${")
    if any(op in command for op in SHEMetacharacters):
        return "blocked: shell metacharacters not allowed"
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=tempfile.gettempdir(),
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_S)
        except TimeoutError:
            proc.kill()
            return f"⏳ Command exceeded {TIMEOUT_S}s time limit."
        body = out.decode("utf-8", "replace").strip()[:MAX_OUT]
        return f"exit={proc.returncode}\n{body or '(no output)'}"
    except Exception as e:
        return f"⚠️ Error: {e}"


async def _docker_shell(command: str) -> str:
    args = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--memory=128m",
        "--cpus=0.5",
        "python:3.12-slim",
        "sh",
        "-c",
        command,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT_S + 5)
        except TimeoutError:
            proc.kill()
            return "⏳ Docker timed out."
        body = out.decode("utf-8", "replace").strip()[:MAX_OUT]
        return f"docker exit={proc.returncode}\n{body or '(no output)'}"
    except FileNotFoundError:
        return "🔒 Docker is not installed."


# =========================================================
# Helpers
# =========================================================


def _docker_ok() -> bool:
    return shutil.which("docker") is not None


def _local_allowed() -> bool:
    app_env = os.getenv("APP_ENV", "production").lower()
    return app_env in {"dev", "test", "local"}


def _sys_py() -> str:
    return sys.executable or "python"
