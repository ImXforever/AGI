"""Website form and content-change workflow for v0.7."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.policy import PolicyDecision, RiskLevel, evaluate_action


class WebsiteChangeKind(StrEnum):
    CONTENT = "content"
    PRICE = "price"
    LEGAL = "legal"
    DELETE = "delete"


class WebsitePhase(StrEnum):
    INGEST_FORM = "ingest_form"
    DRAFT_CMS = "draft_cms"
    APPLY_CMS = "apply_cms"
    REPORT_ISSUE = "report_issue"
    REJECT = "reject"


@dataclass(frozen=True)
class WebsiteLead:
    name: str
    email: str
    message: str
    source: str = "website"


@dataclass(frozen=True)
class WebsiteChange:
    kind: WebsiteChangeKind
    before: str
    after: str
    requires_approval: bool
    risk: RiskLevel
    action: str


@dataclass(frozen=True)
class WebsiteAgentResult:
    """One website-agent step. Never writes production CMS by itself."""

    phase: WebsitePhase
    action: str
    lead: WebsiteLead | None
    change: WebsiteChange | None
    production: bool
    reason: str
    payload: dict[str, Any]


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_contact_form(*, name: str, email: str, message: str) -> WebsiteLead:
    """Validate and normalize a website contact form before creating a lead."""
    clean_name = " ".join(name.split())
    clean_email = email.strip().lower()
    clean_message = message.strip()
    if not clean_name:
        raise ValueError("contact name must not be empty")
    if not _EMAIL_RE.fullmatch(clean_email):
        raise ValueError("contact email is invalid")
    if not clean_message:
        raise ValueError("contact message must not be empty")
    if len(clean_name) > 200 or len(clean_email) > 320 or len(clean_message) > 10_000:
        raise ValueError("contact form field is too long")
    return WebsiteLead(clean_name, clean_email, clean_message)


def classify_content_change(*, before: str, after: str, field: str) -> WebsiteChange:
    """Classify a proposed CMS change and attach the central approval policy."""
    normalized_field = field.strip().lower()
    if normalized_field in {"price", "pricing", "unit_price"}:
        kind, action, risk = WebsiteChangeKind.PRICE, "change_price", RiskLevel.HIGH
    elif normalized_field in {"terms", "legal", "contract", "refund_policy"}:
        kind, action, risk = WebsiteChangeKind.LEGAL, "contract", RiskLevel.HIGH
    elif not after.strip():
        kind, action, risk = WebsiteChangeKind.DELETE, "delete_data", RiskLevel.CRITICAL
    else:
        kind, action, risk = WebsiteChangeKind.CONTENT, "publish_content", RiskLevel.HIGH
    decision = evaluate_action(action)
    return WebsiteChange(
        kind=kind,
        before=before,
        after=after,
        requires_approval=decision.requires_approval,
        risk=risk,
        action=action,
    )


_ISSUE_MARKERS = (
    "404",
    "500",
    "downtime",
    "outage",
    "broken",
    "site down",
    "website down",
    "سایت خراب",
)


def ingest_form(*, name: str, email: str, message: str) -> WebsiteAgentResult:
    """Tool: ingest contact form → create_lead. Invalid forms never become leads."""
    try:
        lead = normalize_contact_form(name=name, email=email, message=message)
    except ValueError as exc:
        return WebsiteAgentResult(
            phase=WebsitePhase.REJECT,
            action="invalid_form",
            lead=None,
            change=None,
            production=False,
            reason=str(exc),
            payload={"error": str(exc)},
        )
    return WebsiteAgentResult(
        phase=WebsitePhase.INGEST_FORM,
        action="create_lead",
        lead=lead,
        change=None,
        production=False,
        reason=f"contact form from {lead.email}",
        payload={
            "name": lead.name,
            "email": lead.email,
            "message": lead.message,
            "source": lead.source,
        },
    )


def draft_cms_change(*, before: str, after: str, field: str) -> WebsiteAgentResult:
    """Tool: draft CMS change. Never hits production, including price edits."""
    change = classify_content_change(before=before, after=after, field=field)
    return WebsiteAgentResult(
        phase=WebsitePhase.DRAFT_CMS,
        action="create_draft",
        lead=None,
        change=change,
        production=False,
        reason=f"draft {change.kind.value} (not live)",
        payload={
            "kind": change.kind.value,
            "field": field,
            "before": before,
            "after": after,
            "apply_action": change.action,
            "production": False,
        },
    )


def apply_cms_change(
    *,
    before: str,
    after: str,
    field: str,
    approved: bool = False,
    approval_id: str = "",
    actor_role: str = "agent",
) -> tuple[WebsiteAgentResult, PolicyDecision]:
    """Tool: apply CMS change. Price / legal / delete / live publish stay HITL."""
    change = classify_content_change(before=before, after=after, field=field)
    decision = evaluate_action(
        change.action,
        actor_role=actor_role,
        approved=approved,
        approval_id=approval_id,
        context={"kind": change.kind.value, "sensitivity": change.kind.value},
    )
    live = bool(decision.allowed)
    return (
        WebsiteAgentResult(
            phase=WebsitePhase.APPLY_CMS,
            action=change.action,
            lead=None,
            change=change,
            production=live,
            reason="applied to production" if live else f"{change.kind.value} held for manager",
            payload={
                "kind": change.kind.value,
                "field": field,
                "before": before,
                "after": after,
                "production": live,
            },
        ),
        decision,
    )


def report_issue(text: str) -> WebsiteAgentResult:
    """Tool: site issue → create_ticket (auto)."""
    return WebsiteAgentResult(
        phase=WebsitePhase.REPORT_ISSUE,
        action="create_ticket",
        lead=None,
        change=None,
        production=False,
        reason="site issue ticket",
        payload={"text": (text or "")[:500], "source": "website"},
    )


def handle_website(
    text: str,
    *,
    extras: dict[str, Any] | None = None,
    approved: bool = False,
    approval_id: str = "",
    actor_role: str = "agent",
) -> WebsiteAgentResult:
    """State machine: ingest_form | report_issue | draft_cms | apply_cms."""
    extras = dict(extras or {})
    if extras.get("form"):
        form = extras["form"] if isinstance(extras["form"], dict) else {}
        return ingest_form(
            name=str(form.get("name", "")),
            email=str(form.get("email", "")),
            message=str(form.get("message", text)),
        )
    if extras.get("issue") or any(m in (text or "").casefold() for m in _ISSUE_MARKERS):
        return report_issue(text)
    field = str(extras.get("field") or extras.get("cms_field") or "description")
    after = str(extras.get("after") or text)
    before = str(extras.get("before") or "")
    change = classify_content_change(before=before, after=after, field=field)
    must_hold = change.kind in {
        WebsiteChangeKind.PRICE,
        WebsiteChangeKind.LEGAL,
        WebsiteChangeKind.DELETE,
    }
    if extras.get("apply") or must_hold:
        result, _decision = apply_cms_change(
            before=before,
            after=after,
            field=field,
            approved=approved,
            approval_id=approval_id,
            actor_role=actor_role,
        )
        return result
    return draft_cms_change(before=before, after=after, field=field)
