"""Secure file operations for AI agents.

Inspired by Hermes Agent's file tools (read_file, write_file, patch, search_files)
with safety guards: path sandboxing, extension allowlists, size limits, and audit log.

All paths are resolved relative to PROJECT_ROOT (env-configurable).
The agent NEVER touches files outside the allowed root.
"""

from __future__ import annotations

import fnmatch
import os
import time
from dataclasses import dataclass

from app.logging_setup import get_logger

logger = get_logger(__name__)


def _root() -> str:
    """Resolve the sandbox root at CALL time, not import time."""
    return os.path.abspath(os.getenv("FILE_TOOLS_ROOT", "."))


ALLOWED_READ_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json",
    ".yaml", ".yml", ".toml", ".md", ".txt", ".csv", ".sql",
    ".env", ".sh", ".bat", ".dockerfile", ".gitignore", ".lock",
    ".cfg", ".ini", ".xml", ".svg", ".mmd",
}
DENIED_READ_PATTERNS = [
    ".env", "credentials", "secret", "token", ".pem", ".key", ".keytab",
    "private_key", "password",
]

MAX_READ_BYTES = 50_000
MAX_WRITE_BYTES = 100_000
MAX_SEARCH_RESULTS = 30


@dataclass
class FileOpResult:
    success: bool
    message: str
    data: dict | None = None
    audit_entry: str = ""


def _audit(action: str, path: str, user_id: int, extra: str = "") -> str:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    return f"[{ts}] uid={user_id} {action} {path} {extra}".strip()


def _safe_resolve(path: str) -> tuple[str, str | None]:
    """Resolve path against the (dynamic) sandbox root, return (resolved, error)."""
    if not path or not path.strip():
        return "", "Empty path"
    root = _root()
    resolved = os.path.abspath(os.path.join(root, path.strip()))
    if not (resolved == root or resolved.startswith(root + os.sep)):
        return "", "Path traversal is blocked"
    return resolved, None


def _is_denied(path: str) -> bool:
    lower = path.lower()
    return any(d in lower for d in DENIED_READ_PATTERNS)


def _check_extension(path: str, allow_write: bool = False) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    if ext in ALLOWED_READ_EXTENSIONS:
        return None
    if allow_write and ext in ALLOWED_READ_EXTENSIONS:
        return None
    if ext == "":
        return None
    if ext not in ALLOWED_READ_EXTENSIONS:
        return f"Extension '{ext}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_READ_EXTENSIONS))}"
    return None


# =========================================================
# read_file
# =========================================================

async def read_file(path: str, line_start: int = 1, line_end: int = 0,
                    user_id: int = 0) -> FileOpResult:
    """Read a file's contents with safety checks."""
    resolved, err = _safe_resolve(path)
    if err:
        return FileOpResult(False, err)

    if _is_denied(resolved):
        return FileOpResult(False, "Sensitive file — reading not allowed.")

    ext_err = _check_extension(resolved)
    if ext_err:
        return FileOpResult(False, ext_err)

    if not os.path.isfile(resolved):
        return FileOpResult(False, f"File not found: {path}")

    file_size = os.path.getsize(resolved)
    if file_size > MAX_READ_BYTES * 3:
        return FileOpResult(False, f"File too large ({file_size:,} bytes)")

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        return FileOpResult(False, f"Read error: {e}")

    total_lines = len(all_lines)
    truncated = False

    line_start = max(line_start, 1)
    if line_end <= 0:
        line_end = total_lines

    selected = all_lines[line_start - 1:line_end]
    raw = "".join(selected)

    if len(raw.encode("utf-8")) > MAX_READ_BYTES:
        truncated = True
        budget_lines = max(1, MAX_READ_BYTES // 80)
        selected = selected[:budget_lines]
        raw = "".join(selected)
        truncated = True

    logger.info("read_file: %s (lines %d-%d of %d)", path, line_start, min(line_end, total_lines), total_lines)

    return FileOpResult(
        True,
        f"File read: {path} (lines {line_start}-{min(line_end, total_lines)} of {total_lines})",
        data={"content": raw, "lines": total_lines, "selected_lines": len(selected), "truncated": truncated},
        audit_entry=_audit("READ", resolved, user_id),
    )


# =========================================================
# write_file
# =========================================================

async def write_file(path: str, content: str, mode: str = "overwrite",
                     user_id: int = 0) -> FileOpResult:
    """Write/create a file. mode: 'overwrite' or 'append'."""
    resolved, err = _safe_resolve(path)
    if err:
        return FileOpResult(False, err)

    if _is_denied(resolved):
        return FileOpResult(False, "Writing to sensitive file is not allowed.")

    ext_err = _check_extension(resolved, allow_write=True)
    if ext_err:
        return FileOpResult(False, ext_err)

    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return FileOpResult(False, f"Content too large ({len(content.encode('utf-8')):,} bytes)")

    os.makedirs(os.path.dirname(resolved), exist_ok=True)

    try:
        file_mode = "w" if mode == "overwrite" else "a"
        existed = os.path.isfile(resolved) and mode == "overwrite"

        with open(resolved, file_mode, encoding="utf-8") as f:
            bytes_written = f.write(content)

        action = "WRITE" if mode == "overwrite" else "APPEND"
        note = "created" if not existed and mode == "overwrite" else ("overwritten" if existed else "appended")
        logger.info("write_file: %s (%s, %d bytes)", path, note, bytes_written)
        return FileOpResult(
            True,
            f"File {note}: {path} ({bytes_written:,} bytes)",
            data={"bytes_written": bytes_written, "path": resolved, "mode": note},
            audit_entry=_audit(action, resolved, user_id, f"({bytes_written}B)"),
        )
    except Exception as e:
        return FileOpResult(False, f"Write error: {e}")


# =========================================================
# patch_file
# =========================================================

async def patch_file(path: str, old: str, new: str, user_id: int = 0,
                     all_occurrences: bool = False) -> FileOpResult:
    """Apply a text patch (find-and-replace). Returns count of replacements."""
    resolved, err = _safe_resolve(path)
    if err:
        return FileOpResult(False, err)

    if not os.path.isfile(resolved):
        return FileOpResult(False, f"File not found: {path}")

    if not old or not new:
        return FileOpResult(False, "old and new cannot be empty")

    if len(old) > 5000 or len(new) > 5000:
        return FileOpResult(False, "Patterns longer than 5000 characters are not allowed")

    try:
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return FileOpResult(False, f"Read error: {e}")

    if old not in content:
        return FileOpResult(False, f"Pattern '{old[:80]}' not found in file.")

    if all_occurrences:
        count = content.count(old)
        new_content = content.replace(old, new)
    else:
        count = 1
        new_content = content.replace(old, new, 1)

    try:
        tmp_path = resolved + f".patch.{int(time.time())}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, resolved)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return FileOpResult(False, f"Patch error: {e}")

    logger.info("patch_file: %s (%d replacements)", path, count)

    return FileOpResult(
        True,
        f"{count} replacement(s) made: {path}",
        data={"replacements": count, "path": resolved},
        audit_entry=_audit("PATCH", resolved, user_id, f"({count} replacements)"),
    )


# =========================================================
# search_files
# =========================================================

async def search_files(pattern: str = "*", content_pattern: str = "",
                       directory: str = ".", max_results: int = 20,
                       user_id: int = 0) -> FileOpResult:
    """Search files by name and/or content."""
    resolved_dir, err = _safe_resolve(directory)
    if err:
        return FileOpResult(False, err)

    if not os.path.isdir(resolved_dir):
        return FileOpResult(False, f"Directory not found: {directory}")

    max_results = min(max_results, MAX_SEARCH_RESULTS)
    results = []

    for root, dirs, files in os.walk(resolved_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("node_modules", "__pycache__", "venv", ".venv", "uploads", "data")]

        for fname in files:
            if len(results) >= max_results:
                break
            if not fnmatch.fnmatch(fname.lower(), pattern.lower()):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, _root())

            if _is_denied(fpath):
                continue

            if content_pattern:
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read(50_000)
                    matches = []
                    for i, line in enumerate(text.splitlines(), 1):
                        if content_pattern.lower() in line.lower():
                            matches.append({"line": i, "text": line.strip()[:120]})
                            if len(matches) >= 3:
                                break
                    if not matches:
                        continue
                    results.append({
                        "path": rel, "size": os.path.getsize(fpath),
                        "matches": matches,
                    })
                except Exception:
                    continue
            else:
                results.append({
                    "path": rel, "size": os.path.getsize(fpath),
                })

    logger.info("search_files: pattern=%s, found=%d", pattern, len(results))

    return FileOpResult(
        True,
        f"{len(results)} file(s) found (pattern: {pattern})",
        data={"results": results},
        audit_entry=_audit("SEARCH", resolved_dir, user_id, f"pattern={pattern}"),
    )


# =========================================================
# Tool specs (OpenAI function-calling format)
# =========================================================

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file within the project sandbox (safe)",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Relative file path"},
            "line_start": {"type": "integer", "description": "Start line (default: 1)"},
            "line_end": {"type": "integer", "description": "End line (default: end of file)"},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write or create a text file",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Relative file path"},
            "content": {"type": "string", "description": "Content to write"},
            "mode": {"type": "string", "enum": ["overwrite", "append"], "description": "Write mode"},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "patch_file",
        "description": "Find-and-replace text in a file (atomic patch)",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "old": {"type": "string", "description": "Original text"},
            "new": {"type": "string", "description": "Replacement text"},
            "all_occurrences": {"type": "boolean", "description": "Replace all occurrences"},
        }, "required": ["path", "old", "new"]},
    }},
    {"type": "function", "function": {
        "name": "search_files",
        "description": "Search files by name or content",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g. *.py)"},
            "content_pattern": {"type": "string", "description": "Content to search for"},
            "directory": {"type": "string", "description": "Directory to search in"},
        }},
    }},
]
