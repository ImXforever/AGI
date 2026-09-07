"""Gateway + storage contracts: authenticity, body-once, HITL SoT, 10k indexes."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from app.core.hitl.sweeper import should_timeout_without_redis

ROOT = Path(__file__).parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_empty_telegram_webhook_secret_is_rejected() -> None:
    verify = _load("gw_verify_mod", ROOT / "app" / "gateway" / "verify.py")
    assert verify.verify_telegram("", "anything").ok is False
    assert verify.verify_telegram("   ", "anything").reason == "secret not configured"
    cfg = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert "telegram_webhook_secret=_secret_or_empty" in cfg
    assert '_auto(source, "TELEGRAM_WEBHOOK_SECRET"' not in cfg


def test_webhooks_parse_body_once() -> None:
    src = (ROOT / "app" / "gateway" / "webhooks.py").read_text(encoding="utf-8")
    assert "json_from_body" in src
    assert "form_from_body" in src
    assert "await request.json()" not in src
    assert "await request.form()" not in src
    body = _load("gw_body_mod", ROOT / "app" / "gateway" / "body.py")
    payload = body.json_from_body(b'{"update_id":1}')
    assert payload["update_id"] == 1
    form = body.form_from_body(b"From=%2B123&Body=hello")
    assert form["From"] == "+123"
    assert form["Body"] == "hello"


def test_hitl_postgres_ledger_redis_consume_once() -> None:
    lua = (ROOT / "app" / "storage" / "lua" / "hitl_claim_decision.lua").read_text(encoding="utf-8")
    assert "EXISTS" in lua and "decided_key" in lua
    assert "orphan" in lua
    assert should_timeout_without_redis(claimed=False, redis_status=None) is True
    assert should_timeout_without_redis(claimed=False, redis_status="timeout") is True
    assert should_timeout_without_redis(claimed=False, redis_status="pending") is False
    assert should_timeout_without_redis(claimed=True, redis_status="pending") is True
    proxy = (ROOT / "app" / "gateway" / "router_proxy.py").read_text(encoding="utf-8")
    assert "_read_token" in proxy
    assert "HMAC never matches" in proxy


def test_ten_k_indexes_and_single_worker() -> None:
    mig = (ROOT / "db" / "migrations" / "0013_gateway_10k_indexes.sql").read_text(encoding="utf-8")
    assert "idx_customers_channel_external" in mig
    assert "idx_messages_conv_extref" in mig
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "--workers 1" in docker
    repo = (ROOT / "app" / "core" / "repository.py").read_text(encoding="utf-8")
    assert "UniqueViolation" in repo


def test_whatsapp_disabled_is_404() -> None:
    src = (ROOT / "app" / "gateway" / "webhooks.py").read_text(encoding="utf-8")
    assert 'status_code=404, detail="whatsapp disabled"' in src
    assert "whatsapp_enabled" in src
