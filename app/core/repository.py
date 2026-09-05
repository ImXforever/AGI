"""Repository — all PostgreSQL read/write operations for the core domain."""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg  # type: ignore[import-untyped]

from app.constants import ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.core.repository")


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.UTC).isoformat()


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------


async def get_customer(pg: asyncpg.Pool, customer_id: str) -> dict[str, Any] | None:
    row = await pg.fetchrow(
        "SELECT * FROM customers WHERE id = $1",
        customer_id,
    )
    return dict(row) if row else None


async def get_or_create_customer(
    pg: asyncpg.Pool,
    *,
    channel: str,
    sender_id: str,
    sender_name: str = "",
) -> dict[str, Any]:
    row = await pg.fetchrow(
        "SELECT * FROM customers WHERE channel = $1 AND external_id = $2",
        channel,
        sender_id,
    )
    if row:
        return dict(row)

    cid = _new_id()
    # BUG #24: only display_name was populated here, but the admin API
    # searches customers on `name` (admin_api/customers.py) and the ticket
    # list renders `c.name`. Every customer created by channel ingestion was
    # therefore nameless and unsearchable in the dashboard. Write both.
    await pg.execute(
        """
        INSERT INTO customers (id, channel, external_id, name, display_name,
                               created_at, updated_at)
        VALUES ($1, $2, $3, $4, $4, now(), now())
        """,
        cid,
        channel,
        sender_id,
        sender_name,
    )
    log.info("customer_created", extra={"action": "get_or_create_customer", "customer_id": cid})
    row = await pg.fetchrow("SELECT * FROM customers WHERE id = $1", cid)
    return dict(row) if row else {"id": cid, "channel": channel, "external_id": sender_id}


async def update_customer(pg: asyncpg.Pool, customer_id: str, fields: dict[str, Any]) -> bool:
    if not fields:
        return False
    set_parts: list[str] = []
    values: list[Any] = []
    idx = 1
    for key, val in fields.items():
        idx += 1
        set_parts.append(f"{key} = ${idx}")
        values.append(val)
    # updated_at is timestamptz: asyncpg refuses a str, so let PostgreSQL
    # stamp it rather than binding an ISO string as a parameter.
    set_parts.append("updated_at = now()")
    sql = f"UPDATE customers SET {', '.join(set_parts)} WHERE id = $1"
    result = await pg.execute(sql, customer_id, *values)
    return result == "UPDATE 1"


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


async def get_conversation(pg: asyncpg.Pool, conversation_id: str) -> dict[str, Any] | None:
    row = await pg.fetchrow(
        "SELECT * FROM conversations WHERE id = $1",
        conversation_id,
    )
    return dict(row) if row else None


async def get_or_create_conversation(
    pg: asyncpg.Pool,
    *,
    conversation_id: str,
    customer_id: str,
    channel: str,
) -> dict[str, Any]:
    row = await pg.fetchrow(
        "SELECT * FROM conversations WHERE id = $1",
        conversation_id,
    )
    if row:
        return dict(row)

    await pg.execute(
        """
        INSERT INTO conversations (id, customer_id, channel, status, created_at, updated_at)
        VALUES ($1, $2, $3, 'active', now(), now())
        ON CONFLICT (id) DO NOTHING
        """,
        conversation_id,
        customer_id,
        channel,
    )
    log.info(
        "conversation_created",
        extra={"action": "get_or_create_conversation", "conversation_id": conversation_id},
    )
    row = await pg.fetchrow("SELECT * FROM conversations WHERE id = $1", conversation_id)
    return (
        dict(row)
        if row
        else {
            "id": conversation_id,
            "customer_id": customer_id,
            "channel": channel,
            "status": "active",
        }
    )


async def set_conversation_status(pg: asyncpg.Pool, conversation_id: str, status: str) -> bool:
    result = await pg.execute(
        "UPDATE conversations SET status = $2, updated_at = now() WHERE id = $1",
        conversation_id,
        status,
    )
    return result == "UPDATE 1"


async def fetch_conversation(pg: asyncpg.Pool, conversation_id: str) -> dict[str, Any] | None:
    return await get_conversation(pg, conversation_id)


async def list_conversations(
    pg: asyncpg.Pool,
    *,
    customer_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    idx = 0
    if customer_id:
        idx += 1
        conditions.append(f"customer_id = ${idx}")
        params.append(customer_id)
    if status:
        idx += 1
        conditions.append(f"status = ${idx}")
        params.append(status)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    idx += 1
    params.append(limit)
    idx += 1
    params.append(offset)

    sql = f"SELECT * FROM conversations{where} ORDER BY created_at DESC LIMIT ${idx - 1} OFFSET ${idx}"
    rows = await pg.fetch(sql, *params)
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


async def store_message(
    pg: asyncpg.Pool,
    *,
    conversation_id: str,
    role: str,
    content: str,
    channel: str = "",
    external_ref: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    mid = _new_id()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)
    await pg.execute(
        """
        INSERT INTO messages (id, conversation_id, sender_role, text, metadata, external_ref, created_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, now())
        """,
        mid,
        conversation_id,
        role,
        content,
        meta_json,
        external_ref or None,
    )
    log.debug(
        "message_stored",
        extra={"action": "store_message", "conversation_id": conversation_id, "role": role},
    )
    return mid


async def get_conversation_history(
    pg: asyncpg.Pool,
    conversation_id: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = await pg.fetch(
        """
        SELECT id, sender_role AS role, text AS content, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        conversation_id,
        limit,
    )
    return [dict(r) for r in reversed(rows)]


async def create_outbound_message(
    pg: asyncpg.Pool,
    *,
    conversation_id: str,
    channel: str,
    recipient_id: str,
    content: str,
    approval_id: str | None = None,
    external_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    mid = _new_id()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)
    await pg.execute(
        """
        INSERT INTO outbound_messages (id, conversation_id, channel, recipient_id,
            content, approval_id, external_ref, metadata, status, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, 'sent', now())
        """,
        mid,
        conversation_id,
        channel,
        recipient_id,
        content,
        approval_id,
        external_ref,
        meta_json,
    )
    log.info(
        "outbound_message_created",
        extra={
            "action": "create_outbound_message",
            "conversation_id": conversation_id,
            "channel": channel,
        },
    )
    return mid


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


async def store_attachment(
    pg: asyncpg.Pool,
    *,
    conversation_id: str,
    message_id: str | None,
    filename: str,
    content_type: str,
    r2_key: str,
    size: int = 0,
    metadata: dict[str, Any] | None = None,
) -> str:
    aid = _new_id()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)
    await pg.execute(
        """
        INSERT INTO attachments (id, conversation_id, message_id, filename,
            content_type, r2_key, size, metadata, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, now())
        """,
        aid,
        conversation_id,
        message_id,
        filename,
        content_type,
        r2_key,
        size,
        meta_json,
    )
    log.info(
        "attachment_stored",
        extra={
            "action": "store_attachment",
            "conversation_id": conversation_id,
            "filename": filename,
        },
    )
    return aid


# ---------------------------------------------------------------------------
# Approvals (HITL)
# ---------------------------------------------------------------------------


async def create_approval(
    pg: asyncpg.Pool,
    *,
    conversation_id: str,
    customer_id: str,
    skill: str,
    intent: str,
    draft_text: str,
    confidence: float,
    needs_hitl: bool = True,
) -> str:
    aid = _new_id()
    await pg.execute(
        """
        INSERT INTO approvals (id, conversation_id, customer_id, skill, intent,
            draft_text, confidence, status, needs_hitl, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, now(), now())
        """,
        aid,
        conversation_id,
        customer_id,
        skill,
        intent,
        draft_text,
        confidence,
        ApprovalStatus.PENDING,
        needs_hitl,
    )
    log.info(
        "approval_created",
        extra={
            "action": "create_approval",
            "approval_id": aid,
            "skill": skill,
            "needs_hitl": needs_hitl,
        },
    )
    return aid


async def get_approval(pg: asyncpg.Pool, approval_id: str) -> dict[str, Any] | None:
    row = await pg.fetchrow(
        "SELECT * FROM approvals WHERE id = $1",
        approval_id,
    )
    return dict(row) if row else None


async def list_approvals(
    pg: asyncpg.Pool,
    *,
    status: str | None = None,
    skill: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    idx = 0
    if status:
        idx += 1
        conditions.append(f"status = ${idx}")
        params.append(status)
    if skill:
        idx += 1
        conditions.append(f"skill = ${idx}")
        params.append(skill)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    idx += 1
    params.append(limit)
    idx += 1
    params.append(offset)

    sql = f"SELECT * FROM approvals{where} ORDER BY created_at DESC LIMIT ${idx - 1} OFFSET ${idx}"
    rows = await pg.fetch(sql, *params)
    return [dict(r) for r in rows]


async def update_approval_status(
    pg: asyncpg.Pool,
    approval_id: str,
    status: str,
    *,
    actor: str = "",
    edited_text: str | None = None,
    note: str = "",
) -> bool:
    if edited_text is not None:
        result = await pg.execute(
            """
            UPDATE approvals
            SET status = $2, edited_text = $3, actor = $4, note = $5, decided_at = now(), updated_at = now()
            WHERE id = $1
            """,
            approval_id,
            status,
            edited_text,
            actor,
            note,
        )
    else:
        result = await pg.execute(
            """
            UPDATE approvals
            SET status = $2, actor = $3, note = $4, decided_at = now(), updated_at = now()
            WHERE id = $1
            """,
            approval_id,
            status,
            actor,
            note,
        )
    return result == "UPDATE 1"


async def mark_tool_executed(
    pg: asyncpg.Pool,
    approval_id: str,
    tool_name: str,
    result: dict[str, Any],
) -> None:
    meta_json = json.dumps(result, ensure_ascii=False, default=str)
    await pg.execute(
        """
        INSERT INTO tool_executions (id, approval_id, tool_name, result, created_at)
        VALUES ($1, $2, $3, $4::jsonb, now())
        """,
        _new_id(),
        approval_id,
        tool_name,
        meta_json,
    )
    log.info(
        "tool_executed",
        extra={"action": "mark_tool_executed", "approval_id": approval_id, "tool_name": tool_name},
    )


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


async def get_catalog_items(pg: asyncpg.Pool, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = await pg.fetch(
        "SELECT * FROM catalog_items ORDER BY name_ar LIMIT $1",
        limit,
    )
    return [dict(r) for r in rows]


async def search_catalog(pg: asyncpg.Pool, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = await pg.fetch(
        """
        SELECT * FROM catalog_items
        WHERE name_ar ILIKE $1 OR name_en ILIKE $1 OR sku ILIKE $1
        LIMIT $2
        """,
        f"%{query}%",
        limit,
    )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------


async def get_sales_summary(
    pg: asyncpg.Pool,
    *,
    days: int = 30,
) -> dict[str, Any]:
    row = await pg.fetchrow(
        """
        SELECT
            COALESCE(SUM(total), 0) as total_sales,
            COUNT(*) as order_count,
            COALESCE(AVG(total), 0) as avg_order_value
        FROM orders
        WHERE created_at >= now() - make_interval(days => $1)
        """,
        days,
    )
    return dict(row) if row else {"total_sales": 0, "order_count": 0, "avg_order_value": 0}


async def get_ticket_stats(pg: asyncpg.Pool) -> dict[str, Any]:
    row = await pg.fetchrow(
        """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'open') as open_count,
            COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
            COUNT(*) FILTER (WHERE priority = 'high') as high_priority
        FROM tickets
        """
    )
    return (
        dict(row) if row else {"total": 0, "open_count": 0, "resolved_count": 0, "high_priority": 0}
    )
