"""Hermes Bridge â€” HTTP adapter connecting Kia-Agent app to Hermes runtime.

This module exposes a lightweight HTTP server that:
1. Receives LLM requests from the Kia-Agent app
2. Translates them into Hermes-compatible format
3. Forwards to the upstream Hermes service
4. Returns the response

~200 lines
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [hermes-bridge] %(message)s")
log = logging.getLogger("hermes-bridge")

UPSTREAM_URL = os.environ.get("HERMES_UPSTREAM_URL", "http://app:8080")
SERVICE_TOKEN = os.environ.get("HERMES_SERVICE_TOKEN", "")
BRIDGE_PORT = int(os.environ.get("HERMES_PORT", "3000"))
TIMEOUT = int(os.environ.get("HERMES_TIMEOUT", "120"))

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=TIMEOUT)
    return _client


async def _forward(method: str, path: str, body: bytes | None = None,
                   headers: dict[str, str] | None = None) -> tuple[int, dict, bytes]:
    client = _get_client()
    url = f"{UPSTREAM_URL.rstrip('/')}{path}"
    req_headers = {"Content-Type": "application/json"}
    if SERVICE_TOKEN:
        req_headers["Authorization"] = f"Bearer {SERVICE_TOKEN}"
    if headers:
        req_headers.update(headers)

    try:
        if method == "GET":
            resp = await client.get(url, headers=req_headers)
        elif method == "POST":
            resp = await client.post(url, content=body, headers=req_headers)
        elif method == "PUT":
            resp = await client.put(url, content=body, headers=req_headers)
        elif method == "DELETE":
            resp = await client.delete(url, headers=req_headers)
        else:
            return 405, {}, json.dumps({"error": "method not allowed"}).encode()

        resp_headers = dict(resp.headers)
        return resp.status_code, resp_headers, resp.content
    except httpx.TimeoutException:
        return 504, {}, json.dumps({"error": "upstream timeout"}).encode()
    except httpx.ConnectError:
        return 502, {}, json.dumps({"error": "upstream unreachable"}).encode()
    except Exception as exc:
        log.error("forward error: %s", exc)
        return 500, {}, json.dumps({"error": "bridge error", "detail": str(exc)}).encode()


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        log.info(fmt, *args)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def _handle(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # Health check
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "hermes-bridge"}).encode())
            return

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Forward asynchronously
        loop = asyncio.new_event_loop()
        try:
            status, resp_headers, resp_body = loop.run_until_complete(
                _forward(method, path, body)
            )
        finally:
            loop.close()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Bridge-Version", "1.0.0")
        self.end_headers()
        self.wfile.write(resp_body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()


class ThreadedHTTPServer(HTTPServer):
    """Handle each request in a new thread."""
    allow_reuse_address = True

    def process_request(self, request: Any, client_address: Any) -> None:
        import threading
        t = threading.Thread(target=self.process_request_thread, args=(request, client_address))
        t.daemon = True
        t.start()

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def main() -> None:
    server = ThreadedHTTPServer(("0.0.0.0", BRIDGE_PORT), BridgeHandler)
    log.info("hermes-bridge listening on :%d â†’ %s", BRIDGE_PORT, UPSTREAM_URL)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
        server.shutdown()
        if _client and not _client.is_closed:
            asyncio.get_event_loop().run_until_complete(_client.aclose())


if __name__ == "__main__":
    main()
