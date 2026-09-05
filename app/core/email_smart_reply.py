"""Smart auto-reply engine for common email questions (v16)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.email_smart_reply")


@dataclass(frozen=True)
class SmartReply:
    template_key: str
    confidence: float
    subject: str
    body: str
    requires_human: bool


_TEMPLATES: dict[str, dict[str, Any]] = {
    "pricing": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your interest in our products.\n\n"
            "Please find our current pricing catalog attached. "
            "For bulk orders or custom requirements, our sales team "
            "will prepare a tailored quote within 24 hours.\n\n"
            "Best regards,\n{company_name} Sales Team"
        ),
        "keywords": ("price", "pricing", "cost", "quote", "قیمت", "تسعير", "سعر"),
        "confidence": 0.85,
        "requires_human": False,
    },
    "availability": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for checking product availability.\n\n"
            "Our team is verifying current stock levels for your requested items. "
            "We will confirm availability and estimated delivery time within "
            "4 business hours.\n\n"
            "Best regards,\n{company_name} Support Team"
        ),
        "keywords": ("available", "stock", "inventory", "in stock", "متوفر", "موجود", "نفد"),
        "confidence": 0.80,
        "requires_human": False,
    },
    "delivery": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your inquiry about delivery.\n\n"
            "Standard delivery takes 3-5 business days for domestic orders "
            "and 7-14 business days for international shipments. "
            "Express delivery options are also available.\n\n"
            "We will provide specific shipping details once your order is confirmed.\n\n"
            "Best regards,\n{company_name} Operations Team"
        ),
        "keywords": ("delivery", "shipping", "ship", "transport", "توصيل", "شحن", "ارسال"),
        "confidence": 0.80,
        "requires_human": False,
    },
    "meeting": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your interest in scheduling a meeting.\n\n"
            "Our team will review your request and propose available time slots "
            "within 24 hours. Please let us know your preferred format "
            "(in-person, video call, or phone).\n\n"
            "Best regards,\n{company_name} Team"
        ),
        "keywords": ("meeting", "schedule", "appointment", "call", "جلسة", "اجتماع", "وقت"),
        "confidence": 0.75,
        "requires_human": False,
    },
    "catalog": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for requesting our product catalog.\n\n"
            "Please find the complete catalog attached to this email. "
            "It includes detailed specifications, technical data sheets, "
            "and safety information for all our petroleum products.\n\n"
            "Best regards,\n{company_name} Sales Team"
        ),
        "keywords": ("catalog", "brochure", "catalogue", "كتالوج", "بروشور", "güncel"),
        "confidence": 0.85,
        "requires_human": False,
    },
    "warranty": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your inquiry about our warranty policy.\n\n"
            "All our products come with a standard manufacturer warranty. "
            "For specific warranty terms and conditions, please refer to "
            "the documentation included with your purchase or contact our "
            "support team for detailed information.\n\n"
            "Best regards,\n{company_name} Support Team"
        ),
        "keywords": ("warranty", "guarantee", "ضمان", "كفالة", "гарантия"),
        "confidence": 0.80,
        "requires_human": False,
    },
    "payment_terms": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your inquiry about payment terms.\n\n"
            "We offer flexible payment options including:\n"
            "- Net 30 (for approved accounts)\n"
            "- Wire transfer\n"
            "- Letter of Credit\n\n"
            "Our finance team will provide specific terms based on your order.\n\n"
            "Best regards,\n{company_name} Finance Team"
        ),
        "keywords": ("payment", "terms", "bank", "transfer", "پرداخت", "شرايط", "条件"),
        "confidence": 0.80,
        "requires_human": False,
    },
    "minimum_order": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for your inquiry about minimum order quantities.\n\n"
            "Our standard minimum order quantities vary by product category. "
            "Our sales team will provide specific MOQ details for your "
            "requested items.\n\n"
            "Best regards,\n{company_name} Sales Team"
        ),
        "keywords": ("minimum order", "moq", "minimum", "حداقل سفارش"),
        "confidence": 0.75,
        "requires_human": False,
    },
    "sample_request": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for requesting product samples.\n\n"
            "We are happy to provide samples for evaluation. "
            "Please specify the products you're interested in, "
            "and we will arrange sample delivery within 5 business days.\n\n"
            "Best regards,\n{company_name} Sales Team"
        ),
        "keywords": ("sample", "trial", "test", "نمونه", "تجربه"),
        "confidence": 0.80,
        "requires_human": False,
    },
    "technical_support": {
        "subject": "Re: {original_subject}",
        "body": (
            "Dear {sender_name},\n\n"
            "Thank you for contacting our technical support team.\n\n"
            "We have received your inquiry and a technical specialist "
            "will review your case and respond within 4 business hours.\n\n"
            "For urgent matters, please call our support hotline.\n\n"
            "Best regards,\n{company_name} Technical Support Team"
        ),
        "keywords": ("technical", "support", "help", "issue", "فني", "دعم", "مشكلة"),
        "confidence": 0.75,
        "requires_human": False,
    },
}


def match_smart_reply(subject: str, body: str) -> SmartReply | None:
    """Match an incoming email against smart reply templates.

    Returns the best matching SmartReply or None if no match exceeds threshold.
    """
    haystack = f"{subject} {body}".lower()
    best_match: SmartReply | None = None
    best_score = 0.0

    for key, template in _TEMPLATES.items():
        hits = sum(1 for kw in template["keywords"] if kw.lower() in haystack)
        if hits == 0:
            continue

        score = min(template["confidence"], 0.5 + hits * 0.15)
        if score > best_score:
            best_score = score
            best_match = SmartReply(
                template_key=key,
                confidence=score,
                subject=template["subject"],
                body=template["body"],
                requires_human=template["requires_human"],
            )

    if best_match and best_match.confidence >= 0.6:
        return best_match
    return None


def render_reply(
    match: SmartReply,
    *,
    original_subject: str = "",
    sender_name: str = "Customer",
    company_name: str = "Our Company",
) -> dict[str, str]:
    """Render a smart reply template with dynamic values."""
    return {
        "subject": match.subject.format(original_subject=original_subject),
        "body": match.body.format(sender_name=sender_name, company_name=company_name),
    }


def list_templates() -> list[dict[str, Any]]:
    """Return all available smart reply templates."""
    return [
        {
            "key": key,
            "keywords": template["keywords"],
            "confidence": template["confidence"],
            "requires_human": template["requires_human"],
        }
        for key, template in _TEMPLATES.items()
    ]
