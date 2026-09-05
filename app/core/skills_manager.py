"""Installable skills — Hermes-format (folder/SKILL.md with YAML frontmatter).

Adapted from Hermes DropAgentX skills.py for Kia-Agent PostgreSQL backend.

Layouts supported inside SKILL_DIR (data/skills):
    <name>.md                 legacy flat file
    <name>/SKILL.md           official Hermes layout

Frontmatter keys understood: name, description, version, tags:[..],
triggers:[..], metadata.hermes.tags:[..].

Injection policy (budget-safe, relevance-ranked):
  - compact INDEX of every enabled skill always included
  - FULL body injected for the top-2 keyword-matched skills

Admin surface: /api/admin/skills-store (list/add/toggle/delete)
Agent surface: tools list_skills / load_skill.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from typing import Any

import asyncpg  # type: ignore[import-untyped]

from app.logging_setup import get_logger

log = get_logger("app.core.skills_manager")

SKILL_DIR = os.path.join("data", "skills")
MAX_INJECT_CHARS = 2600
MAX_BODY_CHARS = 6000


# ---------------------------------------------------------------- storage ---


def _safe(name: str) -> str | None:
    name = (name or "").strip().lower().replace(" ", "_")
    if not re.fullmatch(r"[a-z0-9_\u0600-\u06FF\-]{2,32}", name):
        return None
    return name


def _skill_file(name: str) -> str | None:
    n = _safe(name)
    if not n:
        return None
    hermes = os.path.join(SKILL_DIR, n, "SKILL.md")
    if os.path.isfile(hermes):
        return hermes
    flat = os.path.join(SKILL_DIR, n + ".md")
    if os.path.isfile(flat):
        return flat
    return None


async def _ensure_table(pg: asyncpg.Pool) -> None:
    await pg.execute(
        "CREATE TABLE IF NOT EXISTS skills_state (name TEXT PRIMARY KEY, enabled INTEGER DEFAULT 1)"
    )


async def _state_map(pg: asyncpg.Pool) -> dict[str, int]:
    await _ensure_table(pg)
    rows = await pg.fetch("SELECT name, enabled FROM skills_state")
    return {r["name"]: int(r["enabled"]) for r in rows}


async def _set_state(pg: asyncpg.Pool, name: str, enabled: bool) -> None:
    await _ensure_table(pg)
    await pg.execute(
        "INSERT INTO skills_state (name, enabled) VALUES ($1, $2) "
        "ON CONFLICT (name) DO UPDATE SET enabled = EXCLUDED.enabled",
        name,
        1 if enabled else 0,
    )


# ------------------------------------------------------------ frontmatter ---

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _parse_list(v: str) -> list[str]:
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_unquote(x) for x in v[1:-1].split(",") if x.strip()]
    return []


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML subset: top-level scalars + any ``tags:``/``triggers:`` list,
    including nested metadata.hermes.tags. No pyyaml dependency."""
    fm: dict = {}
    m = _FM_RE.match(text or "")
    body = text[m.end() :] if m else (text or "")
    if not m:
        return fm, body
    block = m.group(1)
    parent = None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[:1] in (" ", "\t")
        kv = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", raw.strip())
        if not kv:
            li = re.match(r"-\s+(.*)$", raw.strip())
            if li and parent:
                fm.setdefault(parent, [])
                if isinstance(fm[parent], list):
                    fm[parent].append(_unquote(li.group(1)))
            continue
        key, val = kv.group(1).lower(), kv.group(2).strip()
        if indented and parent == "metadata":
            parent = "meta." + key
            continue
        if not indented:
            parent = key
        if val in ("", "|", ">"):
            continue
        if val.startswith("["):
            fm[key] = _parse_list(val)
        else:
            fm[key] = _unquote(val)
    for k in ("meta.hermes.tags", "hermes.tags"):
        if k in fm and isinstance(fm[k], list):
            fm.setdefault("tags", []).extend(t for t in fm[k] if t not in fm.get("tags", []))
    return fm, body


# ------------------------------------------------------------------ model ---


class SkillInfo:
    __slots__ = ("name", "desc", "tags", "version", "enabled", "path", "size")

    def __init__(self, **kw: Any):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def _scan_sync() -> list[tuple[str, dict, str, str]]:
    """Yield (name, frontmatter, body, path) for every skill found."""
    out: list[tuple[str, dict, str, str]] = []
    if not os.path.isdir(SKILL_DIR):
        return out
    for entry in sorted(os.listdir(SKILL_DIR)):
        p = os.path.join(SKILL_DIR, entry)
        cand = None
        if entry.endswith(".md"):
            cand = p
        elif os.path.isdir(p):
            hp = os.path.join(p, "SKILL.md")
            if os.path.isfile(hp):
                cand = hp
        if not cand:
            continue
        try:
            text = open(cand, encoding="utf-8").read()
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        name = _safe(fm.get("name") or (entry[:-3] if entry.endswith(".md") else entry))
        if not name:
            continue
        out.append((name, fm, body.strip(), cand))
    return out


def _match_score(query: str, name: str, desc: str, tags: list[str]) -> int:
    tokens = [t.lower() for t in re.findall(r"[\w\u0600-\u06FF]{3,}", query or "")][:10]
    if not tokens:
        return 0
    hay = f"{name} {desc} {' '.join(tags)}".lower()
    return sum(3 for t in tokens if t in hay)


async def list_skills(query: str = "", *, pg: asyncpg.Pool | None = None) -> list[dict]:
    state: dict[str, int] = {}
    if pg is not None:
        state = await _state_map(pg)
    items: list[dict[str, Any]] = []
    seeded = False
    for name, fm, body, path in await asyncio.to_thread(_scan_sync):
        desc = str(fm.get("description") or "").strip() or "no description"
        raw_tags = fm.get("tags") or []
        if isinstance(raw_tags, str):
            tags = [raw_tags]
        elif isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags]
        else:
            tags = []
        items.append(
            {
                "name": name,
                "desc": desc[:160],
                "tags": [str(t) for t in tags][:6],
                "version": str(fm.get("version") or ""),
                "enabled": state.get(name, 1) == 1 if state else True,
                "size": len(body),
                "format": "hermes" if path.endswith(os.path.join("", "SKILL.md")) else "flat",
                "_score": _match_score(query, name, desc, tags),
            }
        )
        seeded = True
    if not seeded:
        await _seed_demo()
        return await list_skills(query, pg=pg)
    if query.strip():
        items.sort(key=lambda x: (-x["_score"], x["name"]))
    else:
        items.sort(key=lambda x: x["name"])
    for it in items:
        it.pop("_score", None)
    return items


DEMO_SKILL = """---
name: selling-tips
description: "Guide to better marketplace selling: credit-based pricing, seller-friendly descriptions, and customer responses."
version: 1.0.0
tags: [sales, marketplace, pricing]
---

# Selling Tips for DropAgentX

## Pricing
- Reference rate: 1000 credits = 1 USDT; comprehensive tutorials usually cost 1500 to 4500 credits.
- Recommended range: Set between 500 and 2500 credits per sale.

## Key Description Elements
- First sentence = main promise ("After this tutorial you will be able to...").
- Feature bullet points — do not skip them.
- Final call-to-action to close the deal.

## Customer Response
- Within 5 minutes of inquiry — service is attention.
- Price negotiation: You have authority to offer a loyalty discount (up to 10% off).
"""


async def _seed_demo() -> None:
    try:
        os.makedirs(SKILL_DIR, exist_ok=True)
        d = os.path.join(SKILL_DIR, "selling-tips")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(DEMO_SKILL)
        log.info("seeded demo skill: selling-tips")
    except OSError:
        pass


# ------------------------------------------------------------- admin CRUD ---


async def skill_write(name: str, content: str) -> tuple[bool, str]:
    n = _safe(name)
    if not n:
        return (
            False,
            "Invalid name (use latin letters/digits/hyphens, 2 to 32 characters)",
        )
    fm, body = parse_frontmatter(content or "")
    if not fm.get("description"):
        return (
            False,
            "Frontmatter must include at least `description:` (Hermes format)",
        )
    from app.core.skills_guard import scan_skill_text

    scan = scan_skill_text(content)
    if scan.blocked:
        return False, "skill blocked by guard: " + "; ".join(scan.reasons[:3])
    content = content.strip()[:MAX_BODY_CHARS]
    d = os.path.join(SKILL_DIR, n)
    await asyncio.to_thread(os.makedirs, d, exist_ok=True)
    p = os.path.join(d, "SKILL.md")

    def _w() -> None:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content + "\n")
        os.replace(tmp, p)

    await asyncio.to_thread(_w)
    return True, ""


async def skill_delete(name: str) -> bool:
    n = _safe(name)
    if not n:
        return False
    d = os.path.join(SKILL_DIR, n)
    flat = os.path.join(SKILL_DIR, n + ".md")
    removed = False

    def _rm() -> None:
        nonlocal removed
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            removed = True
        elif os.path.isfile(flat):
            os.remove(flat)
            removed = True

    await asyncio.to_thread(_rm)
    return removed


async def skill_toggle(name: str, enabled: bool, *, pg: asyncpg.Pool | None = None) -> bool:
    n = _safe(name)
    if not n or not _skill_file(n):
        return False
    if pg is not None:
        await _set_state(pg, n, enabled)
    return True


async def skill_read(name: str) -> str | None:
    p = _skill_file(name)
    if not p:
        return None

    def _r() -> str | None:
        try:
            return open(p, encoding="utf-8").read().strip()[:4000]
        except OSError:
            return None

    return await asyncio.to_thread(_r)


# -------------------------------------------------------------- injection ---


async def build_skills_prompt(
    query: str = "",
    max_chars: int = MAX_INJECT_CHARS,
    *,
    pg: asyncpg.Pool | None = None,
) -> str:
    """Index of enabled skills + full bodies of top-2 relevant matches."""
    scanned = await asyncio.to_thread(_scan_sync)
    state: dict[str, int] = {}
    if pg is not None:
        state = await _state_map(pg)

    enabled: list[tuple[int, str, str, str]] = []
    for name, fm, body, _path in scanned:
        if state.get(name, 1) != 1:
            continue
        desc = str(fm.get("description") or "").strip()
        tags = [str(t) for t in fm.get("tags", [])] if isinstance(fm.get("tags"), list) else []
        score = _match_score(query, name, desc, tags)
        enabled.append((score, name, desc, body))

    if not enabled:
        return ""

    enabled.sort(key=lambda x: (-x[0], x[1]))
    index_lines = [f"- 🧩 {n}: {d}" for _s, n, d, _b in enabled]

    bodies: list[str] = []
    used = 0
    budget = max(600, max_chars - sum(len(l) for l in index_lines) - 220)
    for score, n, _d, body in enabled:
        if score <= 0 or len(bodies) >= 2:
            continue
        chunk = body[: min(len(body), max(0, budget - used))]
        if len(chunk) < 80:
            continue
        bodies.append(f"#### 🧩 {n}\n{chunk}")
        used += len(chunk) + 16

    parts = [
        "\n\n---\n## 🧩 Installed skills (observe during conversation)\n"
    ]
    parts += [l + "\n" for l in index_lines]
    if bodies:
        parts.append(
            "\n### Full instructions for skills relevant to this message:\n"
        )
        parts += [b + "\n" for b in bodies]
    return ("\n".join(parts))[:max_chars]


# ------------------------------------------------- legacy compat shims -----


async def skill_add(name: str, content: str) -> bool:
    ok, _err = await skill_write(name, content)
    return ok


async def skill_del(name: str) -> bool:
    return await skill_delete(name)


async def skill_list(pg: asyncpg.Pool | None = None) -> list[tuple[str, int]]:
    return [(it["name"], it["size"]) for it in await list_skills(pg=pg)]
