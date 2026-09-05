"""Kia-Agent Platform — the ONLY module that reads os.environ."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from typing import Any, Literal

__all__ = [
    "ConfigError",
    "Config",
    "load_config",
    "config",
    "reload_config",
    "get_config",
    "as_redacted_dict",
]

DEFAULT_META_GRAPH_URL = "https://graph.facebook.com/v20.0"
DEFAULT_RESEND_URL = "https://api.resend.com"
DEFAULT_TWILIO_URL = "https://api.twilio.com/2010-04-01"
MIN_SECRET_CHARS = 16


class ConfigError(RuntimeError):
    pass


def _s(env: dict[str, str], name: str, default: str | None = None, required: bool = False) -> str:
    raw = env.get(name, "").strip()
    if raw:
        return raw
    if required:
        raise ConfigError(f"required variable {name} is missing or empty")
    return default if default is not None else ""


def _i(env: dict[str, str], name: str, default: int, *, minimum: int | None = None) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}, got {value}")
    return value


def _f(env: dict[str, str], name: str, default: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _b(env: dict[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise ConfigError(f"{name} must be a boolean (1/0), got {raw!r}")


def _one_of(env: dict[str, str], name: str, allowed: tuple[str, ...], default: str) -> str:
    raw = env.get(name, "").strip() or default
    if raw not in allowed:
        raise ConfigError(f"{name} must be one of {allowed}, got {raw!r}")
    return raw


def _auto(env: dict[str, str], name: str, required: bool = False) -> str:
    raw = env.get(name, "").strip()
    if raw:
        if len(raw) < MIN_SECRET_CHARS:
            raise ConfigError(
                f"{name} must be at least {MIN_SECRET_CHARS} characters "
                f"(got {len(raw)}); leave it empty to auto-generate"
            )
        return raw
    if required:
        raise ConfigError(f"required variable {name} is missing or empty")
    return secrets.token_urlsafe(32)


def _secret_or_empty(env: dict[str, str], name: str) -> str:
    """A shared secret that must match an *external* party's copy.

    Unlike :func:`_auto`, this never invents a value: for webhook tokens the
    counterpart (Telegram, Meta) holds the authoritative copy, so a generated
    secret could only ever produce 403s. Empty disables verification.
    """
    raw = env.get(name, "").strip()
    if not raw:
        return ""
    if len(raw) < MIN_SECRET_CHARS:
        raise ConfigError(
            f"{name} must be at least {MIN_SECRET_CHARS} characters "
            f"(got {len(raw)}); leave it empty to disable verification"
        )
    return raw


def _csv(env: dict[str, str], name: str, default: list[str] | None = None) -> list[str]:
    raw = env.get(name, "").strip()
    if not raw:
        return list(default or [])
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class TenantGroup:
    id: str
    name_ar: str
    name_en: str
    support_contact: str
    brand_logo_url: str
    brand_primary_color: str


@dataclass(frozen=True)
class ChannelsGroup:
    telegram_bot_token: str
    telegram_admin_ids: list[str]
    telegram_webhook_secret: str
    whatsapp_enabled: bool
    whatsapp_provider: Literal["meta", "twilio"]
    whatsapp_verify_token: str
    whatsapp_app_secret: str
    whatsapp_phone_number_id: str
    whatsapp_api_token: str
    whatsapp_base_url: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    twilio_base_url: str
    email_enabled: bool
    email_from: str
    email_reply_to: str
    resend_api_key: str
    resend_base_url: str
    email_inbound_provider: Literal["sendgrid", "imap"]
    sendgrid_api_key: str
    sendgrid_webhook_public_key: str
    resend_webhook_secret: str
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_poll_seconds: int
    rate_limit_per_minute: int
    instagram_enabled: bool
    instagram_access_token: str
    instagram_business_account_id: str
    twitter_enabled: bool
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_secret: str
    twitter_bearer_token: str


@dataclass(frozen=True)
class LLMGroup:
    mode: Literal["router", "direct", "mock"]
    router_base_url: str
    router_access_key: str
    router_timeout: int
    router_fallback_to_direct: bool
    hermes_base_url: str
    hermes_service_token: str
    hermes_timeout: int
    direct_base_url: str
    direct_api_key: str
    direct_model: str
    model_fast: str
    model_standard: str
    temperature: float


@dataclass(frozen=True)
class HITLGroup:
    timeout_seconds: int
    fallback: Literal["auto_ack", "silent"]
    ping_telegram: bool


@dataclass(frozen=True)
class StorageGroup:
    database_url: str
    redis_url: str
    r2_endpoint: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    r2_prefix: str
    r2_signed_url_ttl: int
    pg_dump_retention_days: int
    hot_data_days: int
    archive_final_outputs: bool


@dataclass(frozen=True)
class AdminGroup:
    username: str
    bootstrap_password: str
    web_secret: str
    web_port: int
    cookie_secure: bool
    totp_enabled: bool


@dataclass(frozen=True)
class OpsGroup:
    app_env: Literal["production", "development", "test"]
    log_level: str
    log_json_enabled: bool
    log_to_db: bool
    backup_hour: int
    bootstrap_mode: Literal["full", "lite"]
    backup_enabled: bool


@dataclass(frozen=True)
class DomainGroup:
    currency: str
    tax_rate: float
    quote_valid_days: int
    lead_scoring_enabled: bool
    numeral_style: Literal["arabic-indic", "western"]
    reply_language_policy: str


@dataclass(frozen=True)
class MemoryGroup:
    enabled: bool
    extract_every: int
    budget_chars: int
    persona_refresh_threshold: int


@dataclass(frozen=True)
class FleetGroup:
    enabled: bool
    max_team_size: int
    team_timeout: int


@dataclass(frozen=True)
class CalendarGroup:
    enabled: bool
    credentials_json: str
    calendar_id: str
    default_reminder_minutes: int


@dataclass(frozen=True)
class Config:
    tenant: TenantGroup
    channels: ChannelsGroup
    llm: LLMGroup
    hitl: HITLGroup
    storage: StorageGroup
    admin: AdminGroup
    ops: OpsGroup
    domain: DomainGroup
    memory: MemoryGroup
    fleet: FleetGroup
    calendar: CalendarGroup = field(
        default_factory=lambda: CalendarGroup(
            enabled=False, credentials_json="", calendar_id="primary", default_reminder_minutes=60
        )
    )
    upstream_keys: dict[str, str] = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.ops.app_env == "production"


UPSTREAM_KEY_PREFIXES = (
    "OPENROUTER_",
    "OPENAI_",
    "DEEPSEEK_",
    "ANTHROPIC_",
    "GEMINI_",
    "GOOGLE_",
    "GROQ_",
    "MISTRAL_",
    "XAI_",
    "UPSTREAM_",
)
UPSTREAM_KEY_EXCLUDE = {
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_ORG_ID",
    "OPENAI_ORGANIZATION",
}


def _dotenv_defaults() -> dict[str, str]:
    from pathlib import Path

    from dotenv import dotenv_values

    candidates = (
        [Path(os.environ.get("ENV_FILE", ""))]
        if os.environ.get("ENV_FILE")
        else [
            Path.cwd() / ".env",
            Path(__file__).resolve().parents[1] / ".env",
        ]
    )
    for candidate in candidates:
        try:
            if candidate.is_file():
                return {k: v for k, v in dotenv_values(candidate).items() if v is not None}
        except OSError:
            continue
    return {}


def load_config(env: dict[str, str] | None = None) -> Config:
    if env is None:
        source: dict[str, str] = {**_dotenv_defaults(), **os.environ}
    else:
        source = dict(env)
    app_env = _one_of(source, "APP_ENV", ("production", "development", "test"), "production")

    tenant = TenantGroup(
        id=_s(source, "TENANT_ID", required=True).lower(),
        name_ar=_s(source, "TENANT_NAME_AR", required=True),
        name_en=_s(source, "TENANT_NAME_EN", default="")
        or _s(source, "TENANT_NAME_AR", required=True),
        support_contact=_s(source, "SUPPORT_CONTACT", required=True),
        brand_logo_url=_s(source, "BRAND_LOGO_URL"),
        brand_primary_color=_s(source, "BRAND_PRIMARY_COLOR", default="#0b6e4f"),
    )

    wa_enabled = _b(source, "WHATSAPP_ENABLED", False)
    wa_provider = _one_of(source, "WHATSAPP_PROVIDER", ("meta", "twilio"), "meta")
    email_enabled = _b(source, "EMAIL_ENABLED", False)
    email_inbound = _one_of(source, "EMAIL_INBOUND_PROVIDER", ("sendgrid", "imap"), "sendgrid")

    def _require_if(cond: bool, name: str) -> str:
        return _s(source, name, required=cond) if cond else _s(source, name)

    channels = ChannelsGroup(
        telegram_bot_token=_s(source, "TELEGRAM_BOT_TOKEN", required=True),
        telegram_admin_ids=_csv(source, "TELEGRAM_ADMIN_IDS"),
        # NEVER auto-generate this one. Telegram sends the secret that was
        # registered via setWebhook; a locally invented value can never match,
        # so auto-generation turned every inbound update into a silent 403 —
        # and with multiple uvicorn workers each worker invented a *different*
        # secret. Empty means "verification disabled" (documented, and logged
        # as a warning at startup), any set value must be >= MIN_SECRET_CHARS.
        telegram_webhook_secret=_secret_or_empty(source, "TELEGRAM_WEBHOOK_SECRET"),
        whatsapp_enabled=wa_enabled,
        whatsapp_provider=wa_provider,  # type: ignore[arg-type]
        # Same reasoning as telegram_webhook_secret: Meta holds the
        # authoritative copy of this token, so it must never be invented.
        whatsapp_verify_token=_secret_or_empty(source, "WHATSAPP_VERIFY_TOKEN"),
        whatsapp_app_secret=_require_if(
            wa_enabled and wa_provider == "meta", "WHATSAPP_APP_SECRET"
        ),
        whatsapp_phone_number_id=_require_if(
            wa_enabled and wa_provider == "meta", "WHATSAPP_PHONE_NUMBER_ID"
        ),
        whatsapp_api_token=_require_if(wa_enabled and wa_provider == "meta", "WHATSAPP_API_TOKEN"),
        whatsapp_base_url=_s(source, "WHATSAPP_BASE_URL", default=DEFAULT_META_GRAPH_URL),
        twilio_account_sid=_require_if(
            wa_enabled and wa_provider == "twilio", "TWILIO_ACCOUNT_SID"
        ),
        twilio_auth_token=_require_if(wa_enabled and wa_provider == "twilio", "TWILIO_AUTH_TOKEN"),
        twilio_whatsapp_from=_require_if(
            wa_enabled and wa_provider == "twilio", "TWILIO_WHATSAPP_FROM"
        ),
        twilio_base_url=_s(source, "TWILIO_BASE_URL", default=DEFAULT_TWILIO_URL),
        email_enabled=email_enabled,
        email_from=_require_if(email_enabled, "EMAIL_FROM"),
        email_reply_to=_s(source, "EMAIL_REPLY_TO", default="")
        or _require_if(email_enabled, "EMAIL_FROM"),
        resend_api_key=_require_if(email_enabled, "RESEND_API_KEY"),
        resend_base_url=_s(source, "RESEND_BASE_URL", default=DEFAULT_RESEND_URL),
        email_inbound_provider=email_inbound,  # type: ignore[arg-type]
        sendgrid_api_key=_require_if(
            email_enabled and email_inbound == "sendgrid", "SENDGRID_API_KEY"
        ),
        sendgrid_webhook_public_key=_s(source, "SENDGRID_WEBHOOK_PUBLIC_KEY"),
        resend_webhook_secret=_s(source, "RESEND_WEBHOOK_SECRET"),
        imap_host=_require_if(email_enabled and email_inbound == "imap", "IMAP_HOST"),
        imap_port=_i(source, "IMAP_PORT", 993, minimum=1),
        imap_user=_require_if(email_enabled and email_inbound == "imap", "IMAP_USER"),
        imap_password=_require_if(email_enabled and email_inbound == "imap", "IMAP_PASSWORD"),
        imap_poll_seconds=_i(source, "IMAP_POLL_SECONDS", 60, minimum=5),
        rate_limit_per_minute=_i(source, "RATE_LIMIT_PER_MINUTE", 30, minimum=1),
        instagram_enabled=_b(source, "INSTAGRAM_ENABLED", False),
        instagram_access_token=_s(source, "INSTAGRAM_ACCESS_TOKEN"),
        instagram_business_account_id=_s(source, "INSTAGRAM_BUSINESS_ACCOUNT_ID"),
        twitter_enabled=_b(source, "TWITTER_ENABLED", False),
        twitter_api_key=_s(source, "TWITTER_API_KEY"),
        twitter_api_secret=_s(source, "TWITTER_API_SECRET"),
        twitter_access_token=_s(source, "TWITTER_ACCESS_TOKEN"),
        twitter_access_secret=_s(source, "TWITTER_ACCESS_SECRET"),
        twitter_bearer_token=_s(source, "TWITTER_BEARER_TOKEN"),
    )
    if not channels.telegram_admin_ids:
        raise ConfigError("required variable TELEGRAM_ADMIN_IDS is missing or empty")
    if app_env == "production" and not channels.telegram_webhook_secret:
        raise ConfigError(
            "TELEGRAM_WEBHOOK_SECRET is required when APP_ENV=production "
            "(empty secret leaves /tg/webhook unauthenticated)"
        )
    if email_enabled and not channels.sendgrid_webhook_public_key and not channels.resend_webhook_secret:
        raise ConfigError(
            "At least one of SENDGRID_WEBHOOK_PUBLIC_KEY or RESEND_WEBHOOK_SECRET "
            "is required when EMAIL_ENABLED=true"
        )

    llm_mode = _one_of(source, "LLM_MODE", ("router", "direct", "mock"), "router")
    if llm_mode == "mock" and app_env == "production":
        raise ConfigError("LLM_MODE=mock is not permitted when APP_ENV=production")

    # Support both OPENAI_* and DIRECT_* env vars; OPENAI_* takes precedence.
    # External provider credentials must NEVER be auto-generated here: when the
    # values are absent we need an empty string, not a synthetic token that
    # accidentally flips the app into direct mode.
    openai_key = _s(source, "OPENAI_API_KEY")
    openai_url = _s(source, "OPENAI_BASE_URL")
    direct_key = _s(source, "DIRECT_API_KEY")
    direct_url = _s(source, "DIRECT_BASE_URL")
    if openai_key and llm_mode != "direct":
        llm_mode = "direct"
    if openai_key and not direct_key:
        source["DIRECT_API_KEY"] = openai_key
    if openai_url and not direct_url:
        source["DIRECT_BASE_URL"] = openai_url

    llm = LLMGroup(
        mode=llm_mode,  # type: ignore[arg-type]
        router_base_url=_s(source, "ROUTER_BASE_URL", default="http://9router:20128/v1"),
        router_access_key=_auto(source, "ROUTER_ACCESS_KEY"),
        router_timeout=_i(source, "ROUTER_TIMEOUT", 120, minimum=1),
        router_fallback_to_direct=_b(source, "ROUTER_FALLBACK_TO_DIRECT", True),
        hermes_base_url=_s(source, "HERMES_BASE_URL", default="http://hermes:3000"),
        hermes_service_token=_auto(source, "HERMES_SERVICE_TOKEN"),
        hermes_timeout=_i(source, "HERMES_TIMEOUT", 180, minimum=1),
        direct_base_url=_require_if(llm_mode == "direct", "DIRECT_BASE_URL"),
        direct_api_key=_require_if(llm_mode == "direct", "DIRECT_API_KEY"),
        direct_model=_require_if(llm_mode == "direct", "DIRECT_MODEL"),
        model_fast=_s(source, "LLM_MODEL_FAST"),
        model_standard=_s(source, "LLM_MODEL_STANDARD"),
        temperature=_f(source, "LLM_TEMPERATURE", 0.3),
    )

    hitl = HITLGroup(
        timeout_seconds=_i(source, "HITL_TIMEOUT_SECONDS", 600, minimum=1),
        fallback=_one_of(source, "HITL_FALLBACK", ("auto_ack", "silent"), "auto_ack"),  # type: ignore[arg-type]
        ping_telegram=_b(source, "HITL_PING_TELEGRAM", True),
    )

    storage = StorageGroup(
        database_url=_s(source, "DATABASE_URL", required=True),
        redis_url=_s(source, "REDIS_URL", required=True),
        r2_endpoint=_s(source, "R2_ENDPOINT", required=True),
        r2_access_key_id=_s(source, "R2_ACCESS_KEY_ID", required=True),
        r2_secret_access_key=_s(source, "R2_SECRET_ACCESS_KEY", required=True),
        r2_bucket=_s(source, "R2_BUCKET", required=True),
        r2_prefix=_s(source, "R2_PREFIX", default="") or f"tenants/{tenant.id}",
        r2_signed_url_ttl=_i(source, "R2_SIGNED_URL_TTL", 3600, minimum=1),
        pg_dump_retention_days=_i(source, "PG_DUMP_RETENTION_DAYS", 30, minimum=1),
        hot_data_days=_i(source, "HOT_DATA_DAYS", 90, minimum=1),
        archive_final_outputs=_b(source, "ARCHIVE_FINAL_OUTPUTS", True),
    )

    cookie_secure = _b(source, "COOKIE_SECURE", True)
    admin = AdminGroup(
        username=_s(source, "ADMIN_USERNAME", required=True),
        bootstrap_password=_s(source, "ADMIN_BOOTSTRAP_PASSWORD", required=True),
        web_secret=_auto(source, "WEB_SECRET"),
        web_port=_i(source, "WEB_PORT", 8080, minimum=1),
        cookie_secure=cookie_secure,
        totp_enabled=_b(source, "TOTP_ENABLED", False),
    )

    ops = OpsGroup(
        app_env=app_env,  # type: ignore[arg-type]
        log_level=_s(source, "LOG_LEVEL", default="INFO").upper(),
        log_json_enabled=_b(source, "LOG_JSON_ENABLED", True),
        log_to_db=_b(source, "LOG_TO_DB", True),
        backup_hour=_i(source, "BACKUP_HOUR", 3, minimum=0),
        bootstrap_mode=_one_of(source, "BOOTSTRAP_MODE", ("full", "lite"), "full"),  # type: ignore[arg-type]
        backup_enabled=_b(source, "BACKUP_ENABLED", True),
    )
    if ops.backup_hour > 23:
        raise ConfigError("BACKUP_HOUR must be 0..23")

    domain = DomainGroup(
        currency=_s(source, "CURRENCY", required=True).upper(),
        tax_rate=_f(source, "TAX_RATE", 0.15),
        quote_valid_days=_i(source, "QUOTE_VALID_DAYS", 7, minimum=1),
        lead_scoring_enabled=_b(source, "LEAD_SCORING_ENABLED", True),
        numeral_style=_one_of(source, "NUMERAL_STYLE", ("arabic-indic", "western"), "arabic-indic"),  # type: ignore[arg-type]
        reply_language_policy=_s(source, "REPLY_LANGUAGE_POLICY", default="fusha-formal"),
    )
    if not 0.0 <= domain.tax_rate <= 1.0:
        raise ConfigError(f"TAX_RATE must be between 0 and 1, got {domain.tax_rate}")

    memory = MemoryGroup(
        enabled=_b(source, "MEMORY_ENABLED", True),
        extract_every=_i(source, "MEMORY_EXTRACT_EVERY", 6, minimum=2),
        budget_chars=_i(source, "MEMORY_BUDGET_CHARS", 800, minimum=200),
        persona_refresh_threshold=_i(source, "MEMORY_PERSONA_THRESHOLD", 4, minimum=2),
    )

    fleet = FleetGroup(
        enabled=_b(source, "FLEET_ENABLED", False),
        max_team_size=_i(source, "FLEET_MAX_TEAM_SIZE", 8, minimum=2),
        team_timeout=_i(source, "FLEET_TEAM_TIMEOUT", 300, minimum=30),
    )

    calendar = CalendarGroup(
        enabled=_b(source, "CALENDAR_ENABLED", False),
        credentials_json=_s(source, "GOOGLE_CALENDAR_CREDENTIALS"),
        calendar_id=_s(source, "GOOGLE_CALENDAR_ID", default="primary"),
        default_reminder_minutes=_i(source, "DEFAULT_REMINDER_MINUTES", 60, minimum=1),
    )

    upstream = {
        k: v
        for k, v in source.items()
        if k.startswith(UPSTREAM_KEY_PREFIXES) and k not in UPSTREAM_KEY_EXCLUDE and v.strip()
    }

    return Config(
        tenant=tenant,
        channels=channels,
        llm=llm,
        hitl=hitl,
        storage=storage,
        admin=admin,
        ops=ops,
        domain=domain,
        memory=memory,
        fleet=fleet,
        calendar=calendar,
        upstream_keys=upstream,
    )


config: Config | None = None


def reload_config(env: dict[str, str] | None = None) -> Config:
    global config
    config = load_config(env)
    return config


def get_config() -> Config:
    if config is None:
        return reload_config()
    return config


def as_redacted_dict(cfg: Config) -> dict[str, Any]:
    def mask(value: str) -> str:
        if not value:
            return ""
        return f"***{value[-4:]}" if len(value) > 8 else "***"

    return {
        "tenant": {"id": cfg.tenant.id, "name_ar": cfg.tenant.name_ar},
        "app_env": cfg.ops.app_env,
        "bootstrap_mode": cfg.ops.bootstrap_mode,
        "llm_mode": cfg.llm.mode,
        "channels": {
            "telegram": bool(cfg.channels.telegram_bot_token),
            "whatsapp": cfg.channels.whatsapp_enabled,
            "email": cfg.channels.email_enabled,
            "instagram": cfg.channels.instagram_enabled,
            "twitter": cfg.channels.twitter_enabled,
        },
        "hitl": {"timeout_seconds": cfg.hitl.timeout_seconds, "fallback": cfg.hitl.fallback},
        "storage": {"r2_bucket": cfg.storage.r2_bucket, "r2_prefix": cfg.storage.r2_prefix},
        "admin": {"username": cfg.admin.username, "token_masked": mask(cfg.admin.web_secret)},
        "domain": {"currency": cfg.domain.currency, "tax_rate": cfg.domain.tax_rate},
    }
