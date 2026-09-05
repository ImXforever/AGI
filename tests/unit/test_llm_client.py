"""Unit tests for the LLM client's failover and retry ladder.

`call_with_fallback` is the resilience layer in front of every model call:
it retries a rate-limited model with exponential backoff, walks a failover
chain when a model errors, and returns None once everything is exhausted so
the orchestrator can take the honest-admission path. No network is used —
`_complete_http` is stubbed and `asyncio.sleep` is neutralised so the backoff
ladder runs instantly.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from app.core.llm import LLMClient, _build_model_chain, _ModelStats

pytestmark = pytest.mark.unit


class _Llm:
    mode = "router"
    model_fast = "fast-1"
    model_standard = "std-1"
    router_base_url = "https://router.invalid"
    router_access_key = "k"
    router_timeout = 30
    direct_base_url = "https://direct.invalid"
    direct_api_key = "k"
    direct_model = "direct-1"
    temperature = 0.2


class _Cfg:
    def __init__(self) -> None:
        self.llm = _Llm()


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse the backoff ladder so retries are instant."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> LLMClient:
    monkeypatch.delenv("LLM_FALLBACK_MODELS_FAST", raising=False)
    monkeypatch.delenv("LLM_FALLBACK_MODELS_STD", raising=False)
    return LLMClient(_Cfg())


def http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://router.invalid/v1/chat/completions")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


# ---------------------------------------------------------------------------
# Chain construction
# ---------------------------------------------------------------------------


class TestModelChain:
    def test_an_empty_string_yields_no_models(self):
        assert _build_model_chain("") == []

    def test_entries_are_split_and_trimmed(self):
        assert _build_model_chain(" a , b ,c ") == ["a", "b", "c"]

    def test_blank_entries_are_dropped(self):
        assert _build_model_chain("a,,b,") == ["a", "b"]

    def test_the_primary_model_leads_the_chain(self, client: LLMClient):
        assert client.get_model_chains()["fast"][0] == "fast-1"
        assert client.get_model_chains()["standard"][0] == "std-1"

    def test_env_fallbacks_extend_the_chain(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_FALLBACK_MODELS_FAST", "backup-a,backup-b")
        chain = LLMClient(_Cfg()).get_model_chains()["fast"]
        assert chain == ["fast-1", "backup-a", "backup-b"]

    def test_the_returned_chain_is_a_copy(self, client: LLMClient):
        client.get_model_chains()["fast"].append("mutated")
        assert "mutated" not in client.get_model_chains()["fast"]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestModelStats:
    def test_a_fresh_tracker_is_empty(self):
        assert _ModelStats().snapshot() == {}

    def test_successes_and_failures_are_counted_separately(self):
        stats = _ModelStats()
        stats.record("m", success=True)
        stats.record("m", success=False)
        assert stats.snapshot()["m"] == {"success": 1, "failure": 1, "total": 2}

    def test_models_are_tracked_independently(self):
        stats = _ModelStats()
        stats.record("a", success=True)
        stats.record("b", success=False)
        assert set(stats.snapshot()) == {"a", "b"}

    def test_reset_clears_the_tracker(self):
        stats = _ModelStats()
        stats.record("m", success=True)
        stats.reset()
        assert stats.snapshot() == {}

    def test_the_snapshot_is_a_deep_copy(self):
        stats = _ModelStats()
        stats.record("m", success=True)
        stats.snapshot()["m"]["success"] = 999
        assert stats.snapshot()["m"]["success"] == 1


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------


class TestMockMode:
    @pytest.fixture
    def mock_client(self) -> LLMClient:
        cfg = _Cfg()
        cfg.llm.mode = "mock"
        return LLMClient(cfg)

    async def test_complete_returns_a_canned_answer_without_network(self, mock_client: LLMClient):
        assert await mock_client.complete("sys", "ما هو السعر؟")

    async def test_fallback_also_short_circuits_in_mock_mode(self, mock_client: LLMClient):
        assert await mock_client.call_with_fallback("sys", "hello") is not None

    async def test_health_reports_mock_mode(self, mock_client: LLMClient):
        assert await mock_client.health() == {"ok": True, "mode": "mock"}


# ---------------------------------------------------------------------------
# Failover behaviour
# ---------------------------------------------------------------------------


class TestCallWithFallback:
    async def test_a_successful_first_call_is_returned_directly(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch
    ):
        calls: list[str] = []

        async def ok(**kwargs: Any) -> str:
            calls.append(kwargs["model"])
            return "the answer"

        monkeypatch.setattr(client, "_complete_http", ok)
        assert await client.call_with_fallback("sys", "user") == "the answer"
        assert calls == ["fast-1"]

    async def test_success_is_recorded_in_the_stats(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(client, "_complete_http", lambda **k: _async("ok"))
        await client.call_with_fallback("sys", "user")
        assert client.get_model_stats()["fast-1"]["success"] == 1

    async def test_a_rate_limited_model_is_retried_then_succeeds(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch, no_sleep: None
    ):
        attempts = {"n": 0}

        async def flaky(**kwargs: Any) -> str:
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise http_error(429)
            return "recovered"

        monkeypatch.setattr(client, "_complete_http", flaky)
        assert await client.call_with_fallback("sys", "user") == "recovered"
        assert attempts["n"] == 2

    async def test_backoff_is_awaited_not_blocking(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch
    ):
        """Regression: the retry ladder used a blocking time.sleep(), which
        froze the whole event loop for up to ~28s per call."""
        slept: list[float] = []

        async def record(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(asyncio, "sleep", record)

        async def always_429(**kwargs: Any) -> str:
            raise http_error(429)

        monkeypatch.setattr(client, "_complete_http", always_429)
        await client.call_with_fallback("sys", "user")
        assert slept, "backoff must go through awaitable asyncio.sleep"

    async def test_backoff_grows_exponentially(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch
    ):
        slept: list[float] = []

        async def record(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(asyncio, "sleep", record)

        async def always_429(**kwargs: Any) -> str:
            raise http_error(429)

        monkeypatch.setattr(client, "_complete_http", always_429)
        await client.call_with_fallback("sys", "user")
        assert len(slept) >= 2
        assert slept[1] > slept[0]

    async def test_a_non_429_error_moves_straight_to_the_next_model(
        self, monkeypatch: pytest.MonkeyPatch, no_sleep: None
    ):
        monkeypatch.setenv("LLM_FALLBACK_MODELS_FAST", "backup-1")
        client = LLMClient(_Cfg())
        seen: list[str] = []

        async def fail_first(**kwargs: Any) -> str:
            seen.append(kwargs["model"])
            if kwargs["model"] == "fast-1":
                raise http_error(500)
            return "from backup"

        monkeypatch.setattr(client, "_complete_http", fail_first)
        assert await client.call_with_fallback("sys", "user") == "from backup"
        assert seen == ["fast-1", "backup-1"]

    async def test_an_exhausted_chain_returns_none_for_the_safe_path(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch, no_sleep: None
    ):
        async def always_fail(**kwargs: Any) -> str:
            raise RuntimeError("upstream down")

        monkeypatch.setattr(client, "_complete_http", always_fail)
        assert await client.call_with_fallback("sys", "user") is None

    async def test_an_empty_response_counts_as_a_failure(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch, no_sleep: None
    ):
        monkeypatch.setattr(client, "_complete_http", lambda **k: _async(""))
        assert await client.call_with_fallback("sys", "user") is None
        assert client.get_model_stats()["fast-1"]["failure"] > 0

    async def test_a_429_in_a_plain_exception_message_also_triggers_backoff(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch, no_sleep: None
    ):
        attempts = {"n": 0}

        async def flaky(**kwargs: Any) -> str:
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("429 Too Many Requests")
            return "recovered"

        monkeypatch.setattr(client, "_complete_http", flaky)
        assert await client.call_with_fallback("sys", "user") == "recovered"

    async def test_the_standard_tier_uses_the_standard_chain(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch
    ):
        seen: list[str] = []

        async def ok(**kwargs: Any) -> str:
            seen.append(kwargs["model"])
            return "ok"

        monkeypatch.setattr(client, "_complete_http", ok)
        await client.call_with_fallback("sys", "user", tier="standard")
        assert seen == ["std-1"]

    async def test_failures_are_capped_at_three_attempts_per_model(
        self, client: LLMClient, monkeypatch: pytest.MonkeyPatch, no_sleep: None
    ):
        attempts = {"n": 0}

        async def always_429(**kwargs: Any) -> str:
            attempts["n"] += 1
            raise http_error(429)

        monkeypatch.setattr(client, "_complete_http", always_429)
        await client.call_with_fallback("sys", "user")
        assert attempts["n"] == 3


async def _async(value: Any) -> Any:
    return value


class TestEndpointResolution:
    def test_router_mode_resolves_to_the_router(self, client: LLMClient):
        base, _key = client._resolve_endpoint()
        assert base == "https://router.invalid"

    def test_direct_mode_resolves_to_the_direct_endpoint(self):
        cfg = _Cfg()
        cfg.llm.mode = "direct"
        base, _key = LLMClient(cfg)._resolve_endpoint()
        assert base == "https://direct.invalid"
