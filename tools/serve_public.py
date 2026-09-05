"""Local public site on :8080 (landing at /, static files from repo root)."""

from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self.path = "/admin/landing.html"
        return super().do_GET()

    def guess_type(self, path: str) -> str:  # type: ignore[override]
        guessed, _enc = super().guess_type(path)
        if guessed == "text/html":
            return "text/html; charset=utf-8"
        return guessed or "application/octet-stream"


def main() -> None:
    host = "0.0.0.0"
    port = int(os.environ.get("WEB_PORT", "8080"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"public site http://{host}:{port}/  (landing)", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
