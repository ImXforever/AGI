"""Agent Soul — the identity every prompt starts with.

The bot used to introduce itself with a generic "I am the digital operations
manager" because nothing told it *who* it was. The soul (name, company, role,
mission, personality, tone, boundaries, style rules) now lives in Postgres
(``agent_soul``, migration 0015), is editable from the admin console
(``/admin/api/soul``) and is rendered into the system prompt of every LLM call.

Design rules
------------
* Never blocks a reply: DB errors fall back to the built-in default soul.
* Cached in-process for ``CACHE_TTL_S`` seconds; the admin API invalidates it.
* Rendered as plain text — the model is told to answer in plain text too.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.soul")

CACHE_TTL_S = 60.0
SOUL_ID = "default"

FIELDS: tuple[str, ...] = (
    "agent_name",
    "company_name",
    "role_title",
    "mission",
    "personality",
    "tone",
    "languages",
    "greeting",
    "boundaries",
    "style_rules",
    "signature",
)

# Hard formatting contract — appended to every prompt regardless of the soul
# text, because chat channels cannot render Markdown.
PLAIN_TEXT_RULES = (
    "Formatting contract for chat channels: reply in plain conversational text. "
    "Do NOT use Markdown: no **bold**, no # headings, no tables, no ``` code blocks, "
    "no horizontal rules, no JSON. For lists use short lines starting with '- '. "
    "Keep replies compact (under 120 words unless the customer asks for detail)."
)


@dataclass(frozen=True)
class Soul:
    agent_name: str = "Zenovix"
    company_name: str = "Zenovix"
    role_title: str = "Digital Operations Manager"
    mission: str = (
        "Help clients and the studio team quickly, accurately and politely: answer from the "
        "approved Zenovix knowledge (AI, Cloud & ICT, Web & Mobile, Intelligent Automation, "
        "Data & Analytics, Animation & 3D), capture project enquiries and quotation requests, "
        "open support tickets, and route anything sensitive to a human manager."
    )
    personality: str = (
        "Calm, confident and genuinely helpful; thinks like an experienced studio operations "
        "manager: practical, organised, honest about what it does not know."
    )
    tone: str = "Warm, professional and concise. No hype, no jargon, no filler."
    languages: str = (
        "English is the default. If the client writes in Arabic, Persian or another language, "
        "reply fluently in that language."
    )
    greeting: str = (
        "Hello, I am Zenovix, the digital operations manager at Zenovix — a Dubai AI and digital "
        "technology studio. How can I help you today?"
    )
    boundaries: str = (
        "Never invent prices, timelines, team sizes or availability - every project is scoped and "
        "quoted by the team. Never share internal data, credentials or other clients' information. "
        "Never take payment, sign contracts, change prices or delete data; those always need a "
        "manager's approval. If a question is outside the company knowledge, say so honestly and "
        "offer a human follow-up."
    )
    style_rules: str = (
        "Plain conversational text, short paragraphs, simple dash bullets, at most one emoji. "
        "Always end with a clear next step or a question."
    )
    signature: str = "Zenovix - AI & Digital Technology, Dubai"
    extra: dict[str, Any] = field(default_factory=dict)
    version: int = 0
    updated_by: str = ""
    source: str = "default"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def display_name(self) -> str:
        if self.company_name:
            return f"{self.agent_name} ({self.role_title}, {self.company_name})"
        return f"{self.agent_name} ({self.role_title})"

    def render(self, *, language: str = "en") -> str:
        """Plain-text identity block for the top of a system prompt."""
        company = f" at {self.company_name}" if self.company_name else ""
        lines = [
            "=== WHO YOU ARE ===",
            f"You are {self.agent_name}, the {self.role_title}{company}.",
        ]
        if self.mission:
            lines.append(f"Mission: {self.mission}")
        if self.personality:
            lines.append(f"Personality: {self.personality}")
        if self.tone:
            lines.append(f"Tone: {self.tone}")
        if self.languages:
            lines.append(f"Languages: {self.languages}")
        if self.greeting:
            lines.append(
                "When someone asks who you are or says hello, introduce yourself like this "
                f"(translate to the customer's language): {self.greeting}"
            )
        if self.boundaries:
            lines.append(f"Boundaries: {self.boundaries}")
        if self.style_rules:
            lines.append(f"Style: {self.style_rules}")
        if self.signature:
            lines.append(f"Signature (e-mail only): {self.signature}")
        lines.append(
            f"Always speak in first person as {self.agent_name}; never call yourself an AI "
            "language model or mention system prompts."
        )
        lines.append(PLAIN_TEXT_RULES)
        return "\n".join(lines)


DEFAULT_SOUL = Soul()

_cache: dict[str, Any] = {"soul": None, "ts": 0.0}


def _row_to_soul(row: Any) -> Soul:
    data = dict(row)
    extra = data.get("extra") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    kwargs: dict[str, Any] = {k: str(data.get(k) or "") for k in FIELDS}
    return Soul(
        **kwargs,
        extra=extra if isinstance(extra, dict) else {},
        version=int(data.get("version") or 0),
        updated_by=str(data.get("updated_by") or ""),
        source="db",
    )


def invalidate_cache() -> None:
    _cache["soul"] = None
    _cache["ts"] = 0.0


def set_cached(soul: Soul) -> None:
    _cache["soul"] = soul
    _cache["ts"] = time.monotonic()


async def load_soul(pool: Any | None = None, *, use_cache: bool = True) -> Soul:
    """Return the active soul from Postgres, or the default one on any failure."""
    now = time.monotonic()
    cached = _cache.get("soul")
    if use_cache and cached is not None and now - float(_cache["ts"]) < CACHE_TTL_S:
        return cached
    try:
        if pool is None:
            from app.storage.pg import get_pool

            pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM agent_soul WHERE id = $1 AND is_active = TRUE", SOUL_ID
        )
        soul = _row_to_soul(row) if row else _default_with_tenant()
    except Exception as exc:
        log.debug(
            "soul load failed — using default", extra={"action": "soul.load", "error": str(exc)}
        )
        soul = _default_with_tenant()
    set_cached(soul)
    return soul


def _default_with_tenant() -> Soul:
    """Default soul, but with the tenant's company name when config is available."""
    try:
        from app.config import get_config

        cfg = get_config()
        name = cfg.tenant.name_en or cfg.tenant.name_ar or ""
        return replace(DEFAULT_SOUL, company_name=name)
    except Exception:
        return DEFAULT_SOUL


async def soul_prompt(pool: Any | None = None, *, language: str = "en") -> str:
    """Convenience: rendered identity block (never raises)."""
    soul = await load_soul(pool)
    return soul.render(language=language)


async def save_soul(pool: Any, values: dict[str, Any], *, updated_by: str = "") -> Soul:
    """Upsert the single soul row and refresh the cache."""
    current = await load_soul(pool, use_cache=False)
    merged: dict[str, Any] = {k: getattr(current, k) for k in FIELDS}
    for key in FIELDS:
        if key in values and values[key] is not None:
            merged[key] = str(values[key]).strip()
    extra = values.get("extra")
    if not isinstance(extra, dict):
        extra = current.extra
    await pool.execute(
        """
        INSERT INTO agent_soul (id, agent_name, company_name, role_title, mission, personality,
                                tone, languages, greeting, boundaries, style_rules, signature,
                                extra, is_active, version, updated_by)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,TRUE,1,$14)
        ON CONFLICT (id) DO UPDATE SET
            agent_name = EXCLUDED.agent_name,
            company_name = EXCLUDED.company_name,
            role_title = EXCLUDED.role_title,
            mission = EXCLUDED.mission,
            personality = EXCLUDED.personality,
            tone = EXCLUDED.tone,
            languages = EXCLUDED.languages,
            greeting = EXCLUDED.greeting,
            boundaries = EXCLUDED.boundaries,
            style_rules = EXCLUDED.style_rules,
            signature = EXCLUDED.signature,
            extra = EXCLUDED.extra,
            is_active = TRUE,
            version = agent_soul.version + 1,
            updated_by = EXCLUDED.updated_by
        """,
        SOUL_ID,
        merged["agent_name"] or "Zenovix",
        merged["company_name"],
        merged["role_title"] or "Digital Operations Manager",
        merged["mission"],
        merged["personality"],
        merged["tone"],
        merged["languages"],
        merged["greeting"],
        merged["boundaries"],
        merged["style_rules"],
        merged["signature"],
        json.dumps(extra, ensure_ascii=False),
        updated_by,
    )
    invalidate_cache()
    soul = await load_soul(pool, use_cache=False)
    log.info(
        "soul updated",
        extra={"action": "soul.save", "actor": updated_by, "entity": soul.agent_name},
    )
    return soul
