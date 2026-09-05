"""Integration tests for app.storage.redis against a live Redis (was 32%).

Covers the event/HITL streams, the SET-NX dedup window, the sliding-window
rate limiter Lua script, and the atomic HITL claim scripts — including the
concurrency guarantees those scripts exist to provide.
"""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from app.constants import STREAM_EVENTS, STREAM_HITL
from app.storage import redis as rs

pytestmark = pytest.mark.integration


@pytest.fixture
async def r(app_instance):
    """Live Redis client (app startup already connected the singleton)."""
    return await rs.get_redis()


@pytest.fixture
def rid() -> str:
    return uuid.uuid4().hex[:12]


@pytest.fixture
async def _cleanup(r):
    keys: list[str] = []
    yield keys
    if keys:
        await r.delete(*keys)


# --------------------------------------------------------------------------
# connection
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_redis_returns_a_live_client(r):
    assert await r.ping() is True


@pytest.mark.asyncio
async def test_get_redis_is_a_singleton(r):
    assert await rs.get_redis() is r


@pytest.mark.asyncio
async def test_ensure_streams_is_idempotent():
    await rs.ensure_streams()
    await rs.ensure_streams()


@pytest.mark.asyncio
async def test_streams_exist_after_ensure(r):
    await rs.ensure_streams()
    assert await r.exists(STREAM_EVENTS)


# --------------------------------------------------------------------------
# _json_dumps
# --------------------------------------------------------------------------


def test_json_dumps_keeps_unicode_readable():
    assert "مرحبا" in rs._json_dumps({"m": "مرحبا"})


def test_json_dumps_falls_back_to_str_for_exotic_types():
    from datetime import datetime

    assert "2026" in rs._json_dumps({"at": datetime(2026, 9, 2)})


def test_json_dumps_handles_nested_structures():
    out = json.loads(rs._json_dumps({"a": [1, {"b": None}]}))
    assert out == {"a": [1, {"b": None}]}


# --------------------------------------------------------------------------
# _load_lua
# --------------------------------------------------------------------------


def test_load_lua_reads_the_script():
    assert "redis.call" in rs._load_lua("counter_window.lua")


def test_load_lua_caches_by_name():
    first = rs._load_lua("counter_window.lua")
    assert rs._load_lua("counter_window.lua") is first
    assert "counter_window.lua" in rs._lua_scripts


def test_load_lua_missing_script_raises():
    with pytest.raises(FileNotFoundError):
        rs._load_lua("no_such_script.lua")


# --------------------------------------------------------------------------
# publish_event
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_event_returns_a_stream_id(rid):
    msg_id = await rs.publish_event("test.event", {"rid": rid})
    assert "-" in msg_id


@pytest.mark.asyncio
async def test_publish_event_writes_type_and_payload(r, rid):
    msg_id = await rs.publish_event("test.event", {"rid": rid, "n": 1})
    entries = await r.xrange(STREAM_EVENTS, min=msg_id, max=msg_id)
    _, fields = entries[0]
    assert fields["type"] == "test.event"
    assert json.loads(fields["payload"])["rid"] == rid
    assert float(fields["ts"]) > 0


@pytest.mark.asyncio
async def test_publish_event_includes_optional_routing_fields(r, rid):
    msg_id = await rs.publish_event("t", {"rid": rid}, conversation_id="conv-1", channel="telegram")
    _, fields = (await r.xrange(STREAM_EVENTS, min=msg_id, max=msg_id))[0]
    assert fields["conversation_id"] == "conv-1"
    assert fields["channel"] == "telegram"


@pytest.mark.asyncio
async def test_publish_event_omits_absent_routing_fields(r, rid):
    msg_id = await rs.publish_event("t", {"rid": rid})
    _, fields = (await r.xrange(STREAM_EVENTS, min=msg_id, max=msg_id))[0]
    assert "conversation_id" not in fields
    assert "channel" not in fields


@pytest.mark.asyncio
async def test_publish_event_serialises_unicode_payloads(r, rid):
    msg_id = await rs.publish_event("t", {"rid": rid, "text": "مرحبا بالعالم"})
    _, fields = (await r.xrange(STREAM_EVENTS, min=msg_id, max=msg_id))[0]
    assert json.loads(fields["payload"])["text"] == "مرحبا بالعالم"


# --------------------------------------------------------------------------
# publish_hitl
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_hitl_returns_a_stream_id(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    assert "-" in await rs.publish_hitl(rid, {"draft": "text"})


@pytest.mark.asyncio
async def test_publish_hitl_writes_the_meta_hash(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {"draft": "d"}, conversation_id="c1", channel="email")
    meta = await rs.get_hitl_meta(rid)
    assert meta["approval_id"] == rid
    assert meta["status"] == "pending"
    assert meta["conversation_id"] == "c1"
    assert meta["channel"] == "email"


@pytest.mark.asyncio
async def test_publish_hitl_sets_an_expiry_window(r, rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {}, timeout_seconds=120)
    ttl = await r.ttl(f"hitl:meta:{rid}")
    assert 0 < ttl <= 180


@pytest.mark.asyncio
async def test_publish_hitl_records_expires_at(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {}, timeout_seconds=300)
    meta = await rs.get_hitl_meta(rid)
    assert float(meta["expires_at"]) - float(meta["created_at"]) == pytest.approx(300, abs=1)


@pytest.mark.asyncio
async def test_publish_hitl_pushes_onto_the_hitl_stream(r, rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    msg_id = await rs.publish_hitl(rid, {"draft": "hello"}, timeout_seconds=60)
    _, fields = (await r.xrange(STREAM_HITL, min=msg_id, max=msg_id))[0]
    assert fields["approval_id"] == rid
    assert fields["timeout_seconds"] == "60"
    assert json.loads(fields["payload"])["draft"] == "hello"


@pytest.mark.asyncio
async def test_get_hitl_meta_returns_none_when_absent():
    assert await rs.get_hitl_meta("definitely-not-a-real-approval") is None


# --------------------------------------------------------------------------
# dedup
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_sighting_is_not_a_duplicate(rid):
    assert await rs.check_dedup("telegram", rid) is False


@pytest.mark.asyncio
async def test_second_sighting_is_a_duplicate(rid):
    await rs.check_dedup("telegram", rid)
    assert await rs.check_dedup("telegram", rid) is True


@pytest.mark.asyncio
async def test_dedup_is_scoped_per_channel(rid):
    await rs.check_dedup("telegram", rid)
    assert await rs.check_dedup("whatsapp", rid) is False


@pytest.mark.asyncio
async def test_dedup_sets_the_requested_ttl(r, rid):
    await rs.check_dedup("telegram", rid, ttl=90)
    from app.constants import KEY_DEDUP

    ttl = await r.ttl(KEY_DEDUP.format(channel="telegram", ext_ref=rid))
    assert 0 < ttl <= 90


@pytest.mark.asyncio
async def test_dedup_survives_concurrent_callers(rid):
    """Exactly one of N concurrent callers may see a non-duplicate."""
    results = await asyncio.gather(*[rs.check_dedup("tg", rid) for _ in range(10)])
    assert results.count(False) == 1


# --------------------------------------------------------------------------
# rate limiting
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_request_is_allowed(rid):
    allowed, remaining, retry_after = await rs.check_rate_limit("tg", rid, limit=3)
    assert allowed is True
    assert remaining == 2
    assert retry_after == 0


@pytest.mark.asyncio
async def test_remaining_decreases_per_request(rid):
    await rs.check_rate_limit("tg", rid, limit=5)
    _, remaining, _ = await rs.check_rate_limit("tg", rid, limit=5)
    assert remaining == 3


@pytest.mark.asyncio
async def test_requests_beyond_the_limit_are_denied(rid):
    for _ in range(3):
        await rs.check_rate_limit("tg", rid, limit=3)
    allowed, remaining, retry_after = await rs.check_rate_limit("tg", rid, limit=3)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_rate_limit_is_scoped_per_key(rid):
    for _ in range(3):
        await rs.check_rate_limit("tg", rid, limit=3)
    allowed, _, _ = await rs.check_rate_limit("tg", rid + "-other", limit=3)
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_is_scoped_per_channel(rid):
    for _ in range(3):
        await rs.check_rate_limit("tg", rid, limit=3)
    allowed, _, _ = await rs.check_rate_limit("wa", rid, limit=3)
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_window_expires(r, rid):
    await rs.check_rate_limit("tg", rid, window=1, limit=1)
    denied, _, _ = await rs.check_rate_limit("tg", rid, window=1, limit=1)
    assert denied is False
    await asyncio.sleep(1.2)
    allowed, _, _ = await rs.check_rate_limit("tg", rid, window=1, limit=1)
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limit_is_atomic_under_concurrency(rid):
    """The Lua script must never allow more than `limit` through.

    Kept below the client pool ceiling (max_connections=20) so the test
    exercises the script's atomicity rather than connection exhaustion.
    """
    results = await asyncio.gather(*[rs.check_rate_limit("tg", rid, limit=5) for _ in range(15)])
    assert sum(1 for allowed, _, _ in results if allowed) == 5


# --------------------------------------------------------------------------
# HITL atomic claims
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_claim_succeeds_once(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {})
    assert await rs.hitl_timeout_claim(rid) is True


@pytest.mark.asyncio
async def test_timeout_claim_is_not_repeatable(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {})
    await rs.hitl_timeout_claim(rid)
    assert await rs.hitl_timeout_claim(rid) is False


@pytest.mark.asyncio
async def test_timeout_claim_updates_the_status(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {})
    await rs.hitl_timeout_claim(rid)
    assert (await rs.get_hitl_meta(rid))["status"] == "timeout"


@pytest.mark.asyncio
async def test_timeout_claim_on_an_unknown_item_fails(rid):
    assert await rs.hitl_timeout_claim(f"missing-{rid}") is False


@pytest.mark.asyncio
async def test_only_one_concurrent_timeout_claim_wins(rid, _cleanup):
    _cleanup.append(f"hitl:meta:{rid}")
    await rs.publish_hitl(rid, {})
    results = await asyncio.gather(*[rs.hitl_timeout_claim(rid) for _ in range(10)])
    assert results.count(True) == 1


@pytest.mark.asyncio
async def test_decision_claim_applies_the_status(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    assert await rs.hitl_claim_decision(rid, status="approved", actor="alice") is True
    meta = await rs.get_hitl_meta(rid)
    assert meta["status"] == "approved"
    assert meta["actor"] == "alice"


@pytest.mark.asyncio
async def test_decision_claim_is_not_repeatable(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    await rs.hitl_claim_decision(rid, status="approved", actor="alice")
    assert await rs.hitl_claim_decision(rid, status="rejected", actor="bob") is False


@pytest.mark.asyncio
async def test_decision_claim_preserves_the_first_decision(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    await rs.hitl_claim_decision(rid, status="approved", actor="alice")
    await rs.hitl_claim_decision(rid, status="rejected", actor="bob")
    assert (await rs.get_hitl_meta(rid))["status"] == "approved"


@pytest.mark.asyncio
async def test_decision_claim_stores_an_edited_payload(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    await rs.hitl_claim_decision(
        rid,
        status="approved",
        actor="alice",
        edited_payload={"text": "نسخهٔ ویرایش‌شده"},
        note="tidied up",
    )
    meta = await rs.get_hitl_meta(rid)
    assert "نسخهٔ ویرایش‌شده" in meta.get("edited_payload", "")
    assert meta.get("note") == "tidied up"


@pytest.mark.asyncio
async def test_decision_claim_on_an_unknown_item_fails(rid):
    assert await rs.hitl_claim_decision(f"missing-{rid}", status="approved", actor="a") is False


@pytest.mark.asyncio
async def test_only_one_concurrent_decision_wins(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    results = await asyncio.gather(
        *[rs.hitl_claim_decision(rid, status="approved", actor=f"actor{i}") for i in range(10)]
    )
    assert results.count(True) == 1


@pytest.mark.asyncio
async def test_a_timed_out_item_cannot_then_be_decided(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    await rs.hitl_timeout_claim(rid)
    assert await rs.hitl_claim_decision(rid, status="approved", actor="a") is False


@pytest.mark.asyncio
async def test_a_decided_item_cannot_then_time_out(rid, _cleanup):
    _cleanup.extend([f"hitl:meta:{rid}", f"hitl:decided:{rid}"])
    await rs.publish_hitl(rid, {})
    await rs.hitl_claim_decision(rid, status="approved", actor="a")
    assert await rs.hitl_timeout_claim(rid) is False
