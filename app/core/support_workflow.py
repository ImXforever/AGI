"""Support agent: tickets, SLA, safety vs knowledge. No exploit samples."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SupportPhase(StrEnum):
    ANSWER = "answer_knowledge"
    TICKET = "open_ticket"
    ESCALATE = "escalate_safety"
    FOLLOWUP = "followup"


class TicketSeverity(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CustomerTicketStatus(StrEnum):
    OPEN = "open"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


SLA_HOURS = {
    TicketSeverity.CRITICAL: 0.0,
    TicketSeverity.HIGH: 2.0,
    TicketSeverity.NORMAL: 24.0,
    TicketSeverity.LOW: 72.0,
}

# English tokens match as whole words. Arabic/Persian match as substrings.
_SAFETY_WORDS_EN = frozenset(
    {
        "fire",
        "leak",
        "explosion",
        "poison",
        "injury",
        "accident",
        "danger",
        "threat",
        "evacuate",
        "emergency",
        "spill",
        "hospital",
        "shutdown",
    }
)
_SAFETY_PHRASES = (
    "حريق",
    "تسرب",
    "انفجار",
    "تسمم",
    "إصابة",
    "خطر",
    "إخلاء",
    "هبوط",
    "اختناق",
    "نزيف",
)

_FAQ_MARKERS = (
    "how do i",
    "how to",
    "reset password",
    "opening hours",
    "ساعت کار",
    "كيف",
)

_OUTAGE_MARKERS = (
    "down",
    "outage",
    "cannot login",
    "can't login",
    "خطا",
    "مشکل",
    "broken",
)


@dataclass(frozen=True)
class SupportTicket:
    subject: str
    severity: TicketSeverity
    customer_status: CustomerTicketStatus
    sla_hours: float
    is_safety: bool
    followup_hours: float


@dataclass(frozen=True)
class SupportAgentResult:
    """One support-agent step. Safety always opens a ticket; never dumps exploit text."""

    phase: SupportPhase
    action: str
    ticket: SupportTicket | None
    reason: str
    payload: dict[str, Any]


def is_safety_text(text: str) -> bool:
    """Detect safety language without demonstrating attack payloads."""
    raw = text or ""
    hay = raw.casefold()
    if any(p in raw or p in hay for p in _SAFETY_PHRASES):
        return True
    for word in _SAFETY_WORDS_EN:
        if re.search(rf"\b{re.escape(word)}\b", hay):
            return True
    return False


def customer_status_for(*, is_safety: bool, internal: str = "open") -> CustomerTicketStatus:
    """Customers never see internal pending/draft queues."""
    if is_safety:
        return CustomerTicketStatus.ESCALATED
    mapping = {
        "open": CustomerTicketStatus.OPEN,
        "pending": CustomerTicketStatus.OPEN,
        "waiting_customer": CustomerTicketStatus.WAITING_CUSTOMER,
        "resolved": CustomerTicketStatus.RESOLVED,
        "escalated": CustomerTicketStatus.ESCALATED,
        "closed": CustomerTicketStatus.RESOLVED,
    }
    return mapping.get(internal, CustomerTicketStatus.OPEN)


def classify_severity(text: str, *, is_safety: bool) -> TicketSeverity:
    if is_safety:
        return TicketSeverity.CRITICAL
    hay = (text or "").casefold()
    if any(m in hay for m in _OUTAGE_MARKERS):
        return TicketSeverity.HIGH
    return TicketSeverity.NORMAL


def build_ticket(text: str, *, internal_status: str = "open") -> SupportTicket:
    safety = is_safety_text(text)
    severity = classify_severity(text, is_safety=safety)
    sla = SLA_HOURS[severity]
    followup = 4.0 if safety else min(24.0, max(sla, 4.0))
    return SupportTicket(
        subject=(text or "support request").strip()[:200] or "support request",
        severity=severity,
        customer_status=customer_status_for(is_safety=safety, internal=internal_status),
        sla_hours=sla,
        is_safety=safety,
        followup_hours=followup,
    )


def handle_support(
    text: str,
    *,
    extras: dict[str, Any] | None = None,
) -> SupportAgentResult:
    """State machine: escalate safety | followup | knowledge FAQ | open ticket."""
    extras = dict(extras or {})
    blob = f"{text} {extras.get('subject') or ''}"
    ticket = build_ticket(blob, internal_status=str(extras.get("status") or "open"))

    if ticket.is_safety:
        return SupportAgentResult(
            phase=SupportPhase.ESCALATE,
            action="create_ticket",
            ticket=ticket,
            reason="safety case — ticket + human escalate",
            payload=_ticket_payload(ticket, text, escalate=True),
        )

    if extras.get("followup"):
        return SupportAgentResult(
            phase=SupportPhase.FOLLOWUP,
            action="create_task",
            ticket=ticket,
            reason="support follow-up",
            payload={
                "text": (text or "")[:500],
                "kind": "support",
                "sla_hours": ticket.sla_hours,
            },
        )

    kb_hit = bool(extras.get("kb_hit"))
    faq = any(m in (text or "").casefold() for m in _FAQ_MARKERS)
    if (kb_hit or faq) and not extras.get("force_ticket"):
        return SupportAgentResult(
            phase=SupportPhase.ANSWER,
            action="search_knowledge",
            ticket=None,
            reason="first-line knowledge answer — no ticket",
            payload={"text": (text or "")[:500], "kb_hit": kb_hit},
        )

    return SupportAgentResult(
        phase=SupportPhase.TICKET,
        action="create_ticket",
        ticket=ticket,
        reason="support ticket opened",
        payload=_ticket_payload(ticket, text, escalate=False),
    )


def _ticket_payload(ticket: SupportTicket, text: str, *, escalate: bool) -> dict[str, Any]:
    return {
        "text": (text or "")[:500],
        "subject": ticket.subject,
        "severity": ticket.severity.value,
        "priority": {
            TicketSeverity.LOW: "low",
            TicketSeverity.NORMAL: "medium",
            TicketSeverity.HIGH: "high",
            TicketSeverity.CRITICAL: "urgent",
        }[ticket.severity],
        "customer_status": ticket.customer_status.value,
        "sla_hours": ticket.sla_hours,
        "is_safety": ticket.is_safety,
        "escalate": escalate,
        "followup_hours": ticket.followup_hours,
        "requires_human": ticket.is_safety,
    }
