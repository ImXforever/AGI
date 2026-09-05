"""Tests for v0.7 website lead and CMS workflow boundaries."""

from __future__ import annotations

import pytest

from app.core.policy import RiskLevel
from app.core.website_workflow import (
    WebsiteChangeKind,
    classify_content_change,
    normalize_contact_form,
)


def test_contact_form_is_normalized_before_lead_creation() -> None:
    lead = normalize_contact_form(
        name="  Jane   Doe ",
        email=" JANE@Example.COM ",
        message="Need product information",
    )
    assert lead.name == "Jane Doe"
    assert lead.email == "jane@example.com"
    assert lead.source == "website"


@pytest.mark.parametrize(
    ("field", "kind", "risk"),
    [
        ("price", WebsiteChangeKind.PRICE, RiskLevel.HIGH),
        ("refund_policy", WebsiteChangeKind.LEGAL, RiskLevel.HIGH),
        ("description", WebsiteChangeKind.CONTENT, RiskLevel.HIGH),
        ("description", WebsiteChangeKind.DELETE, RiskLevel.CRITICAL),
    ],
)
def test_cms_changes_are_classified_and_protected(field, kind, risk) -> None:
    after = "" if kind == WebsiteChangeKind.DELETE else "new value"
    change = classify_content_change(before="old value", after=after, field=field)
    assert change.kind == kind
    assert change.risk == risk
    assert change.requires_approval is True


def test_invalid_contact_form_is_rejected() -> None:
    with pytest.raises(ValueError, match="email"):
        normalize_contact_form(name="Jane", email="not-an-email", message="Hello")
    with pytest.raises(ValueError, match="message"):
        normalize_contact_form(name="Jane", email="jane@example.com", message=" ")
