#!/usr/bin/env python3
"""Tenant provisioning CLI for Kia-Agent Platform.

Usage:
    python provision/tenant.py --config provision/tenant.example.yaml
    python provision/tenant.py --id acme --name-ar "Acme Corp" --contact "admin@acme.com"
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


DEFAULT_ENV_TEMPLATE = """\
# =============================================================================
# Kia-Agent Platform â€” Generated for tenant: {tenant_id}
# Generated at: {timestamp}
# =============================================================================

# TENANT
APP_ENV=production
TENANT_ID={tenant_id}
TENANT_NAME_AR={name_ar}
TENANT_NAME_EN={name_en}
SUPPORT_CONTACT={contact}
BRAND_PRIMARY_COLOR={color}

# TELEGRAM
TELEGRAM_BOT_TOKEN={telegram_token}
TELEGRAM_ADMIN_IDS={admin_ids}

# WHATSAPP (configure manually)
WHATSAPP_ENABLED=false
WHATSAPP_PROVIDER=meta

# EMAIL (configure manually)
EMAIL_ENABLED=false

# LLM
LLM_MODE={llm_mode}
ROUTER_ACCESS_KEY={router_key}
HERMES_SERVICE_TOKEN={hermes_token}

# STORAGE
DATABASE_URL={database_url}
REDIS_URL={redis_url}
R2_ENDPOINT={r2_endpoint}
R2_ACCESS_KEY_ID={r2_access_key}
R2_SECRET_ACCESS_KEY={r2_secret}
R2_BUCKET={r2_bucket}

# ADMIN
ADMIN_USERNAME={admin_username}
ADMIN_BOOTSTRAP_PASSWORD={admin_password}
WEB_SECRET={web_secret}
WEB_PORT=8080
COOKIE_SECURE=true

# DOMAIN
CURRENCY={currency}
TAX_RATE=0.15
QUOTE_VALID_DAYS=7
NUMERAL_STYLE=arabic-indic
"""


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)


def _generate_password() -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%"
    return "".join(secrets.choice(chars) for _ in range(20))


def provision_from_yaml(config_path: str) -> dict[str, Any]:
    if yaml is None:
        print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def provision_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "tenant_id": args.id,
        "name_ar": args.name_ar,
        "name_en": args.name_en or args.name_ar,
        "contact": args.contact,
        "color": args.color or "#0b6e4f",
        "telegram_token": args.telegram_token or "",
        "admin_ids": args.admin_ids or "",
        "llm_mode": args.llm_mode or "router",
        "router_key": _generate_secret(),
        "hermes_token": _generate_secret(),
        "database_url": args.database_url or "",
        "redis_url": args.redis_url or "",
        "r2_endpoint": args.r2_endpoint or "",
        "r2_access_key": args.r2_access_key or "",
        "r2_secret": args.r2_secret or "",
        "r2_bucket": args.r2_bucket or "Kia-Agent-assets",
        "admin_username": args.admin_username or "admin",
        "admin_password": _generate_password(),
        "web_secret": _generate_secret(),
        "currency": args.currency or "SAR",
    }


def generate_env(config: dict[str, Any], output_path: str | None = None) -> str:
    import time

    config.setdefault("timestamp", time.strftime("%Y-%m-%d %H:%M:%S UTC"))
    env_content = DEFAULT_ENV_TEMPLATE.format(**config)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"Generated .env file: {output_path}")

    return env_content


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a new Kia-Agent tenant")
    parser.add_argument("--config", type=str, help="Path to YAML config file")
    parser.add_argument("--id", type=str, help="Tenant ID (lowercase)")
    parser.add_argument("--name-ar", type=str, help="Arabic name")
    parser.add_argument("--name-en", type=str, help="English name")
    parser.add_argument("--contact", type=str, help="Support contact email")
    parser.add_argument("--color", type=str, help="Brand primary color")
    parser.add_argument("--telegram-token", type=str, help="Telegram bot token")
    parser.add_argument("--admin-ids", type=str, help="Comma-separated admin IDs")
    parser.add_argument(
        "--llm-mode", type=str, default="router", choices=["router", "direct", "mock"]
    )
    parser.add_argument("--database-url", type=str, help="PostgreSQL URL")
    parser.add_argument("--redis-url", type=str, help="Redis URL")
    parser.add_argument("--r2-endpoint", type=str, help="R2 endpoint")
    parser.add_argument("--r2-access-key", type=str, help="R2 access key")
    parser.add_argument("--r2-secret", type=str, help="R2 secret key")
    parser.add_argument("--r2-bucket", type=str, help="R2 bucket name")
    parser.add_argument("--admin-username", type=str, help="Admin username")
    parser.add_argument("--currency", type=str, default="SAR", help="Currency code")
    parser.add_argument("--output", type=str, help="Output .env file path")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout only")

    args = parser.parse_args()

    if args.config:
        config = provision_from_yaml(args.config)
    elif args.id and args.name_ar and args.contact:
        config = provision_from_args(args)
    else:
        parser.error("Provide either --config or --id, --name-ar, --contact")
        return

    env_content = generate_env(config, output_path=None if args.dry_run else args.output)
    if args.dry_run:
        print(env_content)

    # Summary
    print(f"\nTenant: {config.get('tenant_id', 'unknown')}")
    print(f"Admin:  {config.get('admin_username', 'admin')}")
    print(f"Pass:   {config.get('admin_password', 'N/A')}")
    print("\nNext steps:")
    print("  1. Review the generated .env file")
    print("  2. Add channel credentials (WhatsApp, Email)")
    print("  3. Deploy: make deploy-railway")
    print("  4. Access dashboard: https://your-domain/admin/")


if __name__ == "__main__":
    main()
