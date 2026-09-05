"""Reverse proxy to the 9router dashboard with admin session validation."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.config import get_config
from app.logging_setup import get_logger

log = get_logger("app.gateway.router_proxy")

router = APIRouter(prefix="/9router", tags=["gateway", "router"])

ROUTER_PROXY_TIMEOUT = 30.0


def _target_base_url() -> str:
    cfg = get_config()
    return cfg.llm.router_base_url.rstrip("/").replace("/v1", "")


def _validate_admin_session(session_token: str | None, web_secret: str) -> bool:
    """Validate the admin session cookie against the web secret.

    Uses a simple HMAC-based signed cookie approach.
    """
    if not session_token:
        return False

    import hashlib
    import hmac
    import time

    try:
        parts = session_token.split(":", 1)
        if len(parts) != 2:
            return False
        ts_str, sig = parts
        ts = int(ts_str)

        # Session valid for 24 hours
        if abs(time.time() - ts) > 86400:
            return False

        expected = hmac.new(
            web_secret.encode(),
            ts_str.encode(),
            hashlib.sha256,
        ).hexdigest()[:32]

        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


async def _proxy_request(
    request: Request,
    target_url: str,
    *,
    timeout: float = ROUTER_PROXY_TIMEOUT,
) -> Response:
    """Forward the incoming request to the 9router backend and stream the response."""
    cfg = get_config()

    # Build upstream headers
    headers: dict[str, str] = {}
    for header_name in ("content-type", "accept", "authorization"):
        value = request.headers.get(header_name)
        if value:
            headers[header_name] = value

    # Add the router access key
    if cfg.llm.router_access_key:
        headers["Authorization"] = f"Bearer {cfg.llm.router_access_key}"

    # Forward relevant query parameters
    query_string = str(request.url.query) if request.url.query else ""

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream_response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                params=query_string,
            )
    except httpx.TimeoutException:
        log.error("router proxy timeout", extra={"action": "proxy.timeout", "target": target_url})
        raise HTTPException(status_code=504, detail="gateway timeout")
    except httpx.ConnectError as exc:
        log.error(
            "router proxy connect error", extra={"action": "proxy.connect", "error": str(exc)}
        )
        raise HTTPException(status_code=502, detail="bad gateway")
    except Exception as exc:
        log.error("router proxy error", extra={"action": "proxy.error", "error": str(exc)})
        raise HTTPException(status_code=502, detail="bad gateway")

    # Build response headers
    response_headers: dict[str, str] = {}
    skip_headers = {
        "content-encoding",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "content-length",
        "host",
    }
    for name, value in upstream_response.headers.items():
        if name.lower() not in skip_headers:
            response_headers[name] = value

    content = upstream_response.content
    media_type = upstream_response.headers.get("content-type", "application/octet-stream")

    return Response(
        content=content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=media_type,
    )


# FastAPI derives one operation ID per (path, method) pair from the endpoint
# function name, so a single multi-method api_route emitted seven identical
# IDs — which makes /api/openapi.json invalid and breaks generated clients.
# Registering each verb separately gives every operation a distinct ID.
# The proxy itself is one shared implementation (`_router_proxy_impl`).
@router.get("/{path:path}", operation_id="router_proxy_get", include_in_schema=False)
@router.post("/{path:path}", operation_id="router_proxy_post", include_in_schema=False)
@router.put("/{path:path}", operation_id="router_proxy_put", include_in_schema=False)
@router.delete("/{path:path}", operation_id="router_proxy_delete", include_in_schema=False)
@router.patch("/{path:path}", operation_id="router_proxy_patch", include_in_schema=False)
@router.options("/{path:path}", operation_id="router_proxy_options", include_in_schema=False)
@router.head("/{path:path}", operation_id="router_proxy_head", include_in_schema=False)
async def router_proxy(
    request: Request,
    path: str,
    petro_session: str | None = Cookie(None),
) -> Response:
    """Proxy all /9router/* requests to the 9router dashboard.

    Validates the admin session cookie before forwarding.
    """
    cfg = get_config()

    if not _validate_admin_session(petro_session, cfg.admin.web_secret):
        raise HTTPException(status_code=401, detail="unauthorized")

    base = _target_base_url()
    target_url = f"{base}/{path}"

    log.info(
        "router proxy request",
        extra={"action": "proxy.request", "path": path, "target": target_url},
    )

    return await _proxy_request(request, target_url)
