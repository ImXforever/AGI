"""Admin authentication: argon2id password hashing, itsdangerous session tokens.

Provides:
- ensure_bootstrap_admin() — seed the first admin row on startup.
- login / logout / session endpoints.
- require_admin() — FastAPI dependency that rejects unauthenticated requests.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import Config
from app.logging_setup import get_logger

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    _ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
except ImportError:
    _ph = None  # type: ignore[assignment]

try:
    from itsdangerous import URLSafeTimedSerializer

    def _make_signer(secret: str) -> Any:
        return URLSafeTimedSerializer(secret)
except ImportError:
    URLSafeTimedSerializer = None  # type: ignore[assignment,misc]

    def _make_signer(secret: str) -> Any:
        raise RuntimeError("itsdangerous is required for admin sessions")


log = get_logger("app.admin_api.auth")

router = APIRouter(prefix="/auth", tags=["admin-auth"])

COOKIE_NAME = "pa_session"
SESSION_MAX_AGE = 86400 * 7  # 7 days


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool
    username: str = ""
    expires_in: int = SESSION_MAX_AGE


class SessionInfo(BaseModel):
    authenticated: bool
    username: str = ""
    is_bootstrap: bool = False


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    if _ph is None:
        raise RuntimeError("argon2-cffi is required for password hashing")
    return _ph.hash(plain)


def verify_password(stored: str, plain: str) -> bool:
    if _ph is None:
        return False
    try:
        return _ph.verify(stored, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def _create_token(cfg: Config, username: str, *, is_bootstrap: bool = False) -> str:
    signer = _make_signer(cfg.admin.web_secret)
    return signer.dumps({"u": username, "b": is_bootstrap, "t": int(time.time())})


def _read_token(cfg: Config, token: str) -> dict[str, Any] | None:
    signer = _make_signer(cfg.admin.web_secret)
    try:
        data = signer.loads(token, max_age=SESSION_MAX_AGE)
        return dict(data)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def ensure_bootstrap_admin(pool: Any, cfg: Config) -> None:
    """Insert or sync the bootstrap admin if configured."""
    if not cfg.admin.username or not cfg.admin.bootstrap_password:
        return
    pw_hash = hash_password(cfg.admin.bootstrap_password)
    await pool.execute(
        """INSERT INTO admins (username, password_hash, role, is_bootstrap, is_active, created_at)
           VALUES ($1, $2, 'superadmin', TRUE, TRUE, NOW())
           ON CONFLICT (username) DO UPDATE
               SET password_hash = EXCLUDED.password_hash,
                   is_active = TRUE
           WHERE admins.is_bootstrap = TRUE""",
        cfg.admin.username,
        pw_hash,
    )
    log.info(
        "bootstrap admin ready",
        extra={"action": "admin.bootstrap", "username": cfg.admin.username},
    )


async def _lookup_admin(pool: Any, username: str) -> dict[str, Any] | None:
    row = await pool.fetchrow(
        "SELECT id, username, password_hash, role, is_bootstrap, is_active FROM admins WHERE username = $1",
        username,
    )
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


async def require_admin(request: Request) -> dict[str, Any]:
    """FastAPI dependency — returns the admin row dict or raises 401."""
    cfg: Config = request.app.state.cfg
    token: str | None = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")
    data = _read_token(cfg, token)
    if data is None:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    username = str(data.get("u") or "")
    if username.startswith("twa:"):
        telegram_id = username[4:]
        allowed = {a.strip() for a in cfg.channels.telegram_admin_ids if a.strip()}
        if telegram_id and telegram_id in allowed:
            return {
                "id": 0,
                "username": username,
                "role": "superadmin",
                "is_bootstrap": True,
                "is_active": True,
            }
        raise HTTPException(status_code=401, detail="account disabled or missing")
    pool = request.app.state.services.get("pg")
    if pool is None:
        raise HTTPException(status_code=503, detail="database unavailable")
    admin = await _lookup_admin(pool, username)
    if admin is None or not admin.get("is_active", True):
        raise HTTPException(status_code=401, detail="account disabled or missing")
    return admin


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request, response: Response) -> LoginResponse:
    cfg: Config = request.app.state.cfg
    pool = request.app.state.services.get("pg")
    if pool is None:
        raise HTTPException(status_code=503, detail="database unavailable")

    admin = await _lookup_admin(pool, req.username)
    if admin is None or not verify_password(admin["password_hash"], req.password):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="account disabled")

    token = _create_token(cfg, admin["username"], is_bootstrap=bool(admin.get("is_bootstrap")))
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=cfg.admin.cookie_secure,
        samesite="lax",
        path="/",
    )
    log.info("admin logged in", extra={"action": "admin.login", "username": admin["username"]})
    return LoginResponse(ok=True, username=admin["username"], expires_in=SESSION_MAX_AGE)


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/")
    log.info("admin logged out", extra={"action": "admin.logout"})
    return {"ok": True}


@router.get("/session", response_model=SessionInfo)
async def session_info(request: Request) -> SessionInfo:
    cfg: Config = request.app.state.cfg
    pool = request.app.state.services.get("pg")
    token: str | None = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        return SessionInfo(authenticated=False)
    data = _read_token(cfg, token)
    if data is None:
        return SessionInfo(authenticated=False)
    username = str(data.get("u") or "")
    if username.startswith("twa:"):
        telegram_id = username[4:]
        allowed = {a.strip() for a in cfg.channels.telegram_admin_ids if a.strip()}
        if telegram_id and telegram_id in allowed:
            return SessionInfo(authenticated=True, username=username, is_bootstrap=True)
        return SessionInfo(authenticated=False)
    if pool is None:
        return SessionInfo(authenticated=False)
    admin = await _lookup_admin(pool, username)
    if admin is None or not admin.get("is_active", True):
        return SessionInfo(authenticated=False)
    return SessionInfo(
        authenticated=True,
        username=admin["username"],
        is_bootstrap=bool(data.get("b")),
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str,
    new_password: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, bool]:
    if len(new_password) < 12:
        raise HTTPException(status_code=400, detail="password must be at least 12 characters")
    pool = request.app.state.services["pg"]
    if not verify_password(admin["password_hash"], current_password):
        raise HTTPException(status_code=403, detail="current password is incorrect")
    new_hash = hash_password(new_password)
    await pool.execute("UPDATE admins SET password_hash = $1 WHERE id = $2", new_hash, admin["id"])
    log.info(
        "password changed", extra={"action": "admin.password_change", "username": admin["username"]}
    )
    return {"ok": True}
