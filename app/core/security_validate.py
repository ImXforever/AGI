"""Inbound validation: MIME allowlist, filename sanitisation, text limits."""

from __future__ import annotations

import html as _html_mod
import re
from pathlib import Path

from app.logging_setup import get_logger

log = get_logger(__name__)

SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-\u0600-\u06FF]+")

ALLOWED_MIME: set[str] = {
    # images
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
    # documents
    "application/pdf",
    "text/plain",
    "text/csv",
    # office formats (oil-industry reports, invoices, specs)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "application/vnd.ms-excel",  # legacy XLS
    "application/msword",  # legacy DOC
    "application/vnd.oasis.opendocument.text",  # ODT
    "application/vnd.oasis.opendocument.spreadsheet",  # ODS
    # data
    "application/json",
    "application/xml",
    "text/xml",
}

MAX_INBOUND_CHARS: int = 4000
_MAX_FILENAME_LEN: int = 180
_MAX_ATTACHMENT_BYTES: int = 10 * 1024 * 1024  # 10 MB


def allowed_mime(mime: str) -> bool:
    """Return True if *mime* is in the allowlist."""
    return (mime or "").lower() in ALLOWED_MIME


def sanitize_filename(name: str) -> str:
    """Strip path traversal and unsafe characters from a filename."""
    name = Path(name or "file").name
    name = SAFE_NAME.sub("_", name).strip("._") or "file"
    return name[:_MAX_FILENAME_LEN]


def validate_inbound_text(text: str) -> str:
    """Truncate inbound text to MAX_INBOUND_CHARS."""
    text = (text or "").strip()
    if len(text) > MAX_INBOUND_CHARS:
        text = text[:MAX_INBOUND_CHARS]
    return text


def validate_inbound_attachment(
    *, filename: str, content_type: str, size_bytes: int
) -> dict[str, str | bool]:
    """Validate an inbound file attachment.

    Returns a dict with keys ``ok``, ``reason``, ``safe_name``, ``content_type``.
    If ``ok`` is False the caller should reject the upload.
    """
    safe_name = sanitize_filename(filename)
    mime = (content_type or "").lower()

    if not allowed_mime(mime):
        log.warning(
            "attachment_rejected_mime",
            extra={"action": "validate_attachment", "filename": safe_name, "mime": mime},
        )
        return {
            "ok": False,
            "reason": f"mime_not_allowed:{mime}",
            "safe_name": safe_name,
            "content_type": mime,
        }

    if size_bytes > _MAX_ATTACHMENT_BYTES:
        log.warning(
            "attachment_rejected_size",
            extra={"action": "validate_attachment", "filename": safe_name, "size": size_bytes},
        )
        return {
            "ok": False,
            "reason": f"too_large:{size_bytes}",
            "safe_name": safe_name,
            "content_type": mime,
        }

    return {"ok": True, "reason": "", "safe_name": safe_name, "content_type": mime}


def sanitize_html(raw: str) -> str:
    """Escape HTML entities in *raw* so email content cannot inject markup."""
    if not raw:
        return ""
    return _html_mod.escape(raw, quote=True)
