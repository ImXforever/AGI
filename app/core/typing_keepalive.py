"""Keep the channel's "typing…" indicator alive while the agent thinks.

Telegram shows the typing bubble for ~5 seconds after each ``sendChatAction``.
A full reply takes 20–60 s (classification → knowledge → model → guards), so a
single action at the start meant the bubble vanished long before the answer
arrived and customers assumed the bot had died and sent the question again.

``typing_keepalive`` re-sends the action every few seconds in a background task
and stops the moment the reply is on its way (or the handler fails). It never
raises — losing the indicator must never lose the reply.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.typing_keepalive")

# Telegram keeps the indicator for ~5 s; refresh a little earlier than that.
DEFAULT_INTERVAL_S = 4.0
# Hard stop so a stuck handler can never keep a chat "typing" forever.
DEFAULT_MAX_S = 180.0


# Give up after this many consecutive transport failures (channel is down).
MAX_CONSECUTIVE_FAILURES = 3


async def _loop(adapter: Any, chat_id: str, action: str, interval: float, max_s: float) -> None:
    elapsed = 0.0
    failures = 0
    while elapsed < max_s:
        try:
            await adapter.send_chat_action(chat_id, action)
            failures = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failures += 1
            log.debug("typing keepalive failed", extra={"action": "typing", "error": str(exc)})
            if failures >= MAX_CONSECUTIVE_FAILURES:
                return
        await asyncio.sleep(interval)
        elapsed += interval


@contextlib.asynccontextmanager
async def typing_keepalive(
    adapter: Any,
    chat_id: str,
    *,
    action: str = "typing",
    interval: float | None = None,
    max_seconds: float | None = None,
) -> AsyncIterator[None]:
    """Async context manager: typing indicator stays on for the whole block.

    Works with any adapter exposing ``send_chat_action(chat_id, action)``;
    adapters without it (email, WhatsApp) simply get a no-op.
    """
    if adapter is None or not chat_id or not hasattr(adapter, "send_chat_action"):
        yield
        return

    every = DEFAULT_INTERVAL_S if interval is None else float(interval)
    limit = DEFAULT_MAX_S if max_seconds is None else float(max_seconds)
    task = asyncio.create_task(
        _loop(adapter, chat_id, action, max(0.01, every), limit),
        name=f"typing:{chat_id}",
    )
    try:
        yield
    finally:
        if not task.done():
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
