"""Structured logging (JSON lines for Railway drains) + audit-friendly records."""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def __init__(self, tenant_id: str = "") -> None:
        super().__init__()
        self.tenant_id = tenant_id

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": f"{time.time():.3f}",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "tenant": self.tenant_id,
        }
        # Correlate every log line with the HTTP request that produced it.
        # Imported lazily to keep logging_setup free of app-level imports.
        try:
            from app.observability import current_request_id

            rid = current_request_id()
            if rid:
                payload["request_id"] = rid
        except Exception:
            payload["request_id"] = None
        for key in (
            "conversation_id",
            "approval_id",
            "channel",
            "actor",
            "action",
            "entity",
            "latency_ms",
            "cost_usd",
            "reason",
            "error",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self, tenant_id: str = "") -> None:
        super().__init__(fmt="%(asctime)s %(levelname)-7s [%(tenant)s] %(name)s: %(message)s")
        self.tenant_id = tenant_id

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "tenant"):
            record.tenant = self.tenant_id
        return super().format(record)


class TenantFilter(logging.Filter):
    def __init__(self, tenant_id: str) -> None:
        super().__init__()
        self.tenant_id = tenant_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "tenant"):
            record.tenant = self.tenant_id
        return True


def setup_logging(level: str = "INFO", *, json_enabled: bool = True, tenant_id: str = "") -> None:
    global _CONFIGURED
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(tenant_id) if json_enabled else TextFormatter(tenant_id))
    handler.addFilter(TenantFilter(tenant_id))
    root.addHandler(handler)
    for noisy in ("httpx", "httpcore", "aiogram", "botocore", "asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _CONFIGURED = True


def configured() -> bool:
    return _CONFIGURED


def get_logger(name: str, **bound: Any) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logging.getLogger(name), dict(bound))
