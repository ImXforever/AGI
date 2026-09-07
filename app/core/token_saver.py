"""Compress noisy tool output before it is sent to the LLM.

Ported from DropAgentX token_saver (9Router/RTK). Pure stdlib. Never raises.
If compression grows the text, or the block looks like credentials, the
original is returned.
"""

from __future__ import annotations

import re
from typing import Any

_MIN_BLOCK_CHARS = 512
_MAX_OUT = 12_000
_PROTECTIVE_MARKERS = ("content-type", "token", "api_key", "password", "secret", "BEGIN ")

_KNOWN_PATTERNS = [
    re.compile(r"^\s*(diff|index -{3}|--- \w+|\+\+\+ \w+)", re.MULTILINE),
    re.compile(r"^\s*(commit \w+|Author:|Date:)\b", re.MULTILINE),
    re.compile(r"^\s*On branch |^\s*master|^\s*main", re.MULTILINE),
    re.compile(r"^\s*(\d+)\s+(passed|failed|ok|error)\b", re.MULTILINE),
    re.compile(r"^\s*\S+/\d+\s+\S+\s+\S+\s+", re.MULTILINE),
    re.compile(r"^\s*(File|Exception|Traceback|  File \")\b", re.MULTILINE),
    re.compile(r"^\s*(Compiling|Building|Downloading|Installing|Collecting)", re.MULTILINE),
]

_EMPTY_LINE = re.compile(r"^\s*$")
_LONG_LINE = re.compile(r"^.{160,}$", re.DOTALL)
_WS_RUN = re.compile(r"[ \t]{3,}")


def _looks_known(text: str) -> bool:
    head = text[:_MIN_BLOCK_CHARS]
    return any(p.search(head) for p in _KNOWN_PATTERNS)


def _compress_block(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    prev = None
    empty_run = 0
    dup_run = 0
    for ln in lines:
        stripped = ln.rstrip()
        if _EMPTY_LINE.match(stripped):
            empty_run += 1
            if empty_run <= 1:
                out.append(stripped)
            continue
        empty_run = 0
        if stripped == prev:
            dup_run += 1
            if dup_run > 2:
                continue
        else:
            dup_run = 0
        prev = stripped
        out.append(stripped)
    return "\n".join(out)


def _trim_long_lines(text: str) -> str:
    if not _LONG_LINE.search(text):
        return text
    lines = []
    for ln in text.splitlines():
        if len(ln) > 300:
            lines.append(ln[:300] + " …")
        else:
            lines.append(ln)
    return "\n".join(lines)


def maybe_compress_tool_output(text: str, max_chars: int = _MAX_OUT) -> str:
    if not text or not isinstance(text, str):
        return text
    if len(text) < _MIN_BLOCK_CHARS:
        return text
    lowered = text.lower()
    if any(m.lower() in lowered for m in _PROTECTIVE_MARKERS):
        return text
    if not _looks_known(text):
        return text
    try:
        candidate = _WS_RUN.sub("  ", _trim_long_lines(_compress_block(text)))
        candidate = candidate[:max_chars]
        if len(candidate) >= len(text):
            return text
        return candidate
    except Exception:
        return text


def compress_tool_outputs(results: list[Any], *, min_chars: int = _MIN_BLOCK_CHARS) -> list[Any]:
    out: list[Any] = []
    for r in results:
        if isinstance(r, str):
            out.append(maybe_compress_tool_output(r))
        elif isinstance(r, dict):
            c = r.get("content")
            if isinstance(c, str) and len(c) >= min_chars:
                r = {**r, "content": maybe_compress_tool_output(c)}
            out.append(r)
        else:
            out.append(r)
    return out
