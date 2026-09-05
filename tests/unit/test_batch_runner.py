"""Unit tests for app.core.batch_runner (was 0% covered).

Covers concurrency limiting, per-task and whole-batch timeouts, error
isolation, progress callbacks, result aggregation and the three high-level
helpers (batch_generate / batch_notify / batch_analyze) with a stub LLM.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import batch_runner as br
from app.core.batch_runner import BatchResult, TaskResult, run_batch

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Result dataclasses
# --------------------------------------------------------------------------


async def test_success_rate_empty_batch_does_not_divide_by_zero():
    assert BatchResult(total=0, succeeded=0, failed=0).success_rate == 0


async def test_success_rate_percentage():
    assert BatchResult(total=4, succeeded=3, failed=1).success_rate == 75.0


async def test_summary_lists_totals_and_truncates_errors():
    res = BatchResult(
        total=2,
        succeeded=1,
        failed=1,
        errors=["x" * 300],
        duration=1.25,
    )
    text = res.summary()
    assert "total: 2" in text
    assert "succeeded: 1 (50%)" in text
    assert "duration: 1.2s" in text
    # errors are clipped to 100 chars per line
    assert "x" * 100 in text
    assert "x" * 101 not in text


async def test_summary_omits_error_block_when_clean():
    assert "errors:" not in BatchResult(total=1, succeeded=1, failed=0).summary()


async def test_summary_shows_at_most_five_errors():
    res = BatchResult(total=9, succeeded=0, failed=9, errors=[f"e{i}" for i in range(9)])
    assert res.summary().count("    - ") == 5


async def test_to_dict_shape_and_clipping():
    res = BatchResult(
        total=1,
        succeeded=1,
        failed=0,
        duration=2.345,
        results=[TaskResult(index=0, success=True, result="y" * 500, duration=1.111)],
    )
    d = res.to_dict()
    assert d["total"] == 1 and d["succeeded"] == 1
    assert d["duration"] == 2.35
    assert d["success_rate"] == 100.0
    assert len(d["results"][0]["result"]) == 200
    assert d["results"][0]["duration"] == 1.11


# --------------------------------------------------------------------------
# run_batch core
# --------------------------------------------------------------------------


async def test_empty_task_list_short_circuits():
    res = await run_batch([], lambda i, t: None)
    assert (res.total, res.succeeded, res.failed) == (0, 0, 0)
    assert res.results == []


async def test_all_tasks_succeed_and_keep_their_index():
    async def handler(idx, item):
        return item * 2

    res = await run_batch([1, 2, 3, 4], handler, concurrency=2)
    assert res.total == 4 and res.succeeded == 4 and res.failed == 0
    assert [r.result for r in sorted(res.results, key=lambda r: r.index)] == [2, 4, 6, 8]


async def test_one_failing_task_does_not_kill_the_batch():
    async def handler(idx, item):
        if item == "bad":
            raise ValueError("boom")
        return "ok"

    res = await run_batch(["good", "bad", "good"], handler)
    assert res.succeeded == 2 and res.failed == 1
    assert any("boom" in e for e in res.errors)
    failed = [r for r in res.results if not r.success][0]
    assert failed.index == 1


async def test_error_message_is_truncated_to_300_chars():
    async def handler(idx, item):
        raise ValueError("z" * 1000)

    res = await run_batch([1], handler)
    assert len(res.results[0].error) == 300


async def test_per_task_timeout_is_recorded_as_failure():
    async def handler(idx, item):
        await asyncio.sleep(5)

    res = await run_batch([1], handler, task_timeout=0.05)
    assert res.failed == 1
    assert "timeout 0.05s" in res.results[0].error


async def test_batch_timeout_marks_unfinished_tasks():
    async def handler(idx, item):
        await asyncio.sleep(5)

    res = await run_batch([1, 2, 3], handler, concurrency=3, task_timeout=30, batch_timeout=0.05)
    assert res.failed == 3
    assert all(r.error == "batch timeout" for r in res.results)


async def test_concurrency_semaphore_is_respected():
    live = 0
    peak = 0

    async def handler(idx, item):
        nonlocal live, peak
        live += 1
        peak = max(peak, live)
        await asyncio.sleep(0.02)
        live -= 1
        return idx

    await run_batch(list(range(10)), handler, concurrency=3)
    assert peak <= 3


async def test_progress_callback_fires_once_per_task_with_total():
    seen: list[tuple[int, int]] = []

    async def on_progress(done, total):
        seen.append((done, total))

    async def handler(idx, item):
        return idx

    await run_batch([1, 2, 3], handler, concurrency=1, on_progress=on_progress)
    assert seen == [(1, 3), (2, 3), (3, 3)]


async def test_progress_callback_errors_are_swallowed():
    async def on_progress(done, total):
        raise RuntimeError("callback exploded")

    async def handler(idx, item):
        return idx

    res = await run_batch([1, 2], handler, on_progress=on_progress)
    assert res.succeeded == 2


async def test_progress_callback_also_fires_for_failed_tasks():
    seen: list[int] = []

    async def on_progress(done, total):
        seen.append(done)

    async def handler(idx, item):
        raise ValueError("nope")

    await run_batch([1, 2], handler, concurrency=1, on_progress=on_progress)
    assert seen == [1, 2]


async def test_duration_is_populated():
    async def handler(idx, item):
        await asyncio.sleep(0.01)
        return idx

    res = await run_batch([1], handler)
    assert res.duration > 0
    assert res.results[0].duration > 0


# --------------------------------------------------------------------------
# High-level helpers
# --------------------------------------------------------------------------


class _StubLLM:
    """Minimal stand-in for LLMClient.complete()."""

    def __init__(self, replies=None, fail_on=()):
        self.replies = replies or {}
        self.fail_on = fail_on
        self.calls: list[dict] = []

    async def complete(self, *, system, user, tier, max_tokens, purpose):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "tier": tier,
                "max_tokens": max_tokens,
                "purpose": purpose,
            }
        )
        for needle in self.fail_on:
            if needle in user:
                raise RuntimeError("llm down")
        return self.replies.get(user, f"reply:{user}")


async def test_batch_generate_preserves_prompt_order():
    llm = _StubLLM()
    out = await br.batch_generate(["a", "b", "c"], concurrency=2, llm=llm)
    assert out == ["reply:a", "reply:b", "reply:c"]


async def test_batch_generate_uses_default_system_prompt_and_fast_tier():
    llm = _StubLLM()
    await br.batch_generate(["a"], llm=llm)
    call = llm.calls[0]
    assert call["system"] == "You are a helpful assistant."
    assert call["tier"] == "fast"
    assert call["purpose"] == "batch_generate"


async def test_batch_generate_honours_custom_system_prompt():
    llm = _StubLLM()
    await br.batch_generate(["a"], system_prompt="Be terse.", llm=llm)
    assert llm.calls[0]["system"] == "Be terse."


async def test_batch_generate_substitutes_error_placeholder():
    llm = _StubLLM(fail_on=("b",))
    out = await br.batch_generate(["a", "b"], concurrency=1, llm=llm)
    assert out[0] == "reply:a"
    assert out[1].startswith("[error: ") and "llm down" in out[1]


async def test_batch_notify_sends_to_every_user():
    sent: list[tuple[int, str]] = []

    class _Bot:
        async def send_message(self, uid, message):
            sent.append((uid, message))

    res = await br.batch_notify([1, 2, 3], "hello", _Bot(), concurrency=2)
    assert res.succeeded == 3
    assert sorted(sent) == [(1, "hello"), (2, "hello"), (3, "hello")]


async def test_batch_notify_isolates_a_single_bad_recipient():
    class _Bot:
        async def send_message(self, uid, message):
            if uid == 2:
                raise RuntimeError("blocked by user")

    res = await br.batch_notify([1, 2, 3], "hi", _Bot())
    assert res.succeeded == 2 and res.failed == 1


async def test_batch_analyze_parses_embedded_json():
    llm = _StubLLM()
    llm.replies = {}

    class _JsonLLM(_StubLLM):
        async def complete(self, **kw):
            await super().complete(**kw)
            return 'prose before {"score": 7, "label": "hot"} prose after'

    out = await br.batch_analyze([{"id": 1}], "Rate this", llm=_JsonLLM())
    assert out[0] == {"score": 7, "label": "hot"}


async def test_batch_analyze_falls_back_to_raw_when_no_json():
    class _ProseLLM(_StubLLM):
        async def complete(self, **kw):
            await super().complete(**kw)
            return "no json here at all"

    out = await br.batch_analyze([{"id": 1}], "Rate", llm=_ProseLLM())
    assert out[0]["raw"] == "no json here at all"
    assert "parse_error" not in out[0]


async def test_batch_analyze_flags_malformed_json():
    class _BrokenLLM(_StubLLM):
        async def complete(self, **kw):
            await super().complete(**kw)
            return "{not: valid json,,}"

    out = await br.batch_analyze([{"id": 1}], "Rate", llm=_BrokenLLM())
    assert out[0]["parse_error"] is True


async def test_batch_analyze_keeps_input_order():
    class _EchoLLM(_StubLLM):
        async def complete(self, **kw):
            await super().complete(**kw)
            import json as _json

            payload = _json.loads(kw["user"].split("Data:\n")[1])
            return _json.dumps({"id": payload["id"]})

    items = [{"id": i} for i in range(6)]
    out = await br.batch_analyze(items, "Rate", concurrency=4, llm=_EchoLLM())
    assert [o["id"] for o in out] == list(range(6))
