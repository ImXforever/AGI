"""Channel readiness snapshot for ops. No live network in the pure check."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChannelStatus:
    name: str
    enabled: bool
    configured: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "configured": self.configured,
            "detail": self.detail,
        }


def snapshot(
    *,
    telegram_token: str = "",
    telegram_webhook_secret: str = "",
    whatsapp_enabled: bool = False,
    whatsapp_secret: str = "",
    email_enabled: bool = False,
) -> list[ChannelStatus]:
    tg_ok = bool(telegram_token) and bool(telegram_webhook_secret)
    rows = [
        ChannelStatus(
            "telegram",
            True,
            tg_ok,
            "ok" if tg_ok else "token or webhook secret missing",
        ),
        ChannelStatus(
            "whatsapp",
            whatsapp_enabled,
            bool(whatsapp_secret) if whatsapp_enabled else True,
            "disabled" if not whatsapp_enabled else ("ok" if whatsapp_secret else "secret missing"),
        ),
        ChannelStatus(
            "email",
            email_enabled,
            True,
            "enabled" if email_enabled else "disabled",
        ),
    ]
    return rows


def is_red(rows: list[ChannelStatus]) -> bool:
    return any(
        (r.enabled and not r.configured) or (r.name == "telegram" and not r.configured)
        for r in rows
    )
