"""Tests for v0.8 social content safety boundaries."""

from __future__ import annotations

import pytest

from app.core.policy import RiskLevel
from app.core.social_workflow import (
    SocialContentStatus,
    prepare_post,
    publishing_decision,
)


def test_post_is_normalized_and_stays_a_draft() -> None:
    post = prepare_post(platform=" LinkedIn ", caption="  A   useful   update  ")
    assert post.platform == "linkedin"
    assert post.caption == "A useful update"
    assert post.status == SocialContentStatus.DRAFT
    assert post.requires_approval is True
    assert post.risk == RiskLevel.MEDIUM


def test_sensitive_claim_gets_high_risk() -> None:
    post = prepare_post(platform="instagram", caption="Guaranteed best price")
    assert post.risk == RiskLevel.HIGH
    assert "review" in post.reason


def test_only_manager_approval_allows_publication() -> None:
    assert publishing_decision().allowed is False
    assert publishing_decision(approved=True, actor_role="agent").allowed is False
    assert publishing_decision(approved=True, actor_role="superadmin").allowed is True


@pytest.mark.parametrize("platform, caption", [("", "hello"), ("linkedin", " ")])
def test_empty_post_fields_are_rejected(platform: str, caption: str) -> None:
    with pytest.raises(ValueError):
        prepare_post(platform=platform, caption=caption)
