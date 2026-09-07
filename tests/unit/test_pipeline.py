"""Unit tests for the conversation pipeline and message routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.constants import (
    AUTO_ALLOWED_TOOLS,
    CHANNEL_EMAIL,
    CHANNEL_TELEGRAM,
    CHANNEL_WHATSAPP,
    MUTATING_TOOLS,
    ApprovalStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeMessage:
    channel: str
    sender_id: str
    text: str
    conversation_id: str
    external_ref: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakePool:
    rows: list[Any] = field(default_factory=list)
    _fetchval: Any = None

    async def fetchval(self, *args: Any, **kwargs: Any) -> Any:
        return self._fetchval

    async def fetch(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self.rows

    async def fetchrow(self, *args: Any, **kwargs: Any) -> Any:
        return self.rows[0] if self.rows else None

    async def execute(self, *args: Any, **kwargs: Any) -> str:
        return "INSERT 0 1"


@dataclass
class FakeRedis:
    _stream_data: dict[str, Any] = field(default_factory=dict)

    async def xadd(self, stream: str, data: dict, **kwargs: Any) -> str:
        return "1-0"

    async def xread(self, streams: dict, **kwargs: Any) -> list:
        return []

    async def eval(self, *args: Any, **kwargs: Any) -> int:
        return 1

    async def ping(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    def test_approval_status_terminal(self):
        assert "approved" in ApprovalStatus.TERMINAL
        assert "rejected" in ApprovalStatus.TERMINAL
        assert "edited" in ApprovalStatus.TERMINAL
        assert "pending" not in ApprovalStatus.TERMINAL

    def test_approval_status_decisions(self):
        assert "approved" in ApprovalStatus.DECISIONS
        assert "rejected" in ApprovalStatus.DECISIONS
        assert "edited" in ApprovalStatus.DECISIONS
        assert "timeout" not in ApprovalStatus.DECISIONS

    def test_channels_are_frozen(self):
        assert CHANNEL_TELEGRAM in {"telegram", "whatsapp", "email"}
        assert CHANNEL_WHATSAPP in {"telegram", "whatsapp", "email"}
        assert CHANNEL_EMAIL in {"telegram", "whatsapp", "email"}

    def test_mutting_tools(self):
        assert "create_quote" in MUTATING_TOOLS
        assert "create_ticket" in MUTATING_TOOLS
        assert "update_customer" in MUTATING_TOOLS

    def test_auto_allowed_tools(self):
        assert "create_ticket" in AUTO_ALLOWED_TOOLS
        assert "create_quote" not in AUTO_ALLOWED_TOOLS


# ---------------------------------------------------------------------------
# FakeMessage tests
# ---------------------------------------------------------------------------


class TestFakeMessage:
    def test_create_message(self):
        msg = FakeMessage(
            channel=CHANNEL_TELEGRAM,
            sender_id="12345",
            text="مرحباً",
            conversation_id="conv-1",
            external_ref="msg-1",
        )
        assert msg.channel == "telegram"
        assert msg.text == "مرحباً"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        msg = FakeMessage(
            channel=CHANNEL_WHATSAPP,
            sender_id="9876",
            text="Hello",
            conversation_id="conv-2",
            external_ref="wa-msg-1",
            metadata={"priority": "high"},
        )
        assert msg.metadata["priority"] == "high"


# ---------------------------------------------------------------------------
# FakePool tests
# ---------------------------------------------------------------------------


class TestFakePool:
    @pytest.mark.asyncio
    async def test_fetchval(self):
        pool = FakePool(_fetchval=42)
        result = await pool.fetchval("SELECT 1")
        assert result == 42

    @pytest.mark.asyncio
    async def test_fetch(self):
        pool = FakePool(rows=[{"id": "1"}, {"id": "2"}])
        rows = await pool.fetch("SELECT * FROM test")
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_execute(self):
        pool = FakePool()
        result = await pool.execute("INSERT INTO test VALUES (1)")
        assert result == "INSERT 0 1"


# ---------------------------------------------------------------------------
# Approval workflow tests
# ---------------------------------------------------------------------------


class TestApprovalWorkflow:
    def test_pending_is_not_terminal(self):
        assert ApprovalStatus.PENDING not in ApprovalStatus.TERMINAL

    def test_timeout_is_terminal(self):
        assert ApprovalStatus.TIMEOUT in ApprovalStatus.TERMINAL

    def test_escalated_is_terminal(self):
        assert ApprovalStatus.ESCALATED in ApprovalStatus.TERMINAL

    def test_cancelled_is_terminal(self):
        assert ApprovalStatus.CANCELLED in ApprovalStatus.TERMINAL

    def test_invalid_status(self):
        assert "bogus" not in ApprovalStatus.DECISIONS
        assert "bogus" not in ApprovalStatus.TERMINAL
