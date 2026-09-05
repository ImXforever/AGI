#!/usr/bin/env python3
"""Configuration linter — validates all environment variables against the contract.

Checks:
1. Required variables are present
2. Types are correct (int, float, bool, enum)
3. Ranges are valid
4. No leftover placeholder values
5. Secrets are sufficiently long

Run: python tools/config_lint.py
Exit code 0 = clean, 1 = errors found.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

REQUIRED = [
    "TENANT_ID",
    "TENANT_NAME_AR",
    "SUPPORT_CONTACT",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ADMIN_IDS",
    "DATABASE_URL",
    "REDIS_URL",
    "R2_ENDPOINT",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET",
    "ADMIN_USERNAME",
    "ADMIN_BOOTSTRAP_PASSWORD",
    "CURRENCY",
]

ENUMS: dict[str, list[str]] = {
    "APP_ENV": ["production", "development", "test"],
    "LLM_MODE": ["router", "direct", "mock"],
    "HITL_FALLBACK": ["auto_ack", "silent"],
    "WHATSAPP_PROVIDER": ["meta", "twilio"],
    "EMAIL_INBOUND_PROVIDER": ["sendgrid", "imap"],
    "NUMERAL_STYLE": ["arabic-indic", "western"],
}

INTEGER_MIN: dict[str, int] = {
    "BACKUP_HOUR": 0,
    "HITL_TIMEOUT_SECONDS": 1,
    "RATE_LIMIT_PER_MINUTE": 1,
    "WEB_PORT": 1,
    "IMAP_PORT": 1,
    "IMAP_POLL_SECONDS": 5,
    "QUOTE_VALID_DAYS": 1,
    "PG_DUMP_RETENTION_DAYS": 1,
    "HOT_DATA_DAYS": 1,
    "R2_SIGNED_URL_TTL": 1,
    "ROUTER_TIMEOUT": 1,
    "HERMES_TIMEOUT": 1,
}

INTEGER_MAX: dict[str, int] = {
    "BACKUP_HOUR": 23,
}

FLOAT_RANGE: dict[str, tuple[float, float]] = {
    "TAX_RATE": (0.0, 1.0),
    "LLM_TEMPERATURE": (0.0, 2.0),
}

SECRET_MIN_LENGTH = 16

PLACEHOLDER_PATTERNS = [
    "your-",
    "changeme",
    "placeholder",
    "todo",
    "xxx",
    "replace-me",
]

CONDITIONAL_REQUIRED: dict[str, dict[str, list[str]]] = {
    "WHATSAPP_ENABLED=true": [
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_API_TOKEN",
    ],
    "EMAIL_ENABLED=true": ["EMAIL_FROM", "RESEND_API_KEY"],
    "LLM_MODE=direct": ["DIRECT_BASE_URL", "DIRECT_API_KEY", "DIRECT_MODEL"],
    "EMAIL_INBOUND_PROVIDER=imap": ["IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"],
    "WHATSAPP_PROVIDER=twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"],
}


def load_dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    for path in [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]:
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        env[key.strip()] = value.strip().strip('"').strip("'")
            break
    # Overlay with actual env
    for key in env:
        if key in os.environ:
            env[key] = os.environ[key]
    # Add env-only vars
    for key, val in os.environ.items():
        if key not in env:
            env[key] = val
    return env


def lint(env: dict[str, str]) -> list[str]:
    errors: list[str] = []

    # 1. Required variables
    for var in REQUIRED:
        val = env.get(var, "").strip()
        if not val:
            errors.append(f"MISSING required variable: {var}")

    # 2. Enums
    for var, allowed in ENUMS.items():
        val = env.get(var, "").strip()
        if val and val not in allowed:
            errors.append(f"INVALID enum {var}={val!r} (allowed: {allowed})")

    # 3. Integers
    for var, minimum in INTEGER_MIN.items():
        val = env.get(var, "").strip()
        if val:
            try:
                int_val = int(val)
                if int_val < minimum:
                    errors.append(f"TOO LOW {var}={val} (minimum: {minimum})")
            except ValueError:
                errors.append(f"NOT AN INTEGER {var}={val!r}")

    for var, maximum in INTEGER_MAX.items():
        val = env.get(var, "").strip()
        if val:
            try:
                if int(val) > maximum:
                    errors.append(f"TOO HIGH {var}={val} (maximum: {maximum})")
            except ValueError:
                pass

    # 4. Floats
    for var, (lo, hi) in FLOAT_RANGE.items():
        val = env.get(var, "").strip()
        if val:
            try:
                fval = float(val)
                if not lo <= fval <= hi:
                    errors.append(f"OUT OF RANGE {var}={val} (range: {lo}-{hi})")
            except ValueError:
                errors.append(f"NOT A NUMBER {var}={val!r}")

    # 5. Secret length
    for var in ["WEB_SECRET", "ROUTER_ACCESS_KEY", "HERMES_SERVICE_TOKEN"]:
        val = env.get(var, "").strip()
        if val and len(val) < SECRET_MIN_LENGTH:
            errors.append(
                f"SECRET TOO SHORT {var} ({len(val)} chars, minimum: {SECRET_MIN_LENGTH})"
            )

    # 6. Placeholder detection
    for var, val in env.items():
        val_lower = val.lower()
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in val_lower:
                errors.append(f"PLACEHOLDER value in {var} (contains '{pattern}')")
                break

    # 7. Conditional requirements
    for condition, vars_needed in CONDITIONAL_REQUIRED.items():
        key, _, expected = condition.partition("=")
        actual = env.get(key, "").strip()
        if actual == expected:
            for var in vars_needed:
                if not env.get(var, "").strip():
                    errors.append(f"CONDITIONAL: {var} required when {condition}")

    # 8. Integer range check (backup hour)
    backup = env.get("BACKUP_HOUR", "").strip()
    if backup:
        try:
            if not 0 <= int(backup) <= 23:
                errors.append(f"BACKUP_HOUR must be 0-23, got {backup}")
        except ValueError:
            pass

    return errors


def main() -> None:
    print("=" * 60)
    print("Kia-Agent Config Lint")
    print("=" * 60)

    env = load_dotenv()
    errors = lint(env)

    if errors:
        print(f"\n{len(errors)} error(s) found:\n")
        for error in errors:
            print(f"  ERROR  {error}")
        sys.exit(1)
    else:
        print("\nAll configuration checks passed.")
        print(f"  Variables checked: {len(env)}")
        print(f"  Required: {len(REQUIRED)}")
        print(f"  Enums: {len(ENUMS)}")
        sys.exit(0)


if __name__ == "__main__":
    main()
