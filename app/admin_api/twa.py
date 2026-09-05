"""Telegram Web App (TWA) login and admin probe.

Validates the ``initData`` string sent by Telegram's Mini App.
Only TELEGRAM_ADMIN_IDS may receive a session cookie.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.admin_api.auth import COOKIE_NAME, SESSION_MAX_AGE, _create_token
from app.config import Config
from app.logging_setup import get_logger

log = get_logger("app.admin_api.twa")

router = APIRouter(prefix="/twa", tags=["admin-twa"])


class TWALoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    init_data: str = Field(validation_alias=AliasChoices("init_data", "initData"))


class TWALoginResponse(BaseModel):
    ok: bool
    token: str
    username: str = ""
    next: str = "/admin/ops/ecosystem.html"


class TWAProbeResponse(BaseModel):
    ok: bool
    admin: bool = False


def _verify_telegram_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Parse and verify Telegram Mini App ``initData``.

    Returns the parsed data dict on success, raises on failure.
    """
    parsed = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in parsed:
        raise ValueError("missing hash in initData")
    received_hash = parsed.pop("hash")

    check_pairs = sorted(f"{k}={v}" for k, v in parsed.items() if k != "hash")
    check_string = "\n".join(check_pairs)

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("invalid initData hash")

    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > 300:
        raise ValueError("initData expired")

    return parsed


def _telegram_user_id(data: dict[str, str]) -> str:
    try:
        user_data = json.loads(data.get("user", "{}"))
    except (ValueError, TypeError):
        user_data = {}
    if not isinstance(user_data, dict):
        user_data = {}
    return str(user_data.get("id", "")).strip()


def _is_admin_id(cfg: Config, telegram_id: str) -> bool:
    allowed = {a.strip() for a in cfg.channels.telegram_admin_ids if a.strip()}
    return bool(telegram_id and telegram_id in allowed)


@router.post("/probe", response_model=TWAProbeResponse)
async def twa_probe(req: TWALoginRequest, request: Request) -> TWAProbeResponse:
    """Does not create a session. ``admin`` is true only for TELEGRAM_ADMIN_IDS."""
    cfg: Config = request.app.state.cfg
    try:
        data = _verify_telegram_data(req.init_data, cfg.channels.telegram_bot_token)
    except ValueError:
        return TWAProbeResponse(ok=False, admin=False)
    telegram_id = _telegram_user_id(data)
    return TWAProbeResponse(ok=True, admin=_is_admin_id(cfg, telegram_id))


@router.post("/login", response_model=TWALoginResponse)
async def twa_login(
    req: TWALoginRequest,
    request: Request,
    response: Response,
) -> TWALoginResponse:
    cfg: Config = request.app.state.cfg

    try:
        data = _verify_telegram_data(req.init_data, cfg.channels.telegram_bot_token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=f"TWA verification failed: {exc}") from exc

    telegram_id = _telegram_user_id(data)
    if not _is_admin_id(cfg, telegram_id):
        log.warning(
            "TWA login rejected",
            extra={
                "action": "twa.login.denied",
                "reason": "user not in TELEGRAM_ADMIN_IDS",
                "user_id": telegram_id or "<unknown>",
            },
        )
        raise HTTPException(status_code=403, detail="user not authorized as admin")

    token = _create_token(cfg, f"twa:{telegram_id}", is_bootstrap=True)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=cfg.admin.cookie_secure,
        samesite="lax",
        path="/",
    )
    log.info("TWA login", extra={"action": "twa.login", "user_id": telegram_id})
    return TWALoginResponse(ok=True, token=token, username=str(telegram_id))


@router.get("/verify")
async def twa_verify(
    request: Request,
    token: str = "",
) -> dict[str, Any]:
    """Quick verify endpoint for the TWA frontend."""
    from app.admin_api.auth import _read_token

    cfg: Config = request.app.state.cfg
    if not token:
        return {"valid": False}
    data = _read_token(cfg, token)
    if data is None:
        return {"valid": False}
    return {"valid": True, "username": data.get("u", "")}
