from __future__ import annotations

import secrets
import time


def new_public_id() -> str:
    n = (int(time.time()) % 900000) + secrets.randbelow(1000)
    return f"TCK-{n:06d}"


def new_token(nbytes: int = 16) -> str:
    return secrets.token_urlsafe(nbytes)


def new_ticket_id(tenant_prefix: str = "PT") -> str:
    ts = int(time.time())
    rand = secrets.randbelow(10000)
    return f"{tenant_prefix.upper()}-TCK-{ts:010d}-{rand:04d}"


def new_approval_id() -> str:
    ts = int(time.time())
    rand = secrets.randbelow(100000)
    return f"APR-{ts:010d}-{rand:05d}"
