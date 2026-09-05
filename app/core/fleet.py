"""Kia-Agent Fleet — one query, one team.

Adapted from Hermes Fleet architecture (Profiles + Delegation + Memory):
- ATLAS   chief of staff: routes queries (simple→direct / multi-layer→team)
- CIPHER  researcher: evidence from memory and knowledge base
- VEGA    strategist: options/scenarios/risk
- QUANT   numbers: calculations with real platform constants
- FORGE   engineer: technical solutions/build steps
- ROOK    Red Team: challenges assumptions
- LIBRARIAN saves valuable knowledge to the knowledge base
- MUSE    final narrator (readable Persian)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from app.config import get_config
from app.core.llm import LLMClient
from app.logging_setup import get_logger
from app.storage.pg import audit, get_pool

log = get_logger("app.core.fleet")

ROLES = ("atlas", "cipher", "vega", "quant", "forge", "rook", "librarian", "muse")
ROLE_FA: dict[str, str] = {
    "atlas": "Atlas",
    "cipher": "Cipher",
    "vega": "Vega",
    "quant": "Quant",
    "forge": "Forge",
    "rook": "Rook",
    "librarian": "Librarian",
    "muse": "Muse",
}

COMPLEX_HINTS = (
    "why",
    "how",
    "plan",
    "strategy",
    "analysis",
    "compare",
    "value",
    "profit",
    "risk",
    "sell",
    "price",
    "idea",
    "scenario",
    "help me build",
    "start",
    "better",
    "or ",
    "\u0686\u0631\u0627",
    "\u0686\u0637\u0648\u0631",
    "\u0686\u06af\u0648\u0646\u0647",
    "\u0628\u0631\u0646\u0627\u0645\u0647",
    "\u0627\u0633\u062a\u0631\u0627\u062a\u0698\u06cc",
    "\u062a\u062d\u0644\u06cc\u0644",
    "\u0645\u0642\u0627\u06cc\u0633\u0647",
    "\u0627\u0631\u0632\u0634",
    "\u0633\u0648\u062f",
    "\u0631\u06cc\u0633\u06a9",
    "\u0628\u0641\u0631\u0648\u0634\u0645",
    "\u0642\u06cc\u0645\u062a \u0628\u0630\u0627\u0631\u0645",
    "\u0627\u06cc\u062f\u0647",
    "\u0633\u0646\u0627\u0631\u06cc\u0648",
    "\u06a9\u0645\u06a9\u0645 \u06a9\u0646 \u0628\u0633\u0627\u0632\u0645",
    "\u0634\u0631\u0648\u0639 \u06a9\u0646\u0645",
    "\u0628\u0647\u062a\u0631\u0647",
    "\u06cc\u0627 ",
)


def platform_facts() -> str:
    """Return platform constants as a context block for fleet roles."""
    cfg = get_config()
    return (
        f"Kia-Agent platform constants:\n"
        f"- Currency: {cfg.domain.currency}; tax rate: {int(cfg.domain.tax_rate * 100)}%\n"
        f"- Quote validity: {cfg.domain.quote_valid_days} days\n"
        f"- Reply language policy: {cfg.domain.reply_language_policy}\n"
        f"- Numeral style: {cfg.domain.numeral_style}\n"
    )


async def _call(
    role: str,
    system: str,
    user: str,
    *,
    llm: LLMClient,
    max_tokens: int = 700,
    temperature: float = 0.6,
) -> str:
    """Make an LLM call for a fleet role via Kia-Agent's LLMClient."""
    tier: Literal["fast", "standard"] = "fast" if max_tokens <= 500 else "standard"
    try:
        return await llm.complete(
            system=system,
            user=user,
            tier=tier,
            temperature=temperature,
            max_tokens=max_tokens,
            purpose=f"fleet:{role}",
        )
    except Exception as e:
        log.warning("fleet %s failed: %s", role, e, extra={"action": f"fleet.{role}"})
        return ""


def _looks_complex(text: str) -> bool:
    t = text.strip()
    if len(t) < 60 and t.count("?") + t.count("\u061f") <= 1:
        if not any(h in t for h in COMPLEX_HINTS):
            return False
    return True


async def atlas_route(
    user_text: str, has_history: bool, *, llm: LLMClient | None = None
) -> dict[str, Any]:
    """Cheap fast router. Returns {'mode','roles','brief','worth_saving','needs_tools'}."""
    if llm is None:
        llm = LLMClient()
    system = (
        "You are Atlas, the chief of staff. Given the user message, decide:\n"
        '- mode = "direct" if the question is simple/conversational requiring only a direct reply.\n'
        '- mode = "team" if the problem is multi-layered (analysis/strategy/product/numbers/risk).\n'
        "If team: choose up to 3 suitable roles from:\n"
        "cipher(evidence), vega(strategy), quant(numbers), forge(building), rook(critique)\n"
        "— muse always runs last automatically, do NOT list it.\n"
        "brief = two-line mission summary for the team.\n"
        "worth_saving = true only if the result likely has long-term knowledge value.\n"
        "needs_tools = true if the user needs actual data (inventory, products, stats, "
        "coupon creation, price changes, market/memory search).\n"
        "Return pure JSON only:\n"
        '{"mode":"direct|team","roles":["..."],"brief":"...","worth_saving":false,"needs_tools":false}'
    )

    raw = await _call(
        "atlas",
        system,
        f"User message:\n{user_text}\n\n(has_history: {has_history})",
        llm=llm,
        max_tokens=240,
        temperature=0.2,
    )

    data = _extract_json(raw)
    mode = data.get("mode") if data.get("mode") in ("direct", "team") else None
    if not mode:
        mode = "team" if _looks_complex(user_text) else "direct"
    roles = [r for r in (data.get("roles") or []) if r in ROLES and r not in ("atlas", "muse")][:3]
    if mode == "team" and not roles:
        roles = ["cipher", "vega"]
    return {
        "mode": mode,
        "roles": roles,
        "brief": (data.get("brief") or "")[:400],
        "worth_saving": bool(data.get("worth_saving")),
        "needs_tools": bool(data.get("needs_tools")),
    }


ROLE_PROMPTS: dict[str, str] = {
    "cipher": (
        "You are Cipher; the team researcher. Using CONTEXT (platform constants, memory, "
        "knowledge base) list only relevant findings in short bullets. End with "
        "'Confidence: high/medium/low'. Max 120 words."
    ),
    "vega": (
        "You are Vega; the strategist. Give 2-3 options or scenarios with pros/cons and "
        "risk for each. One clear final recommendation. Max 150 words."
    ),
    "quant": (
        "You are Quant; the quantitative analyst. Use exact numbers from CONTEXT for "
        "calculations (currency/tax/quotes). Simple mental table with explicit numbers. "
        "If data is insufficient, state your assumptions. Max 120 words."
    ),
    "forge": (
        "You are Forge; the engineer. Practical build steps (1-6 steps) with available "
        "platform tools. Each step one line. Max 120 words."
    ),
    "rook": (
        "You are Rook; Red Team. Blunt and unapologetic: 2-4 overlooked issues/risks in "
        "the previous analysis + suggested fix for each. No sugarcoating. Max 100 words."
    ),
    "muse": (
        "You are Muse; the final narrator. Combine all team findings into one warm, readable "
        "response: start with a key sentence, then short bullets, end with 'next step'. "
        "Do NOT mention agent names. Max 300 words. Use balanced emoji."
    ),
}


async def run_fleet(
    user_text: str,
    user_id: int,
    on_status: Callable[[str], Awaitable[None]],
    *,
    llm: LLMClient | None = None,
) -> tuple[str, dict[str, Any]]:
    """Full team run. on_status(str) gets live status lines for the chat.
    Returns (final_answer, meta)."""
    if llm is None:
        llm = LLMClient()

    pool = await get_pool()

    # Fetch recent memory
    history = await _mem_recent(pool, user_id, turns=4)
    hist_digest = (
        "\n".join(f"{h['role']}: {h['content'][:200]}" for h in history[-4:]) if history else ""
    )
    notes = await _kb_search(pool, user_id, user_text, limit=2)
    kb_block = "\n".join(f"- {n['topic']}: {n['content'][:300]}" for n in notes) or "---"

    await on_status("Atlas is analyzing the query...")
    route = await atlas_route(user_text, bool(history), llm=llm)

    if route["mode"] != "team":
        return "", {"mode": "direct", "needs_tools": route.get("needs_tools", False)}

    context = (
        platform_facts()
        + f"\nRecent memory:\n{hist_digest or '---'}\n\nKnowledge base:\n{kb_block}"
    )

    running = f"TASK: {user_text}"
    if route["brief"]:
        running += f"\nBRIEF Atlas: {route['brief']}"

    independent = [r for r in route["roles"] if r != "rook"]
    critic = [r for r in route["roles"] if r == "rook"]

    async def _run_role(role: str) -> tuple[str, str]:
        fa = ROLE_FA[role]
        out = await _call(
            role,
            ROLE_PROMPTS[role] + "\n\nCONTEXT:\n" + context,
            running,
            llm=llm,
            max_tokens=650 if role != "rook" else 500,
            temperature=0.5 if role != "vega" else 0.7,
        )
        return role, out

    results: list[tuple[str, str]] = []
    done_line0 = ""
    for i, role in enumerate(independent, 1):
        await on_status(f"{done_line0}{ROLE_FA[role]} working... ({i}/{len(route['roles']) + 1})")
        results.append(await _run_role(role))
        done_line0 += f"{ROLE_FA[role]} OK  "

    for role, out in results:
        if out:
            running += f"\n\n[{ROLE_FA[role]}]:\n{out}"

    done_line = "".join(f"{ROLE_FA[r]} OK  " for r, o in results if o)

    # Red Team always runs AFTER the panel
    for role in critic:
        await on_status(f"{done_line}Rook: Red Team attack...")
        out = await _call(
            "rook",
            ROLE_PROMPTS["rook"] + "\n\nCONTEXT:\n" + context,
            running,
            llm=llm,
            max_tokens=500,
        )
        if out:
            running += f"\n\n[{ROLE_FA['rook']}]:\n{out}"
            done_line += f"{ROLE_FA['rook']} OK  "

    await on_status(f"{done_line}Muse: finalizing...")
    final = await _call(
        "muse",
        ROLE_PROMPTS["muse"] + "\n\nCONTEXT:\n" + context,
        running,
        llm=llm,
        max_tokens=900,
        temperature=0.65,
    )
    answer = (final or "").strip()
    if not answer:
        # graceful degradation: stitch last outputs raw
        answer = running.split("\n\n[", 1)[-1][:3000]

    meta: dict[str, Any] = {
        "mode": "team",
        "roles": route["roles"],
        "worth_saving": route["worth_saving"],
        "needs_tools": False,
    }

    if route["worth_saving"]:
        try:
            await _kb_save(
                pool, user_id, topic=user_text[:120], content=answer[:1500], source="librarian:auto"
            )
            meta["saved"] = True
        except Exception as e:
            log.warning("kb_save failed: %s", e, extra={"action": "fleet.kb_save"})

    try:
        await audit(
            action="fleet.run",
            actor=str(user_id),
            entity="fleet",
            entity_id="",
            details={
                "mode": route["mode"],
                "roles": route["roles"],
                "worth_saving": route["worth_saving"],
                "answer_len": len(answer),
            },
        )
    except Exception:
        log.debug("fleet_memory_store_failed", exc_info=True)

    return answer, meta


async def fleet_status_line(user_id: int) -> str:
    """Return a status line showing fleet state and knowledge base count."""
    try:
        pool = await get_pool()
        n = await _kb_count(pool, user_id)
    except Exception:
        n = 0
    return f"Fleet: active | Knowledge base: {n} notes"


# =========================================================
# Internal knowledge-base / memory helpers (PostgreSQL)
# =========================================================


async def _mem_recent(pool: Any, user_id: int, turns: int = 4) -> list[dict[str, Any]]:
    """Fetch recent conversation turns for a user."""
    try:
        rows = await pool.fetch(
            """
            SELECT role, content
            FROM conversation_turns
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id,
            turns,
        )
        return [dict(r) for r in reversed(rows)]
    except Exception:
        return []


async def _kb_search(pool: Any, user_id: int, query: str, limit: int = 2) -> list[dict[str, Any]]:
    """Search knowledge base notes for a user."""
    safe_limit = max(1, min(limit, 10))
    safe_query = query.replace("%", "\\%").replace("_", "\\_")
    try:
        rows = await pool.fetch(
            """
            SELECT topic, content
            FROM kb_notes
            WHERE user_id = $1
              AND (topic ILIKE '%' || $2 || '%' ESCAPE '\\' OR content ILIKE '%' || $2 || '%' ESCAPE '\\')
            ORDER BY created_at DESC
            LIMIT $3
            """,
            user_id,
            safe_query,
            safe_limit,
        )
        return [dict(r) for r in rows]
    except Exception:
        return []


async def _kb_save(pool: Any, user_id: int, topic: str, content: str, source: str = "") -> None:
    """Save a note to the knowledge base."""
    await pool.execute(
        """
        INSERT INTO kb_notes (user_id, topic, content, source, created_at)
        VALUES ($1, $2, $3, $4, now())
        """,
        user_id,
        topic,
        content,
        source,
    )


async def _kb_count(pool: Any, user_id: int) -> int:
    """Count knowledge base notes for a user."""
    try:
        return await pool.fetchval(
            "SELECT COUNT(*) FROM kb_notes WHERE user_id = $1",
            user_id,
        )
    except Exception:
        return 0


# =========================================================
# JSON extraction helper
# =========================================================


def _extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from text."""
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        return {}
