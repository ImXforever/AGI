"""In-process capacity model for Railway (1 web + optional worker).

Used by tests and ops to answer: can this tenant handle N members?
No network. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapacityReport:
    members: int
    active_per_hour: int
    inbound_per_hour: int
    inbound_per_sec: float
    auto_per_hour: int
    hitl_per_hour: int
    redis_mb: float
    postgres_mb: float
    llm_calls_per_hour: int
    workers_recommended: int
    verdict: str
    bottlenecks: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "members": self.members,
            "active_per_hour": self.active_per_hour,
            "inbound_per_hour": self.inbound_per_hour,
            "inbound_per_sec": round(self.inbound_per_sec, 3),
            "auto_per_hour": self.auto_per_hour,
            "hitl_per_hour": self.hitl_per_hour,
            "redis_mb": round(self.redis_mb, 1),
            "postgres_mb": round(self.postgres_mb, 1),
            "llm_calls_per_hour": self.llm_calls_per_hour,
            "workers_recommended": self.workers_recommended,
            "verdict": self.verdict,
            "bottlenecks": list(self.bottlenecks),
        }


def simulate_members(
    members: int = 10_000,
    *,
    active_pct: float = 0.12,
    msgs_per_active: float = 2.0,
    auto_ratio: float = 0.85,
    session_kb: float = 4.0,
    message_bytes: float = 900.0,
    rate_limit_per_minute: int = 60,
    web_rps_budget: float = 25.0,
) -> CapacityReport:
    """Model a busy hour for ``members`` registered users."""
    active = max(1, int(members * active_pct))
    inbound = int(active * msgs_per_active)
    per_sec = inbound / 3600.0
    auto = int(inbound * auto_ratio)
    hitl = inbound - auto
    redis_mb = (members * session_kb) / 1024.0
    postgres_mb = (members * 2.5 + inbound * (message_bytes / 1024.0) * 24) / 1024.0
    llm_calls = auto + hitl  # every inbound still classified
    bottlenecks: list[str] = []
    if per_sec > web_rps_budget:
        bottlenecks.append("web RPS over single uvicorn worker budget — add a worker service")
    if hitl > 80:
        bottlenecks.append("HITL queue: more than ~80 manager decisions/hour — staffing, not CPU")
    if llm_calls > 8_000:
        bottlenecks.append("LLM quota: >8k completions/hour — enable prompt cache + cheaper fast model")
    if redis_mb > 400:
        bottlenecks.append("Redis memory: raise plan or shorten session TTL")
    # Per-user rate limit cannot be the 10k bottleneck unless a single user floods.
    flood_cap = rate_limit_per_minute / 60.0
    if flood_cap < 0.2:
        bottlenecks.append("RATE_LIMIT_PER_MINUTE too low for conversational UX")

    # Workers follow inbound RPS, not HITL staffing.
    if per_sec <= 5:
        verdict = "yes"
        workers = 1
    elif per_sec <= 25:
        verdict = "yes-with-worker"
        workers = 2
    else:
        verdict = "scale-out"
        workers = 4

    return CapacityReport(
        members=members,
        active_per_hour=active,
        inbound_per_hour=inbound,
        inbound_per_sec=per_sec,
        auto_per_hour=auto,
        hitl_per_hour=hitl,
        redis_mb=redis_mb,
        postgres_mb=postgres_mb,
        llm_calls_per_hour=llm_calls,
        workers_recommended=workers,
        verdict=verdict,
        bottlenecks=bottlenecks,
    )


def simulate_burst(n_events: int = 10_000, consume_rps: float = 80.0) -> dict[str, float]:
    """Drain ``n_events`` through an in-memory stream at ``consume_rps``."""
    seconds = n_events / max(consume_rps, 0.01)
    return {
        "events": float(n_events),
        "consume_rps": consume_rps,
        "drain_seconds": round(seconds, 2),
        "ok": seconds < 180.0,
    }
