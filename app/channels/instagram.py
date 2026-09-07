"""Instagram channel adapter via Meta Graph API (v18)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.channels.instagram")


@dataclass(frozen=True)
class InstagramPost:
    id: str
    caption: str
    media_type: str
    media_url: str
    permalink: str
    timestamp: str
    like_count: int
    comments_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "caption": self.caption,
            "media_type": self.media_type,
            "media_url": self.media_url,
            "permalink": self.permalink,
            "timestamp": self.timestamp,
            "like_count": self.like_count,
            "comments_count": self.comments_count,
        }


@dataclass
class InstagramAdapter:
    """Instagram Graph API adapter.

    Requires: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID
    """

    access_token: str = ""
    business_account_id: str = ""
    base_url: str = "https://graph.facebook.com/v20.0"
    mock_mode: bool = True
    _posts: list[InstagramPost] = field(default_factory=list)

    async def publish_post(
        self,
        caption: str,
        *,
        image_url: str = "",
        media_type: str = "IMAGE",
    ) -> InstagramPost:
        """Publish a post to Instagram."""
        if self.mock_mode:
            return self._mock_publish(caption, image_url, media_type)
        return await self._api_publish(caption, image_url, media_type)

    async def reply_comment(self, comment_id: str, message: str) -> bool:
        """Reply to an Instagram comment."""
        if self.mock_mode:
            log.info(
                "mock_reply_comment",
                extra={"action": "instagram.reply_comment", "comment_id": comment_id},
            )
            return True
        return await self._api_reply_comment(comment_id, message)

    async def reply_dm(self, user_id: str, message: str) -> bool:
        """Reply to an Instagram DM."""
        if self.mock_mode:
            log.info("mock_reply_dm", extra={"action": "instagram.reply_dm", "user_id": user_id})
            return True
        return await self._api_reply_dm(user_id, message)

    async def get_engagement(self, post_id: str) -> dict[str, Any]:
        """Get engagement metrics for a post."""
        if self.mock_mode:
            return {"likes": 42, "comments": 7, "shares": 3, "saves": 12}
        return await self._api_engagement(post_id)

    async def get_media_feed(self, limit: int = 20) -> list[InstagramPost]:
        """Get recent media from the business account."""
        if self.mock_mode:
            return self._mock_feed()
        return await self._api_feed(limit)

    async def get_comments(self, media_id: str) -> list[dict[str, Any]]:
        """Get comments on a media post."""
        if self.mock_mode:
            return [
                {
                    "id": "mock-c1",
                    "text": "Great product!",
                    "username": "user1",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            ]
        return await self._api_comments(media_id)

    async def _api_publish(self, caption: str, image_url: str, media_type: str) -> InstagramPost:
        import httpx

        container_resp = await httpx.AsyncClient().post(
            f"{self.base_url}/{self.business_account_id}/media",
            data={
                "caption": caption,
                "image_url": image_url,
                "media_type": media_type,
                "access_token": self.access_token,
            },
            timeout=30,
        )
        container_resp.raise_for_status()
        container_id = container_resp.json().get("id", "")
        publish_resp = await httpx.AsyncClient().post(
            f"{self.base_url}/{self.business_account_id}/media_publish",
            data={"creation_id": container_id, "access_token": self.access_token},
            timeout=30,
        )
        publish_resp.raise_for_status()
        data = publish_resp.json()
        return InstagramPost(
            id=data.get("id", ""),
            caption=caption,
            media_type=media_type,
            media_url=image_url,
            permalink=f"https://instagram.com/p/{data.get('id', '')}",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            like_count=0,
            comments_count=0,
        )

    async def _api_reply_comment(self, comment_id: str, message: str) -> bool:
        import httpx

        resp = await httpx.AsyncClient().post(
            f"{self.base_url}/{comment_id}/replies",
            data={"message": message, "access_token": self.access_token},
            timeout=30,
        )
        resp.raise_for_status()
        return True

    async def _api_reply_dm(self, user_id: str, message: str) -> bool:
        import httpx

        resp = await httpx.AsyncClient().post(
            f"{self.base_url}/me/messages",
            json={"recipient": {"id": user_id}, "message": {"text": message}},
            params={"access_token": self.access_token},
            timeout=30,
        )
        resp.raise_for_status()
        return True

    async def _api_engagement(self, post_id: str) -> dict[str, Any]:
        import httpx

        resp = await httpx.AsyncClient().get(
            f"{self.base_url}/{post_id}",
            params={"fields": "like_count,comments_count", "access_token": self.access_token},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"likes": data.get("like_count", 0), "comments": data.get("comments_count", 0)}

    async def _api_feed(self, limit: int) -> list[InstagramPost]:
        import httpx

        resp = await httpx.AsyncClient().get(
            f"{self.base_url}/{self.business_account_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
                "limit": limit,
                "access_token": self.access_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            InstagramPost(
                id=item.get("id", ""),
                caption=item.get("caption", ""),
                media_type=item.get("media_type", ""),
                media_url=item.get("media_url", ""),
                permalink=item.get("permalink", ""),
                timestamp=item.get("timestamp", ""),
                like_count=item.get("like_count", 0),
                comments_count=item.get("comments_count", 0),
            )
            for item in data.get("data", [])
        ]

    async def _api_comments(self, media_id: str) -> list[dict[str, Any]]:
        import httpx

        resp = await httpx.AsyncClient().get(
            f"{self.base_url}/{media_id}/comments",
            params={"fields": "id,text,username,timestamp", "access_token": self.access_token},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def _mock_publish(self, caption: str, image_url: str, media_type: str) -> InstagramPost:
        import hashlib
        import os

        post_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
        post = InstagramPost(
            id=post_id,
            caption=caption,
            media_type=media_type,
            media_url=image_url or "https://example.com/mock.jpg",
            permalink=f"https://instagram.com/p/{post_id}",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            like_count=0,
            comments_count=0,
        )
        self._posts.append(post)
        return post

    def _mock_feed(self) -> list[InstagramPost]:
        return (
            self._posts[-20:]
            if self._posts
            else [
                InstagramPost(
                    id="mock-ig-1",
                    caption="New industrial lubricant available!",
                    media_type="IMAGE",
                    media_url="https://example.com/lubricant.jpg",
                    permalink="https://instagram.com/p/mock-ig-1",
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    like_count=42,
                    comments_count=7,
                ),
            ]
        )
