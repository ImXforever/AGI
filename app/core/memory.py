"""Long-term user memory — Kia-Agent memory providers + purchase profile.

Layers:
    1. user_memories   → durable facts extracted from chat (preference/interest/
                         skill/goal), deduplicated, importance-scored
    2. user_profile    → purchase aggregates (buys, spend, categories) + LLM persona
    3. recall          → relevance-ranked injection into AI prompts
    4. recommend       → "For you" products from category affinity

Providers are pluggable (MemoryProvider ABC). Default: PostgreSQL. Register another
provider (mem0/honcho/…) via register_provider() and pick it with the
`memory_provider` setting or MEMORY_PROVIDER env var.

Everything degrades gracefully: if the AI backend is down, extraction is simply
skipped; if memory is disabled (`memory_enabled` setting = 0), context is empty.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import time
from abc import ABC, abstractmethod

from app.logging_setup import get_logger

log = get_logger("app.core.memory")

MEMORY_BUDGET_CHARS = 800
RECALL_CANDIDATES = 60
PERSONA_MIN_MEMORIES = 4
MEMORY_EXTRACT_EVERY = 6


# ---------------------------------------------------------------------------
# Provider abstraction (Hermes plugins/memory pattern, single-file edition)
# ---------------------------------------------------------------------------


class MemoryProvider(ABC):
    """Base class for pluggable long-term memory backends."""

    name: str = "abstract"

    @abstractmethod
    async def remember(
        self, user_id: int, kind: str, content: str, importance: int, source: str
    ) -> bool: ...

    @abstractmethod
    async def recall(self, user_id: int, query: str, limit: int) -> list[dict]: ...

    @abstractmethod
    async def forget_all(self, user_id: int) -> int: ...

    @abstractmethod
    async def list_all(self, user_id: int, limit: int = 100) -> list[dict]: ...

    @abstractmethod
    async def delete_one(self, user_id: int, mem_id: int) -> bool: ...

    @abstractmethod
    async def add_note(self, user_id: int, kind: str, content: str) -> bool: ...


class PostgreSQLMemoryProvider(MemoryProvider):
    name = "postgresql"

    async def _pool(self):
        from app.storage.pg import get_pool

        return await get_pool()

    async def remember(self, user_id, kind, content, importance, source):
        key = _dedup_key(content)
        pool = await self._pool()
        result = await pool.execute(
            """INSERT INTO user_memories
               (user_id, kind, content, importance, source, dedup_key)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT DO NOTHING""",
            user_id,
            kind,
            content.strip()[:400],
            max(1, min(5, importance)),
            source,
            key,
        )
        return result != "INSERT 0 0"

    async def recall(self, user_id, query, limit):
        pool = await self._pool()
        rows = await pool.fetch(
            """SELECT id, kind, content, importance, source,
                      COALESCE(recall_count,0) AS recall_count, created_at
               FROM user_memories WHERE user_id = $1
               ORDER BY importance DESC, id DESC LIMIT $2""",
            user_id,
            RECALL_CANDIDATES,
        )
        now = time.time()
        tokens = [t.lower() for t in re.findall(r"[\w\u0600-\u06FF]{4,}", query or "")][:8]
        scored = []
        for row in rows:
            mid = row["id"]
            kind = row["kind"]
            content = row["content"]
            imp = row["importance"]
            src = row["source"]
            rc = row["recall_count"]
            created = row["created_at"]
            age_days = max(0.0, (now - (created or now)) / 86400)
            score = imp * 10 + 30 * math.exp(-age_days / 45) + min(rc, 5)
            c = (content or "").lower()
            score += sum(15 for t in tokens if t in c)
            scored.append(
                (
                    score,
                    {"id": mid, "kind": kind, "content": content, "importance": imp, "source": src},
                )
            )
        scored.sort(key=lambda x: -x[0])
        out = [m for _, m in scored[:limit]]
        if out:
            ids = [m["id"] for m in out]
            pool = await self._pool()
            await pool.execute(
                """UPDATE user_memories SET recall_count = recall_count + 1,
                    last_recalled_at = EXTRACT(EPOCH FROM NOW())::bigint
                    WHERE id = ANY($1::bigint[])""",
                ids,
            )
        return out

    async def forget_all(self, user_id):
        pool = await self._pool()
        result = await pool.execute("DELETE FROM user_memories WHERE user_id = $1", user_id)
        await pool.execute("DELETE FROM user_profile WHERE user_id = $1", user_id)
        count = int(result.split()[-1]) if result else 0
        return count

    async def list_all(self, user_id, limit=100):
        pool = await self._pool()
        rows = await pool.fetch(
            """SELECT id, kind, content, importance, source, created_at, recall_count
               FROM user_memories WHERE user_id = $1
               ORDER BY id DESC LIMIT $2""",
            user_id,
            limit,
        )
        return [dict(r) for r in rows]

    async def delete_one(self, user_id, mem_id):
        pool = await self._pool()
        result = await pool.execute(
            "DELETE FROM user_memories WHERE id = $1 AND user_id = $2", mem_id, user_id
        )
        return result != "DELETE 0"

    async def add_note(self, user_id, kind, content):
        return await self.remember(user_id, kind, content, 4, "admin")


_PROVIDERS: dict[str, type[MemoryProvider]] = {"postgresql": PostgreSQLMemoryProvider}


def register_provider(provider_cls: type[MemoryProvider]) -> None:
    """Plugin hook: register_provider(MyMem0Provider) then set
    `memory_provider` setting / MEMORY_PROVIDER env to its .name."""
    _PROVIDERS[provider_cls.name] = provider_cls


async def get_provider() -> MemoryProvider:
    name = os.getenv("MEMORY_PROVIDER", "postgresql")
    cls = _PROVIDERS.get(name) or PostgreSQLMemoryProvider
    return cls()


# ---------------------------------------------------------------------------


def _dedup_key(content: str) -> str:
    norm = re.sub(r"\s+", " ", (content or "").strip().lower())[:160]
    return hashlib.sha256(norm.encode()).hexdigest()[:24]


async def memory_enabled() -> bool:
    try:
        return os.getenv("MEMORY_ENABLED", "1") == "1"
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Purchase profile
# ---------------------------------------------------------------------------


async def record_purchase_event(user_id: int, product: dict) -> None:
    """Called after every successful buy — no LLM involved, pure SQL."""
    if not product:
        return
    cat = product.get("category") or "general"
    price = int(product.get("price_credits") or 0)
    try:
        pool = await (await _get_provider_instance())._pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO user_profile (user_id, buys_count, total_spent_credits,
                                                last_categories, updated_at)
                       VALUES ($1, 1, $2, '', EXTRACT(EPOCH FROM NOW())::bigint)
                       ON CONFLICT(user_id) DO UPDATE SET
                         buys_count = user_profile.buys_count + 1,
                         total_spent_credits = user_profile.total_spent_credits + EXCLUDED.total_spent_credits,
                         updated_at = EXCLUDED.updated_at""",
                    user_id,
                    price,
                )
                cur = await conn.fetchrow(
                    "SELECT last_categories FROM user_profile WHERE user_id = $1", user_id
                )
                hist = ((cur["last_categories"] or "") if cur else "").split(",")
                hist = [c.strip() for c in hist if c.strip()]
                if cat in hist:
                    hist.remove(cat)
                hist.insert(0, cat)
                await conn.execute(
                    "UPDATE user_profile SET last_categories = $1 WHERE user_id = $2",
                    ",".join(hist[:12]),
                    user_id,
                )
    except Exception:
        log.debug("purchase_profile_update_failed", exc_info=True)

    p = await get_provider()
    await p.remember(
        user_id,
        "interest",
        f"Interested in products in category \"{cat}\" (purchased)",
        importance=3,
        source="purchase",
    )


async def _get_provider_instance() -> PostgreSQLMemoryProvider:
    return PostgreSQLMemoryProvider()


async def purchase_profile(user_id: int) -> dict:
    """Live purchases are source of truth; user_profile caches rolling
    category history + persona (and covers brand-new buyers instantly)."""
    pool = await (await _get_provider_instance())._pool()
    row = await pool.fetchrow(
        """SELECT COUNT(*) AS n, COALESCE(SUM(pc.price_credits),0) AS spent,
                  COALESCE(AVG(pc.price_credits),0) AS avg_price,
                  STRING_AGG(DISTINCT pr.category, ',') AS cats
           FROM purchases pc JOIN products pr ON pr.id = pc.product_id
           WHERE pc.buyer_id = $1""",
        user_id,
    )
    n = row["n"] if row else 0
    spent = row["spent"] if row else 0
    avg_price = row["avg_price"] if row else 0
    cats = row["cats"] if row else None

    prof_row = await pool.fetchrow(
        """SELECT buys_count, total_spent_credits, last_categories,
                  persona, interests
           FROM user_profile WHERE user_id = $1""",
        user_id,
    )
    if prof_row:
        cb = prof_row["buys_count"] or 0
        cspend = prof_row["total_spent_credits"] or 0
        ccats = prof_row["last_categories"] or ""
        persona = prof_row["persona"] or ""
        interests = prof_row["interests"] or ""
    else:
        cb, cspend, ccats, persona, interests = 0, 0, "", "", ""

    seen, merged = set(), []
    for c in (cats or "").split(",") + [c.strip() for c in ccats.split(",")]:
        c = c.strip()
        if c and c.lower() not in seen:
            seen.add(c.lower())
            merged.append(c)
    return {
        "buys": max(n or 0, cb or 0),
        "spent": max(spent or 0, cspend or 0),
        "avg_ticket": round(avg_price or 0),
        "categories": merged[:8],
        "persona": persona or "",
        "interests": interests or "",
    }


# ---------------------------------------------------------------------------
# Prompt injection
# ---------------------------------------------------------------------------

_KIND_ICON = {
    "preference": "⭐",
    "interest": "🎯",
    "fact": "📌",
    "skill": "ðŸ› ï¸",
    "goal": "🎯",
    "habit": "ðŸ”",
    "admin": "ðŸ›¡ï¸",
}


async def build_memory_context(user_id: int, query: str = "") -> str:
    """Compact block injected into the system prompt (~budget-capped)."""
    if not await memory_enabled():
        return ""
    try:
        p = await get_provider()
        memories = await p.recall(user_id, query, limit=6)
        prof = await purchase_profile(user_id)
    except Exception:
        log.debug("memory_context_failed", exc_info=True)
        return ""

    lines = []
    if memories:
        seen = set()
        for m in memories:
            c = m["content"].strip()
            if c.lower() in seen:
                continue
            seen.add(c.lower())
            lines.append(f"{_KIND_ICON.get(m['kind'], '•')} {c}")
    pp = []
    if prof["buys"]:
        pp.append(f"{prof['buys']} purchases")
        pp.append(f"Average basket {prof['avg_ticket']:,} credits")
        if prof["categories"]:
            pp.append("Purchase categories: " + ", ".join(prof["categories"][:4]))
    if prof["persona"]:
        lines.insert(0, f"👤 {prof['persona'][:220]}")

    block = ""
    if lines:
        block += "\n".join(f"- {l}" for l in lines)
    if pp:
        block += (
            ("\n\n🛒 Purchase profile:\n- " + " | ".join(pp))
            if block
            else "\n".join(f"- 🛒 {x}" for x in pp)
        )
    if not block:
        return ""
    return (
        "\n\n🧠 Long-term memory for this user (from conversations and past purchases — use for "
        "personalizing responses, without revealing you are reading from memory):\n"
        + block
    )[:MEMORY_BUDGET_CHARS]


# ---------------------------------------------------------------------------
# Extraction pipeline (cost-guarded, fire-and-forget)
# ---------------------------------------------------------------------------

_EXTRACT_CONTRACT = """Return valid JSON only, with the following added field:
{"facts": [{"kind": "preference|interest|skill|goal|fact", "content": "...", "importance": 1-5}]}
Rules:
- Extract only facts about the current user (preferences, skills, goals, habits) — nothing the user already knows
- If no extractable facts are found, return: {"facts": []}
- Maximum 3 items per call, each content must be at least 10 characters, in Farsi"""


async def maybe_extract_memories(user_id: int, user_text: str, assistant_text: str) -> None:
    """Cheap periodic extraction — schedule with asyncio.create_task()."""
    try:
        if not user_text or len(user_text) < 25 or user_text.startswith("/"):
            return
        if not await memory_enabled():
            return

        p = await get_provider()
        total = await _count_memories(user_id)
        if total < 2 or total % MEMORY_EXTRACT_EVERY != 0:
            return

        from app.core.llm import LLMClient

        llm = LLMClient()
        convo = f"User: {user_text[:600]}\nAssistant: {(assistant_text or '')[:600]}"
        raw = await llm.complete(
            system=_EXTRACT_CONTRACT,
            user=convo,
            tier="fast",
            purpose="memory:extract",
        )
        data = _safe_json(raw)
        facts = (data or {}).get("facts") or []
        added = 0
        for f in facts[:3]:
            if not isinstance(f, dict):
                continue
            content = str(f.get("content", "")).strip()
            if len(content) < 6:
                continue
            kind = str(f.get("kind", "fact"))
            if kind not in ("preference", "interest", "skill", "goal", "fact"):
                kind = "fact"
            if await p.remember(user_id, kind, content, int(f.get("importance") or 3), "chat"):
                added += 1

        total = await _count_memories(user_id)
        if total >= PERSONA_MIN_MEMORIES and (
            total % (MEMORY_EXTRACT_EVERY * 4) == 0
            or not (await purchase_profile(user_id))["persona"]
        ):
            await persona_refresh(user_id)
        if added:
            log.info(
                "memory_facts_extracted",
                extra={"action": "memory_extract", "added": added, "user_id": user_id},
            )
    except Exception:
        log.debug("memory_extraction_skipped", exc_info=True)


def _safe_json(raw: str) -> dict | None:
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


async def _count_memories(user_id: int) -> int:
    pool = await (await _get_provider_instance())._pool()
    row = await pool.fetchrow(
        "SELECT COUNT(*) AS cnt FROM user_memories WHERE user_id = $1", user_id
    )
    return row["cnt"] if row else 0


async def persona_refresh(user_id: int) -> None:
    """LLM-written one-liner stored on user_profile.persona."""
    try:
        p = await get_provider()
        items = await p.list_all(user_id, limit=20)
        if len(items) < PERSONA_MIN_MEMORIES:
            return
        prof = await purchase_profile(user_id)
        bullets = "\n".join(f"- {i['content']}" for i in items[:14])
        extra = (
            f"\nPurchase pattern: {prof['buys']} purchases, categories: {', '.join(prof['categories'][:4])}"
            if prof["buys"]
            else ""
        )
        from app.core.llm import LLMClient

        llm = LLMClient()
        text = await llm.complete(
            system="In a short single sentence (under 25 words) describe this user "
            "so the assistant can personalize. Just the sentence.",
            user=bullets + extra,
            tier="fast",
            purpose="memory:persona",
        )
        persona = text.strip().splitlines()[0][:240]
        pool = await (await _get_provider_instance())._pool()
        await pool.execute(
            """INSERT INTO user_profile (user_id, persona, persona_at, updated_at)
               VALUES ($1, $2, EXTRACT(EPOCH FROM NOW())::bigint,
                       EXTRACT(EPOCH FROM NOW())::bigint)
               ON CONFLICT(user_id) DO UPDATE SET
                 persona = EXCLUDED.persona,
                 persona_at = EXCLUDED.persona_at,
                 updated_at = EXCLUDED.updated_at""",
            user_id,
            persona,
        )
    except Exception:
        log.debug("persona_refresh_failed", exc_info=True)


# ---------------------------------------------------------------------------
# Recommendations ("🎯 For you")
# ---------------------------------------------------------------------------


async def recommend_for_user(user_id: int, limit: int = 5) -> list[dict]:
    if not await memory_enabled():
        return []
    try:
        prof = await purchase_profile(user_id)
        p = await get_provider()
        memories = await p.recall(user_id, "", limit=10)
    except Exception:
        return []

    affinity: dict[str, float] = {}
    cats = prof.get("categories") or []
    for i, c in enumerate(cats):
        affinity[c] = affinity.get(c, 0) + 3.0 / (1 + i * 0.3)
    text = " ".join([prof.get("interests") or ""] + [m["content"] for m in memories]).lower()
    for c in ("education", "coding", "graphics", "content", "template", "tools"):
        if c in text:
            affinity[c] = affinity.get(c, 0) + 2.0
    if not affinity:
        return []

    pool = await (await _get_provider_instance())._pool()
    cat_list = list(affinity)

    # BUG #23: this query used to target a marketplace schema that does not
    # exist in Kia-Agent (products.title / price_credits / creator_id /
    # sales_count / is_featured, plus `users` and `reviews` tables). Every
    # call raised UndefinedColumnError and was swallowed by the caller, so
    # recommendations were permanently empty. Rewritten against the real
    # products table.
    rows = await pool.fetch(
        """SELECT p.id, p.sku, p.name_ar, p.name_en, p.category,
                  p.unit_price, p.unit, p.stock_qty
           FROM products p
           WHERE p.is_active = true
             AND p.category = ANY($1::text[])
           ORDER BY p.created_at DESC LIMIT 40""",
        cat_list,
    )
    if not rows:
        return []

    pids = [r["id"] for r in rows]
    owned_rows = await pool.fetch(
        "SELECT product_id FROM purchases WHERE buyer_id = $1 AND product_id = ANY($2::uuid[])",
        user_id,
        pids,
    )
    owned = {r["product_id"] for r in owned_rows}

    out = []
    for row in rows:
        pid = row["id"]
        if pid in owned:
            continue
        # In-stock items rank above back-ordered ones.
        score = affinity.get(row["category"], 0) * 3 + math.log1p(max(row["stock_qty"] or 0, 0))
        out.append(
            (
                score,
                {
                    "id": str(pid),
                    "sku": row["sku"],
                    "name_ar": row["name_ar"],
                    "name_en": row["name_en"],
                    "unit_price": float(row["unit_price"] or 0),
                    "unit": row["unit"],
                    "stock_qty": row["stock_qty"] or 0,
                    "category": row["category"],
                },
            )
        )
    out.sort(key=lambda x: -x[0])
    return [item for _, item in out[:limit]]


# ---------------------------------------------------------------------------
# User-facing summary ("My Memory")
# ---------------------------------------------------------------------------


async def my_memory_summary(user_id: int) -> tuple[str, int]:
    if not await memory_enabled():
        return "Long-term memory is currently disabled.", 0
    p = await get_provider()
    items = await p.list_all(user_id, limit=12)
    prof = await purchase_profile(user_id)
    total = await _count_memories(user_id)

    lines = []
    if prof["persona"]:
        lines.append(f"👤 {prof['persona']}\n")
    if items:
        for m in items[:8]:
            icon = _KIND_ICON.get(m["kind"], "•")
            lines.append(f"{icon} {m['content']}")
    else:
        lines.append(
            "I haven't learned anything yet — just chat with Hermes and I'll gradually learn your preferences."
        )
    if prof["buys"]:
        lines.append("")
        lines.append(
            f"🛒 Purchase profile: {prof['buys']} purchases · Average basket "
            f"{prof['avg_ticket']:,} credits"
            + (
                f" · Categories: {', '.join(prof['categories'][:4])}"
                if prof["categories"]
                else ""
            )
        )
    return "\n".join(lines), total


async def forget_me(user_id: int) -> int:
    """GDPR-style right to be forgotten (long-term layer only)."""
    p = await get_provider()
    return await p.forget_all(user_id)


# background task helper used by handlers ------------------------------------


def schedule_extraction(user_id: int, user_text: str, assistant_text: str) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(maybe_extract_memories(user_id, user_text, assistant_text))
    except RuntimeError:
        pass
