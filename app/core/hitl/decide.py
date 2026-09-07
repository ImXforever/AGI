"""One decision path for every surface (1.4.0).

The admin console, the Telegram Web App and the new Telegram inline buttons
all call :func:`decide_approval`.  It performs, in order:

1. status check (409-style conflicts are reported, never raised);
2. atomic Redis claim (``hitl_claim_decision.lua``) so two managers cannot
   decide the same item;
3. Postgres ledger + ``approvals`` row update + bus event;
4. policy-gated execution (:mod:`app.core.hitl.execute`);
5. **real delivery** to the customer through the channel registry — the
   1.3.x console only recorded the decision and the customer never heard
   back;
6. quote bookkeeping for order-flow requests (``quotes.status`` → ``sent`` /
   ``rejected``) and the manager hold release.

Returns a plain dict so FastAPI and the bot can both use it.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.constants import ApprovalStatus
from app.logging_setup import get_logger

log = get_logger("app.core.hitl.decide")

_LUA_PATH = Path(__file__).resolve().parents[2] / "storage" / "lua" / "hitl_claim_decision.lua"
_LUA_CACHE: dict[str, str] = {}


def _lua() -> str:
    if "claim" not in _LUA_CACHE:
        _LUA_CACHE["claim"] = _LUA_PATH.read_text(encoding="utf-8")
    return _LUA_CACHE["claim"]


def _payload_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return {}
    return dict(raw) if isinstance(raw, dict) else {}


def customer_text_for(
    status: str, payload: dict[str, Any], draft_text: str, edited: dict[str, Any] | None
) -> str:
    """What the customer receives for a decision (edited text wins)."""
    if edited and str(edited.get("text") or "").strip():
        return str(edited["text"]).strip()
    if status == ApprovalStatus.REJECTED:
        return str(payload.get("rejected_text") or "").strip()
    return str(payload.get("text") or payload.get("draft_text") or draft_text or "").strip()


class DecisionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def decide_approval(
    *,
    services: dict[str, Any],
    approval_id: str,
    new_status: str,
    actor: str,
    actor_role: str = "admin",
    note: str = "",
    edited_payload: dict[str, Any] | None = None,
    claim_store: Any = None,
) -> dict[str, Any]:
    if new_status not in ApprovalStatus.DECISIONS:
        raise DecisionError(
            400, f"status must be one of {sorted(ApprovalStatus.DECISIONS)}, got {new_status!r}"
        )
    pool = services.get("pg")
    redis = services.get("redis")
    if pool is None or redis is None:
        raise DecisionError(503, "database or redis unavailable")

    row = await pool.fetchrow(
        "SELECT status, payload, draft_text, channel, customer_id, conversation_id FROM approvals WHERE id = $1",
        approval_id,
    )
    if row is None:
        raise DecisionError(404, "approval not found")
    current = str(row["status"])
    if current in ApprovalStatus.TERMINAL:
        raise DecisionError(
            409, f"approval {approval_id} is already {current!r} — cannot decide again"
        )
    if current != ApprovalStatus.PENDING:
        raise DecisionError(409, f"approval {approval_id} has status {current!r}, expected pending")

    now = time.time()
    edited_json = json.dumps(edited_payload, ensure_ascii=False) if edited_payload else ""
    claimed = await redis.eval(
        _lua(),
        2,
        f"hitl:meta:{approval_id}",
        f"hitl:decided:{approval_id}",
        ApprovalStatus.PENDING,
        new_status,
        actor,
        str(int(now)),
        edited_json,
        note or "",
    )
    if int(claimed or 0) == 0:
        raise DecisionError(409, f"approval {approval_id} was decided concurrently (409)")

    await pool.execute(
        """INSERT INTO approval_execution_ledger
               (approval_id, decided_status, actor, decided_at, edited_payload, note)
           VALUES ($1, $2, $3, to_timestamp($4), $5, $6)
           ON CONFLICT (approval_id) DO UPDATE SET
               decided_status = EXCLUDED.decided_status,
               actor = EXCLUDED.actor,
               decided_at = EXCLUDED.decided_at,
               edited_payload = EXCLUDED.edited_payload,
               note = EXCLUDED.note""",
        approval_id,
        new_status,
        actor,
        now,
        edited_json or None,
        note or None,
    )
    await pool.execute(
        """UPDATE approvals SET status = $1, decided_at = to_timestamp($2), actor = $3, note = $4,
                  updated_at = now()
           WHERE id = $5""",
        new_status,
        now,
        actor,
        note or None,
        approval_id,
    )
    try:
        await redis.xadd(
            "bus:events",
            {"type": "approval-decided", "approval_id": approval_id, "status": new_status},
            maxlen=10000,
        )
    except Exception:
        pass

    payload = _payload_dict(row["payload"])
    channel = str(payload.get("channel") or row["channel"] or "")
    recipient = str(payload.get("recipient_id") or payload.get("sender_id") or "")
    conversation_id = str(row["conversation_id"] or "")
    if not recipient and row["customer_id"] is not None:
        try:
            recipient = str(
                await pool.fetchval(
                    "SELECT external_id FROM customers WHERE id = $1", row["customer_id"]
                )
                or ""
            )
        except Exception:
            recipient = ""
    if not channel and row["customer_id"] is not None:
        try:
            channel = str(
                await pool.fetchval(
                    "SELECT channel FROM customers WHERE id = $1", row["customer_id"]
                )
                or ""
            )
        except Exception:
            channel = ""

    execution: dict[str, Any] | None = None
    if new_status in (ApprovalStatus.APPROVED, ApprovalStatus.EDITED):
        action_name = str(payload.get("action") or payload.get("type") or "")
        if action_name:
            from app.core.hitl.execute import execute_action

            outcome = execute_action(
                action_name,
                payload,
                actor_role=actor_role or "admin",
                approved=True,
                approval_id=approval_id,
                context={"approval_id": approval_id, "channel": channel},
                idempotency_key=approval_id,
            )
            execution = outcome.as_dict()

    # --- customer delivery (real send, exactly once) ---
    text = customer_text_for(new_status, payload, str(row["draft_text"] or ""), edited_payload)
    delivered: dict[str, Any] = {"sent": False, "reason": "no_text"}
    if text and recipient and channel:
        from app.core.outbound import MemoryClaimStore, OutboundJob, deliver_once

        store = claim_store if claim_store is not None else MemoryClaimStore()
        registry = services.get("registry")
        adapter = registry.get(channel) if registry is not None else None
        job = OutboundJob(
            channel=channel,
            recipient_id=recipient,
            text=text,
            approval_id=f"{approval_id}:{new_status}",
        )
        if adapter is None:
            delivered = {"sent": False, "reason": "no_adapter"}
        else:
            key = f"{approval_id}:{new_status}"
            if not store.claim(key):
                delivered = {"sent": False, "duplicate": True, "reason": "duplicate"}
            else:
                try:
                    from app.channels.base import normalize_text

                    result = await adapter.send(recipient_id=recipient, text=normalize_text(text))
                    ok = bool(getattr(result, "success", True))
                    delivered = {"sent": ok, "reason": "sent" if ok else "send_failed"}
                    if not ok:
                        store.release(key)
                    elif conversation_id:
                        # 1.6.0: the approved answer is part of the conversation
                        # memory too — before, the bot "forgot" what a manager
                        # had just sent and the next turn contradicted it.
                        try:
                            from app.core.repository import store_message

                            await store_message(
                                pool,
                                conversation_id=conversation_id,
                                role="agent",
                                content=text[:8000],
                                channel=channel,
                                metadata={
                                    "approval_id": approval_id,
                                    "decided_by": actor,
                                    "status": new_status,
                                },
                            )
                        except Exception:
                            log.debug("approved reply store failed", exc_info=True)
                except Exception as exc:
                    store.release(key)
                    delivered = {"sent": False, "reason": f"send_failed: {str(exc)[:120]}"}
        _ = deliver_once  # keep the idempotent helper importable for callers/tests
    if execution is not None:
        execution["outbound"] = delivered

    # --- quote bookkeeping for order-flow requests ---
    if payload.get("type") == "quote_request" or payload.get("reference"):
        quote_status = (
            "sent" if new_status in (ApprovalStatus.APPROVED, ApprovalStatus.EDITED) else "rejected"
        )
        try:
            await pool.execute(
                "UPDATE quotes SET status = $2, updated_at = NOW() WHERE approval_id = $1",
                approval_id,
                quote_status,
            )
        except Exception as exc:
            log.debug(
                "quote status update failed",
                extra={"action": "decide.quote", "error": str(exc)[:200]},
            )

    # --- release the manager hold so the bot answers again ---
    if conversation_id:
        try:
            from app.core.conversation_hold import hold_redis_key

            await redis.delete(hold_redis_key(conversation_id))
        except Exception:
            pass

    log.info(
        "approval decided",
        extra={
            "action": "approval.decide",
            "approval_id": approval_id,
            "status": new_status,
            "actor": actor,
            "delivered": delivered.get("sent"),
        },
    )
    return {
        "ok": True,
        "approval_id": approval_id,
        "status": new_status,
        "execution": execution,
        "delivered": delivered,
        "reference": payload.get("reference") or "",
        "customer_name": payload.get("sender_name") or "",
        "summary": payload.get("summary_en") or "",
    }
