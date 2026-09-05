"""Postprocess — Arabic verification, formatting fixes, and safety gating."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.config import Config, get_config
from app.constants import ARABIC_INDIC_DIGITS, WESTERN_DIGITS
from app.logging_setup import get_logger

log = get_logger("app.core.postprocess")


@dataclass
class PostprocessReport:
    """Result of a postprocess pass over a draft reply."""

    text: str
    original_length: int = 0
    final_length: int = 0
    fixes_applied: list[str] = field(default_factory=list)
    language: str = "ar"
    has_content: bool = True
    sanitized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "original_length": self.original_length,
            "final_length": self.final_length,
            "fixes_applied": self.fixes_applied,
            "language": self.language,
            "has_content": self.has_content,
            "sanitized": self.sanitized,
        }


_BIDI_CHARS = re.compile(r"[\u202a-\u202e\u2066-\u2069]")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EXCESS_WHITESPACE = re.compile(r"[^\S\n]+")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")
# NOTE: must not match "\n" itself, otherwise the MULTILINE end-of-line strip
# swallows the newlines and welds separate paragraphs into one word.
_LEADING_TRAILING = re.compile(r"^[^\S\n]+|[^\S\n]+$", re.MULTILINE)

_UNWANTED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"```[\s\S]*?```", re.DOTALL), "code_block"),
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), "markdown_link"),
]


def _arabic_digit_swap(text: str) -> str:
    """Convert Western digits to Arabic-Indic when configured."""
    result = text
    for western, indic in zip(WESTERN_DIGITS, ARABIC_INDIC_DIGITS):
        result = result.replace(western, indic)
    return result


def _verify_arabic_ratio(text: str) -> str:
    """Remove orphaned non-Arabic sequences that break RTL flow."""
    if not text:
        return text
    arabic_count = sum(
        1
        for c in text
        if "\u0600" <= c <= "\u06ff"
        or "\u0750" <= c <= "\u077f"
        or "\ufb50" <= c <= "\ufdff"
        or "\ufe70" <= c <= "\ufeff"
    )
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0:
        return text
    ratio = arabic_count / total_alpha
    if ratio < 0.3 and total_alpha > 5:
        log.debug("low_arabic_ratio", extra={"action": "verify_arabic", "ratio": f"{ratio:.2f}"})
    return text


def _sanitize(text: str) -> str:
    """Remove control characters, bidi overrides, and excess whitespace."""
    cleaned = _CONTROL_CHARS.sub("", text)
    cleaned = _BIDI_CHARS.sub("", cleaned)
    cleaned = _EXCESS_WHITESPACE.sub(" ", cleaned)
    cleaned = _EXCESS_NEWLINES.sub("\n\n", cleaned)
    cleaned = _LEADING_TRAILING.sub("", cleaned)
    return cleaned.strip()


def _strip_unwanted(text: str) -> str:
    """Remove code blocks and markdown links that leak into channel messages."""
    result = text
    for pattern, _name in _UNWANTED_PATTERNS:
        result = pattern.sub("", result)
    return result.strip()


def run(text: str, *, config: Config | None = None) -> PostprocessReport:
    """Run the full postprocess pipeline on a draft reply.

    Steps:
        1. Record original length
        2. Sanitize (control chars, bidi, whitespace)
        3. Strip unwanted markdown artifacts
        4. Arabic verification
        5. Digit style conversion (Arabic-Indic)
        6. Final length check

    Returns a ``PostprocessReport`` with the cleaned text and applied fixes.
    """
    cfg = config or get_config()
    fixes: list[str] = []
    original_length = len(text)

    sanitized = _sanitize(text)
    if sanitized != text:
        fixes.append("sanitize")
        text = sanitized

    stripped = _strip_unwanted(text)
    if stripped != text:
        fixes.append("strip_unwanted")
        text = stripped

    verified = _verify_arabic_ratio(text)
    if verified != text:
        fixes.append("arabic_verify")
        text = verified

    if cfg.domain.numeral_style == "arabic-indic":
        converted = _arabic_digit_swap(text)
        if converted != text:
            fixes.append("arabic_indic_digits")
            text = converted

    text = text.strip()

    report = PostprocessReport(
        text=text,
        original_length=original_length,
        final_length=len(text),
        fixes_applied=fixes,
        language="ar",
        has_content=bool(text.strip()),
        sanitized=len(fixes) > 0,
    )

    if fixes:
        log.info(
            "postprocess_applied",
            extra={
                "action": "postprocess",
                "fixes": fixes,
                "original_length": original_length,
                "final_length": report.final_length,
            },
        )

    return report
