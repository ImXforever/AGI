"""Central risk and approval policy for business actions.

Aligned with the client access matrix:

    read/classify email          → automatic
    common replies               → automatic under rules
    sensitive/important email    → manager approval
    ordinary calendar publish    → automatic
    price / sensitive site info  → manager approval
    payment / contract / money   → manager approval only
    delete data / change access  → manager approval
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    risk: RiskLevel
    allowed: bool
    requires_approval: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "risk": int(self.risk),
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
        }


# Unknown actions fail closed rather than inheriting a permissive default.
_ACTIONS: dict[str, tuple[RiskLevel, bool]] = {
    "read_email": (RiskLevel.LOW, False),
    "classify_email": (RiskLevel.LOW, False),
    "create_draft": (RiskLevel.LOW, False),
    "reply_common": (RiskLevel.LOW, False),
    "create_task": (RiskLevel.LOW, False),
    "create_lead": (RiskLevel.LOW, False),
    "search_knowledge": (RiskLevel.LOW, False),
    "create_ticket": (RiskLevel.MEDIUM, False),
    "update_customer": (RiskLevel.MEDIUM, True),
    "create_quote": (RiskLevel.HIGH, True),
    "send_email": (RiskLevel.HIGH, True),
    "publish_calendar": (RiskLevel.MEDIUM, False),
    "publish_content": (RiskLevel.HIGH, True),
    "change_price": (RiskLevel.HIGH, True),
    "payment": (RiskLevel.CRITICAL, True),
    "contract": (RiskLevel.CRITICAL, True),
    "delete_data": (RiskLevel.CRITICAL, True),
    "change_access": (RiskLevel.CRITICAL, True),
}

_MANAGER_ROLES = {"admin", "superadmin", "owner", "root", "manager"}

_SENSITIVE_CONTEXT = {
    "financial",
    "finance",
    "legal",
    "confidential",
    "secret",
    "money",
    "payment",
    "contract",
}

_ALWAYS_APPROVAL = {
    "payment",
    "contract",
    "change_price",
    "delete_data",
    "change_access",
    "create_quote",
}


def _context_sensitivity(context: dict[str, Any] | None) -> str:
    if not context:
        return ""
    raw = str(
        context.get("sensitivity")
        or context.get("category")
        or context.get("kind")
        or ""
    ).strip().lower()
    return raw


def evaluate_action(
    action: str,
    *,
    actor_role: str = "agent",
    approved: bool = False,
    context: dict[str, Any] | None = None,
) -> PolicyDecision:
    """Evaluate an action with fail-closed defaults.

    ``approved`` is accepted only as an explicit signal from the approval
    subsystem. A prompt or a claimed role inside user text is not approval.

    ``context`` may include:
      - sensitivity: routine | important | financial | legal | confidential
      - routine: bool  (common email reply)
      - calendar_scheduled: bool
    """
    normalized = action.strip().lower()
    ctx = dict(context or {})
    sensitivity = _context_sensitivity(ctx)

    # Common replies are a distinct auto action. A caller may also pass
    # send_email + routine=True; we refuse to silently auto-send if the
    # context is financial/legal/confidential.
    if normalized == "send_email" and ctx.get("routine") and sensitivity not in _SENSITIVE_CONTEXT:
        normalized = "reply_common"

    if normalized == "publish_content" and ctx.get("calendar_scheduled") and sensitivity not in _SENSITIVE_CONTEXT:
        if not ctx.get("sensitive"):
            normalized = "publish_calendar"

    definition = _ACTIONS.get(normalized)
    if definition is None:
        return PolicyDecision(
            normalized,
            RiskLevel.HIGH,
            False,
            True,
            "unknown actions are denied until explicitly registered",
        )

    risk, approval_required = definition

    if normalized in _ALWAYS_APPROVAL:
        approval_required = True
        if risk < RiskLevel.HIGH:
            risk = RiskLevel.HIGH

    if sensitivity in _SENSITIVE_CONTEXT and normalized in {"reply_common", "publish_calendar", "create_draft"}:
        approval_required = True
        risk = max(risk, RiskLevel.HIGH)
        normalized = "send_email" if "email" in action.lower() or normalized == "reply_common" else normalized

    if not approval_required:
        return PolicyDecision(normalized, risk, True, False, "allowed by low-risk policy")

    role = actor_role.strip().lower()
    if not approved:
        return PolicyDecision(normalized, risk, False, True, "manager approval is required")
    if role not in _MANAGER_ROLES:
        return PolicyDecision(normalized, risk, False, True, "approval actor is not a manager")
    return PolicyDecision(normalized, risk, True, True, "approved by manager")


def registered_actions() -> tuple[str, ...]:
    """Return the stable action vocabulary for UI and audit tooling."""
    return tuple(sorted(_ACTIONS))


def auto_actions() -> tuple[str, ...]:
    return tuple(sorted(name for name, (_risk, needs) in _ACTIONS.items() if not needs))


def approval_actions() -> tuple[str, ...]:
    return tuple(sorted(name for name, (_risk, needs) in _ACTIONS.items() if needs))
