"""Execute an approved (or auto-allowed) business action.

The LLM never calls this directly. The router produces a plan; this module
re-evaluates policy at execution time so a stale approval cannot widen scope.

Handlers are in-process and auditable. They never talk to a bank, never hold
keys, and never send mail unless a caller registers a real adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.policy import PolicyDecision, evaluate_action
from app.logging_setup import get_logger

log = get_logger("app.core.hitl.execute")

_IDEMPOTENCY: dict[str, "ExecutionResult"] = {}

Handler = Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]]
_HANDLERS: dict[str, Handler] = {}


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    action: str
    executed: bool
    reason: str
    policy: PolicyDecision
    result: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "executed": self.executed,
            "reason": self.reason,
            "policy": self.policy.as_dict(),
            "result": self.result,
        }


def register_handler(action: str, fn: Handler) -> None:
    _HANDLERS[action.strip().lower()] = fn


def _audit_handler(action: str, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "status": "executed",
        "mode": "ledger",
        "payload_keys": sorted(payload.keys()),
        "channel": str(context.get("channel") or payload.get("channel") or "internal"),
    }


def _critical_handler(action: str, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Money / legal / destructive — recorded, never sent to an external rail here."""
    out = _audit_handler(action, payload, context)
    out["mode"] = "hitl-dispatch"
    out["external"] = False
    out["note"] = "dispatched to ledger only; no bank, mailbox or CMS write in this process"
    return out


for _name in (
    "read_email",
    "classify_email",
    "create_draft",
    "reply_common",
    "create_task",
    "create_lead",
    "search_knowledge",
    "create_ticket",
    "publish_calendar",
):
    register_handler(_name, _audit_handler)

for _name in (
    "update_customer",
    "create_quote",
    "send_email",
    "publish_content",
    "change_price",
    "payment",
    "contract",
    "delete_data",
    "change_access",
):
    register_handler(_name, _critical_handler)


def execute_action(
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    actor_role: str = "agent",
    approved: bool = False,
    context: dict[str, Any] | None = None,
    idempotency_key: str = "",
) -> ExecutionResult:
    """Apply policy then dispatch to a registered handler.

    Side effects against channels/DB stay behind handlers. This function
    guarantees the gate cannot be bypassed.
    """
    if idempotency_key and idempotency_key in _IDEMPOTENCY:
        return _IDEMPOTENCY[idempotency_key]

    policy = evaluate_action(
        action, actor_role=actor_role, approved=approved, context=context
    )
    if not policy.allowed:
        outcome = ExecutionResult(
            ok=False,
            action=policy.action,
            executed=False,
            reason=policy.reason,
            policy=policy,
        )
        log.info(
            "execution_blocked",
            extra={"action": "hitl.execute", "business_action": policy.action, "reason": policy.reason},
        )
        return outcome

    body = dict(payload or {})
    ctx = dict(context or {})
    handler = _HANDLERS.get(policy.action, _audit_handler)
    try:
        dispatched = handler(policy.action, body, ctx)
    except Exception as exc:  # noqa: BLE001 — fail closed, never raise into the bus
        log.exception("handler_failed", extra={"action": "hitl.execute", "business_action": policy.action})
        outcome = ExecutionResult(
            ok=False,
            action=policy.action,
            executed=False,
            reason=f"handler failed: {exc}",
            policy=policy,
            result={"error": str(exc)},
        )
        return outcome

    outcome = ExecutionResult(
        ok=True,
        action=policy.action,
        executed=True,
        reason=policy.reason,
        policy=policy,
        result=dict(dispatched or {}),
    )
    if idempotency_key:
        _IDEMPOTENCY[idempotency_key] = outcome
    log.info(
        "execution_ok",
        extra={"action": "hitl.execute", "business_action": policy.action},
    )
    return outcome


def reset_idempotency() -> None:
    _IDEMPOTENCY.clear()
