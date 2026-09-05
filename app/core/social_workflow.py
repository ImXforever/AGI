"""Social content planning and publishing policy (v18 — extended with platform + scheduling)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from app.core.policy import RiskLevel, evaluate_action


class SocialContentStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    BLOCKED = "blocked"


class SocialPlatform(StrEnum):
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


@dataclass(frozen=True)
class SocialPost:
    platform: str
    caption: str
    status: SocialContentStatus
    risk: RiskLevel
    requires_approval: bool
    reason: str
    scheduled_at: float = 0.0
    media_url: str = ""
    hashtags: tuple[str, ...] = ()


_SENSITIVE_MARKERS = (
    "guaranteed",
    "مضمون",
    "best price",
    "ارزان‌ترین",
    "contract",
    "قرارداد",
    "cure",
    "درمان",
    "investment return",
    "سود قطعی",
)

_PLATFORM_LIMITS = {
    SocialPlatform.INSTAGRAM: 2200,
    SocialPlatform.TWITTER: 280,
    SocialPlatform.LINKEDIN: 3000,
    SocialPlatform.FACEBOOK: 63206,
}


def prepare_post(
    *,
    platform: str,
    caption: str,
    scheduled_at: float = 0.0,
    media_url: str = "",
    hashtags: list[str] | None = None,
) -> SocialPost:
    """Prepare a social post with platform validation and scheduling support."""
    clean_platform = platform.strip().lower()
    clean_caption = " ".join(caption.split())
    if not clean_platform:
        raise ValueError("social platform must not be empty")
    if not clean_caption:
        raise ValueError("social caption must not be empty")

    platform_enum = SocialPlatform(clean_platform)
    max_length = _PLATFORM_LIMITS.get(platform_enum, 5000)
    if len(clean_caption) > max_length:
        raise ValueError(f"social caption exceeds {max_length} characters for {clean_platform}")

    sensitive = any(marker.casefold() in clean_caption.casefold() for marker in _SENSITIVE_MARKERS)

    status = SocialContentStatus.DRAFT
    if scheduled_at > 0:
        if scheduled_at <= time.time():
            raise ValueError("scheduled_at must be in the future")
        status = SocialContentStatus.SCHEDULED

    # Client matrix: ordinary calendar content publishes automatically.
    # Ad-hoc drafts and any sensitive claim still require the manager.
    if sensitive:
        requires_approval = True
        reason = "sensitive claim requires review"
    elif status == SocialContentStatus.SCHEDULED:
        requires_approval = False
        reason = "ordinary calendar content publishes automatically"
    else:
        requires_approval = True
        reason = "ad-hoc publishing requires approval"

    return SocialPost(
        platform=clean_platform,
        caption=clean_caption,
        status=status,
        risk=RiskLevel.HIGH if sensitive else RiskLevel.MEDIUM,
        requires_approval=requires_approval,
        reason=reason,
        scheduled_at=scheduled_at,
        media_url=media_url,
        hashtags=tuple(hashtags or []),
    )


def publishing_decision(*, approved: bool = False, actor_role: str = "agent"):
    """Use the central policy for the final publication action."""
    return evaluate_action("publish_content", actor_role=actor_role, approved=approved)


def get_platform_limit(platform: str) -> int:
    """Get the character limit for a platform."""
    try:
        return _PLATFORM_LIMITS.get(SocialPlatform(platform), 5000)
    except ValueError:
        return 5000


def truncate_caption(caption: str, platform: str, suffix: str = "...") -> str:
    """Truncate a caption to fit within platform limits."""
    limit = get_platform_limit(platform)
    if len(caption) <= limit:
        return caption
    return caption[: limit - len(suffix)] + suffix


def format_engagement_report(metrics: dict[str, Any], platform: str) -> str:
    """Format engagement metrics into a readable report."""
    lines = [f"📊 {platform.upper()} Engagement Report\n"]
    lines.append(f"{'=' * 30}")
    for key, value in metrics.items():
        lines.append(f"  {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines)


from typing import Any
