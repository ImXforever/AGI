"""Analytics and reporting endpoints for the admin dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.analytics")

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])


@router.get("/overview")
async def overview(
    request: Request,
    days: int = 30,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """
        SELECT
            COUNT(DISTINCT c.id) AS total_conversations,
            COUNT(DISTINCT cu.id) AS total_customers,
            COUNT(q.id) FILTER (WHERE q.status = 'accepted') AS quotes_accepted,
            COUNT(q.id) FILTER (WHERE q.status = 'sent') AS quotes_sent,
            COALESCE(SUM(q.total) FILTER (WHERE q.status = 'accepted'), 0) AS revenue,
            COUNT(t.id) AS total_tickets,
            COUNT(t.id) FILTER (WHERE t.status = 'resolved') AS tickets_resolved,
            COUNT(a.id) FILTER (WHERE a.status = 'pending') AS pending_approvals
        FROM conversations c
        LEFT JOIN customers cu ON cu.id = c.customer_id
        LEFT JOIN quotes q ON q.customer_id = cu.id AND q.created_at >= NOW() - INTERVAL '1 day' * $1
        LEFT JOIN tickets t ON t.customer_id = cu.id AND t.created_at >= NOW() - INTERVAL '1 day' * $1
        LEFT JOIN approvals a ON a.conversation_id = c.id
    """,
        days,
    )
    return dict(row) if row else {}


@router.get("/channels")
async def channel_stats(
    request: Request,
    days: int = 30,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        """
        SELECT channel, COUNT(*) AS count
        FROM conversations
        WHERE created_at >= NOW() - INTERVAL '1 day' * $1
        GROUP BY channel ORDER BY count DESC
    """,
        days,
    )
    return {"items": [dict(r) for r in rows]}


@router.get("/hourly")
async def hourly_volume(
    request: Request,
    days: int = 7,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        """
        SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS count
        FROM conversations
        WHERE created_at >= NOW() - INTERVAL '1 day' * $1
        GROUP BY hour ORDER BY hour
    """,
        days,
    )
    items = []
    for r in rows:
        d = dict(r)
        d["hour"] = d["hour"].isoformat() if hasattr(d["hour"], "isoformat") else str(d["hour"])
        items.append(d)
    return {"items": items}


@router.get("/top-products")
async def top_products(
    request: Request,
    days: int = 30,
    limit: int = 10,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        """
        SELECT p.name_ar, p.name_en, p.sku, COUNT(q.id) AS quote_count,
               COALESCE(SUM(q.total), 0) AS total_value
        FROM quotes q
        JOIN products p ON p.sku = (q.items::json->0->>'sku')
        WHERE q.created_at >= NOW() - INTERVAL '1 day' * $1
        GROUP BY p.id ORDER BY total_value DESC LIMIT $2
    """,
        days,
        limit,
    )
    return {"items": [dict(r) for r in rows]}


@router.get("/response-times")
async def response_times(
    request: Request,
    days: int = 30,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """
        SELECT
            AVG(EXTRACT(EPOCH FROM (m2.created_at - m1.created_at))) AS avg_response_s,
            PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY EXTRACT(EPOCH FROM (m2.created_at - m1.created_at))
            ) AS p50_response_s,
            PERCENTILE_CONT(0.95) WITHIN GROUP (
                ORDER BY EXTRACT(EPOCH FROM (m2.created_at - m1.created_at))
            ) AS p95_response_s
        FROM messages m1
        JOIN messages m2 ON m2.conversation_id = m1.conversation_id
            AND m2.sender_role = 'agent'
            AND m2.created_at > m1.created_at
        WHERE m1.sender_role = 'user'
            AND m1.created_at >= NOW() - INTERVAL '1 day' * $1
    """,
        days,
    )
    result = dict(row) if row else {}
    for k in result:
        if result[k] is not None:
            result[k] = round(float(result[k]), 2)
    return result
