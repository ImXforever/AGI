"""Deterministic email triage and draft policy (v16 — extended with auto-reply templates)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.policy import RiskLevel, evaluate_action


class EmailCategory(StrEnum):
    CUSTOMER = "customer"
    SALES = "sales"
    SUPPORT = "support"
    FINANCE = "finance"
    LEGAL = "legal"
    INTERNAL = "internal"
    SPAM = "spam"
    OTHER = "other"


@dataclass(frozen=True)
class EmailTriage:
    category: EmailCategory
    priority: str
    confidence: float
    requires_human: bool
    reason: str


_KEYWORDS: tuple[tuple[EmailCategory, tuple[str, ...], str], ...] = (
    (EmailCategory.LEGAL, ("contract", "قرارداد", "قانونی", "legal", "terms"), "legal content"),
    (
        EmailCategory.FINANCE,
        ("invoice", "payment", "پرداخت", "فاکتور", "bank"),
        "financial content",
    ),
    (
        EmailCategory.SUPPORT,
        ("error", "problem", "support", "خطا", "مشکل", "پشتیبانی"),
        "support content",
    ),
    (
        EmailCategory.SALES,
        ("price", "pricing", "quote", "buy", "catalog", "catalogue", "قیمت", "خرید", "پیش فاکتور", "کاتالوگ"),
        "sales content",
    ),
    (
        EmailCategory.CUSTOMER,
        ("customer", "order", "سفارش", "مشتری", "delivery"),
        "customer content",
    ),
)


def triage_email(subject: str, body: str, *, sender: str = "") -> EmailTriage:
    """Classify an email using transparent, deterministic rules.

    This is intentionally a safe pre-filter. An LLM may enrich the result
    later, but it must not silently lower the human-review requirement.
    """
    haystack = f"{subject} {body}".casefold()
    if any(token in haystack for token in ("unsubscribe", "viagra", "casino", "تبلیغ")):
        return EmailTriage(EmailCategory.SPAM, "low", 0.95, False, "spam marker")

    for category, keywords, reason in _KEYWORDS:
        hits = sum(keyword.casefold() in haystack for keyword in keywords)
        if hits:
            sensitive = category in {EmailCategory.FINANCE, EmailCategory.LEGAL}
            return EmailTriage(
                category,
                "high" if sensitive else "normal",
                min(0.95, 0.55 + hits * 0.15),
                sensitive,
                reason,
            )

    return EmailTriage(
        EmailCategory.INTERNAL if sender.endswith("@company.local") else EmailCategory.OTHER,
        "normal",
        0.35,
        True,
        "no strong category signal",
    )


def sending_decision(*, approved: bool = False, actor_role: str = "agent"):
    """Return the central policy decision for sending an email.

    Default is the sensitive/important path (manager approval). Common
    template replies use ``reply_common`` instead.
    """
    return evaluate_action("send_email", actor_role=actor_role, approved=approved)


def common_reply_decision(*, approved: bool = False, actor_role: str = "agent"):
    """Automatic path for classified common questions."""
    return evaluate_action("reply_common", actor_role=actor_role, approved=approved)


def risk_for_triage(triage: EmailTriage) -> RiskLevel:
    """Map triage to the minimum operational risk level."""
    if triage.category in {EmailCategory.FINANCE, EmailCategory.LEGAL}:
        return RiskLevel.HIGH
    if triage.category in {EmailCategory.CUSTOMER, EmailCategory.SALES, EmailCategory.SUPPORT}:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ---------------------------------------------------------------------------
# v16: Auto-reply templates
# ---------------------------------------------------------------------------

_AUTO_REPLY_TEMPLATES: dict[EmailCategory, dict[str, str]] = {
    EmailCategory.SALES: {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your interest in our products.\n\n"
            "Our sales team has received your inquiry and will prepare "
            "a detailed response within 24 hours.\n\n"
            "Best regards,\n{company_name} Sales Team"
        ),
    },
    EmailCategory.SUPPORT: {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "We have received your support request and a specialist "
            "will review it shortly.\n\n"
            "Expected response time: 4 business hours.\n\n"
            "Best regards,\n{company_name} Support Team"
        ),
    },
    EmailCategory.CUSTOMER: {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for contacting us.\n\n"
            "Your request has been logged and our team will follow up "
            "within 24 hours.\n\n"
            "Best regards,\n{company_name} Customer Service"
        ),
    },
    EmailCategory.SPAM: {
        "subject": "",
        "body": "",
    },
}


def auto_reply_template(
    category: EmailCategory,
    *,
    original_subject: str = "",
    sender_name: str = "Customer",
    company_name: str = "Our Company",
) -> dict[str, str] | None:
    """Get an auto-reply template for a given email category.

    Returns None if no template is available or if the category is spam.
    """
    template = _AUTO_REPLY_TEMPLATES.get(category)
    if template is None:
        return None
    if not template["body"]:
        return None
    return {
        "subject": template["subject"].format(original_subject=original_subject),
        "body": template["body"].format(sender_name=sender_name, company_name=company_name),
    }


def should_auto_reply(triage: EmailTriage) -> bool:
    """Determine if an email should receive an auto-reply based on triage."""
    if triage.requires_human:
        return False
    if triage.category == EmailCategory.SPAM:
        return False
    if triage.confidence < 0.6:
        return False
    return True
