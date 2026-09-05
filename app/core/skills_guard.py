"""Scan installable SKILL.md files for injection / shell smuggling.

Ported from DropAgentX shared.security.skills_guard. Conservative: flag by
default, never execute anything. Never raises.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field

TRUSTED_REPOS = {
    "NousResearch/hermes-agent",
    "9router",
    "kia-agent",
}

_BLOCK_PATTERNS = [
    re.compile(r"\brm\s+-rf?\s+/", re.IGNORECASE),
    re.compile(r"\b(shutdown|poweroff|reboot)\b", re.IGNORECASE),
    re.compile(r"curl\s+.*\|\s*(sh|bash)", re.IGNORECASE),
    re.compile(r"base64\s+-d.*\|\s*(sh|bash)", re.IGNORECASE),
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(\s*['\"]?\b(system|open)", re.IGNORECASE),
    re.compile(r"\b(wget|curl)\s+.*-o\s+/etc/", re.IGNORECASE),
]

_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a\s+|an\s+)?(root|god|admin|without\s+restrictions)", re.IGNORECASE),
    re.compile(r"\[INST\]|</s>|<\|im_start\|>", re.IGNORECASE),
]

_MAX_TEXT = 200_000


@dataclass
class ScanResult:
    ok: bool
    blocked: bool
    suspicious: bool
    trusted: bool
    reasons: list[str] = field(default_factory=list)
    sha: str = ""


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def scan_skill_text(text: str, origin: str = "") -> ScanResult:
    text = text or ""
    sha = content_hash(text)
    trusted = bool(origin) and any(r.lower() in origin.lower() for r in TRUSTED_REPOS)
    reasons: list[str] = []
    blocked = False
    suspicious = False
    for pat in _BLOCK_PATTERNS:
        m = pat.search(text)
        if m:
            blocked = True
            reasons.append(f"blocked: {m.group(0)[:60]}")
            break
    for pat in _SUSPICIOUS_PATTERNS:
        m = pat.search(text)
        if m:
            suspicious = True
            reasons.append(f"suspicious: {m.group(0)[:60]}")
    ok = (not blocked) and (not suspicious or trusted)
    return ScanResult(
        ok=ok, blocked=blocked, suspicious=suspicious, trusted=trusted, reasons=reasons, sha=sha
    )


def scan_skill_file(path: str, origin: str = "") -> ScanResult:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read(_MAX_TEXT)
    except OSError as e:
        return ScanResult(
            ok=False, blocked=True, suspicious=False, trusted=False, reasons=[f"unreadable: {e}"]
        )
    return scan_skill_text(text, origin=origin or os.path.basename(path))
