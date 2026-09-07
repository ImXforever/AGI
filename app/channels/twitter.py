"""Twitter/X channel adapter via API v2 (v18)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.channels.twitter")


@dataclass(frozen=True)
class Tweet:
    id: str
    text: str
    created_at: str
    like_count: int
    retweet_count: int
    reply_count: int
    impression_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "created_at": self.created_at,
            "like_count": self.like_count,
            "retweet_count": self.retweet_count,
            "reply_count": self.reply_count,
            "impression_count": self.impression_count,
        }


@dataclass
class TwitterAdapter:
    """Twitter/X API v2 adapter.

    Requires: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
    """

    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    access_secret: str = ""
    bearer_token: str = ""
    base_url: str = "https://api.twitter.com/2"
    mock_mode: bool = True
    _tweets: list[Tweet] = field(default_factory=list)

    async def publish_tweet(self, text: str, *, media_ids: list[str] | None = None) -> Tweet:
        """Publish a tweet."""
        if self.mock_mode:
            return self._mock_publish(text)
        return await self._api_publish(text, media_ids or [])

    async def reply_to_tweet(self, tweet_id: str, text: str) -> Tweet:
        """Reply to a tweet."""
        if self.mock_mode:
            return self._mock_reply(tweet_id, text)
        return await self._api_reply(tweet_id, text)

    async def reply_to_mention(self, mention_id: str, text: str) -> Tweet:
        """Reply to a mention."""
        return await self.reply_to_tweet(mention_id, text)

    async def get_mentions(self, limit: int = 20) -> list[Tweet]:
        """Get recent mentions."""
        if self.mock_mode:
            return self._mock_mentions()
        return await self._api_mentions(limit)

    async def get_analytics(self, tweet_id: str) -> dict[str, Any]:
        """Get tweet analytics."""
        if self.mock_mode:
            return {"impressions": 1500, "engagements": 85, "engagement_rate": 5.67}
        return await self._api_analytics(tweet_id)

    async def search_tweets(self, query: str, limit: int = 20) -> list[Tweet]:
        """Search for tweets."""
        if self.mock_mode:
            return []
        return await self._api_search(query, limit)

    async def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet."""
        if self.mock_mode:
            self._tweets = [t for t in self._tweets if t.id != tweet_id]
            return True
        return await self._api_delete(tweet_id)

    async def _api_publish(self, text: str, media_ids: list[str]) -> Tweet:
        import httpx

        payload: dict[str, Any] = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        resp = await httpx.AsyncClient().post(
            f"{self.base_url}/tweets",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return Tweet(
            id=data.get("id", ""),
            text=data.get("text", ""),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            like_count=0,
            retweet_count=0,
            reply_count=0,
            impression_count=0,
        )

    async def _api_reply(self, tweet_id: str, text: str) -> Tweet:
        import httpx

        resp = await httpx.AsyncClient().post(
            f"{self.base_url}/tweets",
            json={"text": text, "reply": {"in_reply_to_tweet_id": tweet_id}},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return Tweet(
            id=data.get("id", ""),
            text=data.get("text", ""),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            like_count=0,
            retweet_count=0,
            reply_count=0,
            impression_count=0,
        )

    async def _api_mentions(self, limit: int) -> list[Tweet]:
        import httpx

        resp = await httpx.AsyncClient().get(
            f"{self.base_url}/users/me/mentions",
            params={"max_results": limit, "tweet.fields": "created_at,public_metrics"},
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [self._parse_tweet(item) for item in data]

    async def _api_analytics(self, tweet_id: str) -> dict[str, Any]:
        import httpx

        resp = await httpx.AsyncClient().get(
            f"{self.base_url}/tweets/{tweet_id}",
            params={"tweet.fields": "public_metrics"},
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        metrics = resp.json().get("data", {}).get("public_metrics", {})
        impressions = metrics.get("impression_count", 0)
        engagements = (
            metrics.get("like_count", 0)
            + metrics.get("retweet_count", 0)
            + metrics.get("reply_count", 0)
        )
        return {
            "impressions": impressions,
            "engagements": engagements,
            "engagement_rate": round(engagements / impressions * 100, 2) if impressions > 0 else 0,
        }

    async def _api_search(self, query: str, limit: int) -> list[Tweet]:
        import httpx

        resp = await httpx.AsyncClient().get(
            f"{self.base_url}/tweets/search/recent",
            params={
                "query": query,
                "max_results": limit,
                "tweet.fields": "created_at,public_metrics",
            },
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return [self._parse_tweet(item) for item in resp.json().get("data", [])]

    async def _api_delete(self, tweet_id: str) -> bool:
        import httpx

        resp = await httpx.AsyncClient().delete(
            f"{self.base_url}/tweets/{tweet_id}",
            headers={"Authorization": f"Bearer {self.bearer_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return True

    def _parse_tweet(self, data: dict[str, Any]) -> Tweet:
        metrics = data.get("public_metrics", {})
        return Tweet(
            id=data.get("id", ""),
            text=data.get("text", ""),
            created_at=data.get("created_at", ""),
            like_count=metrics.get("like_count", 0),
            retweet_count=metrics.get("retweet_count", 0),
            reply_count=metrics.get("reply_count", 0),
            impression_count=metrics.get("impression_count", 0),
        )

    def _mock_publish(self, text: str) -> Tweet:
        import hashlib
        import os

        tweet_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
        tweet = Tweet(
            id=tweet_id,
            text=text,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            like_count=0,
            retweet_count=0,
            reply_count=0,
            impression_count=0,
        )
        self._tweets.append(tweet)
        return tweet

    def _mock_reply(self, tweet_id: str, text: str) -> Tweet:
        import hashlib
        import os

        tweet_id_new = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
        tweet = Tweet(
            id=tweet_id_new,
            text=text,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            like_count=0,
            retweet_count=0,
            reply_count=0,
            impression_count=0,
        )
        self._tweets.append(tweet)
        return tweet

    def _mock_mentions(self) -> list[Tweet]:
        return [
            Tweet(
                id="mock-tw-1",
                text="@ZenovixDigital Do you ship to Europe?",
                created_at=time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                like_count=2,
                retweet_count=0,
                reply_count=1,
                impression_count=150,
            ),
        ]
