"""Analytics tools — parameterised query templates with role-based access control."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from asyncpg.pool import Pool

from app.logging_setup import get_logger

log = get_logger("tools.analytics")


@dataclass(frozen=True)
class QueryTemplate:
    """A named, parameterised SQL template with role gate."""

    name: str
    sql: str
    description: str
    params: dict[str, dict[str, Any]] = field(default_factory=dict)
    min_role: str = "viewer"


WHITELIST: dict[str, QueryTemplate] = {
    "daily_revenue": QueryTemplate(
        name="daily_revenue",
        sql="""
            SELECT DATE(created_at) AS day,
                   SUM(total) AS revenue,
                   COUNT(*) AS order_count
            FROM orders
            WHERE status NOT IN ('cancelled', 'refunded')
              AND created_at >= $1::date AND created_at < $2::date
            GROUP BY day ORDER BY day
        """,
        description="Daily revenue breakdown for a date range.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
        },
        min_role="viewer",
    ),
    "monthly_revenue": QueryTemplate(
        name="monthly_revenue",
        sql="""
            SELECT DATE_TRUNC('month', created_at) AS month,
                   SUM(total) AS revenue,
                   COUNT(*) AS order_count
            FROM orders
            WHERE status NOT IN ('cancelled', 'refunded')
              AND created_at >= $1::date AND created_at < $2::date
            GROUP BY month ORDER BY month
        """,
        description="Monthly revenue aggregation.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
        },
        min_role="viewer",
    ),
    "top_products": QueryTemplate(
        name="top_products",
        sql="""
            SELECT p.id, p.sku, p.name_en, p.name_ar,
                   SUM(oi.quantity) AS units_sold,
                   SUM(oi.quantity * oi.unit_price) AS revenue
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status NOT IN ('cancelled', 'refunded')
              AND o.created_at >= $1::date AND o.created_at < $2::date
            GROUP BY p.id, p.sku, p.name_en, p.name_ar
            ORDER BY revenue DESC
            LIMIT $3
        """,
        description="Top-selling products by revenue.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 10},
        },
        min_role="viewer",
    ),
    "customer_summary": QueryTemplate(
        name="customer_summary",
        sql="""
            SELECT COUNT(*) AS total_customers,
                   COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS new_30d,
                   AVG(lead_score) FILTER (WHERE lead_score IS NOT NULL) AS avg_lead_score
            FROM customers
        """,
        description="High-level customer summary metrics.",
        min_role="viewer",
    ),
    "open_tickets": QueryTemplate(
        name="open_tickets",
        sql="""
            SELECT severity, COUNT(*) AS cnt
            FROM tickets
            WHERE status IN ('open', 'pending')
            GROUP BY severity
            ORDER BY CASE severity
                WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                WHEN 'normal' THEN 3 WHEN 'low' THEN 4
            END
        """,
        description="Count of open support tickets by severity.",
        min_role="viewer",
    ),
    "ticket_volume": QueryTemplate(
        name="ticket_volume",
        sql="""
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM tickets
            WHERE created_at >= $1::date AND created_at < $2::date
            GROUP BY day ORDER BY day
        """,
        description="Daily ticket volume for a date range.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
        },
        min_role="viewer",
    ),
    "lead_funnel": QueryTemplate(
        name="lead_funnel",
        sql="""
            SELECT
                CASE
                    WHEN lead_score >= 80 THEN 'hot'
                    WHEN lead_score >= 50 THEN 'warm'
                    WHEN lead_score > 0 THEN 'cold'
                    ELSE 'unscored'
                END AS bucket,
                COUNT(*) AS count
            FROM customers
            GROUP BY bucket
            ORDER BY
                CASE bucket
                    WHEN 'hot' THEN 1 WHEN 'warm' THEN 2
                    WHEN 'cold' THEN 3 WHEN 'unscored' THEN 4
                END
        """,
        description="Lead scoring funnel distribution.",
        min_role="viewer",
    ),
    "quote_conversion": QueryTemplate(
        name="quote_conversion",
        sql="""
            SELECT
                COUNT(*) FILTER (WHERE status = 'approved') AS approved,
                COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
                COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                COUNT(*) FILTER (WHERE status = 'edited') AS edited,
                COUNT(*) AS total
            FROM quotes
            WHERE created_at >= $1::date AND created_at < $2::date
        """,
        description="Quote conversion rates for a date range.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
        },
        min_role="editor",
    ),
    "channel_activity": QueryTemplate(
        name="channel_activity",
        sql="""
            SELECT channel, COUNT(*) AS message_count
            FROM conversations
            WHERE created_at >= $1::date AND created_at < $2::date
            GROUP BY channel ORDER BY message_count DESC
        """,
        description="Message volume by channel.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
        },
        min_role="viewer",
    ),
    "revenue_by_category": QueryTemplate(
        name="revenue_by_category",
        sql="""
            SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status NOT IN ('cancelled', 'refunded')
              AND o.created_at >= $1::date AND o.created_at < $2::date
            GROUP BY p.category ORDER BY revenue DESC
        """,
        description="Revenue breakdown by product category.",
        params={
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
        },
        min_role="viewer",
    ),
    "low_stock": QueryTemplate(
        name="low_stock",
        sql="""
            SELECT id, sku, name_ar, name_en, stock_qty, reorder_point
            FROM products
            WHERE is_active = TRUE
              AND stock_qty <= reorder_point
            ORDER BY stock_qty ASC
            LIMIT 50
        """,
        description="Products at or below reorder point.",
        min_role="viewer",
    ),
}

# DEPRECATED: kept for backwards compatibility only. The canonical ranks live
# in app.admin_api.rbac (viewer < admin < superadmin). This table used the old
# viewer/editor/admin vocabulary, under which a real "superadmin" fell through
# to rank 0 and was denied every guarded tool. "editor" is retained as an alias
# of admin. Prefer app.admin_api.rbac.has_role().
ROLE_RANK: dict[str, int] = {
    "viewer": 0,
    "editor": 1,
    "admin": 1,
    "superadmin": 2,
}


async def run_metrics_query(
    pool: Pool,
    *,
    template_name: str,
    params: dict[str, Any] | None = None,
    role: str = "viewer",
) -> dict[str, Any]:
    """Execute a whitelisted analytics query template with parameter binding."""
    tpl = WHITELIST.get(template_name)
    if tpl is None:
        return {"error": "unknown_template", "available": sorted(WHITELIST.keys())}

    required_role = ROLE_RANK.get(tpl.min_role, 0)
    caller_role = ROLE_RANK.get(role, 0)
    if caller_role < required_role:
        return {"error": "insufficient_role", "required": tpl.min_role, "caller": role}

    params = params or {}
    args: list[Any] = []
    for name, spec in tpl.params.items():
        value = params.get(name, spec.get("default"))
        if spec.get("required") and value is None:
            return {"error": "missing_param", "param": name}
        # The templates bind dates as $n::date. asyncpg will not coerce a
        # Python str into a date, so ISO date strings must be parsed here or
        # every date-ranged report raises DataError.
        if isinstance(value, str) and name.endswith("_date"):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                return {"error": "invalid_date", "param": name, "value": value}
        args.append(value)

    rows = await pool.fetch(tpl.sql, *args)
    return {
        "template": template_name,
        "description": tpl.description,
        "count": len(rows),
        "rows": [dict(r) for r in rows],
    }


async def get_revenue_summary(
    pool: Pool,
    *,
    start_date: str,
    end_date: str,
    role: str = "viewer",
) -> dict[str, Any]:
    """Shortcut: total revenue, order count, and average order value."""
    return await run_metrics_query(
        pool,
        template_name="daily_revenue",
        params={"start_date": start_date, "end_date": end_date},
        role=role,
    )


async def get_ticket_stats(
    pool: Pool,
    *,
    role: str = "viewer",
) -> dict[str, Any]:
    """Shortcut: open ticket counts by severity."""
    return await run_metrics_query(
        pool,
        template_name="open_tickets",
        role=role,
    )


REGISTRY: dict[str, dict[str, Any]] = {
    "run_metrics_query": {
        "fn": run_metrics_query,
        "description": "Execute a whitelisted analytics query template.",
        "skill": "analytics_agent",
        "params": {
            "template_name": {"type": "string", "required": True},
            "params": {"type": "object", "default": {}},
            "role": {"type": "string", "default": "viewer"},
        },
        "mutating": False,
    },
    "get_revenue_summary": {
        "fn": get_revenue_summary,
        "description": "Get revenue summary for a date range.",
        "skill": "analytics_agent",
        "params": {
            "start_date": {"type": "string", "required": True},
            "end_date": {"type": "string", "required": True},
            "role": {"type": "string", "default": "viewer"},
        },
        "mutating": False,
    },
    "get_ticket_stats": {
        "fn": get_ticket_stats,
        "description": "Get open ticket counts by severity.",
        "skill": "analytics_agent",
        "params": {
            "role": {"type": "string", "default": "viewer"},
        },
        "mutating": False,
    },
}
