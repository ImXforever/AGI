"""Website form and content-change workflow for v0.7."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.core.policy import RiskLevel, evaluate_action


class WebsiteChangeKind(StrEnum):
    CONTENT = "content"
    PRICE = "price"
    LEGAL = "legal"
    DELETE = "delete"


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
