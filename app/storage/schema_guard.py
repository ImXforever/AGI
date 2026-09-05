"""Schema Guard — startup contract check between the code and the database.

Why this exists
---------------
The single largest source of runtime failures in this codebase was *schema
drift*: SQL statements scattered across ``app/`` referenced tables and columns
that the migrations never created (``products.unit_price``,
``approvals.skill``, ``tickets``, ``order_items``, …).  Every one of
those bugs surfaced only when a specific endpoint was hit in production, as an
opaque HTTP 500 with an ``UndefinedColumnError`` buried in the logs.

This module turns that whole class of bug into a *startup-time* check.  It
declares the contract the application relies on, verifies it against
``information_schema`` once at boot, and reports precisely what is missing.

Modes (``SCHEMA_GUARD_MODE``)
-----------------------------
``off``     — skip the check entirely.
``warn``    — log every violation and continue (default; safe for rolling deploys).
``strict``  — raise :class:`SchemaDriftError` and refuse to start.

The result is cached on the app state and surfaced by ``/healthz`` so operators
can see drift without reading logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from app.logging_setup import get_logger

log = get_logger(__name__)

MODE_OFF = "off"
MODE_WARN = "warn"
MODE_STRICT = "strict"
_VALID_MODES = (MODE_OFF, MODE_WARN, MODE_STRICT)


class SchemaDriftError(RuntimeError):
    """Raised in ``strict`` mode when the database is missing required objects."""


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------
# Only columns the application actually reads or writes are listed.  Keeping
# this deliberately narrow means the check stays useful instead of becoming a
# duplicate of the DDL that nobody updates.

REQUIRED_SCHEMA: dict[str, tuple[str, ...]] = {
    "admins": ("id", "username", "password_hash"),
    "customers": (
        "id",
        "external_id",
        "channel",
        "display_name",
        "name_ar",
        "name_en",
        "phone",
        "email",
        "lead_score",
        "lead_score_bant",
        "tags",
        "company",
    ),
    "conversations": ("id", "customer_id", "channel", "status", "hitl_pending"),
    "messages": ("id", "conversation_id", "sender_role", "text", "metadata", "external_ref"),
    "outbound_messages": (
        "id",
        "conversation_id",
        "channel",
        "recipient_id",
        "content",
        "approval_id",
        "external_ref",
        "metadata",
        "status",
    ),
    "approvals": (
        "id",
        "conversation_id",
        "customer_id",
        "channel",
        "status",
        "payload",
        "skill",
        "intent",
        "draft_text",
        "confidence",
        "needs_hitl",
        "decided_at",
        "actor",
        "note",
        "edited_text",
    ),
    "attachments": (
        "id",
        "conversation_id",
        "message_id",
        "filename",
        "content_type",
        "r2_key",
        "size",
        "metadata",
    ),
    "approval_execution_ledger": ("approval_id",),
    "tool_executions": ("id", "approval_id", "tool_name", "result"),
    "products": (
        "id",
        "sku",
        "name_ar",
        "name_en",
        "category",
        "unit",
        "base_price",
        "unit_price",
        "currency",
        "stock_qty",
        "reorder_point",
        "discount_tiers",
        "description_ar",
        "description_en",
        "specs",
        "is_active",
    ),
    "product_specs": ("product_id", "technical_specs", "safety_data", "compliance_notes"),
    "msds_documents": ("id", "product_id", "title_ar", "title_en", "r2_key", "version", "language"),
    "quotes": ("id", "customer_id", "status", "items", "subtotal", "tax", "total", "currency"),
    "orders": ("id", "customer_id", "quote_id", "order_number", "status", "total", "currency"),
    "order_items": ("id", "order_id", "product_id", "quantity", "unit_price"),
    "tickets": (
        "id",
        "customer_id",
        "subject",
        "description",
        "status",
        "priority",
        "assigned_to",
        "severity",
        "channel",
        "is_safety",
    ),
    "ticket_notes": ("id", "ticket_id", "author", "content"),
    "ticket_events": ("id", "ticket_id", "actor", "action", "body"),
    "customer_notes": ("id", "customer_id", "body", "actor"),
    "purchases": ("id", "buyer_id", "product_id", "price_credits", "created_at"),
    "user_memories": ("id", "user_id", "kind", "content", "importance", "source", "dedup_key"),
    "user_profile": (
        "user_id",
        "buys_count",
        "total_spent_credits",
        "last_categories",
        "persona",
        "interests",
    ),
    "faq": (
        "id",
        "question_ar",
        "question_en",
        "answer_ar",
        "answer_en",
        "category",
        "language",
        "is_active",
    ),
    "troubleshooting": (
        "id",
        "title_ar",
        "title_en",
        "problem_ar",
        "problem_en",
        "solution_ar",
        "solution_en",
        "category",
        "severity",
        "is_active",
    ),
    "fallback_templates": ("id", "key", "name_ar", "body_ar", "channel", "is_active"),
    "audit_log": ("id", "actor", "action", "entity_type", "entity_id", "old_value", "new_value"),
    "conversation_turns": ("id", "user_id", "role", "content"),
    "kb_notes": ("id", "user_id", "topic", "content", "source"),
    "settings": ("key",),
}

# Views are checked for existence only (their columns follow the base table).
REQUIRED_VIEWS: tuple[str, ...] = ("catalog_items",)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaReport:
    """Outcome of a schema verification pass."""

    ok: bool
    mode: str
    missing_tables: tuple[str, ...] = ()
    missing_columns: tuple[str, ...] = ()
    missing_views: tuple[str, ...] = ()
    checked_tables: int = 0
    checked_columns: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def violation_count(self) -> int:
        return len(self.missing_tables) + len(self.missing_columns) + len(self.missing_views)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "violations": self.violation_count,
            "missing_tables": list(self.missing_tables),
            "missing_columns": list(self.missing_columns),
            "missing_views": list(self.missing_views),
            "checked_tables": self.checked_tables,
            "checked_columns": self.checked_columns,
        }

    def summary(self) -> str:
        if self.ok:
            return (
                f"schema OK — {self.checked_tables} tables / "
                f"{self.checked_columns} columns verified"
            )
        parts: list[str] = []
        if self.missing_tables:
            parts.append(f"missing tables: {', '.join(self.missing_tables)}")
        if self.missing_views:
            parts.append(f"missing views: {', '.join(self.missing_views)}")
        if self.missing_columns:
            parts.append(f"missing columns: {', '.join(self.missing_columns)}")
        return "schema drift detected — " + "; ".join(parts)


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------


def _env_mode() -> str:
    """Read SCHEMA_GUARD_MODE from the same source the rest of the config uses.

    ``.env`` values are not exported into ``os.environ``, so fall back to the
    dotenv defaults before giving up — otherwise the setting would silently be
    ignored for anyone configuring the app via a ``.env`` file.
    """
    value = os.environ.get("SCHEMA_GUARD_MODE")
    if value:
        return value
    return _dotenv_lookup().get("SCHEMA_GUARD_MODE", MODE_WARN)


def _dotenv_lookup() -> dict[str, str]:
    """Values from the project ``.env`` file (empty when unavailable)."""
    try:
        from app.config import _dotenv_defaults

        return _dotenv_defaults()
    except Exception:
        return {}


def resolve_mode(raw: str | None = None) -> str:
    """Resolve the guard mode from an explicit value or ``SCHEMA_GUARD_MODE``."""
    value = (raw if raw is not None else _env_mode()).strip().lower()
    if value not in _VALID_MODES:
        log.warning(
            "invalid_schema_guard_mode",
            extra={"action": "schema_guard", "value": value, "fallback": MODE_WARN},
        )
        return MODE_WARN
    return value


def diff_schema(
    actual: dict[str, set[str]],
    views: set[str],
    *,
    expected: dict[str, tuple[str, ...]] | None = None,
    expected_views: tuple[str, ...] = REQUIRED_VIEWS,
    mode: str = MODE_WARN,
) -> SchemaReport:
    """Compare an observed schema against the contract.

    Pure function — no I/O — so it is trivially unit-testable.  ``actual`` maps
    table name to the set of its column names.
    """
    contract = expected if expected is not None else REQUIRED_SCHEMA

    missing_tables: list[str] = []
    missing_columns: list[str] = []
    checked_columns = 0

    for table, columns in sorted(contract.items()):
        present = actual.get(table)
        if present is None:
            missing_tables.append(table)
            continue
        for column in columns:
            checked_columns += 1
            if column not in present:
                missing_columns.append(f"{table}.{column}")

    missing_views = [v for v in expected_views if v not in views and v not in actual]

    ok = not (missing_tables or missing_columns or missing_views)
    return SchemaReport(
        ok=ok,
        mode=mode,
        missing_tables=tuple(missing_tables),
        missing_columns=tuple(missing_columns),
        missing_views=tuple(missing_views),
        checked_tables=len(contract),
        checked_columns=checked_columns,
    )


async def fetch_actual_schema(pool: Any) -> tuple[dict[str, set[str]], set[str]]:
    """Read tables/columns and view names from ``information_schema``."""
    rows = await pool.fetch(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    actual: dict[str, set[str]] = {}
    for row in rows:
        actual.setdefault(row["table_name"], set()).add(row["column_name"])

    view_rows = await pool.fetch(
        "SELECT table_name FROM information_schema.views WHERE table_schema = 'public'"
    )
    views = {r["table_name"] for r in view_rows}
    return actual, views


async def verify_schema(pool: Any, *, mode: str | None = None) -> SchemaReport:
    """Verify the live database against :data:`REQUIRED_SCHEMA`.

    Returns a :class:`SchemaReport`.  Raises :class:`SchemaDriftError` only when
    running in ``strict`` mode and drift was found.
    """
    resolved = resolve_mode(mode)

    if resolved == MODE_OFF:
        log.info("schema_guard_disabled", extra={"action": "schema_guard"})
        return SchemaReport(ok=True, mode=MODE_OFF)

    actual, views = await fetch_actual_schema(pool)
    report = diff_schema(actual, views, mode=resolved)

    if report.ok:
        log.info(
            "schema_guard_ok",
            extra={
                "action": "schema_guard",
                "tables": report.checked_tables,
                "columns": report.checked_columns,
            },
        )
        return report

    log.error(
        "schema_guard_drift",
        extra={
            "action": "schema_guard",
            "mode": resolved,
            "violations": report.violation_count,
            "missing_tables": ",".join(report.missing_tables),
            "missing_views": ",".join(report.missing_views),
            "missing_columns": ",".join(report.missing_columns[:25]),
        },
    )

    if resolved == MODE_STRICT:
        raise SchemaDriftError(report.summary())

    return report
