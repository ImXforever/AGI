"""Tests for v18 Twitter adapter."""

from __future__ import annotations

import pytest

from app.channels.twitter import Tweet, TwitterAdapter


class TestTwitterMock:
    @pytest.mark.asyncio
    async def test_publish_tweet(self):
        adapter = TwitterAdapter(mock_mode=True)
        tweet = await adapter.publish_tweet("Hello world!")
        assert tweet.id != ""
        assert tweet.text == "Hello world!"

    @pytest.mark.asyncio
    async def test_reply_to_tweet(self):
        adapter = TwitterAdapter(mock_mode=True)
        tweet = await adapter.reply_to_tweet("tweet-123", "Reply text")
        assert tweet.id != ""

    @pytest.mark.asyncio
    async def test_get_mentions(self):
        adapter = TwitterAdapter(mock_mode=True)
        mentions = await adapter.get_mentions()
        assert len(mentions) >= 1

    @pytest.mark.asyncio
    async def test_get_analytics(self):
        adapter = TwitterAdapter(mock_mode=True)
        analytics = await adapter.get_analytics("tweet-123")
        assert "impressions" in analytics
        assert "engagement_rate" in analytics

    @pytest.mark.asyncio
    async def test_delete_tweet(self):
        adapter = TwitterAdapter(mock_mode=True)
        result = await adapter.delete_tweet("tweet-123")
        assert result is True


class TestTweet:
    def test_as_dict(self):
        tweet = Tweet(
            id="test-1",
            text="Hello",
            created_at="2025-06-15T10:00:00Z",
            like_count=5,
            retweet_count=2,
            reply_count=1,
            impression_count=100,
        )
        d = tweet.as_dict()
        assert d["id"] == "test-1"
        assert d["like_count"] == 5
        assert d["impression_count"] == 100
