"""Content calendar system (v18).

Schedule, manage, and auto-publish social media posts across platforms.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.content_calendar")


class CalendarPostStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentPlatform(StrEnum):
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


@dataclass
class CalendarPost:
    id: str
    title: str
    caption: str
    platform: ContentPlatform
    scheduled_at: float
    status: CalendarPostStatus
    created_at: float
    published_at: float | None
    post_id: str | None
    media_url: str
    hashtags: tuple[str, ...]
    created_by: str
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "caption": self.caption,
            "platform": self.platform.value,
            "scheduled_at": self.scheduled_at,
            "status": self.status.value,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "post_id": self.post_id,
            "media_url": self.media_url,
            "hashtags": list(self.hashtags),
            "created_by": self.created_by,
            "notes": self.notes,
        }

    def to_text(self) -> str:
        import datetime

        sched = datetime.datetime.fromtimestamp(self.scheduled_at).strftime("%Y-%m-%d %H:%M")
        return (
            f"{self.title}\n"
            f"  Platform: {self.platform.value}\n"
            f"  Scheduled: {sched}\n"
            f"  Status: {self.status.value}\n"
            f"  Caption: {self.caption[:100]}..."
        )


def _gen_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


def create_calendar_post(
    title: str,
    caption: str,
    platform: str,
    scheduled_at: float,
    *,
    media_url: str = "",
    hashtags: list[str] | None = None,
    created_by: str = "admin",
    notes: str = "",
) -> CalendarPost:
    """Create a new content calendar post.

    A small grace window allows recently-due posts to be created for retry or
    import flows, but obviously stale timestamps are rejected.
    """
    if scheduled_at < time.time() - 300:
        raise ValueError("scheduled_at cannot be far in the past")

    return CalendarPost(
        id=_gen_id(),
        title=title,
        caption=caption,
        platform=ContentPlatform(platform),
        scheduled_at=scheduled_at,
        status=CalendarPostStatus.SCHEDULED,
        created_at=time.time(),
        published_at=None,
        post_id=None,
        media_url=media_url,
        hashtags=tuple(hashtags or []),
        created_by=created_by,
        notes=notes,
    )


def is_ready_to_publish(post: CalendarPost) -> bool:
    """Check if a post should be published now."""
    if post.status != CalendarPostStatus.SCHEDULED:
        return False
    return time.time() >= post.scheduled_at


def mark_publishing(post: CalendarPost) -> CalendarPost:
    """Mark a post as currently being published."""
    post.status = CalendarPostStatus.PUBLISHING
    return post


def mark_published(post: CalendarPost, post_id: str) -> CalendarPost:
    """Mark a post as successfully published."""
    post.status = CalendarPostStatus.PUBLISHED
    post.published_at = time.time()
    post.post_id = post_id
    return post


def mark_failed(post: CalendarPost) -> CalendarPost:
    """Mark a post as failed."""
    post.status = CalendarPostStatus.FAILED
    return post


def cancel_post(post: CalendarPost) -> CalendarPost:
    """Cancel a scheduled post."""
    post.status = CalendarPostStatus.CANCELLED
    return post


def reschedule(post: CalendarPost, new_time: float) -> CalendarPost:
    """Reschedule a post to a new time."""
    post.scheduled_at = new_time
    post.status = CalendarPostStatus.SCHEDULED
    return post


def get_ready_posts(posts: list[CalendarPost]) -> list[CalendarPost]:
    """Filter posts that are ready to publish now."""
    return [p for p in posts if is_ready_to_publish(p)]


def get_upcoming(posts: list[CalendarPost], hours: int = 24) -> list[CalendarPost]:
    """Get posts scheduled within the next N hours."""
    now = time.time()
    cutoff = now + hours * 3600
    return [
        p
        for p in posts
        if p.status == CalendarPostStatus.SCHEDULED and now <= p.scheduled_at <= cutoff
    ]


def get_content_plan(posts: list[CalendarPost], days: int = 7) -> dict[str, list[CalendarPost]]:
    """Get content plan grouped by day for the next N days."""
    import datetime

    now = time.time()
    plan: dict[str, list[CalendarPost]] = {}
    for post in posts:
        if post.status not in (CalendarPostStatus.SCHEDULED, CalendarPostStatus.PUBLISHED):
            continue
        post_time = datetime.datetime.fromtimestamp(post.scheduled_at)
        day_key = post_time.strftime("%Y-%m-%d")
        if post_time.timestamp() >= now and post_time.timestamp() <= now + days * 86400:
            plan.setdefault(day_key, []).append(post)
    return dict(sorted(plan.items()))


def build_post_caption(
    title: str,
    body: str,
    *,
    hashtags: list[str] | None = None,
    platform: str = "instagram",
) -> str:
    """Build a formatted caption for a social post."""
    caption = f"{title}\n\n{body}"
    tags = " ".join(f"#{t.lstrip('#')}" for t in (hashtags or []))

    if platform == "twitter":
        suffix = f"\n\n{tags}" if tags else ""
        if len(caption) + len(suffix) > 280:
            max_body = max(0, 280 - len(title) - len(suffix) - 5)
            trimmed_body = f"{body[:max_body]}..." if max_body < len(body) else body
            caption = f"{title}\n\n{trimmed_body}"
        if tags:
            caption = f"{caption}{suffix}"
        return caption[:280]

    if tags:
        caption = f"{caption}\n\n{tags}"
    return caption
