"""Sales tools — quote creation with line items, tax, discount tiers (approval-gated)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from asyncpg.pool import Pool

from app.config import get_config
from app.logging_setup import get_logger

log = get_logger("tools.sales")


from app.core.tools.catalog import _as_json_list


async def create_quote(
    pool: Pool,
    *,
    customer_id: str,
    items: list[dict[str, Any]],
    notes: str = "",
) -> dict[str, Any]:
    """Build a quote with line items, tiered discounts, and tax.

    Each item in *items* must contain ``product_id`` and ``quantity``.
    Optional keys per item: ``unit_price`` override, ``discount_pct`` override.

    This tool is approval-gated: the quote is stored with status ``pending``
    and must be approved by an admin before it is sent to the customer.
    """
    cfg = get_config()
    tax_rate = cfg.domain.tax_rate
    currency = cfg.domain.currency
    valid_days = cfg.domain.quote_valid_days

    if not items:
        return {"error": "items_required"}

    line_items: list[dict[str, Any]] = []
    subtotal = 0.0

    for item in items:
        product_id = item.get("product_id")
        quantity = max(1, int(item.get("quantity", 1)))
        if not product_id:
            return {"error": "item_missing_product_id"}

        row = await pool.fetchrow(
            """
            SELECT id, sku, name_ar, name_en, unit_price, currency, discount_tiers, stock_qty
            FROM products
            WHERE id = $1 AND is_active = TRUE
            """,
            product_id,
        )
        if row is None:
            return {"error": "product_not_found", "product_id": product_id}

        base_price = float(row["unit_price"])
        unit_price = float(item["unit_price"]) if "unit_price" in item else base_price
        product_currency = row["currency"] or currency

        if "discount_pct" in item:
            discount_pct = float(item["discount_pct"])
        else:
            discount_pct = 0.0
            # jsonb arrives as a str from asyncpg; decode before treating it
            # as a list of dicts (same bug as catalog.get_price had).
            for tier in sorted(
                _as_json_list(row["discount_tiers"]),
                key=lambda t: t.get("min_qty", 0),
                reverse=True,
            ):
                if quantity >= tier.get("min_qty", 0):
                    discount_pct = tier.get("discount_pct", 0.0)
                    break

        discounted_unit = unit_price * (1 - discount_pct / 100)
        line_total = round(discounted_unit * quantity, 4)

        line_items.append(
            {
                "product_id": row["id"],
                "sku": row["sku"],
                "name_ar": row["name_ar"],
                "name_en": row["name_en"],
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "discounted_unit_price": round(discounted_unit, 4),
                "line_total": line_total,
                "currency": product_currency,
            }
        )
        subtotal += line_total

    tax_amount = round(subtotal * tax_rate, 4)
    total = round(subtotal + tax_amount, 4)
    # valid_until is timestamptz, so hand asyncpg a datetime, not a date.
    valid_until = datetime.now(UTC) + timedelta(days=valid_days)

    quote_row = await pool.fetchrow(
        """
        INSERT INTO quotes (
            customer_id, items, subtotal, tax,
            total, currency, notes, valid_until, status
        ) VALUES ($1, $2::jsonb, $3, $4, $5, $6, $7, $8, 'draft')
        RETURNING id, created_at
        """,
        customer_id,
        # items is jsonb: asyncpg cannot encode a python list directly.
        json.dumps(line_items, ensure_ascii=False, default=str),
        subtotal,
        tax_amount,
        total,
        currency,
        notes,
        valid_until,
    )

    log.info(
        "quote created",
        extra={
            "action": "tools.create_quote",
            "entity": f"quote:{quote_row['id']}",
            "customer_id": customer_id,
            "total": total,
        },
    )

    return {
        "quote_id": quote_row["id"],
        "created_at": str(quote_row["created_at"]),
        "customer_id": customer_id,
        "items": line_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "currency": currency,
        "valid_until": str(valid_until),
        "status": "pending",
        "notes": notes,
    }


REGISTRY: dict[str, dict[str, Any]] = {
    "create_quote": {
        "min_role": "admin",
        "fn": create_quote,
        "description": (
            "Create a sales quote with line items, automatic discount tiers, "
            "and tax calculation. Approval-gated."
        ),
        "skill": "sales_agent",
        "params": {
            "customer_id": {"type": "integer", "required": True},
            "items": {
                "type": "array",
                "required": True,
                "items": {
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "integer", "default": 1},
                    "unit_price": {"type": "number", "required": False},
                    "discount_pct": {"type": "number", "required": False},
                },
            },
            "notes": {"type": "string", "default": ""},
        },
        "mutating": True,
        "approval_required": True,
    },
}
