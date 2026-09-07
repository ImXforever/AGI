"""Context builder — assembles prompt context for skill execution.

Extended with long-term memory injection via memory.build_memory_context().
"""

from __future__ import annotations

import time
from typing import Any

from app.config import get_config
from app.logging_setup import get_logger

log = get_logger("app.core.context")


async def build(
    *,
    conversation_id: str,
    customer_id: str,
    channel: str,
    language: str = "ar",
    pg: Any = None,
    memory: Any = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a rich context dict for skill prompt composition.

    Pulls customer profile, conversation history, catalog hints, and
    long-term memory into a single dict consumed by
    ``HermesClient._compose_user_prompt()``.
    """
    t0 = time.perf_counter()
    cfg = get_config()
    ctx: dict[str, Any] = {
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "channel": channel,
        "language": language,
        "currency": cfg.domain.currency,
        "numeral_style": cfg.domain.numeral_style,
        "reply_language_policy": cfg.domain.reply_language_policy,
    }

    if pg is not None:
        from app.core.repository import get_conversation_history, get_customer

        customer = await get_customer(pg, customer_id)
        if customer:
            ctx["customer_name"] = customer.get("display_name", "")
            ctx["customer_channel"] = customer.get("channel", "")
            ctx["customer_tags"] = customer.get("tags", [])
            ctx["customer_lead_score"] = customer.get("lead_score", 0)

        history = await get_conversation_history(pg, conversation_id, limit=10)
        if history:
            ctx["history"] = [
                {"role": m.get("role", "user"), "content": m.get("content", "")} for m in history
            ]

    if memory is not None:
        try:
            build_mem_ctx = getattr(memory, "build_memory_context", None)
            if build_mem_ctx is not None:
                try:
                    user_id = int(customer_id)
                except (ValueError, TypeError):
                    user_id = hash(customer_id) & 0x7FFFFFFF
                query_text = extra.get("query", "") if extra else ""
                mem_ctx = await build_mem_ctx(user_id, query=query_text)
                if mem_ctx:
                    ctx["memory_context"] = mem_ctx
                    log.debug(
                        "memory_context_injected",
                        extra={"action": "build_context", "conversation_id": conversation_id},
                    )
        except Exception:
            log.debug("memory context injection failed", exc_info=True)

    if extra:
        ctx.update(extra)

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    log.debug(
        "context_built",
        extra={
            "action": "build_context",
            "conversation_id": conversation_id,
            "latency_ms": latency_ms,
            "fields": len(ctx),
        },
    )
    return ctx


async def catalog_hints(
    query: str,
    *,
    pg: Any = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search the catalog for relevant items matching the user query.

    Returns a list of lightweight dicts suitable for injection into prompts.
    """
    if pg is None:
        return []

    from app.core.repository import search_catalog

    items = await search_catalog(pg, query, limit=limit)
    hints: list[dict[str, Any]] = []
    for item in items:
        hints.append(
            {
                "sku": item.get("sku", ""),
                "name_ar": item.get("name_ar", ""),
                "name_en": item.get("name_en", ""),
                "unit_price": item.get("unit_price", 0),
                "unit": item.get("unit", ""),
                "category": item.get("category", ""),
            }
        )

    if hints:
        log.debug(
            "catalog_hints_found",
            extra={"action": "catalog_hints", "query": query, "count": len(hints)},
        )

    return hints
