"""Manager-editable business variables (1.4.0).

Environment variables (``app/config.py``) are *deployment* settings — secrets,
URLs, ports — and need a redeploy.  The values here are *business* settings a
non-technical manager changes from the admin console without touching
Railway: company contact details, what the bot shows, quote rules and which
notifications fire.  They live in the existing ``settings`` table
(``key TEXT PRIMARY KEY, value JSONB``) and fall back to code defaults, so an
empty table is a fully working system.

The spec below is the single source of truth: the admin page renders it, the
API validates against it and the bot reads it through :func:`get_settings`.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.business_settings")

CACHE_TTL_SECONDS = 20.0


@dataclass(frozen=True)
class SettingSpec:
    key: str
    group: str
    label: str
    kind: str  # text | textarea | number | bool | select | list
    default: Any
    help: str = ""
    options: tuple[str, ...] = ()
    min: float | None = None
    max: float | None = None
    bot: bool = False  # True → the Telegram bot reads this value


@dataclass(frozen=True)
class SettingGroup:
    key: str
    title: str
    hint: str
    items: tuple[SettingSpec, ...] = field(default_factory=tuple)


LANGUAGE_CODES: tuple[str, ...] = (
    "en", "fa", "ar", "es", "fr", "de", "it", "pt", "tr", "ru", "zh", "ja",
    "ko", "hi", "nl", "uk", "sv", "id", "ms", "vi", "he",
)  # fmt: skip

SPECS: tuple[SettingSpec, ...] = (
    # --- Company -----------------------------------------------------------
    SettingSpec(
        "company_name",
        "company",
        "Company name",
        "text",
        "Zenovix",
        "Shown in the bot welcome and quote messages.",
        bot=True,
    ),
    SettingSpec(
        "company_short",
        "company",
        "Short name",
        "text",
        "ZX",
        "Prefix for request references (ZX-…).",
        bot=True,
    ),
    SettingSpec(
        "company_tagline",
        "company",
        "Tagline",
        "text",
        "AI & Digital Technology · Dubai",
        "One line under the welcome title.",
        bot=True,
    ),
    SettingSpec(
        "support_email",
        "company",
        "Support e-mail",
        "text",
        "",
        "Empty → SUPPORT_CONTACT from the environment.",
        bot=True,
    ),
    SettingSpec("support_phone", "company", "Phone", "text", "+971 4570 1100", "", bot=True),
    SettingSpec(
        "support_whatsapp",
        "company",
        "WhatsApp link",
        "text",
        "https://wa.me/97145701100",
        "Full https://wa.me/… link.",
        bot=True,
    ),
    SettingSpec("website_url", "company", "Website", "text", "https://zenovix.ae", "", bot=True),
    SettingSpec(
        "office_address",
        "company",
        "Office address",
        "textarea",
        "Office 2703, Aspect Tower, Business Bay, Dubai, UAE",
        "",
        bot=True,
    ),
    SettingSpec(
        "office_hours",
        "company",
        "Office hours",
        "text",
        "Mon–Fri 9:00–18:00 GST (UTC+4)",
        "",
        bot=True,
    ),
    SettingSpec(
        "map_url",
        "company",
        "Map link",
        "text",
        "https://www.google.com/maps?cid=9389408557797241110",
        "",
        bot=True,
    ),
    # --- Bot ---------------------------------------------------------------
    SettingSpec(
        "bot_default_language",
        "bot",
        "Default language",
        "select",
        "en",
        "Used before a customer picks a language.",
        options=LANGUAGE_CODES,
        bot=True,
    ),
    SettingSpec(
        "bot_languages",
        "bot",
        "Languages offered",
        "list",
        ["en", "fa", "ar", "tr", "ru", "de", "fr", "es"],
        "Language picker buttons, in this order. Codes: " + ", ".join(LANGUAGE_CODES) + ".",
        bot=True,
    ),
    SettingSpec(
        "bot_ask_language_on_start",
        "bot",
        "Ask language on /start",
        "bool",
        True,
        "Off → /start opens the menu in the default language.",
        bot=True,
    ),
    SettingSpec(
        "bot_show_prices",
        "bot",
        "Show prices in the bot",
        "bool",
        True,
        "Off → every product shows “price on request”.",
        bot=True,
    ),
    SettingSpec("bot_show_images", "bot", "Send product images", "bool", True, "", bot=True),
    SettingSpec(
        "bot_order_flow",
        "bot",
        "Order flow (category → product → quantity)",
        "bool",
        True,
        "Off → the Products button shows a text list only.",
        bot=True,
    ),
    SettingSpec(
        "bot_custom_quantity",
        "bot",
        "Allow typed quantities",
        "bool",
        True,
        "Off → only the preset quantity buttons.",
        bot=True,
    ),
    SettingSpec(
        "bot_show_my_requests",
        "bot",
        "“My requests” button",
        "bool",
        True,
        "Lets a customer see the status of their own requests.",
        bot=True,
    ),
    SettingSpec(
        "bot_support_ticket", "bot", "Support tickets from the bot", "bool", True, "", bot=True
    ),
    SettingSpec(
        "bot_emergency_keyword", "bot", "Emergency keyword", "text", "emergency", "", bot=True
    ),
    SettingSpec(
        "bot_welcome_extra",
        "bot",
        "Extra welcome line",
        "textarea",
        "",
        "Optional sentence appended to the welcome message (English; shown to everyone).",
        bot=True,
    ),
    # --- Commerce ------------------------------------------------------------
    SettingSpec(
        "quote_currency",
        "commerce",
        "Quote currency",
        "text",
        "",
        "Empty → CURRENCY from the environment (USD).",
        bot=True,
    ),
    SettingSpec(
        "quote_tax_rate",
        "commerce",
        "Tax rate",
        "number",
        None,
        "0.05 = 5 %. Empty → TAX_RATE from the environment.",
        min=0,
        max=1,
    ),
    SettingSpec(
        "quote_valid_days",
        "commerce",
        "Quote validity (days)",
        "number",
        None,
        "Empty → QUOTE_VALID_DAYS from the environment.",
        min=1,
        max=365,
    ),
    SettingSpec(
        "quote_min_quantity",
        "commerce",
        "Minimum quantity",
        "number",
        1,
        "Requests below this are refused by the bot.",
        min=1,
        bot=True,
    ),
    SettingSpec(
        "quote_reference_prefix",
        "commerce",
        "Request reference prefix",
        "text",
        "ZX",
        "ZX → ZX-7F3A2B",
        bot=True,
    ),
    SettingSpec(
        "quote_manager_note",
        "commerce",
        "Note sent with every approved request",
        "textarea",
        "Scope, timeline and price are confirmed in the formal proposal.",
        "",
        bot=True,
    ),
    # --- Notifications -------------------------------------------------------
    SettingSpec(
        "notify_new_request",
        "notify",
        "Telegram alert for new requests",
        "bool",
        True,
        "Managers get Approve / Reject buttons.",
        bot=True,
    ),
    SettingSpec(
        "notify_new_ticket", "notify", "Telegram alert for new tickets", "bool", True, "", bot=True
    ),
    SettingSpec(
        "notify_customer_on_decision",
        "notify",
        "Tell the customer when a request is decided",
        "bool",
        True,
        "",
        bot=True,
    ),
    SettingSpec(
        "notify_daily_summary_hour",
        "notify",
        "Daily summary hour (0–23, empty = off)",
        "number",
        None,
        "Reserved for the report scheduler.",
        min=0,
        max=23,
    ),
)

GROUPS: tuple[SettingGroup, ...] = (
    SettingGroup(
        "company",
        "Company",
        "What customers see in Contact and in quotes.",
        tuple(s for s in SPECS if s.group == "company"),
    ),
    SettingGroup(
        "bot",
        "Telegram bot",
        "Menu behaviour. Changes apply to the next message, no redeploy.",
        tuple(s for s in SPECS if s.group == "bot"),
    ),
    SettingGroup(
        "commerce",
        "Quotes & orders",
        "Rules for the order flow and quotes.",
        tuple(s for s in SPECS if s.group == "commerce"),
    ),
    SettingGroup(
        "notify",
        "Notifications",
        "Who gets told, and when.",
        tuple(s for s in SPECS if s.group == "notify"),
    ),
)

SPEC_BY_KEY: dict[str, SettingSpec] = {s.key: s for s in SPECS}

_cache: dict[str, Any] = {"at": 0.0, "values": None}


def defaults() -> dict[str, Any]:
    return {s.key: (list(s.default) if isinstance(s.default, list) else s.default) for s in SPECS}


def spec_payload() -> list[dict[str, Any]]:
    """JSON-friendly description of every group/field for the admin page."""
    out: list[dict[str, Any]] = []
    for group in GROUPS:
        out.append(
            {
                "key": group.key,
                "title": group.title,
                "hint": group.hint,
                "items": [
                    {
                        "key": s.key,
                        "label": s.label,
                        "kind": s.kind,
                        "default": s.default,
                        "help": s.help,
                        "options": list(s.options),
                        "min": s.min,
                        "max": s.max,
                        "bot": s.bot,
                    }
                    for s in group.items
                ],
            }
        )
    return out


class SettingError(ValueError):
    pass


def coerce(spec: SettingSpec, value: Any) -> Any:
    """Validate one value against its spec; raise SettingError with a message."""
    if value is None or (
        isinstance(value, str)
        and value.strip() == ""
        and spec.kind != "text"
        and spec.kind != "textarea"
    ):
        return (
            None
            if spec.kind == "number"
            else (list(spec.default) if spec.kind == "list" else spec.default)
        )
    if spec.kind in ("text", "textarea"):
        text = str(value).strip()
        if len(text) > (4000 if spec.kind == "textarea" else 400):
            raise SettingError(f"{spec.label}: too long")
        return text
    if spec.kind == "bool":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if spec.kind == "number":
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise SettingError(f"{spec.label}: must be a number") from exc
        if spec.min is not None and number < spec.min:
            raise SettingError(f"{spec.label}: minimum is {spec.min:g}")
        if spec.max is not None and number > spec.max:
            raise SettingError(f"{spec.label}: maximum is {spec.max:g}")
        return int(number) if number == int(number) else number
    if spec.kind == "select":
        text = str(value).strip().lower()
        if spec.options and text not in spec.options:
            raise SettingError(f"{spec.label}: must be one of {', '.join(spec.options)}")
        return text
    if spec.kind == "list":
        if isinstance(value, str):
            items = [x.strip() for x in value.replace("\n", ",").split(",")]
        elif isinstance(value, (list, tuple)):
            items = [str(x).strip() for x in value]
        else:
            raise SettingError(f"{spec.label}: must be a list")
        items = [x.lower() for x in items if x]
        if spec.key == "bot_languages":
            bad = [x for x in items if x not in LANGUAGE_CODES]
            if bad:
                raise SettingError(f"{spec.label}: unknown language code(s) {', '.join(bad)}")
            if not items:
                raise SettingError(f"{spec.label}: at least one language")
            # keep order, drop duplicates
            items = list(dict.fromkeys(items))
        return items
    return value


def validate(values: dict[str, Any]) -> dict[str, Any]:
    """Return only known keys, coerced. Unknown keys raise."""
    clean: dict[str, Any] = {}
    for key, value in (values or {}).items():
        spec = SPEC_BY_KEY.get(str(key))
        if spec is None:
            raise SettingError(f"unknown setting {key!r}")
        clean[spec.key] = coerce(spec, value)
    return clean


def merge(stored: dict[str, Any]) -> dict[str, Any]:
    """Defaults overlaid with stored values (bad stored values are ignored)."""
    values = defaults()
    for key, raw in (stored or {}).items():
        spec = SPEC_BY_KEY.get(key)
        if spec is None:
            continue
        try:
            values[key] = coerce(spec, raw)
        except SettingError:
            continue
    return values


def invalidate_cache() -> None:
    _cache["at"] = 0.0
    _cache["values"] = None


async def load_settings(pool: Any | None, *, use_cache: bool = True) -> dict[str, Any]:
    """Merged settings. Never raises: on any DB problem the defaults win."""
    now = time.monotonic()
    if use_cache and _cache["values"] is not None and now - float(_cache["at"]) < CACHE_TTL_SECONDS:
        return dict(_cache["values"])
    stored: dict[str, Any] = {}
    if pool is not None:
        try:
            rows = await pool.fetch(
                "SELECT key, value FROM settings WHERE key = ANY($1::text[])",
                list(SPEC_BY_KEY),
            )
            for row in rows:
                raw = row["value"]
                if isinstance(raw, (str, bytes)):
                    try:
                        raw = json.loads(raw)
                    except (ValueError, TypeError):
                        pass
                stored[str(row["key"])] = raw
        except Exception as exc:
            log.debug(
                "business settings load failed",
                extra={"action": "business.load", "error": str(exc)},
            )
    values = merge(stored)
    _cache["at"] = now
    _cache["values"] = dict(values)
    return values


async def save_settings(
    pool: Any, values: dict[str, Any], *, updated_by: str = ""
) -> dict[str, Any]:
    clean = validate(values)
    for key, value in clean.items():
        spec = SPEC_BY_KEY[key]
        await pool.execute(
            """
            INSERT INTO settings (key, value, description, updated_by, updated_at)
            VALUES ($1, $2::jsonb, $3, $4, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                description = EXCLUDED.description,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            """,
            key,
            json.dumps(value, ensure_ascii=False),
            spec.label,
            updated_by[:80],
        )
    invalidate_cache()
    log.info(
        "business settings saved",
        extra={"action": "business.save", "keys": ",".join(sorted(clean)), "actor": updated_by},
    )
    return await load_settings(pool, use_cache=False)


async def get_settings(services: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convenience for the bot: settings via the shared pool (cached)."""
    pool = (services or {}).get("pg")
    if pool is None:
        try:
            from app.storage.pg import get_pool

            pool = await get_pool()
        except Exception:
            pool = None
    return await load_settings(pool)
