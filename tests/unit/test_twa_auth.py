"""TWA probe/login helpers: only TELEGRAM_ADMIN_IDS are treated as admins."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from app.admin_api.twa import (
    _is_admin_id,
    _telegram_user_id,
    _verify_telegram_data,
)

TOKEN = "123456:TEST-token-for-twa-suite"


def _sign(user_id: int) -> str:
    user = json.dumps({"id": user_id, "first_name": "Sara"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "user": user}
    check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**params, "hash": digest})


def test_verify_accepts_signed_init_data() -> None:
    data = _verify_telegram_data(_sign(42), TOKEN)
    assert _telegram_user_id(data) == "42"


def test_verify_rejects_forged_hash() -> None:
    with pytest.raises(ValueError):
        _verify_telegram_data("auth_date=1&user=%7B%7D&hash=dead", TOKEN)


def test_admin_id_match() -> None:
    cfg = SimpleNamespace(channels=SimpleNamespace(telegram_admin_ids=["42", "99"]))
    assert _is_admin_id(cfg, "42") is True
    assert _is_admin_id(cfg, "7") is False
    assert _is_admin_id(cfg, "") is False


def test_telegram_user_id_from_json_blob() -> None:
    assert _telegram_user_id({"user": json.dumps({"id": 42})}) == "42"
    assert _telegram_user_id({"user": "not-json"}) == ""
