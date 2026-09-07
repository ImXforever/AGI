"""Customer tools — lookup, orders, notes, profile updates, BANT lead scoring."""

from __future__ import annotations

import json
from typing import Any

from asyncpg.pool import Pool

from app.logging_setup import get_logger

log = get_logger("tools.customers")

BANT_FIELDS = frozenset({"budget", "authority", "need", "timeline"})


async def get_customer(
    pool: Pool, *, customer_id: str | None = None, phone: str | None = None
) -> dict[str, Any]:
    """Fetch a customer by ID or phone number."""
    if customer_id:
        row = await pool.fetchrow(
            "SELECT * FROM customers WHERE id = $1",
            customer_id,
        )
    elif phone:
        row = await pool.fetchrow(
            "SELECT * FROM customers WHERE phone = $1",
            phone,
        )
    else:
        return {"error": "provide_customer_id_or_phone"}

    if row is None:
        return {"error": "customer_not_found"}
    return dict(row)


async def get_orders(pool: Pool, *, customer_id: str, limit: int = 20) -> dict[str, Any]:
    """Fetch recent orders for a customer."""
    rows = await pool.fetch(
        """
        SELECT id, status, total, currency, created_at, items
        FROM orders
        WHERE customer_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        customer_id,
        max(1, min(limit, 100)),
    )
    return {
        "customer_id": customer_id,
        "count": len(rows),
        "orders": [dict(r) for r in rows],
    }


async def add_note(
    pool: Pool, *, customer_id: str, body: str, actor: str = "system"
) -> dict[str, Any]:
    """Append a note to a customer's record."""
    if not body.strip():
        return {"error": "body_required"}

    row = await pool.fetchrow(
        """
        INSERT INTO customer_notes (customer_id, body, actor)
        VALUES ($1, $2, $3)
        RETURNING id, created_at
        """,
        customer_id,
        body.strip(),
        actor,
    )
    log.info(
        "note added",
        extra={"action": "tools.add_note", "entity": f"customer:{customer_id}"},
    )
    return {
        "note_id": row["id"],
        "customer_id": customer_id,
        "body": body.strip(),
        "actor": actor,
        "created_at": str(row["created_at"]),
    }


async def update_customer(
    pool: Pool,
    *,
    customer_id: str,
    name_ar: str | None = None,
    name_en: str | None = None,
    email: str | None = None,
    company: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update customer profile fields. Approval-gated — the change is staged."""
    existing = await pool.fetchrow("SELECT id FROM customers WHERE id = $1", customer_id)
    if existing is None:
        return {"error": "customer_not_found"}

    sets: list[str] = []
    args: list[Any] = []
    idx = 1

    for field_name, value in (
        ("name_ar", name_ar),
        ("name_en", name_en),
        ("email", email),
        ("company", company),
    ):
        if value is not None:
            sets.append(f"{field_name} = ${idx}")
            args.append(value)
            idx += 1

    if tags is not None:
        # tags is a jsonb column: asyncpg will not encode a python list for it.
        sets.append(f"tags = ${idx}::jsonb")
        args.append(json.dumps(tags, ensure_ascii=False))
        idx += 1

    if not sets:
        return {"error": "no_fields_to_update"}

    sets.append("updated_at = NOW()")
    args.append(customer_id)

    await pool.execute(
        f"UPDATE customers SET {', '.join(sets)} WHERE id = ${idx}",
        *args,
    )
    log.info(
        "customer updated",
        extra={"action": "tools.update_customer", "entity": f"customer:{customer_id}"},
    )
    return {
        "customer_id": customer_id,
        "updated_fields": [s.split(" =")[0] for s in sets if "updated_at" not in s],
    }


async def set_lead_score(
    pool: Pool,
    *,
    customer_id: str,
    budget: str = "",
    authority: str = "",
    need: str = "",
    timeline: str = "",
    score: int | None = None,
) -> dict[str, Any]:
    """Set lead score using BANT framework.

    If *score* is provided directly, it is used. Otherwise a heuristic
    score (0-100) is computed from the four BANT fields.

    Approval-gated: the score update is staged for admin review.
    """
    existing = await pool.fetchrow(
        "SELECT id, lead_score FROM customers WHERE id = $1",
        customer_id,
    )
    if existing is None:
        return {"error": "customer_not_found"}

    if score is None:
        filled = sum(1 for v in (budget, authority, need, timeline) if v.strip())
        score = min(100, filled * 25)

    score = max(0, min(100, int(score)))

    bant_data: dict[str, str] = {}
    for field_name, value in zip(BANT_FIELDS, (budget, authority, need, timeline)):
        if value.strip():
            bant_data[field_name] = value.strip()

    await pool.execute(
        """
        UPDATE customers
        SET lead_score = $1, lead_score_bant = $2::jsonb, updated_at = NOW()
        WHERE id = $3
        """,
        score,
        json.dumps(bant_data, ensure_ascii=False) if bant_data else None,
        customer_id,
    )

    log.info(
        "lead score set",
        extra={"action": "tools.set_lead_score", "entity": f"customer:{customer_id}"},
    )
    return {
        "customer_id": customer_id,
        "lead_score": score,
        "bant": bant_data or None,
        "previous_score": existing["lead_score"],
    }


REGISTRY: dict[str, dict[str, Any]] = {
    "get_customer": {
        "fn": get_customer,
        "description": "Fetch customer details by ID or phone.",
        "skill": "customer_agent",
        "params": {
            "customer_id": {"type": "integer", "required": False},
            "phone": {"type": "string", "required": False},
        },
        "mutating": False,
    },
    "get_orders": {
        "fn": get_orders,
        "description": "List recent orders for a customer.",
        "skill": "customer_agent",
        "params": {
            "customer_id": {"type": "integer", "required": True},
            "limit": {"type": "integer", "default": 20},
        },
        "mutating": False,
    },
    "add_note": {
        "min_role": "admin",
        "fn": add_note,
        "description": "Append a note to a customer record.",
        "skill": "customer_agent",
        "params": {
            "customer_id": {"type": "integer", "required": True},
            "body": {"type": "string", "required": True},
            "actor": {"type": "string", "default": "system"},
        },
        "mutating": True,
    },
    "update_customer": {
        "min_role": "admin",
        "fn": update_customer,
        "description": "Update customer profile fields. Approval-gated.",
        "skill": "customer_agent",
        "params": {
            "customer_id": {"type": "integer", "required": True},
            "name_ar": {"type": "string", "required": False},
            "name_en": {"type": "string", "required": False},
            "email": {"type": "string", "required": False},
            "company": {"type": "string", "required": False},
            "tags": {"type": "array", "required": False},
        },
        "mutating": True,
        "approval_required": True,
    },
    "set_lead_score": {
        "min_role": "admin",
        "fn": set_lead_score,
        "description": "Set lead score using BANT framework. Approval-gated.",
        "skill": "customer_agent",
        "params": {
            "customer_id": {"type": "integer", "required": True},
            "budget": {"type": "string", "default": ""},
            "authority": {"type": "string", "default": ""},
            "need": {"type": "string", "default": ""},
            "timeline": {"type": "string", "default": ""},
            "score": {"type": "integer", "required": False},
        },
        "mutating": True,
        "approval_required": True,
    },
}
