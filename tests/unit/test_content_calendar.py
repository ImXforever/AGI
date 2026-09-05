"""Tests for v18 content calendar."""

from __future__ import annotations

import time

import pytest

from app.core.content_calendar import (
    CalendarPostStatus,
    ContentPlatform,
    build_post_caption,
    cancel_post,
    create_calendar_post,
    get_content_plan,
    get_ready_posts,
    is_ready_to_publish,
    mark_failed,
    mark_published,
    mark_publishing,
    reschedule,
)


class TestCalendarPostCreation:
    def test_create_basic(self):
        post = create_calendar_post("Title", "Caption body", "instagram", time.time() + 3600)
        assert post.status == CalendarPostStatus.SCHEDULED
        assert post.platform == ContentPlatform.INSTAGRAM

    def test_create_twitter(self):
        post = create_calendar_post("Title", "Tweet text", "twitter", time.time() + 3600)
        assert post.platform == ContentPlatform.TWITTER

    def test_create_with_hashtags(self):
        post = create_calendar_post(
            "Title", "Caption", "instagram", time.time() + 3600, hashtags=["oil", "petroleum"]
        )
        assert len(post.hashtags) == 2

    def test_create_past_time_raises(self):
        with pytest.raises(ValueError):
            create_calendar_post("Title", "Caption", "instagram", time.time() - 3600)


class TestCalendarPostLogic:
    def test_is_ready_when_scheduled_and_past(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() - 100)
        assert is_ready_to_publish(post)

    def test_is_not_ready_when_future(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() + 3600)
        assert not is_ready_to_publish(post)

    def test_mark_publishing(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() - 100)
        post = mark_publishing(post)
        assert post.status == CalendarPostStatus.PUBLISHING

    def test_mark_published(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() - 100)
        post = mark_published(post, "ig-123")
        assert post.status == CalendarPostStatus.PUBLISHED
        assert post.post_id == "ig-123"
        assert post.published_at is not None

    def test_mark_failed(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() - 100)
        post = mark_failed(post)
        assert post.status == CalendarPostStatus.FAILED

    def test_cancel(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() + 3600)
        post = cancel_post(post)
        assert post.status == CalendarPostStatus.CANCELLED

    def test_reschedule(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() + 3600)
        new_time = time.time() + 7200
        post = reschedule(post, new_time)
        assert post.scheduled_at == new_time
        assert post.status == CalendarPostStatus.SCHEDULED


class TestCalendarFiltering:
    def test_get_ready_posts(self):
        p1 = create_calendar_post("T1", "C1", "instagram", time.time() - 100)
        p2 = create_calendar_post("T2", "C2", "twitter", time.time() + 3600)
        ready = get_ready_posts([p1, p2])
        assert len(ready) == 1

    def test_get_content_plan(self):
        p1 = create_calendar_post("T1", "C1", "instagram", time.time() + 86400)
        p2 = create_calendar_post("T2", "C2", "twitter", time.time() + 172800)
        plan = get_content_plan([p1, p2], days=7)
        assert len(plan) >= 1


class TestCaptionBuilding:
    def test_basic_caption(self):
        caption = build_post_caption("Title", "Body text")
        assert "Title" in caption
        assert "Body text" in caption

    def test_caption_with_hashtags(self):
        caption = build_post_caption("Title", "Body", hashtags=["oil", "gas"])
        assert "#oil" in caption
        assert "#gas" in caption

    def test_twitter_truncation(self):
        long_body = "x" * 300
        caption = build_post_caption("Title", long_body, platform="twitter")
        assert len(caption) <= 280


class TestCalendarPostSerialization:
    def test_as_dict(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() + 3600)
        d = post.as_dict()
        assert "id" in d
        assert "platform" in d
        assert d["platform"] == "instagram"

    def test_to_text(self):
        post = create_calendar_post("Title", "Caption", "instagram", time.time() + 3600)
        text = post.to_text()
        assert "Title" in text
        assert "instagram" in text
