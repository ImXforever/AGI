"""Unit tests for app.config — configuration loading, validation, and helpers."""

from __future__ import annotations

import pytest

from app.config import (
    Config,
    ConfigError,
    _b,
    _csv,
    _f,
    _i,
    _one_of,
    _s,
    as_redacted_dict,
    load_config,
)

# ---------------------------------------------------------------------------
# Minimal valid env for tests
# ---------------------------------------------------------------------------

VALID_ENV: dict[str, str] = {
    "TENANT_ID": "test-tenant",
    "TENANT_NAME_AR": "شركة اختبار",
    "SUPPORT_CONTACT": "support@test.com",
    "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "TELEGRAM_ADMIN_IDS": "12345",
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "REDIS_URL": "redis://localhost:6379/0",
    "R2_ENDPOINT": "https://test.r2.cloudflarestorage.com",
    "R2_ACCESS_KEY_ID": "testkey12345678",
    "R2_SECRET_ACCESS_KEY": "testsecret12345678",
    "R2_BUCKET": "test-bucket",
    "ADMIN_USERNAME": "admin",
    "ADMIN_BOOTSTRAP_PASSWORD": "StrongPassword123!",
    "CURRENCY": "SAR",
    "APP_ENV": "test",
    "LLM_MODE": "mock",
}


def _make_env(**overrides: str) -> dict[str, str]:
    env = dict(VALID_ENV)
    env.update(overrides)
    return env


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_s_basic(self):
        assert _s({"A": "hello"}, "A") == "hello"

    def test_s_default(self):
        assert _s({}, "A", default="fallback") == "fallback"

    def test_s_required_missing(self):
        with pytest.raises(ConfigError, match="required"):
            _s({}, "A", required=True)

    def test_s_strips_whitespace(self):
        assert _s({"A": "  hello  "}, "A") == "hello"

    def test_i_valid(self):
        assert _i({"A": "42"}, "A", 0) == 42

    def test_i_default(self):
        assert _i({}, "A", 99) == 99

    def test_i_invalid(self):
        with pytest.raises(ConfigError, match="must be an integer"):
            _i({"A": "abc"}, "A", 0)

    def test_i_minimum(self):
        with pytest.raises(ConfigError, match="must be >="):
            _i({"A": "1"}, "A", 0, minimum=5)

    def test_f_valid(self):
        assert _f({"A": "3.14"}, "A", 0.0) == pytest.approx(3.14)

    def test_f_invalid(self):
        with pytest.raises(ConfigError, match="must be a number"):
            _f({"A": "abc"}, "A", 0.0)

    def test_b_true(self):
        assert _b({"A": "1"}, "A", False) is True
        assert _b({"A": "true"}, "A", False) is True
        assert _b({"A": "yes"}, "A", False) is True
        assert _b({"A": "on"}, "A", False) is True

    def test_b_false(self):
        assert _b({"A": "0"}, "A", True) is False
        assert _b({"A": "false"}, "A", True) is False
        assert _b({"A": "no"}, "A", True) is False

    def test_b_invalid(self):
        with pytest.raises(ConfigError, match="must be a boolean"):
            _b({"A": "maybe"}, "A", False)

    def test_one_of_valid(self):
        assert _one_of({"A": "x"}, "A", ("x", "y", "z"), "x") == "x"

    def test_one_of_invalid(self):
        with pytest.raises(ConfigError, match="must be one of"):
            _one_of({"A": "w"}, "A", ("x", "y", "z"), "x")

    def test_one_of_default(self):
        assert _one_of({}, "A", ("x", "y"), "x") == "x"

    def test_csv_basic(self):
        assert _csv({"A": "a,b,c"}, "A") == ["a", "b", "c"]

    def test_csv_empty(self):
        assert _csv({}, "A") == []

    def test_csv_with_default(self):
        assert _csv({}, "A", default=["x"]) == ["x"]

    def test_csv_strips(self):
        assert _csv({"A": " a , b , c "}, "A") == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Full config loading tests
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_load_valid_config(self):
        cfg = load_config(_make_env())
        assert isinstance(cfg, Config)
        assert cfg.tenant.id == "test-tenant"
        assert cfg.tenant.name_ar == "شركة اختبار"
        assert cfg.ops.app_env == "test"
        assert cfg.llm.mode == "mock"
        assert cfg.domain.currency == "SAR"

    def test_missing_required(self):
        env = _make_env()
        del env["TENANT_ID"]
        with pytest.raises(ConfigError, match="TENANT_ID"):
            load_config(env)

    def test_invalid_llm_mode(self):
        with pytest.raises(ConfigError, match="must be one of"):
            load_config(_make_env(LLM_MODE="invalid"))

    def test_mock_not_allowed_in_production(self):
        with pytest.raises(ConfigError, match="mock is not permitted"):
            load_config(
                _make_env(
                    APP_ENV="production",
                    LLM_MODE="mock",
                    TELEGRAM_WEBHOOK_SECRET="telegram-webhook-secret",
                )
            )

    def test_invalid_backup_hour(self):
        with pytest.raises(ConfigError, match="BACKUP_HOUR must be 0..23"):
            load_config(_make_env(BACKUP_HOUR="25"))

    def test_invalid_tax_rate(self):
        with pytest.raises(ConfigError, match="TAX_RATE must be between"):
            load_config(_make_env(TAX_RATE="1.5"))

    def test_invalid_app_env(self):
        with pytest.raises(ConfigError, match="must be one of"):
            load_config(_make_env(APP_ENV="staging"))

    def test_auto_generated_secret(self):
        cfg = load_config(_make_env(WEB_SECRET=""))
        assert cfg.admin.web_secret != ""

    def test_explicit_secret(self):
        cfg = load_config(_make_env(WEB_SECRET="my-very-long-secret-key-1234"))
        assert cfg.admin.web_secret == "my-very-long-secret-key-1234"

    def test_short_secret_rejected(self):
        with pytest.raises(ConfigError, match="at least"):
            load_config(_make_env(WEB_SECRET="short"))

    def test_csv_telegram_admin_ids(self):
        cfg = load_config(_make_env(TELEGRAM_ADMIN_IDS="111,222,333"))
        assert cfg.channels.telegram_admin_ids == ["111", "222", "333"]

    def test_domain_defaults(self):
        cfg = load_config(_make_env())
        assert cfg.domain.tax_rate == pytest.approx(0.15)
        assert cfg.domain.quote_valid_days == 7
        assert cfg.domain.numeral_style == "arabic-indic"

    def test_hitl_defaults(self):
        cfg = load_config(_make_env())
        assert cfg.hitl.timeout_seconds == 600
        assert cfg.hitl.fallback == "auto_ack"
        assert cfg.hitl.ping_telegram is True

    def test_social_channels_default_off(self):
        cfg = load_config(_make_env())
        assert cfg.channels.instagram_enabled is False
        assert cfg.channels.twitter_enabled is False

    def test_production_requires_telegram_webhook_secret(self):
        with pytest.raises(ConfigError, match="TELEGRAM_WEBHOOK_SECRET"):
            load_config(
                _make_env(
                    APP_ENV="production",
                    LLM_MODE="direct",
                    DIRECT_BASE_URL="https://api.example.com/v1",
                    DIRECT_API_KEY="direct-api-key-123456",
                    DIRECT_MODEL="gpt-4o-mini",
                )
            )

    def test_production_accepts_webhook_secret(self):
        cfg = load_config(
            _make_env(
                APP_ENV="production",
                LLM_MODE="direct",
                DIRECT_BASE_URL="https://api.example.com/v1",
                DIRECT_API_KEY="direct-api-key-123456",
                DIRECT_MODEL="gpt-4o-mini",
                TELEGRAM_WEBHOOK_SECRET="telegram-webhook-secret",
            )
        )
        assert cfg.channels.telegram_webhook_secret == "telegram-webhook-secret"


# ---------------------------------------------------------------------------
# as_redacted_dict tests
# ---------------------------------------------------------------------------


class TestAsRedactedDict:
    def test_structure(self):
        cfg = load_config(_make_env())
        d = as_redacted_dict(cfg)
        assert "tenant" in d
        assert "admin" in d
        assert "channels" in d
        assert "domain" in d
        assert d["tenant"]["id"] == "test-tenant"

    def test_token_masked(self):
        cfg = load_config(_make_env(WEB_SECRET="abcdefghijklmnop"))
        d = as_redacted_dict(cfg)
        assert "***" in d["admin"]["token_masked"]

    def test_empty_token(self):
        # An empty WEB_SECRET is auto-generated, so the mask is never empty.
        cfg = load_config(_make_env(WEB_SECRET=""))
        d = as_redacted_dict(cfg)
        assert d["admin"]["token_masked"].startswith("***")
