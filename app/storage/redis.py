"""Redis storage: connection, streams, dedup, rate-limiting."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, cast

import redis.asyncio as aioredis  # type: ignore[import-untyped]

from app.config import get_config
from app.constants import (
    GROUP_EVENTS,
    GROUP_HITL,
    KEY_DEDUP,
    KEY_RATE_LIMIT,
    STREAM_EVENTS,
    STREAM_HITL,
)
from app.logging_setup import get_logger

log = get_logger(__name__)

_pool: aioredis.Redis | None = None

_LUA_DIR = Path(__file__).resolve().parent / "lua"
_lua_scripts: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


async def connect_redis() -> aioredis.Redis:
    """Create and return a redis.asyncio client (singleton)."""
    global _pool
    if _pool is not None:
        try:
            await _pool.ping()
            return _pool
        except Exception:
            log.warning("redis_reconnect_stale", extra={"action": "redis_connect"})

    cfg = get_config()
    log.info("connecting_to_redis", extra={"action": "redis_connect"})

    _pool = aioredis.from_url(
        cfg.storage.redis_url,
        decode_responses=True,
        max_connections=20,
        socket_connect_timeout=5,
        # Must exceed the longest blocking read (XREADGROUP BLOCK 5000ms),
        # otherwise the stream consumers die with a spurious read timeout.
        socket_timeout=30,
        socket_keepalive=True,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    await _pool.ping()
    log.info("redis_connected", extra={"action": "redis_connect"})
    return _pool


async def get_redis() -> aioredis.Redis:
    """Return the existing client or create one."""
    global _pool
    if _pool is None:
        return await connect_redis()
    return _pool


async def close_redis() -> None:
    """Gracefully close the Redis connection."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        log.info("redis_closed", extra={"action": "redis_close"})
    _pool = None


# ---------------------------------------------------------------------------
# Stream setup
# ---------------------------------------------------------------------------


async def ensure_streams() -> None:
    """Create the HITL and events streams and their consumer groups.

    XGROUP CREATE is idempotent when MKSTREAM is used and the group already
    exists — Redis will raise ``-BUSYGROUP`` which we silently ignore.
    """
    r = await get_redis()

    for stream, group in (
        (STREAM_HITL, GROUP_HITL),
        (STREAM_EVENTS, GROUP_EVENTS),
    ):
        try:
            await r.xgroup_create(stream, group, id="0", mkstream=True)
            log.info(
                "stream_group_created",
                extra={"action": "ensure_streams", "stream": stream, "group": group},
            )
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                log.debug(
                    "stream_group_exists",
                    extra={"action": "ensure_streams", "stream": stream, "group": group},
                )
            else:
                raise


# ---------------------------------------------------------------------------
# Event publishing
# ---------------------------------------------------------------------------


async def publish_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    conversation_id: str | None = None,
    channel: str | None = None,
) -> str:
    """Publish an event onto the ``bus:events`` stream.

    Returns the message ID assigned by Redis.
    """
    r = await get_redis()
    message: dict[str, Any] = {
        "type": event_type,
        "payload": _json_dumps(payload),
        "ts": f"{time.time():.3f}",
    }
    if conversation_id:
        message["conversation_id"] = conversation_id
    if channel:
        message["channel"] = channel

    msg_id = str(
        await r.xadd(
            cast("str", STREAM_EVENTS), cast("Any", message), maxlen=10_000, approximate=True
        )
    )
    log.debug(
        "event_published",
        extra={
            "action": "publish_event",
            "event_type": event_type,
            "stream": STREAM_EVENTS,
            "msg_id": msg_id,
            "conversation_id": conversation_id,
        },
    )
    return msg_id


async def publish_hitl(
    approval_id: str,
    payload: dict[str, Any],
    *,
    conversation_id: str | None = None,
    channel: str | None = None,
    timeout_seconds: int = 600,
) -> str:
    """Push a HITL approval request onto the ``hitl:queue`` stream.

    Also sets the metadata key used by the Lua scripts for atomic
    claim/decision logic.
    """

    r = await get_redis()

    now = time.time()

    meta_key = f"hitl:meta:{approval_id}"
    pipe = r.pipeline()
    pipe.hset(
        meta_key,
        mapping={
            "approval_id": approval_id,
            "status": "pending",
            "created_at": f"{now:.3f}",
            "expires_at": f"{now + timeout_seconds:.3f}",
            "conversation_id": conversation_id or "",
            "channel": channel or "",
        },
    )
    pipe.expire(meta_key, timeout_seconds + 60)
    await pipe.execute()

    message: dict[str, Any] = {
        "approval_id": approval_id,
        "payload": _json_dumps(payload),
        "ts": f"{now:.3f}",
        "timeout_seconds": str(timeout_seconds),
    }
    if conversation_id:
        message["conversation_id"] = conversation_id
    if channel:
        message["channel"] = channel

    msg_id = str(
        await r.xadd(cast("str", STREAM_HITL), cast("Any", message), maxlen=5_000, approximate=True)
    )
    log.info(
        "hitl_published",
        extra={
            "action": "publish_hitl",
            "approval_id": approval_id,
            "conversation_id": conversation_id,
            "channel": channel,
            "msg_id": msg_id,
        },
    )
    return msg_id


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


async def check_dedup(channel: str, ext_ref: str, *, ttl: int = 86400) -> bool:
    """Return ``True`` if the message is a duplicate (already seen).

    Uses SET NX with a TTL window.  Returns ``True`` when the key already
    existed (duplicate), ``False`` when this is the first occurrence.
    """
    r = await get_redis()
    key = KEY_DEDUP.format(channel=channel, ext_ref=ext_ref)
    exists = await r.set(key, "1", nx=True, ex=ttl)
    is_dup = exists is None  # None means key already existed
    if is_dup:
        log.debug(
            "dedup_hit",
            extra={"action": "check_dedup", "channel": channel, "ext_ref": ext_ref},
        )
    return is_dup


# ---------------------------------------------------------------------------
# Rate limiting (sliding window via Lua)
# ---------------------------------------------------------------------------


def _load_lua(name: str) -> str:
    """Load a Lua script from the lua/ directory, caching in memory."""
    if name not in _lua_scripts:
        path = _LUA_DIR / name
        _lua_scripts[name] = path.read_text(encoding="utf-8")
    return _lua_scripts[name]


async def check_rate_limit(
    channel: str,
    key: str,
    *,
    window: int = 60,
    limit: int = 30,
) -> tuple[bool, int, float]:
    """Sliding-window rate limiter backed by a Redis Lua script.

    Returns (allowed, remaining, retry_after_seconds).
    """
    r = await get_redis()
    redis_key = KEY_RATE_LIMIT.format(channel=channel, key=key)
    now = time.time()
    request_id = f"{now:.6f}:{uuid.uuid4().hex[:8]}"

    script = _load_lua("counter_window.lua")
    result: list[int] = await r.eval(
        script, 1, redis_key, str(window), str(limit), f"{now:.6f}", request_id
    )

    allowed = bool(result[0])
    remaining = int(result[1])
    retry_after = float(result[2])

    if not allowed:
        log.debug(
            "rate_limit_exceeded",
            extra={
                "action": "check_rate_limit",
                "channel": channel,
                "key": key,
                "retry_after": retry_after,
            },
        )
    return allowed, remaining, retry_after


# ---------------------------------------------------------------------------
# HITL atomic operations (Lua-backed)
# ---------------------------------------------------------------------------


async def hitl_timeout_claim(approval_id: str) -> bool:
    """Atomically claim a timed-out HITL item.

    Returns ``True`` if this caller successfully transitioned the item from
    ``pending`` → ``timeout``.
    """

    r = await get_redis()
    now = f"{time.time():.3f}"
    meta_key = f"hitl:meta:{approval_id}"

    script = _load_lua("hitl_timeout_claim.lua")
    result = await r.eval(script, 1, meta_key, "pending", "timeout", now)
    claimed = bool(result)

    if claimed:
        log.info(
            "hitl_timeout_claimed",
            extra={"action": "hitl_timeout_claim", "approval_id": approval_id},
        )
    return claimed


async def hitl_claim_decision(
    approval_id: str,
    *,
    status: str,
    actor: str,
    edited_payload: dict[str, Any] | None = None,
    note: str = "",
) -> bool:
    """Atomically apply a human decision to a HITL approval item.

    Returns ``True`` if this caller successfully transitioned the item from
    ``pending`` → the given decision status.
    """

    r = await get_redis()
    now = f"{time.time():.3f}"
    meta_key = f"hitl:meta:{approval_id}"
    decided_key = f"hitl:decided:{approval_id}"

    edited_json = ""
    if edited_payload is not None:
        edited_json = _json_dumps(edited_payload)

    script = _load_lua("hitl_claim_decision.lua")
    result = await r.eval(
        script,
        2,
        meta_key,
        decided_key,
        "pending",
        status,
        actor,
        now,
        edited_json,
        note,
    )
    applied = bool(result)

    if applied:
        log.info(
            "hitl_decision_applied",
            extra={
                "action": "hitl_claim_decision",
                "approval_id": approval_id,
                "status": status,
                "actor": actor,
            },
        )
    else:
        log.warning(
            "hitl_decision_conflict",
            extra={
                "action": "hitl_claim_decision",
                "approval_id": approval_id,
                "status": status,
            },
        )
    return applied


async def get_hitl_meta(approval_id: str) -> dict[str, str] | None:
    """Fetch the full metadata hash for a HITL approval item."""
    r = await get_redis()
    meta_key = f"hitl:meta:{approval_id}"
    data = await r.hgetall(meta_key)
    if not data:
        return None
    return {str(k): str(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, default=str)
