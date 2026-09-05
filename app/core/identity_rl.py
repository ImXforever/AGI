"""
Kia-Agent — Identity reinforcement-learning agent.

Goal: learn a *small, actionable* identity label per user from their behaviour,
so the bot can personalise (wording, onboarding, offers) and so admins can spot
farming / high-value users without hand-labelling.

Approach (lightweight, no ML deps, pure Python):

  * State   = a discretised feature vector of the user's behaviour
              (visit count, purchases, tasks done, withdrawals, freshness,
               chat depth, session cadence).
  * Actions = a fixed set of identity labels.
  * Reward  = an event-driven signal: when we observe a real behaviour event we
              reward the labels that behaviour implies.
  * Update  = Q-learning (tabulated) with epsilon-greedy exploration, a learning
              rate and a discount factor. All tuned via env/config.

Persistence: a ``rl_identity`` table stores per-user Q-values and the live label,
so learning survives restarts and can be inspected by admins.
"""

from __future__ import annotations

import hashlib as _hl
import json
import math
import random
import time

from app.config import get_config
from app.logging_setup import get_logger
from app.storage.pg import get_pool

log = get_logger("app.core.identity_rl")

ACTIONS = [
    "new_user",
    "browser",
    "task_earner",
    "returning_buyer",
    "high_value",
    "supporter",
    "churn_risk",
]

_EVENT_REWARD = {
    "purchase":     {"returning_buyer": 5.0, "high_value": 2.0, "supporter": 1.0},
    "withdraw":     {"high_value": 5.0, "returning_buyer": 1.0},
    "task_done":    {"task_earner": 4.0, "new_user": 0.5},
    "visit":        {"returning_buyer": 1.0, "supporter": 0.5, "new_user": 0.3},
    "chat_message": {"supporter": 1.5, "returning_buyer": 0.5},
    "refund":       {"churn_risk": 3.0, "high_value": -1.0},
    "chargeback":   {"churn_risk": 5.0, "task_earner": -1.0},
    "mystery_box":  {"task_earner": 1.5, "returning_buyer": -0.5},
}

_BUCKETS = {
    "visits": 4,
    "purchases": 4,
    "tasks": 4,
    "withdraws": 3,
    "chat_level": 4,
    "session_bucket": 4,
    "freshness": 2,
}


class IdentityRL:
    """Tabulated Q-learning identity classifier (persisted per user)."""

    def __init__(self, user_id: int) -> None:
        self.user_id = int(user_id)
        cfg = get_config()
        self.alpha = getattr(cfg, "rl_learn_rate", 0.3)
        self.gamma = getattr(cfg, "rl_gamma", 0.9)
        self.epsilon = getattr(cfg, "rl_explore", 0.2)

    # ---- feature/state ------------------------------------------------

    async def _features(self) -> dict[str, float]:
        pool = await get_pool()

        user = await pool.fetchrow(
            "SELECT created_at FROM customers WHERE id = $1",
            str(self.user_id),
        )

        row_bought = await pool.fetchrow(
            "SELECT COUNT(*)::int AS cnt FROM orders WHERE customer_id = $1",
            str(self.user_id),
        )
        n_bought = row_bought["cnt"] if row_bought else 0

        row_chat = await pool.fetchrow(
            "SELECT COUNT(*)::int AS cnt FROM messages WHERE conversation_id IN "
            "(SELECT id FROM conversations WHERE customer_id = $1)",
            str(self.user_id),
        )
        n_chat = row_chat["cnt"] if row_chat else 0

        row_tasks = await pool.fetchrow(
            "SELECT COUNT(*)::int AS cnt FROM tool_executions "
            "WHERE approval_id IN (SELECT id FROM approvals WHERE customer_id = $1)",
            str(self.user_id),
        )
        n_tasks = row_tasks["cnt"] if row_tasks else 0

        row_wd = await pool.fetchrow(
            "SELECT COUNT(*)::int AS cnt FROM orders "
            "WHERE customer_id = $1 AND status = 'paid'",
            str(self.user_id),
        )
        n_wd = row_wd["cnt"] if row_wd else 0

        created = float(user["created_at"].timestamp()) if user and user.get("created_at") else time.time()
        age_days = max(0.0, (time.time() - created) / 86400)

        return {
            "visits": n_chat + n_bought,
            "purchases": n_bought,
            "tasks": n_tasks,
            "withdraws": n_wd,
            "chat_level": n_chat,
            "session_bucket": int(time.localtime().tm_hour / 6),
            "freshness": 1 if age_days < 2 else 0,
        }

    def _state(self, feats: dict[str, float]) -> str:
        parts: list[str] = []
        for k, b in _BUCKETS.items():
            v = int(min(feats.get(k, 0), b - 1))
            parts.append(f"{k}:{v}")
        return "|".join(parts)

    @staticmethod
    def _hash_state(state: str) -> int:
        return int.from_bytes(
            _hl.blake2b(state.encode(), digest_size=4).digest(), "big"
        ) % 100000

    # ---- Q persistence ------------------------------------------------

    async def _load_q(self) -> dict[str, dict[str, float]]:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT qvalues, label FROM rl_identity WHERE user_id = $1",
            self.user_id,
        )
        if row:
            try:
                return json.loads(row["qvalues"])
            except Exception:
                return {}
        return {}

    async def _save_q(self, q: dict[str, dict[str, float]], label: str) -> None:
        pool = await get_pool()
        await pool.execute(
            """
            INSERT INTO rl_identity (user_id, qvalues, label, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id)
            DO UPDATE SET qvalues = EXCLUDED.qvalues,
                          label   = EXCLUDED.label,
                          updated_at = EXCLUDED.updated_at
            """,
            self.user_id,
            json.dumps(q, ensure_ascii=False),
            label,
            time.time(),
        )

    # ---- core RL -------------------------------------------------------

    async def act(self) -> str:
        """Pick the current identity label (epsilon-greedy)."""
        q = await self._load_q()
        if not q or random.random() < self.epsilon:
            return random.choice(ACTIONS)
        state = self._state(await self._features())
        h = self._hash_state(state)
        qs = q.get(str(h), {})
        return max(ACTIONS, key=lambda a: qs.get(a, 0.0))

    async def learn(self, event: str) -> str:
        """Apply a reward from a real behaviour event. Returns updated label."""
        reward = _EVENT_REWARD.get(event)
        if not reward:
            return await self.profile_label()

        feats = await self._features()
        state = self._state(feats)
        h = str(self._hash_state(state))
        q = await self._load_q()
        qs = q.setdefault(h, {a: 0.0 for a in ACTIONS})

        max_next = max(qs.values()) if qs else 0.0
        for action, r in reward.items():
            if action not in qs:
                qs[action] = 0.0
            qs[action] += self.alpha * (r + self.gamma * max_next - qs[action])

        label = max(ACTIONS, key=lambda a: qs.get(a, 0.0))
        await self._save_q(q, label)
        log.info(
            "identity_rl.learn",
            extra={
                "action": "identity_rl.learn",
                "user_id": self.user_id,
                "event": event,
                "label": label,
            },
        )
        return label

    async def profile_label(self) -> str:
        q = await self._load_q()
        if not q:
            return "new_user"
        totals = {a: 0.0 for a in ACTIONS}
        for qs in q.values():
            for a, v in qs.items():
                totals[a] = totals.get(a, 0.0) + v
        return max(ACTIONS, key=lambda a: totals.get(a, 0.0))

    async def confidence(self) -> float:
        """Softmax-ish confidence in the winning label (0..1)."""
        q = await self._load_q()
        if not q:
            return 0.0
        totals = {a: 0.0 for a in ACTIONS}
        for qs in q.values():
            for a, v in qs.items():
                totals[a] = totals.get(a, 0.0) + v
        best = max(totals.values())
        denom = sum(math.exp(v) for v in totals.values() if v >= best - 20)
        return min(1.0, round(math.exp(best) / denom, 3)) if denom else 0.0

    async def snapshot(self) -> dict:
        feats = await self._features()
        return {
            "user_id": self.user_id,
            "label": await self.profile_label(),
            "confidence": await self.confidence(),
            "q": await self._load_q(),
            "features": feats,
            "state": self._state(feats),
        }


# ---------------------------------------------------------------------------
# Table init
# ---------------------------------------------------------------------------


async def init_tables() -> None:
    pool = await get_pool()
    await pool.execute(
        """
        CREATE TABLE IF NOT EXISTS rl_identity (
            user_id    BIGINT PRIMARY KEY,
            qvalues    TEXT   DEFAULT '{}',
            label      TEXT   DEFAULT 'new_user',
            updated_at DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM now())
        )
        """
    )


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------


async def get_identity(user_id: int) -> dict:
    agent = IdentityRL(user_id)
    return await agent.snapshot()


async def signal(user_id: int, event: str) -> None:
    """Fire-and-forget reward signal on a real behaviour event."""
    cfg = get_config()
    if not getattr(cfg, "identity_rl_enabled", True):
        return
    try:
        agent = IdentityRL(user_id)
        await agent.learn(event)
    except Exception as exc:
        log.warning(
            "identity_rl.signal failed",
            extra={
                "action": "identity_rl.signal",
                "user_id": user_id,
                "event": event,
                "error": str(exc)[:300],
            },
        )
