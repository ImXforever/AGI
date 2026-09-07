"""Social content planning and publishing policy (v18 — extended with platform + scheduling)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

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


class SocialPhase(StrEnum):
    PLAN = "plan_calendar"
    CAPTION = "write_caption"
    PUBLISH_ORDINARY = "publish_ordinary"
    HOLD = "hold"
    REPLY = "reply_comment"
    REPORT = "report_engagement"
    REFUSE = "refuse_ad_spend"


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


@dataclass(frozen=True)
class SocialAgentResult:
    """One social-agent step. Never spends ads. Never posts by itself."""

    phase: SocialPhase
    action: str
    post: SocialPost | None
    production: bool
    reason: str
    payload: dict[str, Any]


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

_AD_SPEND_MARKERS = (
    "buy ads",
    "ad spend",
    "boost post",
    "boost this",
    "paid campaign",
    "promote this post",
    "meta ads",
    "google ads",
    "ad budget",
    "spend budget",
)

_COMMON_COMMENT_MARKERS = (
    "thank",
    "thanks",
    "opening hours",
    "catalog",
    "catalogue",
    "where are you",
    "ساعت کار",
    "کاتالوگ",
)

_PLATFORM_LIMITS = {
    SocialPlatform.INSTAGRAM: 2200,
    SocialPlatform.TWITTER: 280,
    SocialPlatform.LINKEDIN: 3000,
    SocialPlatform.FACEBOOK: 63206,
}


def caption_is_ad_spend(caption: str) -> bool:
    hay = (caption or "").casefold()
    return any(marker in hay for marker in _AD_SPEND_MARKERS)


def caption_is_sensitive(caption: str) -> bool:
    hay = (caption or "").casefold()
    return any(marker.casefold() in hay for marker in _SENSITIVE_MARKERS)


def caption_is_ordinary(caption: str) -> bool:
    """Ordinary = on-calendar eligible: no claims, no ad spend."""
    return not caption_is_sensitive(caption) and not caption_is_ad_spend(caption)


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

    sensitive = caption_is_sensitive(clean_caption)
    ad_spend = caption_is_ad_spend(clean_caption)

    status = SocialContentStatus.DRAFT
    if scheduled_at > 0:
        if scheduled_at <= time.time():
            raise ValueError("scheduled_at must be in the future")
        status = SocialContentStatus.SCHEDULED

    # Client matrix: ordinary calendar content publishes automatically.
    # Ad-hoc drafts, ads, and any sensitive claim still require the manager.
    if ad_spend:
        requires_approval = True
        reason = "ad spend is not allowed"
        status = SocialContentStatus.BLOCKED
    elif sensitive:
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
        risk=RiskLevel.HIGH if (sensitive or ad_spend) else RiskLevel.MEDIUM,
        requires_approval=requires_approval,
        reason=reason,
        scheduled_at=scheduled_at,
        media_url=media_url,
        hashtags=tuple(hashtags or []),
    )


def publishing_decision(
    *, approved: bool = False, actor_role: str = "agent", approval_id: str = ""
):
    """Use the central policy for the final publication action."""
    return evaluate_action(
        "publish_content", actor_role=actor_role, approved=approved, approval_id=approval_id
    )


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
    lines = [f"{platform.upper()} Engagement Report", "=" * 30]
    for key, value in metrics.items():
        lines.append(f"  {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines)


def prepare_comment_reply(text: str) -> SocialAgentResult:
    """Tool: comment/DM reply under policy. Common thanks/hours AUTO; claims HITL."""
    body = (text or "").strip()
    if caption_is_ad_spend(body):
        return SocialAgentResult(
            phase=SocialPhase.REFUSE,
            action="invalid_ad_spend",
            post=None,
            production=False,
            reason="ad spend is not allowed",
            payload={"text": body[:500]},
        )
    if caption_is_sensitive(body):
        return SocialAgentResult(
            phase=SocialPhase.HOLD,
            action="publish_content",
            post=None,
            production=False,
            reason="sensitive comment/DM held for manager",
            payload={"text": body[:500], "kind": "comment"},
        )
    hay = body.casefold()
    common = any(m in hay for m in _COMMON_COMMENT_MARKERS)
    if common:
        return SocialAgentResult(
            phase=SocialPhase.REPLY,
            action="reply_common",
            post=None,
            production=False,
            reason="ordinary social reply",
            payload={"text": body[:500], "kind": "comment"},
        )
    return SocialAgentResult(
        phase=SocialPhase.HOLD,
        action="publish_content",
        post=None,
        production=False,
        reason="off-policy comment held for manager",
        payload={"text": body[:500], "kind": "comment"},
    )


def handle_social(
    text: str,
    *,
    extras: dict[str, Any] | None = None,
) -> SocialAgentResult:
    """State machine: refuse ads | report | reply | publish_ordinary | hold."""
    extras = dict(extras or {})
    caption = str(extras.get("caption") or text or "")
    if extras.get("ad") or caption_is_ad_spend(caption) or caption_is_ad_spend(text):
        return SocialAgentResult(
            phase=SocialPhase.REFUSE,
            action="invalid_ad_spend",
            post=None,
            production=False,
            reason="ad spend is not allowed",
            payload={"text": caption[:500]},
        )
    if extras.get("metrics") is not None or extras.get("engagement"):
        raw_metrics = extras.get("metrics")
        metrics: dict[str, Any] = dict(raw_metrics) if isinstance(raw_metrics, dict) else {}
        platform = str(extras.get("platform") or "instagram")
        return SocialAgentResult(
            phase=SocialPhase.REPORT,
            action="create_task",
            post=None,
            production=False,
            reason="engagement report for manager",
            payload={
                "title": f"{platform} engagement report",
                "kind": "ops",
                "report": format_engagement_report(metrics, platform),
            },
        )
    if extras.get("comment") or extras.get("dm"):
        raw = extras.get("comment") or extras.get("dm") or text
        return prepare_comment_reply(str(raw))

    platform = str(extras.get("platform") or "instagram")
    scheduled_at = float(extras.get("scheduled_at") or 0.0)
    post = prepare_post(
        platform=platform,
        caption=caption,
        scheduled_at=scheduled_at,
        media_url=str(extras.get("media_url") or ""),
        hashtags=list(extras.get("hashtags") or []),
    )
    payload = {
        "platform": post.platform,
        "caption": post.caption,
        "status": post.status.value,
        "scheduled_at": post.scheduled_at,
        "reason": post.reason,
    }
    if post.requires_approval:
        return SocialAgentResult(
            phase=SocialPhase.HOLD,
            action="publish_content",
            post=post,
            production=False,
            reason=post.reason,
            payload=payload,
        )
    return SocialAgentResult(
        phase=SocialPhase.PUBLISH_ORDINARY,
        action="publish_calendar",
        post=post,
        production=False,
        reason=post.reason,
        payload=payload,
    )
