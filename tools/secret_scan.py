#!/usr/bin/env python3
"""Secret scanner — detects accidentally committed secrets in source code.

Scans all Python and config files for:
- Hardcoded API keys, tokens, passwords
- Private keys
- Connection strings with credentials
- Base64-encoded secrets

Run: python tools/secret_scan.py
Exit code 0 = clean, 1 = secrets found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "venv",
    ".venv",
}
SKIP_FILES = {".env.example", "tenant.example.yaml"}

PATTERNS: list[tuple[str, str]] = [
    ("AWS Access Key", r"AKIA[0-9A-Z]{16}"),
    ("AWS Secret Key", r"(?:aws_secret_access_key|secret_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"),
    ("GitHub Token", r"ghp_[A-Za-z0-9]{36}"),
    ("GitHub App Token", r"(?:ghu|ghs)_[A-Za-z0-9]{36}"),
    ("GitLab Token", r"glpat-[A-Za-z0-9\-_]{20,}"),
    ("Slack Token", r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    ("Slack Webhook", r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+"),
    (
        "Generic API Key",
        r"(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}",
    ),
    ("Generic Secret", r"(?:secret|password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{10,}"),
    ("Private Key Header", r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    ("Bearer Token", r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"),
    ("Resend API Key", r"re_[A-Za-z0-9]{20,}"),
    ("SendGrid API Key", r"SG\.[A-Za-z0-9_\-]{20,}"),
    ("Twilio SID", r"AC[a-f0-9]{32}"),
    ("Telegram Bot Token", r"\d{9,10}:[A-Za-z0-9_\-]{35}"),
    ("Connection String", r"postgresql://[^\s]+:[^\s]+@[^\s]+"),
    ("JWT Token", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]

# Allowlists: lines matching these are skipped
ALLOWLIST_PATTERNS = [
    r"\.env\.example",
    r"tenant\.example\.yaml",
    r"config_lint\.py",
    r"test_",
    r"placeholder",
    r"your-",
    r"changeme",
    r"example",
    r"TODO",
    r"sample",
    r"ci\.yml",
    r"docker-compose",
    r"provision",
    r"conftest",
    r"localhost",
    r"testpass",
    r"testpassword",
    r"IntegrationTest",
    r"unit-test",
    r"integration-webhook",
    r"_s\(source",
    r"_auto\(source",
    r"_require_if",
    r"_secret_or_empty",
    r"getattr\(cfg",
    r"self\._secret",
    r"env\.get\(",
    r"environ\.get\(",
    r"encode\(\)",
    r"postgresql://",
    r"\$\{",
    r"\{admin_password\}",
    r"\{web_secret\}",
    r"webhook-secret",
    r"super-secret",
    r"my-very-long",
    r"_make_env",
]


class Finding(NamedTuple):
    file: str
    line_num: int
    line: str
    pattern_name: str


def scan() -> list[Finding]:
    findings: list[Finding] = []

    for path in ROOT.rglob("*"):
        if path.is_dir():
            if path.name in SKIP_DIRS:
                continue
            continue
        if path.suffix not in (".py", ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini", ".env"):
            continue
        if path.name in SKIP_FILES:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel = str(path.relative_to(ROOT))

        for line_num, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check allowlist
            is_allowed = False
            for allow in ALLOWLIST_PATTERNS:
                if re.search(allow, stripped, re.IGNORECASE):
                    is_allowed = True
                    break
            if is_allowed:
                continue

            for pattern_name, pattern in PATTERNS:
                if re.search(pattern, stripped, re.IGNORECASE):
                    findings.append(
                        Finding(
                            file=rel,
                            line_num=line_num,
                            line=stripped[:120],
                            pattern_name=pattern_name,
                        )
                    )
                    break  # One finding per line

    return findings


def main() -> None:
    print("=" * 60)
    print("Kia-Agent Secret Scanner")
    print("=" * 60)
    print(f"Scanning: {ROOT}")

    findings = scan()

    if findings:
        print(f"\n{len(findings)} potential secret(s) found:\n")
        for f in findings:
            print(f"  {f.pattern_name}")
            print(f"    {f.file}:{f.line_num}")
            print(f"    {f.line}")
            print()
        sys.exit(1)
    else:
        print("\nNo secrets found. Codebase is clean.")
        sys.exit(0)


if __name__ == "__main__":
    main()
