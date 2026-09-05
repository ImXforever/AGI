"""Unit tests for app.core.hitl.fallback (was 0% covered).

The module reaches Postgres via the passed pool and Redis via a lazy
``from app.storage.redis import get_redis`` inside each function, so both are
replaced with recording fakes.
"""

from __future__ import annotations

import dataclasses

import pytest

import app.config as config_mod
from app.constants import EVENT_TIMEOUT, STREAM_EVENTS, ApprovalStatus
from app.core.hitl import fallback as fb

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


class _FakePool:
    def __init__(self):
        self.executed: list[tuple] = []

    async def execute(self, sql, *args):
        self.executed.append((" ".join(sql.split()), args))
        return "UPDATE 1"


class _FakePipeline:
    def __init__(self, owner):
        self.owner = owner

    def hset(self, key, mapping=None):
        self.owner.hsets.append((key, mapping))
        return self

    def set(self, key, value, ex=None):
        self.owner.sets.append((key, value, ex))
        return self

    async def execute(self):
        self.owner.pipelines_executed += 1
        return []


class _FakeRedis:
    def __init__(self):
        self.hsets: list[tuple] = []
        self.sets: list[tuple] = []
        self.xadds: list[tuple] = []
        self.pipelines_executed = 0

    def pipeline(self):
        return _FakePipeline(self)

    async def xadd(self, stream, payload, maxlen=None):
        self.xadds.append((stream, payload, maxlen))
        return "1-0"


@pytest.fixture
def redis(monkeypatch):
    fake = _FakeRedis()
    import app.storage.redis as redis_mod

    async def _get_redis():
        return fake

    monkeypatch.setattr(redis_mod, "get_redis", _get_redis)
    return fake


@pytest.fixture
def pool():
    return _FakePool()


@pytest.fixture
def strategy(monkeypatch):
    """Override cfg.hitl.fallback without touching the real environment."""

    def _set(value):
        cfg = config_mod.get_config()
        new_hitl = dataclasses.replace(cfg.hitl, fallback=value)
        new_cfg = dataclasses.replace(cfg, hitl=new_hitl)
        monkeypatch.setattr(config_mod, "config", new_cfg, raising=False)
        monkeypatch.setattr(config_mod, "get_config", lambda: new_cfg)
        monkeypatch.setattr(fb, "get_config", lambda: new_cfg)
        return new_cfg

    return _set


# --------------------------------------------------------------------------
# Strategy dispatch
# --------------------------------------------------------------------------


async def test_auto_ack_strategy_is_selected(pool, redis, strategy):
    strategy("auto_ack")
    out = await fb.apply_fallback(pool, approval_id="a1", conversation_id="c1", channel="telegram")
    assert out["strategy"] == "auto_ack"
    assert out["status"] == ApprovalStatus.APPROVED


async def test_silent_strategy_is_selected(pool, redis, strategy):
    strategy("silent")
    out = await fb.apply_fallback(pool, approval_id="a1", conversation_id="c1")
    assert out["strategy"] == "silent"
    assert out["status"] == ApprovalStatus.REJECTED


async def test_unknown_strategy_falls_back_to_silent(pool, redis, strategy):
    strategy("silent")  # any non-auto_ack value takes the else branch
    out = await fb.apply_fallback(pool, approval_id="a1", conversation_id="c1")
    assert out["strategy"] == "silent"


# --------------------------------------------------------------------------
# auto_ack
# --------------------------------------------------------------------------


async def test_auto_ack_marks_the_approval_approved_in_postgres(pool, redis):
    await fb._auto_ack(
        pool,
        approval_id="a1",
        conversation_id="c1",
        channel="",
        customer_id="",
        skill="",
        draft_text="",
        now=1000.0,
    )
    sql, args = pool.executed[0]
    assert "UPDATE approvals" in sql
    assert args[0] == ApprovalStatus.APPROVED
    assert args[1] == 1000.0
    assert args[2] == "system:auto_ack"
    assert args[3] == "a1"
    assert "auto-ack fallback (timeout)" in sql


async def test_auto_ack_writes_redis_meta_and_decided_keys(pool, redis):
    await fb._auto_ack(
        pool,
        approval_id="a1",
        conversation_id="c1",
        channel="",
        customer_id="",
        skill="",
        draft_text="",
        now=1.0,
    )
    assert redis.hsets == [
        ("hitl:meta:a1", {"status": ApprovalStatus.APPROVED, "actor": "system:auto_ack"})
    ]
    assert redis.sets == [("hitl:decided:a1", ApprovalStatus.APPROVED, 86400)]
    assert redis.pipelines_executed == 1


async def test_auto_ack_publishes_a_timeout_event(pool, redis):
    await fb._auto_ack(
        pool,
        approval_id="a1",
        conversation_id="c9",
        channel="whatsapp",
        customer_id="",
        skill="",
        draft_text="",
        now=1.0,
    )
    stream, payload, maxlen = redis.xadds[0]
    assert stream == STREAM_EVENTS
    assert payload["type"] == EVENT_TIMEOUT
    assert payload["approval_id"] == "a1"
    assert payload["status"] == ApprovalStatus.APPROVED
    assert payload["strategy"] == "auto_ack"
    assert payload["conversation_id"] == "c9"
    assert payload["channel"] == "whatsapp"
    assert maxlen == 10_000


async def test_auto_ack_delivers_when_draft_and_channel_present(pool, redis, monkeypatch):
    sent = {}

    async def _deliver(*, channel, recipient_id, text, reply_to_ref=None):
        sent.update(channel=channel, recipient_id=recipient_id, text=text)
        return True

    monkeypatch.setattr(fb, "_deliver_fallback_message", _deliver)
    out = await fb._auto_ack(
        pool,
        approval_id="a1",
        conversation_id="c1",
        channel="telegram",
        customer_id="cu7",
        skill="sales",
        draft_text="Your quote is ready.",
        now=1.0,
    )
    assert out["delivered"] is True
    assert sent == {"channel": "telegram", "recipient_id": "cu7", "text": "Your quote is ready."}


async def test_auto_ack_skips_delivery_without_draft_text(pool, redis, monkeypatch):
    called = False

    async def _deliver(**kw):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(fb, "_deliver_fallback_message", _deliver)
    out = await fb._auto_ack(
        pool,
        approval_id="a1",
        conversation_id="c1",
        channel="telegram",
        customer_id="cu7",
        skill="",
        draft_text="",
        now=1.0,
    )
    assert out["delivered"] is False
    assert called is False


async def test_auto_ack_skips_delivery_without_channel(pool, redis, monkeypatch):
    async def _deliver(**kw):
        raise AssertionError("must not deliver without a channel")

    monkeypatch.setattr(fb, "_deliver_fallback_message", _deliver)
    out = await fb._auto_ack(
        pool,
        approval_id="a1",
        conversation_id="c1",
        channel="",
        customer_id="cu7",
        skill="",
        draft_text="draft",
        now=1.0,
    )
    assert out["delivered"] is False


# --------------------------------------------------------------------------
# silent reject
# --------------------------------------------------------------------------


async def test_silent_marks_the_approval_rejected(pool, redis):
    await fb._silent_reject(pool, approval_id="a2", conversation_id="c1", channel="", now=55.0)
    sql, args = pool.executed[0]
    assert args[0] == ApprovalStatus.REJECTED
    assert args[2] == "system:silent"
    assert "silent fallback (timeout)" in sql


async def test_silent_writes_redis_state(pool, redis):
    await fb._silent_reject(pool, approval_id="a2", conversation_id="c1", channel="", now=1.0)
    assert redis.hsets[0][1]["status"] == ApprovalStatus.REJECTED
    assert redis.sets[0] == ("hitl:decided:a2", ApprovalStatus.REJECTED, 86400)


async def test_silent_publishes_a_rejected_timeout_event(pool, redis):
    await fb._silent_reject(pool, approval_id="a2", conversation_id="c3", channel="email", now=1.0)
    _, payload, _ = redis.xadds[0]
    assert payload["strategy"] == "silent"
    assert payload["status"] == ApprovalStatus.REJECTED
    assert payload["channel"] == "email"


async def test_silent_never_reports_delivery(pool, redis):
    out = await fb._silent_reject(
        pool, approval_id="a2", conversation_id="c1", channel="telegram", now=1.0
    )
    assert out["delivered"] is False


async def test_silent_result_echoes_the_approval_id(pool, redis):
    out = await fb._silent_reject(
        pool, approval_id="abc-123", conversation_id="c1", channel="", now=1.0
    )
    assert out["approval_id"] == "abc-123"


# --------------------------------------------------------------------------
# delivery helper
# --------------------------------------------------------------------------


async def test_deliver_returns_true_on_the_best_effort_path():
    assert (
        await fb._deliver_fallback_message(channel="telegram", recipient_id="1", text="hi") is True
    )


async def test_deliver_swallows_import_failure(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _boom(name, *a, **kw):
        if name == "app.channels":
            raise ImportError("channels unavailable")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _boom)
    assert (
        await fb._deliver_fallback_message(channel="telegram", recipient_id="1", text="hi") is False
    )
