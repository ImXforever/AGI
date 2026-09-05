"""Support tools — troubleshooting search, ticket management, human escalation."""

from __future__ import annotations

from typing import Any

from asyncpg.pool import Pool

from app.logging_setup import get_logger

log = get_logger("tools.support")

# tickets.priority CHECK is (low|medium|high|urgent); severity is
# (low|normal|high|critical). Map one onto the other when the AI opens a ticket.
_PRIORITY_BY_SEVERITY = {
    "low": "low",
    "normal": "medium",
    "high": "high",
    "critical": "urgent",
}

SAFETY_KEYWORDS = frozenset(
    {
        "حريق",
        "fire",
        "تسرب",
        "leak",
        "انفجار",
        "explosion",
        "تسمم",
        "poison",
        "إصابة",
        "injury",
        "accident",
        "خطر",
        "danger",
        "هدد",
        "threat",
        "إخلاء",
        "evacuate",
        "disable",
        "تعطيل",
        "هبوط",
        "shutdown",
    }
)


async def search_troubleshooting(pool: Pool, *, query: str, limit: int = 5) -> dict[str, Any]:
    """Search the troubleshooting knowledge base by keyword."""
    rows = await pool.fetch(
        """
        SELECT id, title_ar, title_en, problem_ar, problem_en,
               solution_ar, solution_en, category, severity
        FROM troubleshooting
        WHERE (
            title_ar ILIKE '%' || $1 || '%'
            OR title_en ILIKE '%' || $1 || '%'
            OR problem_ar ILIKE '%' || $1 || '%'
            OR problem_en ILIKE '%' || $1 || '%'
            OR category ILIKE '%' || $1 || '%'
        )
        ORDER BY severity DESC, title_en
        LIMIT $2
        """,
        query,
        max(1, min(limit, 20)),
    )
    return {
        "count": len(rows),
        "articles": [dict(r) for r in rows],
    }


async def get_ticket(pool: Pool, *, ticket_id: str) -> dict[str, Any]:
    """Fetch a support ticket with its history."""
    ticket = await pool.fetchrow(
        """
        SELECT t.*, c.name_ar, c.name_en, c.phone, c.email
        FROM tickets t
        LEFT JOIN customers c ON c.id = t.customer_id
        WHERE t.id = $1
        """,
        ticket_id,
    )
    if ticket is None:
        return {"error": "ticket_not_found", "ticket_id": ticket_id}

    history = await pool.fetch(
        """
        SELECT id, actor, action, body, created_at
        FROM ticket_events
        WHERE ticket_id = $1
        ORDER BY created_at ASC
        """,
        ticket_id,
    )
    return {
        "ticket": dict(ticket),
        "history": [dict(h) for h in history],
    }


async def escalate_to_human(
    pool: Pool,
    *,
    conversation_id: str,
    ticket_id: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Escalate a conversation to a human agent via the HITL queue.

    Optionally links to an existing ticket. Publishes an escalation event
    on the HITL stream so the sweeper or an on-call admin is notified.
    """
    from app.constants import STREAM_HITL
    from app.core.hitl.queue import enqueue

    approval_id = await enqueue(
        pool=pool,
        conversation_id=conversation_id,
        tool_name="escalate_to_human",
        params={
            "ticket_id": ticket_id,
            "reason": reason,
        },
        stream=STREAM_HITL,
    )

    log.info(
        "escalated to human",
        extra={
            "action": "tools.escalate_to_human",
            "conversation_id": conversation_id,
            "approval_id": approval_id,
        },
    )
    return {
        "approval_id": approval_id,
        "conversation_id": conversation_id,
        "status": "escalated",
        "reason": reason,
    }


async def create_ticket(
    pool: Pool,
    *,
    customer_id: str,
    subject: str,
    body: str,
    severity: str = "normal",
    channel: str = "system",
    auto_open: bool = True,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Create a support ticket.

    If *severity* matches a safety keyword (``SAFETY_KEYWORDS``), the ticket
    is automatically opened and escalated regardless of the ``auto_open`` flag.
    """
    is_safety = any(kw in (subject + " " + body).lower() for kw in SAFETY_KEYWORDS)

    status = "open" if (auto_open or is_safety) else "pending"

    row = await pool.fetchrow(
        """
        INSERT INTO tickets (
            customer_id, subject, description, severity, channel, status,
            is_safety, priority
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, created_at
        """,
        customer_id,
        subject,
        body,
        severity,
        channel,
        status,
        is_safety,
        _PRIORITY_BY_SEVERITY.get(severity, "medium"),
    )

    log.info(
        "ticket created",
        extra={
            "action": "tools.create_ticket",
            "entity": f"ticket:{row['id']}",
            "is_safety": is_safety,
        },
    )

    if is_safety:
        # The HITL queue stores conversation_id in a uuid column with a foreign
        # key to conversations. The old code passed f"ticket:{id}", which is
        # neither a UUID nor an existing conversation, so *every* safety
        # escalation raised an exception and the ticket silently lost its
        # escalation. Escalate against the originating conversation when we
        # have one, and record why we could not otherwise.
        if conversation_id:
            await escalate_to_human(
                pool=pool,
                conversation_id=str(conversation_id),
                ticket_id=row["id"],
                reason=f"Safety keyword detected in ticket #{row['id']}",
            )
        else:
            log.warning(
                "safety ticket created without a conversation to escalate",
                extra={
                    "action": "tools.create_ticket",
                    "entity": f"ticket:{row['id']}",
                },
            )

    return {
        "ticket_id": row["id"],
        "customer_id": customer_id,
        "subject": subject,
        "severity": severity,
        "status": status,
        "is_safety": is_safety,
        "created_at": str(row["created_at"]),
    }


REGISTRY: dict[str, dict[str, Any]] = {
    "search_troubleshooting": {
        "fn": search_troubleshooting,
        "description": "Search the troubleshooting knowledge base.",
        "skill": "support_agent",
        "params": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
        "mutating": False,
    },
    "get_ticket": {
        "fn": get_ticket,
        "description": "Fetch a support ticket with its event history.",
        "skill": "support_agent",
        "params": {
            "ticket_id": {"type": "integer", "required": True},
        },
        "mutating": False,
    },
    "escalate_to_human": {
        "min_role": "admin",
        "fn": escalate_to_human,
        "description": "Escalate a conversation to a human agent via HITL queue.",
        "skill": "support_agent",
        "params": {
            "conversation_id": {"type": "string", "required": True},
            "ticket_id": {"type": "integer", "required": False},
            "reason": {"type": "string", "default": ""},
        },
        "mutating": True,
    },
    "create_ticket": {
        "min_role": "admin",
        "fn": create_ticket,
        "description": (
            "Create a support ticket. Auto-opens and escalates if safety keywords are detected."
        ),
        "skill": "support_agent",
        "params": {
            "customer_id": {"type": "integer", "required": True},
            "subject": {"type": "string", "required": True},
            "body": {"type": "string", "required": True},
            "severity": {"type": "string", "default": "normal"},
            "channel": {"type": "string", "default": "system"},
            "auto_open": {"type": "boolean", "default": True},
        },
        "mutating": True,
    },
}
