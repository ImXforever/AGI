"""HTTP gate: public site is open; /admin needs a session.

Open: landing, TWA probe/login, password login form + auth endpoints.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.admin_api.auth import COOKIE_NAME, _read_token
from app.config import get_config

_PUBLIC_PREFIXES = (
    "/admin/landing.html",
    "/admin/ops/login.html",
    "/admin/api/twa/",
    "/admin/api/auth/login",
    "/admin/api/auth/logout",
    "/admin/api/auth/session",
)


def _is_public_admin(path: str) -> bool:
    if path in ("/admin/", "/admin", "/admin/index.html", "/admin/landing.html", "/admin/landing", "/admin/ops/login.html"):
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


class AdminGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/admin"):
            return await call_next(request)
        if _is_public_admin(path):
            return await call_next(request)

        try:
            config = request.app.state.cfg
        except AttributeError:
            config = get_config()

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token = auth[7:]
        data = _read_token(config, token) if token else None
        if data is not None:
            return await call_next(request)

        accept = request.headers.get("accept", "")
        wants_html = "text/html" in accept or path.endswith(".html") or path.endswith("/")
        if wants_html and request.method in ("GET", "HEAD"):
            return RedirectResponse("/", status_code=302)
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
