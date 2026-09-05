"""Catalog tools — read-only product search, pricing, stock and recommendations."""

from __future__ import annotations

import json
from typing import Any

from asyncpg.pool import Pool

from app.logging_setup import get_logger

log = get_logger("tools.catalog")


def _as_json_list(value: Any) -> list[dict[str, Any]]:
    """Decode a jsonb column into a list of dicts.

    asyncpg returns jsonb as a raw ``str`` unless a codec is registered, so
    callers that treated it as a list silently crashed with AttributeError.
    """
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return []
    if isinstance(value, list):
        return [t for t in value if isinstance(t, dict)]
    return []


async def search_products(pool: Pool, *, query: str, limit: int = 10) -> dict[str, Any]:
    """Full-text ILIKE search across product name, SKU and description."""
    rows = await pool.fetch(
        """
        SELECT id, sku, name_ar, name_en, description_ar, description_en,
               category, unit_price, currency
        FROM products
        WHERE is_active = TRUE
          AND (
              name_ar ILIKE '%' || $1 || '%'
              OR name_en ILIKE '%' || $1 || '%'
              OR sku ILIKE '%' || $1 || '%'
              OR COALESCE(description_ar, '') ILIKE '%' || $1 || '%'
              OR COALESCE(description_en, '') ILIKE '%' || $1 || '%'
          )
        ORDER BY name_en
        LIMIT $2
        """,
        query,
        max(1, min(limit, 50)),
    )
    return {
        "count": len(rows),
        "products": [dict(r) for r in rows],
    }


async def get_product_specs(pool: Pool, *, product_id: str) -> dict[str, Any]:
    """Fetch full specifications for a single product."""
    row = await pool.fetchrow(
        """
        SELECT p.*, s.technical_specs, s.safety_data, s.compliance_notes
        FROM products p
        LEFT JOIN product_specs s ON s.product_id = p.id
        WHERE p.id = $1
        """,
        product_id,
    )
    if row is None:
        return {"error": "product_not_found", "product_id": product_id}
    return dict(row)


async def get_price(pool: Pool, *, product_id: str, quantity: int = 1) -> dict[str, Any]:
    """Return unit price, applicable discount tier, and line total."""
    row = await pool.fetchrow(
        """
        SELECT id, unit_price, currency, discount_tiers
        FROM products
        WHERE id = $1 AND is_active = TRUE
        """,
        product_id,
    )
    if row is None:
        return {"error": "product_not_found", "product_id": product_id}

    unit_price = float(row["unit_price"])
    tiers = _as_json_list(row["discount_tiers"])
    discount_pct = 0.0

    for tier in sorted(tiers, key=lambda t: t.get("min_qty", 0), reverse=True):
        if quantity >= tier.get("min_qty", 0):
            discount_pct = tier.get("discount_pct", 0.0)
            break

    discounted_unit = unit_price * (1 - discount_pct / 100)
    total = discounted_unit * quantity

    return {
        "product_id": row["id"],
        "unit_price": unit_price,
        "currency": row["currency"],
        "quantity": quantity,
        "discount_pct": discount_pct,
        "discounted_unit_price": round(discounted_unit, 4),
        "total": round(total, 4),
    }


async def check_stock(pool: Pool, *, product_id: str) -> dict[str, Any]:
    """Check current stock level and availability status."""
    row = await pool.fetchrow(
        """
        SELECT id, sku, stock_qty, reorder_point, is_active
        FROM products
        WHERE id = $1
        """,
        product_id,
    )
    if row is None:
        return {"error": "product_not_found", "product_id": product_id}

    stock = row["stock_qty"]
    reorder = row["reorder_point"] or 0
    status = "in_stock" if stock > 0 else "out_of_stock"
    if stock > 0 and stock <= reorder:
        status = "low_stock"

    return {
        "product_id": row["id"],
        "sku": row["sku"],
        "stock_qty": stock,
        "reorder_point": reorder,
        "status": status,
        "is_active": row["is_active"],
    }


async def list_products(
    pool: Pool,
    *,
    category: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """List active products with optional category filter and pagination."""
    conditions = ["p.is_active = TRUE"]
    args: list[Any] = []
    idx = 1

    if category:
        conditions.append(f"p.category = ${idx}")
        args.append(category)
        idx += 1

    where = " AND ".join(conditions)
    args.extend([max(0, offset), max(1, min(limit, 100))])

    rows = await pool.fetch(
        f"""
        SELECT p.id, p.sku, p.name_ar, p.name_en, p.category,
               p.unit_price, p.currency, p.stock_qty, p.is_active
        FROM products p
        WHERE {where}
        ORDER BY p.name_en
        OFFSET ${idx} LIMIT ${idx + 1}
        """,
        *args,
    )
    return {
        "count": len(rows),
        "offset": offset,
        "products": [dict(r) for r in rows],
    }


async def recommend_products(pool: Pool, *, context: str, limit: int = 3) -> dict[str, Any]:
    """Recommend up to `limit` products based on keyword context.

    This is a keyword-match heuristic; the orchestrator agent can refine via
    follow-up calls to `search_products` or `get_product_specs`.
    """
    limit = max(1, min(limit, 5))
    words = [w.strip() for w in context.replace(",", " ").split() if len(w.strip()) >= 2]
    if not words:
        return {"count": 0, "recommendations": [], "hint": "provide_more_context"}

    ilike_parts: list[str] = []
    args: list[Any] = []
    for i, word in enumerate(words[:5]):
        args.append(word)
        ilike_parts.append(
            f"(p.name_ar ILIKE '%' || ${i + 1} || '%' "
            f"OR p.name_en ILIKE '%' || ${i + 1} || '%' "
            f"OR p.category ILIKE '%' || ${i + 1} || '%')"
        )

    where = " OR ".join(ilike_parts)
    args.append(limit)

    rows = await pool.fetch(
        f"""
        SELECT DISTINCT p.id, p.sku, p.name_ar, p.name_en, p.category,
               p.unit_price, p.currency, p.stock_qty
        FROM products p
        WHERE p.is_active = TRUE AND ({where})
        ORDER BY p.name_en
        LIMIT ${len(args)}
        """,
        *args,
    )
    return {
        "count": len(rows),
        "recommendations": [dict(r) for r in rows],
    }


async def get_discount_table(pool: Pool, *, product_id: str) -> dict[str, Any]:
    """Return all discount tiers for a product."""
    row = await pool.fetchrow(
        """
        SELECT id, sku, name_ar, name_en, discount_tiers
        FROM products
        WHERE id = $1 AND is_active = TRUE
        """,
        product_id,
    )
    if row is None:
        return {"error": "product_not_found", "product_id": product_id}
    return {
        "product_id": row["id"],
        "sku": row["sku"],
        "name_ar": row["name_ar"],
        "name_en": row["name_en"],
        "tiers": _as_json_list(row["discount_tiers"]),
    }


REGISTRY: dict[str, dict[str, Any]] = {
    "search_products": {
        "fn": search_products,
        "description": "Search products by name, SKU or description (ILIKE).",
        "skill": "knowledge_agent",
        "params": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 10},
        },
        "mutating": False,
    },
    "get_product_specs": {
        "fn": get_product_specs,
        "description": "Get full technical specs for a product.",
        "skill": "knowledge_agent",
        "params": {
            "product_id": {"type": "integer", "required": True},
        },
        "mutating": False,
    },
    "get_price": {
        "fn": get_price,
        "description": "Calculate price with discount tiers for a given quantity.",
        "skill": "sales_agent",
        "params": {
            "product_id": {"type": "integer", "required": True},
            "quantity": {"type": "integer", "default": 1},
        },
        "mutating": False,
    },
    "check_stock": {
        "fn": check_stock,
        "description": "Check stock level and availability status.",
        "skill": "knowledge_agent",
        "params": {
            "product_id": {"type": "integer", "required": True},
        },
        "mutating": False,
    },
    "list_products": {
        "fn": list_products,
        "description": "List active products with optional category filter.",
        "skill": "knowledge_agent",
        "params": {
            "category": {"type": "string", "required": False},
            "offset": {"type": "integer", "default": 0},
            "limit": {"type": "integer", "default": 20},
        },
        "mutating": False,
    },
    "recommend_products": {
        "fn": recommend_products,
        "description": "Recommend up to 3 products based on context keywords.",
        "skill": "knowledge_agent",
        "params": {
            "context": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 3},
        },
        "mutating": False,
    },
    "get_discount_table": {
        "fn": get_discount_table,
        "description": "List all discount tiers for a product.",
        "skill": "sales_agent",
        "params": {
            "product_id": {"type": "integer", "required": True},
        },
        "mutating": False,
    },
}
