"""Prompt cache optimizer — cost savings via stable prefix caching.

Core insight: system prompt + compressed history must form a STABLE PREFIX
across API calls so the LLM provider caches expensive prefix computation
and only reprocesses the delta (new user message).

Tracks hit/miss rate and estimates token savings across conversations.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.prompt_cache")

COMPRESS_THRESHOLD = 8
KEEP_RECENT = 4
MAX_SUMMARY_CHARS = 1500
MAX_CONTEXT_CHARS = 6000


class PromptCache:
    def __init__(self) -> None:
        self._prev_prefix_hash: str | None = None
        self._hits: int = 0
        self._misses: int = 0
        self._total_tokens_saved: int = 0

    def build(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        user_text: str,
        compress_callback: Any = None,
    ) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if len(history) > COMPRESS_THRESHOLD:
            old_turns = history[:-KEEP_RECENT]
            recent_turns = history[-KEEP_RECENT:]
            if compress_callback:
                summary = compress_callback(old_turns)
            else:
                summary = self._compact(old_turns)
            if summary:
                msgs.append(
                    {"role": "system", "content": f"[گفتگوهای قبلی — خلاصه‌سازی خودکار]\n{summary}"}
                )
            msgs.extend(recent_turns)
        elif history:
            msgs.extend(history)

        msgs.append({"role": "user", "content": user_text})
        return self._enforce_budget(msgs)

    def track(self, messages: list[dict[str, str]]) -> None:
        if len(messages) < 2:
            return
        prefix_msgs = messages[:-1]
        try:
            prefix = json.dumps(
                [{"role": m["role"], "content": m["content"][:200]} for m in prefix_msgs],
                ensure_ascii=False,
            )
        except Exception:
            return
        h = hashlib.sha256(prefix.encode("utf-8")).hexdigest()[:16]
        if h == self._prev_prefix_hash:
            self._hits += 1
            prefix_chars = sum(len(m.get("content", "")) for m in prefix_msgs)
            self._total_tokens_saved += prefix_chars // 2
        else:
            self._misses += 1
        self._prev_prefix_hash = h

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": f"{rate:.1f}%",
            "est_tokens_saved": self._total_tokens_saved,
        }

    def reset(self) -> None:
        self._prev_prefix_hash = None
        self._hits = 0
        self._misses = 0
        self._total_tokens_saved = 0

    def _compact(self, turns: list[dict[str, str]]) -> str:
        lines = []
        for t in turns:
            role = "👤" if t.get("role") == "user" else "🤖"
            content = (t.get("content") or "")[:200]
            if content and t.get("role") in ("user", "assistant"):
                lines.append(f"{role} {content}")
        joined = "\n".join(lines)
        if len(joined) > MAX_SUMMARY_CHARS:
            joined = "...\n" + joined[-(MAX_SUMMARY_CHARS - 4) :]
        return joined

    def _enforce_budget(self, msgs: list[dict[str, str]]) -> list[dict[str, str]]:
        total = sum(len(m.get("content", "")) for m in msgs)
        if total <= MAX_CONTEXT_CHARS:
            return msgs
        budget = MAX_CONTEXT_CHARS - len(msgs[0].get("content", "")) - 200
        if budget <= 0:
            return [msgs[0], msgs[-1]]
        system = msgs[:1]
        user = msgs[-1:]
        middle = msgs[1:-1]
        if len(middle) > 1:
            summary = middle[0]
            recent = middle[1:]
            summary_budget = max(400, budget - sum(len(m.get("content", "")) for m in recent) - 200)
            content = summary.get("content", "")
            if len(content) > summary_budget:
                summary = {**summary, "content": content[:summary_budget] + "…"}
            return system + [summary] + recent[-KEEP_RECENT:] + user
        return system + middle + user


_cache = PromptCache()


def get_prompt_cache() -> PromptCache:
    return _cache


def reset_prompt_cache() -> PromptCache:
    _cache.reset()
    return _cache


def add_anthropic_cache_markers(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    result = []
    for i, msg in enumerate(messages):
        enriched: dict[str, Any] = dict(msg)
        if (
            i == 0
            and msg.get("role") == "system"
            or i > 0
            and msg.get("role") == "system"
            and "خلاصه" in msg.get("content", "")
        ):
            enriched["cache_control"] = {"type": "ephemeral"}
        result.append(enriched)
    return result


def estimate_savings(
    cache_stats: dict[str, Any], cost_per_1k_input: float = 0.003
) -> dict[str, Any]:
    hits = cache_stats.get("hits", 0)
    saved_tokens = cache_stats.get("est_tokens_saved", 0)
    if hits == 0:
        return {"cache_hits": 0, "tokens_saved": 0, "estimated_savings_usd": 0}
    cost_without = hits * saved_tokens / 1000 * cost_per_1k_input
    cost_with = hits * saved_tokens / 1000 * cost_per_1k_input * 0.10
    savings = cost_without - cost_with
    return {
        "cache_hits": hits,
        "tokens_saved": saved_tokens,
        "estimated_savings_usd": round(savings, 4),
    }
