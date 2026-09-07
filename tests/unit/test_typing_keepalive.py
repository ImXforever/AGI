"""Typing indicator stays alive until the reply is delivered."""

from __future__ import annotations

import asyncio

import pytest

from app.core.typing_keepalive import typing_keepalive


class _Adapter:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple[str, str]] = []
        self.fail = fail

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        self.calls.append((chat_id, action))
        if self.fail:
            raise RuntimeError("telegram down")


class _NoTyping:
    pass


@pytest.mark.asyncio
async def test_resends_typing_until_exit():
    adapter = _Adapter()
    async with typing_keepalive(adapter, "42", interval=0.02):
        await asyncio.sleep(0.11)
    n = len(adapter.calls)
    assert n >= 3
    assert all(c == ("42", "typing") for c in adapter.calls)
    await asyncio.sleep(0.05)
    assert len(adapter.calls) == n, "background task must stop after the block"


@pytest.mark.asyncio
async def test_first_ping_is_immediate():
    adapter = _Adapter()
    async with typing_keepalive(adapter, "7", interval=10.0):
        await asyncio.sleep(0)
        assert adapter.calls == [("7", "typing")]


@pytest.mark.asyncio
async def test_adapter_errors_never_break_the_reply():
    adapter = _Adapter(fail=True)
    async with typing_keepalive(adapter, "1", interval=0.01):
        await asyncio.sleep(0.03)
    assert adapter.calls


@pytest.mark.asyncio
async def test_noop_without_send_chat_action():
    async with typing_keepalive(_NoTyping(), "1", interval=0.01):
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_exception_inside_block_propagates_and_stops():
    adapter = _Adapter()
    with pytest.raises(ValueError):
        async with typing_keepalive(adapter, "9", interval=0.01):
            raise ValueError("boom")
    n = len(adapter.calls)
    await asyncio.sleep(0.03)
    assert len(adapter.calls) == n
