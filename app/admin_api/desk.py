"""Manager desk — one call feeds the simplified 1.4.0 console.

The old console needed a dozen requests per page.  ``GET /desk`` returns the
few numbers a non-technical manager actually looks at, the pending requests
with a *readable* summary (who, what, how much), the latest conversations and
a plain system status.  ``GET /desk/conversation/{id}`` returns one thread
(customer and bot turns) so the manager can read before deciding.
"""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.admin_api.auth import require_admin
from app.constants import APP_VERSION
from app.logging_setup import get_logger

log = get_logger("app.admin_api.desk")

router = APIRouter(prefix="/desk", tags=["admin-desk"])

STARTED = time.time()


def _payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return {}
    return dict(raw) if isinstance(raw, dict) else {}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def approval_summary(row: dict[str, Any]) -> dict[str, Any]:
    """Readable card data for one approval row (pure — unit-tested)."""
    payload = _payload(row.get("payload"))
    kind = str(
        payload.get("type")
        or payload.get("action")
        or row.get("intent")
        or row.get("skill")
        or "review"
    )
    who = str(
        payload.get("sender_name")
        or row.get("customer_name")
        or row.get("customer_external")
        or "customer"
    )
    what = str(payload.get("summary_en") or row.get("draft_text") or "").strip()
    if payload.get("product_name"):
        qty = payload.get("quantity")
        unit = payload.get("unit") or ""
        what = (
            f"{payload.get('product_name')} · {qty:,} {unit}".strip()
            if isinstance(qty, int)
            else str(payload.get("product_name"))
        )
    amount = None
    try:
        total = float(payload.get("total") or 0)
        if total > 0:
            amount = f"{total:,.2f} {payload.get('currency') or 'USD'}"
    except (TypeError, ValueError):
        amount = None
    created = row.get("created_at")
    age_s = None
    if hasattr(created, "timestamp"):
        try:
            age_s = max(0, int(time.time() - created.timestamp()))
        except Exception:
            age_s = None
    severity = "info"
    if kind in ("quote_request", "create_quote", "payment", "contract"):
        severity = "high"
    if age_s is not None and age_s > 1800:
        severity = "high" if severity == "high" else "warn"
    return {
        "id": str(row.get("id") or ""),
        "kind": kind,
        "reference": str(payload.get("reference") or ""),
        "who": who,
        "what": what[:240],
        "amount": amount,
        "channel": str(payload.get("channel") or row.get("channel") or ""),
        "language": str(payload.get("language") or ""),
        "conversation_id": str(row.get("conversation_id") or ""),
        "created_at": _iso(created),
        "age_s": age_s,
        "severity": severity,
        "customer_text": str(payload.get("text") or row.get("draft_text") or "")[:1200],
    }


@router.get("")
async def desk(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    services = request.app.state.services
    pool = services["pg"]

    metrics = await pool.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM approvals WHERE status = 'pending') AS pending,
            (SELECT COUNT(*) FROM approvals WHERE status IN ('approved','edited')
                AND decided_at >= NOW() - INTERVAL '1 day') AS approved_24h,
            (SELECT COUNT(*) FROM approvals WHERE status = 'rejected'
                AND decided_at >= NOW() - INTERVAL '1 day') AS rejected_24h,
            (SELECT COUNT(*) FROM messages WHERE created_at >= NOW() - INTERVAL '1 day') AS messages_24h,
            (SELECT COUNT(*) FROM conversations WHERE updated_at >= NOW() - INTERVAL '1 day') AS active_24h,
            (SELECT COUNT(*) FROM customers) AS customers,
            (SELECT COUNT(*) FROM products WHERE is_active) AS products,
            (SELECT COUNT(*) FROM tickets WHERE status IN ('open','pending')) AS open_tickets,
            (SELECT COUNT(*) FROM quotes WHERE status = 'sent') AS quotes_sent
        """
    )

    pending_rows = await pool.fetch(
        """
        SELECT a.id, a.conversation_id, a.channel, a.status, a.payload, a.skill, a.intent,
               a.draft_text, a.created_at, c.name AS customer_name, c.external_id AS customer_external
        FROM approvals a
        LEFT JOIN customers c ON c.id = a.customer_id
        WHERE a.status = 'pending'
        ORDER BY a.created_at ASC
        LIMIT 30
        """
    )

    recent = await pool.fetch(
        """
        SELECT conv.id, conv.channel, conv.updated_at, cu.name AS customer_name,
               cu.external_id, cu.preferred_language,
               (SELECT m.text FROM messages m WHERE m.conversation_id = conv.id
                ORDER BY m.created_at DESC LIMIT 1) AS last_text,
               (SELECT m.sender_role FROM messages m WHERE m.conversation_id = conv.id
                ORDER BY m.created_at DESC LIMIT 1) AS last_role,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = conv.id) AS turns
        FROM conversations conv
        LEFT JOIN customers cu ON cu.id = conv.customer_id
        ORDER BY conv.updated_at DESC
        LIMIT 12
        """
    )

    volume = await pool.fetch(
        """
        SELECT date_trunc('hour', created_at) AS h, COUNT(*) AS n
        FROM messages
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY h ORDER BY h
        """
    )

    redis_ok = False
    redis = services.get("redis")
    if redis is not None:
        try:
            redis_ok = bool(await redis.ping())
        except Exception:
            redis_ok = False

    from app.config import get_config

    cfg = get_config()
    registry = services.get("registry")
    channels = []
    if registry is not None:
        for name in ("telegram", "whatsapp", "email"):
            try:
                channels.append({"name": name, "up": registry.get(name) is not None})
            except Exception:
                channels.append({"name": name, "up": False})

    return {
        "version": APP_VERSION,
        "now": time.time(),
        "uptime_s": int(time.time() - STARTED),
        "metrics": {k: int(v or 0) for k, v in dict(metrics or {}).items()},
        "pending": [approval_summary(dict(r)) for r in pending_rows],
        "recent": [
            {
                "id": str(r["id"]),
                "channel": r["channel"],
                "customer": r["customer_name"] or r["external_id"] or "",
                "language": r["preferred_language"] or "",
                "last_text": (r["last_text"] or "")[:160],
                "last_role": r["last_role"] or "",
                "turns": int(r["turns"] or 0),
                "updated_at": _iso(r["updated_at"]),
            }
            for r in recent
        ],
        "volume": [{"h": _iso(r["h"]), "n": int(r["n"])} for r in volume],
        "system": {
            "postgres": True,
            "redis": redis_ok,
            "llm_mode": cfg.llm.mode,
            "hitl_timeout_s": cfg.hitl.timeout_seconds,
            "hitl_fallback": cfg.hitl.fallback,
            "channels": channels,
            "admins": len(cfg.channels.telegram_admin_ids),
        },
        "viewer": admin.get("username") or "",
        "role": admin.get("role") or "",
    }


@router.get("/conversation/{conversation_id}")
async def conversation_thread(
    conversation_id: str, request: Request, admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    conv = await pool.fetchrow(
        """
        SELECT conv.id, conv.channel, conv.status, conv.created_at, conv.updated_at,
               cu.id AS customer_id, cu.name AS customer_name, cu.external_id, cu.preferred_language,
               cu.company, cu.phone, cu.email
        FROM conversations conv LEFT JOIN customers cu ON cu.id = conv.customer_id
        WHERE conv.id = $1
        """,
        conversation_id,
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    rows = await pool.fetch(
        """
        SELECT sender_role, text, created_at FROM messages
        WHERE conversation_id = $1 ORDER BY created_at DESC LIMIT 60
        """,
        conversation_id,
    )
    turns = [
        {"role": r["sender_role"], "text": r["text"] or "", "at": _iso(r["created_at"])}
        for r in reversed(rows)
    ]
    memories: list[dict[str, Any]] = []
    try:
        from app.core.orchestrator import _memory_user_id

        uid = _memory_user_id(str(conv["customer_id"] or ""))
        mem_rows = await pool.fetch(
            "SELECT kind, content, importance FROM user_memories WHERE user_id = $1 ORDER BY importance DESC, created_at DESC LIMIT 8",
            uid,
        )
        memories = [dict(m) for m in mem_rows]
    except Exception:
        memories = []
    requests_rows = await pool.fetch(
        "SELECT reference, status, total, currency, created_at FROM quotes WHERE conversation_id = $1 ORDER BY created_at DESC LIMIT 5",
        conversation_id,
    )
    return {
        "conversation": {
            "id": str(conv["id"]),
            "channel": conv["channel"],
            "status": conv["status"],
            "customer": conv["customer_name"] or conv["external_id"] or "",
            "external_id": conv["external_id"] or "",
            "language": conv["preferred_language"] or "",
            "company": conv["company"] or "",
            "phone": conv["phone"] or "",
            "email": conv["email"] or "",
            "created_at": _iso(conv["created_at"]),
            "updated_at": _iso(conv["updated_at"]),
        },
        "turns": turns,
        "memories": memories,
        "requests": [
            {
                "reference": r["reference"],
                "status": r["status"],
                "total": float(r["total"] or 0),
                "currency": r["currency"],
                "created_at": _iso(r["created_at"]),
            }
            for r in requests_rows
        ],
    }
