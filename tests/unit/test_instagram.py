"""Tests for v18 Instagram adapter."""

from __future__ import annotations

import pytest

from app.channels.instagram import InstagramAdapter, InstagramPost


class TestInstagramMock:
    @pytest.mark.asyncio
    async def test_publish_post(self):
        adapter = InstagramAdapter(mock_mode=True)
        post = await adapter.publish_post("Test caption", image_url="https://example.com/img.jpg")
        assert post.id != ""
        assert post.caption == "Test caption"
        assert post.media_type == "IMAGE"

    @pytest.mark.asyncio
    async def test_reply_comment(self):
        adapter = InstagramAdapter(mock_mode=True)
        result = await adapter.reply_comment("comment-123", "Thanks for your comment!")
        assert result is True

    @pytest.mark.asyncio
    async def test_reply_dm(self):
        adapter = InstagramAdapter(mock_mode=True)
        result = await adapter.reply_dm("user-123", "Hello!")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_engagement(self):
        adapter = InstagramAdapter(mock_mode=True)
        metrics = await adapter.get_engagement("post-123")
        assert "likes" in metrics
        assert "comments" in metrics

    @pytest.mark.asyncio
    async def test_get_media_feed(self):
        adapter = InstagramAdapter(mock_mode=True)
        feed = await adapter.get_media_feed()
        assert len(feed) >= 1

    @pytest.mark.asyncio
    async def test_get_comments(self):
        adapter = InstagramAdapter(mock_mode=True)
        comments = await adapter.get_comments("media-123")
        assert len(comments) >= 1


class TestInstagramPost:
    def test_as_dict(self):
        post = InstagramPost(
            id="test-1",
            caption="Hello",
            media_type="IMAGE",
            media_url="https://example.com/img.jpg",
            permalink="https://instagram.com/p/test-1",
            timestamp="2025-06-15T10:00:00",
            like_count=10,
            comments_count=3,
        )
        d = post.as_dict()
        assert d["id"] == "test-1"
        assert d["like_count"] == 10
