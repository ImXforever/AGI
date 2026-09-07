"""Channel registry — maps channel names to adapter instances (v18 — added Instagram + Twitter)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.channels.base import ChannelAdapter
from app.config import Config
from app.constants import CHANNEL_EMAIL, CHANNEL_TELEGRAM, CHANNEL_WHATSAPP

if TYPE_CHECKING:
    import redis.asyncio as aioredis

__all__ = ["ChannelRegistry", "build_registry"]

CHANNEL_INSTAGRAM = "instagram"
CHANNEL_TWITTER = "twitter"


class ChannelRegistry:
    """Thread-safe lookup of active channel adapters."""

    def __init__(self, adapters: dict[str, ChannelAdapter]) -> None:
        self._adapters = dict(adapters)

    def has(self, name: str) -> bool:
        return name in self._adapters

    def get(self, name: str) -> ChannelAdapter | None:
        return self._adapters.get(name)

    @property
    def enabled(self) -> list[str]:
        return sorted(self._adapters.keys())

    def __len__(self) -> int:
        return len(self._adapters)

    def __repr__(self) -> str:
        return f"ChannelRegistry({', '.join(self.enabled)})"


def build_registry(cfg: Config, *, redis: aioredis.Redis) -> ChannelRegistry:
    """Instantiate adapters that are enabled in configuration."""
    from app.channels.email import EmailAdapter
    from app.channels.telegram import TelegramAdapter
    from app.channels.whatsapp import WhatsAppAdapter

    adapters: dict[str, ChannelAdapter] = {}

    adapters[CHANNEL_TELEGRAM] = TelegramAdapter(cfg=cfg, redis=redis)

    if cfg.channels.whatsapp_enabled:
        adapters[CHANNEL_WHATSAPP] = WhatsAppAdapter(cfg=cfg, redis=redis)

    if cfg.channels.email_enabled:
        adapters[CHANNEL_EMAIL] = EmailAdapter(cfg=cfg, redis=redis)

    if cfg.channels.instagram_enabled:
        from app.channels.instagram import InstagramAdapter

        adapters[CHANNEL_INSTAGRAM] = cast(
            "ChannelAdapter",
            InstagramAdapter(
                access_token=cfg.channels.instagram_access_token,
                business_account_id=cfg.channels.instagram_business_account_id,
                mock_mode=not bool(cfg.channels.instagram_access_token),
            ),
        )

    if cfg.channels.twitter_enabled:
        from app.channels.twitter import TwitterAdapter

        adapters[CHANNEL_TWITTER] = cast(
            "ChannelAdapter",
            TwitterAdapter(
                api_key=cfg.channels.twitter_api_key,
                api_secret=cfg.channels.twitter_api_secret,
                access_token=cfg.channels.twitter_access_token,
                access_secret=cfg.channels.twitter_access_secret,
                bearer_token=cfg.channels.twitter_bearer_token,
                mock_mode=not bool(cfg.channels.twitter_bearer_token),
            ),
        )

    return ChannelRegistry(adapters)
