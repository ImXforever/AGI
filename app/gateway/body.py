"""Read webhook bodies once. Starlette will not re-parse after ``request.body()``."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs


def json_from_body(body: bytes) -> Any:
    if not body:
        raise ValueError("empty body")
    return json.loads(body.decode("utf-8"))


def form_from_body(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {k: (v[-1] if v else "") for k, v in parsed.items()}
