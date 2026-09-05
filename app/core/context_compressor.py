"""Compress the middle of a long chat trajectory.

Ported from DropAgentX shared.context.context_compressor. Pure and
deterministic — no LLM call. Never raises.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_MIN_TURNS = 4


@dataclass
class CompressResult:
    messages: list
    compressed: bool
    removed_count: int
    removed_tokens_estimate: int


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    latin = sum(1 for c in text if ord(c) < 0x0600)
    other = len(text) - latin
    return latin // 4 + other // 2


def _simple_summary(middle: list, budget_chars: int) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    used = 0
    for m in middle:
        content = str(m.get("content", ""))
        key = content[:80]
        if key in seen:
            continue
        seen.add(key)
        role = m.get("role", "")
        line = f"[{role}] {content}" if role and role != "user" else content
        if used + len(line) + 1 > budget_chars:
            break
        parts.append(line)
        used += len(line) + 1
    return " ".join(parts) if len(parts) > 1 else (parts[0] if parts else "")


def compress_messages(
    messages: list,
    keep_first: int = 3,
    keep_last: int = 3,
    max_messages: int = 40,
    summarizer: Callable[[list], str] | None = None,
    budget_chars: int = 3000,
) -> CompressResult:
    if not messages or len(messages) < max(_MIN_TURNS, keep_first + keep_last + 1):
        return CompressResult(list(messages), False, 0, 0)
    if len(messages) <= max_messages:
        return CompressResult(list(messages), False, 0, 0)
    head = messages[:keep_first]
    tail = messages[-keep_last:]
    middle = messages[keep_first:-keep_last]
    if len(middle) < 2:
        return CompressResult(list(messages), False, 0, 0)
    try:
        summary = summarizer(middle) if summarizer is not None else _simple_summary(middle, budget_chars)
    except Exception:
        summary = _simple_summary(middle, budget_chars)
    removed = len(middle)
    removed_tokens = sum(_estimate_tokens(str(m.get("content", ""))) for m in middle)
    merged = list(head)
    merged.append(
        {
            "role": "user",
            "content": f"[compressed {removed} turns] {summary} — continue from here.",
            "_compressed_summary": True,
        }
    )
    merged.extend(tail)
    return CompressResult(merged, True, removed, removed_tokens)


def assign_token_budget(messages: list[Any], budget_tokens: int) -> list[Any]:
    total = 0
    for m in messages:
        if isinstance(m, dict):
            total += _estimate_tokens(str(m.get("content", "")))
    if total <= budget_tokens:
        return messages
    return compress_messages(
        messages, keep_first=2, keep_last=2, max_messages=max(6, budget_tokens // 20)
    ).messages
