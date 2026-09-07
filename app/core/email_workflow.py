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
    CONFIDENTIAL = "confidential"
    INTERNAL = "internal"
    SPAM = "spam"
    OTHER = "other"


class EmailPhase(StrEnum):
    CLASSIFY = "classify"
    DRAFT = "draft"
    SEND_COMMON = "send_common"
    QUEUE_APPROVAL = "queue_approval"
    FOLLOWUP = "followup"
    DROP = "drop"


@dataclass(frozen=True)
class EmailTriage:
    category: EmailCategory
    priority: str
    confidence: float
    requires_human: bool
    reason: str


@dataclass(frozen=True)
class EmailAgentResult:
    """One step of the email agent state machine. Never sends by itself."""

    phase: EmailPhase
    action: str
    triage: EmailTriage
    thread_id: str
    bounce: bool
    sla_hours: float
    draft: dict[str, str] | None
    reason: str
    template_key: str = ""


_KEYWORDS: tuple[tuple[EmailCategory, tuple[str, ...], str], ...] = (
    (
        EmailCategory.CONFIDENTIAL,
        ("confidential", "nda", "محرمانه"),
        "confidential content",
    ),
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
        (
            "price",
            "pricing",
            "quote",
            "buy",
            "catalog",
            "catalogue",
            "قیمت",
            "خرید",
            "پیش فاکتور",
            "کاتالوگ",
        ),
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
            sensitive = category in {
                EmailCategory.FINANCE,
                EmailCategory.LEGAL,
                EmailCategory.CONFIDENTIAL,
            }
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


def sending_decision(*, approved: bool = False, actor_role: str = "agent", approval_id: str = ""):
    """Return the central policy decision for sending an email.

    Default is the sensitive/important path (manager approval). Common
    template replies use ``reply_common`` instead.
    """
    return evaluate_action(
        "send_email", actor_role=actor_role, approved=approved, approval_id=approval_id
    )


def common_reply_decision(*, approved: bool = False, actor_role: str = "agent"):
    """Automatic path for classified common questions."""
    return evaluate_action("reply_common", actor_role=actor_role, approved=approved)


def risk_for_triage(triage: EmailTriage) -> RiskLevel:
    """Map triage to the minimum operational risk level."""
    if triage.category in {
        EmailCategory.FINANCE,
        EmailCategory.LEGAL,
        EmailCategory.CONFIDENTIAL,
    }:
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
    if triage.category in {
        EmailCategory.SPAM,
        EmailCategory.FINANCE,
        EmailCategory.LEGAL,
        EmailCategory.CONFIDENTIAL,
    }:
        return False
    if triage.confidence < 0.6:
        return False
    return True


# ---------------------------------------------------------------------------
# Thread identity, bounces, SLA clocks
# ---------------------------------------------------------------------------

_BOUNCE_SENDERS = ("mailer-daemon@", "postmaster@", "mail-daemon@")
_BOUNCE_MARKERS = (
    "undeliverable",
    "delivery status notification",
    "mail delivery failed",
    "delivery failure",
    "returned mail",
)


def normalize_message_id(raw: str) -> str:
    return (raw or "").strip().strip("<>").strip().lower()


def make_thread_id(
    *,
    message_id: str = "",
    in_reply_to: str = "",
    references: str = "",
) -> str:
    """Prefer In-Reply-To, then the first References token, else Message-ID."""
    irt = normalize_message_id(in_reply_to)
    if irt:
        return irt
    for token in (references or "").replace(",", " ").split():
        ref = normalize_message_id(token)
        if ref:
            return ref
    return normalize_message_id(message_id)


def is_bounce(subject: str, body: str, *, sender: str = "") -> bool:
    """Detect DSN / bounce mail. Never auto-reply to a bounce."""
    from_l = (sender or "").casefold()
    if any(token in from_l for token in _BOUNCE_SENDERS):
        return True
    hay = f"{subject} {body}".casefold()
    return any(marker in hay for marker in _BOUNCE_MARKERS)


def sla_hours_for(triage: EmailTriage) -> float:
    """First-response clock in hours. Clock only — never auto-sends."""
    if triage.category in {
        EmailCategory.FINANCE,
        EmailCategory.LEGAL,
        EmailCategory.CONFIDENTIAL,
    }:
        return 1.0
    if triage.category == EmailCategory.SUPPORT:
        return 4.0
    if triage.category == EmailCategory.SPAM:
        return 0.0
    return 24.0


def classify(subject: str, body: str, *, sender: str = "") -> EmailTriage:
    """Tool: classify. Bounce short-circuits to a non-reply triage."""
    if is_bounce(subject, body, sender=sender):
        return EmailTriage(EmailCategory.OTHER, "low", 0.9, False, "bounce")
    return triage_email(subject, body, sender=sender)


def draft(
    subject: str,
    body: str,
    *,
    sender_name: str = "Customer",
    company_name: str = "Our Company",
) -> dict[str, str] | None:
    """Tool: draft. Template body only — does not send."""
    from app.core.email_smart_reply import match_smart_reply, render_reply

    smart = match_smart_reply(subject, body)
    if smart is None:
        return None
    return render_reply(
        smart,
        original_subject=subject,
        sender_name=sender_name,
        company_name=company_name,
    )


def send_common(triage: EmailTriage, *, actor_role: str = "agent"):
    """Tool: send_common. Policy gate for classified common replies."""
    if not should_auto_reply(triage):
        return evaluate_action("send_email", actor_role=actor_role)
    return common_reply_decision(actor_role=actor_role)


def queue_approval(*, actor_role: str = "agent", approval_id: str = "", approved: bool = False):
    """Tool: queue_approval. Sensitive send always needs a manager record."""
    return sending_decision(approved=approved, actor_role=actor_role, approval_id=approval_id)


def followup(
    email_id: str,
    sender: str,
    recipient: str,
    subject: str,
    category: str = "standard",
):
    """Tool: followup. Schedule only — outbound follow-up is still send_email HITL."""
    from app.core.email_followup import create_followup

    return create_followup(email_id, sender, recipient, subject, category)


def handle_inbound_email(
    subject: str,
    body: str,
    *,
    sender: str = "",
    message_id: str = "",
    in_reply_to: str = "",
    references: str = "",
    sender_name: str = "",
    company_name: str = "Our Company",
) -> EmailAgentResult:
    """State machine: classify → drop | send_common | queue_approval | draft."""
    thread_id = make_thread_id(
        message_id=message_id, in_reply_to=in_reply_to, references=references
    )
    bounce = is_bounce(subject, body, sender=sender)
    if bounce:
        triage = classify(subject, body, sender=sender)
        return EmailAgentResult(
            phase=EmailPhase.DROP,
            action="classify_email",
            triage=triage,
            thread_id=thread_id,
            bounce=True,
            sla_hours=0.0,
            draft=None,
            reason="bounce — no outbound",
        )

    triage = triage_email(subject, body, sender=sender)
    sla = sla_hours_for(triage)
    if triage.category == EmailCategory.SPAM:
        return EmailAgentResult(
            phase=EmailPhase.DROP,
            action="classify_email",
            triage=triage,
            thread_id=thread_id,
            bounce=False,
            sla_hours=0.0,
            draft=None,
            reason="spam — no outbound",
        )

    from app.core.email_smart_reply import match_smart_reply, render_reply

    smart = match_smart_reply(subject, body)
    sensitive = triage.category in {
        EmailCategory.FINANCE,
        EmailCategory.LEGAL,
        EmailCategory.CONFIDENTIAL,
    }

    if (
        smart is not None
        and not smart.requires_human
        and should_auto_reply(triage)
        and not sensitive
    ):
        rendered = render_reply(
            smart,
            original_subject=subject,
            sender_name=sender_name or sender or "Customer",
            company_name=company_name,
        )
        return EmailAgentResult(
            phase=EmailPhase.SEND_COMMON,
            action="reply_common",
            triage=triage,
            thread_id=thread_id,
            bounce=False,
            sla_hours=sla,
            draft=rendered,
            reason=f"common reply via {smart.template_key}",
            template_key=smart.template_key,
        )

    if sensitive:
        return EmailAgentResult(
            phase=EmailPhase.QUEUE_APPROVAL,
            action="send_email",
            triage=triage,
            thread_id=thread_id,
            bounce=False,
            sla_hours=sla,
            draft=None,
            reason=f"{triage.category.value} held for manager",
        )

    return EmailAgentResult(
        phase=EmailPhase.DRAFT,
        action="create_draft",
        triage=triage,
        thread_id=thread_id,
        bounce=False,
        sla_hours=sla,
        draft=None,
        reason=triage.reason,
    )
