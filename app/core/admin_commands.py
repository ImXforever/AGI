"""Telegram admin commands — change every business variable from the chat (1.5.0).

Managers (``TELEGRAM_ADMIN_IDS``) can now read and change everything the admin
console's *Variables* and *Soul* pages expose, straight from Telegram:

    /admin                     help — every command below
    /vars [group]              list variables (company · bot · commerce · notify)
    /get <key>                 show one variable with its help text
    /set <key> <value>         change one variable (validated like the console)
    /reset <key>               back to the code default
    /soul [field]              show the agent soul (or one field)
    /soul <field> <text>       change a soul field (agent_name, tone, greeting …)
    /status                    version, pending approvals, channels
    /approvals                 last pending requests with their ids
    /reload                    drop the settings + soul caches

Everything is validated by the same code the console uses
(:mod:`app.core.business_settings` and :mod:`app.core.soul`), so a bad value
is refused with the same message and a good one applies to the very next
customer message — no redeploy. Only managers reach this module: the
orchestrator checks ``is_manager`` before calling :func:`handle_admin_command`.
Replies are plain text (no Markdown) so nothing can break Telegram rendering.
"""

from __future__ import annotations

import json
from typing import Any

from app.constants import APP_VERSION
from app.core.business_settings import (
    GROUPS,
    SPEC_BY_KEY,
    SettingError,
    defaults,
    load_settings,
    save_settings,
)
from app.core.business_settings import invalidate_cache as invalidate_settings
from app.core.soul import FIELDS as SOUL_FIELDS
from app.core.soul import invalidate_cache as invalidate_soul
from app.core.soul import load_soul, save_soul
from app.logging_setup import get_logger

log = get_logger("app.core.admin_commands")

COMMANDS: tuple[str, ...] = (
    "admin",
    "vars",
    "get",
    "set",
    "reset",
    "soul",
    "status",
    "approvals",
    "reload",
)

HELP_TEXT = (
    f"Zenovix admin · {APP_VERSION}\n"
    "Change every business variable from here — no redeploy.\n\n"
    "/vars — all variables (or /vars company · bot · commerce · notify)\n"
    "/get <key> — one variable with its help text\n"
    "/set <key> <value> — change it (validated like the console)\n"
    "/reset <key> — back to the default\n"
    "/soul — the agent soul · /soul tone — one field\n"
    "/soul <field> <text> — change a soul field\n"
    "/status — version, queue, channels\n"
    "/approvals — pending requests with ids\n"
    "/reload — drop caches\n\n"
    "Examples:\n"
    "/set bot_show_prices off\n"
    "/set support_phone +971 4570 1100\n"
    "/set bot_languages en, ar, fa\n"
    "/soul greeting Hello, I am Zenovix. How can I help?"
)

MAX_REPLY = 3500


def parse_admin_command(text: str) -> tuple[str, str] | None:
    """Return ``(command, argument_string)`` when *text* is an admin command.

    Accepts ``/set key value``, ``set key value`` (Telegram strips nothing) and
    ``/set@BotName key value``. Returns ``None`` for anything else so the
    normal router keeps working for managers too.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("/"):
        raw = raw[1:]
    head, _, rest = raw.partition(" ")
    head = head.split("@", 1)[0].strip().lower()
    if head not in COMMANDS:
        return None
    return head, rest.strip()


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if value is None or value == "":
        return "—"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(x) for x in value) or "—"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _clip(text: str) -> str:
    return text if len(text) <= MAX_REPLY else text[: MAX_REPLY - 20] + "\n… (truncated)"


def render_vars(values: dict[str, Any], group: str = "") -> str:
    """Grouped ``key = value`` listing; ``group`` filters to one group."""
    wanted = group.strip().lower()
    groups = [g for g in GROUPS if not wanted or g.key == wanted or g.title.lower() == wanted]
    if not groups:
        return "Unknown group. Use: " + " · ".join(g.key for g in GROUPS)
    lines: list[str] = []
    for g in groups:
        lines.append(f"[{g.key}] {g.title}")
        for spec in g.items:
            lines.append(f"  {spec.key} = {_fmt(values.get(spec.key, spec.default))}")
        lines.append("")
    lines.append("Change one: /set <key> <value> · details: /get <key>")
    return _clip("\n".join(lines).strip())


def render_get(values: dict[str, Any], key: str) -> str:
    spec = SPEC_BY_KEY.get(key.strip().lower())
    if spec is None:
        return f"Unknown key {key!r}. See /vars."
    parts = [
        f"{spec.key} ({spec.group}) — {spec.label}",
        f"value: {_fmt(values.get(spec.key, spec.default))}",
        f"default: {_fmt(spec.default)}",
        f"type: {spec.kind}" + (f" · options: {', '.join(spec.options)}" if spec.options else ""),
    ]
    if spec.min is not None or spec.max is not None:
        parts.append(
            f"range: {spec.min if spec.min is not None else '…'} – {spec.max if spec.max is not None else '…'}"
        )
    if spec.help:
        parts.append(f"help: {spec.help}")
    parts.append(f"change: /set {spec.key} <value>")
    return "\n".join(parts)


def render_soul(soul: Any, field: str = "") -> str:
    data = soul.as_dict() if hasattr(soul, "as_dict") else dict(soul)
    wanted = field.strip().lower()
    if wanted:
        if wanted not in SOUL_FIELDS:
            return f"Unknown soul field {field!r}. Fields: {', '.join(SOUL_FIELDS)}"
        return f"{wanted}:\n{_fmt(data.get(wanted))}\n\nchange: /soul {wanted} <text>"
    lines = [f"Agent soul (v{data.get('version', '?')})"]
    for name in SOUL_FIELDS:
        value = str(data.get(name) or "")
        short = value if len(value) <= 140 else value[:137] + "…"
        lines.append(f"  {name}: {short or '—'}")
    lines.append("")
    lines.append("one field: /soul tone · change: /soul tone <text>")
    return _clip("\n".join(lines))


async def _pending(services: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    pool = services.get("pg")
    if pool is None:
        return []
    try:
        rows = await pool.fetch(
            """
            SELECT id, skill, intent, channel, customer_id, created_at, draft_text
            FROM approvals WHERE status = 'pending'
            ORDER BY created_at DESC LIMIT $1
            """,
            limit,
        )
    except Exception:
        log.debug("admin_pending_failed", exc_info=True)
        return []
    return [dict(r) for r in rows]


async def handle_admin_command(
    command: str,
    arg: str,
    *,
    services: dict[str, Any],
    actor: str,
) -> str:
    """Execute one admin command and return the plain-text reply."""
    pool = services.get("pg")

    if command == "admin":
        return HELP_TEXT

    if command == "reload":
        invalidate_settings()
        invalidate_soul()
        return "Caches cleared. Settings and soul reload on the next message."

    if command == "vars":
        values = await load_settings(pool, use_cache=False)
        return render_vars(values, arg)

    if command == "get":
        if not arg:
            return "Usage: /get <key> — e.g. /get support_phone"
        values = await load_settings(pool, use_cache=False)
        return render_get(values, arg.split()[0])

    if command == "set":
        key, _, value = arg.partition(" ")
        key = key.strip().lower()
        if not key:
            return "Usage: /set <key> <value> — e.g. /set bot_show_prices off"
        spec = SPEC_BY_KEY.get(key)
        if spec is None:
            return f"Unknown key {key!r}. See /vars."
        if pool is None:
            return "Database unavailable — try again in a moment."
        try:
            values = await save_settings(pool, {key: value.strip()}, updated_by=f"tg:{actor}")
        except SettingError as exc:
            return f"Not saved — {exc}"
        except Exception as exc:
            log.warning("admin_set_failed", extra={"key": key, "error": str(exc)[:200]})
            return "Not saved — database error."
        await _audit("settings.set", actor, key, {"value": values.get(key)})
        return f"Saved. {key} = {_fmt(values.get(key))}\nApplies to the next customer message."

    if command == "reset":
        key = arg.strip().lower().split()[0] if arg.strip() else ""
        spec = SPEC_BY_KEY.get(key)
        if spec is None:
            return f"Unknown key {key!r}. See /vars." if key else "Usage: /reset <key>"
        if pool is None:
            return "Database unavailable — try again in a moment."
        value = defaults()[key]
        try:
            values = await save_settings(pool, {key: value}, updated_by=f"tg:{actor}")
        except Exception as exc:
            log.warning("admin_reset_failed", extra={"key": key, "error": str(exc)[:200]})
            return "Not reset — database error."
        await _audit("settings.reset", actor, key, {"value": values.get(key)})
        return f"Reset. {key} = {_fmt(values.get(key))}"

    if command == "soul":
        field, _, value = arg.partition(" ")
        field = field.strip().lower()
        if field and value.strip():
            if field not in SOUL_FIELDS:
                return f"Unknown soul field {field!r}. Fields: {', '.join(SOUL_FIELDS)}"
            if pool is None:
                return "Database unavailable — try again in a moment."
            try:
                soul = await save_soul(pool, {field: value.strip()}, updated_by=f"tg:{actor}")
            except Exception as exc:
                log.warning("admin_soul_failed", extra={"field": field, "error": str(exc)[:200]})
                return "Not saved — database error."
            await _audit("soul.set", actor, field, {"chars": len(value.strip())})
            return f"Saved soul.{field} (v{getattr(soul, 'version', '?')}). It is used from the next reply."
        soul = await load_soul(pool, use_cache=False)
        return render_soul(soul, field)

    if command == "status":
        registry = services.get("registry")
        channels = ", ".join(getattr(registry, "enabled", []) or []) or "—"
        pending = await _pending(services, limit=50)
        llm = services.get("llm")
        return (
            f"Zenovix {APP_VERSION}\n"
            f"pending approvals: {len(pending)}\n"
            f"channels: {channels}\n"
            f"llm: {'ready' if llm is not None else 'missing'}\n"
            f"database: {'ready' if pool is not None else 'missing'}\n"
            f"redis: {'ready' if services.get('redis') is not None else 'missing'}"
        )

    if command == "approvals":
        rows = await _pending(services)
        if not rows:
            return "No pending approvals."
        lines = [f"Pending approvals ({len(rows)}):"]
        for r in rows:
            draft = str(r.get("draft_text") or "").replace("\n", " ")
            lines.append(
                f"- {str(r.get('id'))[:8]} · {r.get('skill') or '-'} / {r.get('intent') or '-'}"
                f" · {r.get('channel') or '-'} · {draft[:70]}"
            )
        lines.append("Decide in the console (Approvals) or with the buttons under each alert.")
        return _clip("\n".join(lines))

    return HELP_TEXT


async def _audit(action: str, actor: str, key: str, details: dict[str, Any]) -> None:
    try:
        from app.storage.pg import audit

        await audit(
            action=f"telegram.{action}",
            actor=f"tg:{actor}",
            entity="settings",
            entity_id=key,
            details=details,
        )
    except Exception:
        log.debug("admin_audit_failed", exc_info=True)
