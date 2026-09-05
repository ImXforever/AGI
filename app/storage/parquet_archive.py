"""Dual-format (JSON + Parquet) archival to Cloudflare R2.

Adapted from hermes-desk parquet_archive for Kia-Agent Platform.
Uses pyarrow when available for native Parquet output; gracefully
falls back to storing the JSON payload with a ``.parquet`` suffix
so callers never need to care about the on-disk format.
"""

from __future__ import annotations

import io
import json
from typing import Any

from app.logging_setup import get_logger
from app.storage.r2 import R2Archive

log = get_logger(__name__)

_pyarrow_available: bool | None = None


def _has_pyarrow() -> bool:
    global _pyarrow_available
    if _pyarrow_available is None:
        try:
            import pyarrow  # noqa: F401

            _pyarrow_available = True
        except ImportError:
            _pyarrow_available = False
            log.info(
                "pyarrow_not_found", extra={"action": "parquet_archive", "fallback": "json_only"}
            )
    return _pyarrow_available


def _to_parquet_bytes(records: list[dict[str, Any]]) -> bytes:
    """Convert a list of dicts to a Parquet byte buffer."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pylist(records)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def write_transcript(
    *, r2: R2Archive, conversation_id: str, record: dict[str, Any]
) -> dict[str, str]:
    """Archive a single transcript record in both JSON and Parquet formats.

    Returns ``{"json": "<key>", "parquet": "<key>"}``.
    """
    json_key = r2.write_transcript(
        conversation_id,
        json.dumps(record, ensure_ascii=False, default=str).encode(),
        content_type="application/json",
    )
    parquet_key = json_key.replace(".json", ".parquet")

    if _has_pyarrow():
        try:
            data = _to_parquet_bytes([record])
            r2._put(
                parquet_key,
                data,
                content_type="application/vnd.apache.parquet",
                metadata={"conversation-id": conversation_id, "type": "transcript"},
            )
            log.info(
                "parquet_transcript_written",
                extra={"action": "write_transcript", "parquet_key": parquet_key},
            )
        except Exception:
            log.exception("parquet_transcript_fallback", extra={"action": "write_transcript"})
            r2._put(
                parquet_key,
                json.dumps(record, ensure_ascii=False, default=str).encode(),
                content_type="application/json",
                metadata={"conversation-id": conversation_id, "type": "transcript-fallback"},
            )
    else:
        r2._put(
            parquet_key,
            json.dumps(record, ensure_ascii=False, default=str).encode(),
            content_type="application/json",
            metadata={"conversation-id": conversation_id, "type": "transcript-fallback"},
        )

    return {"json": json_key, "parquet": parquet_key}


def write_quote_archive(*, r2: R2Archive, quote_id: str, record: dict[str, Any]) -> dict[str, str]:
    """Archive a quote record in both JSON and Parquet formats.

    Returns ``{"json": "<key>", "parquet": "<key>"}``.
    """
    payload = json.dumps(record, ensure_ascii=False, default=str).encode()
    filename = f"{quote_id}.json"
    key_prefix = r2._date_prefix("quotes")
    json_key = r2._key(key_prefix, filename)
    r2._put(
        json_key,
        payload,
        content_type="application/json",
        metadata={
            "quote-id": quote_id,
            "type": "quote",
        },
    )

    parquet_key = json_key.replace(".json", ".parquet")

    if _has_pyarrow():
        try:
            data = _to_parquet_bytes([record])
            r2._put(
                parquet_key,
                data,
                content_type="application/vnd.apache.parquet",
                metadata={"quote-id": quote_id, "type": "quote"},
            )
            log.info(
                "parquet_quote_written",
                extra={"action": "write_quote_archive", "parquet_key": parquet_key},
            )
        except Exception:
            log.exception("parquet_quote_fallback", extra={"action": "write_quote_archive"})
            r2._put(
                parquet_key,
                payload,
                content_type="application/json",
                metadata={
                    "quote-id": quote_id,
                    "type": "quote-fallback",
                },
            )
    else:
        r2._put(
            parquet_key,
            payload,
            content_type="application/json",
            metadata={
                "quote-id": quote_id,
                "type": "quote-fallback",
            },
        )

    return {"json": json_key, "parquet": parquet_key}


def write_ticket_archive(
    *, r2: R2Archive, ticket_id: str, records: list[dict[str, Any]]
) -> dict[str, str]:
    """Archive ticket records in both JSON and Parquet formats.

    Accepts a list of records (multiple events/updates for the ticket).
    Returns ``{"json": "<key>", "parquet": "<key>"}``.
    """
    payload = json.dumps(records, ensure_ascii=False, default=str).encode()
    filename = f"{ticket_id}.json"
    key_prefix = r2._date_prefix("tickets")
    json_key = r2._key(key_prefix, filename)
    r2._put(
        json_key,
        payload,
        content_type="application/json",
        metadata={
            "ticket-id": ticket_id,
            "type": "ticket",
        },
    )

    parquet_key = json_key.replace(".json", ".parquet")

    if _has_pyarrow():
        try:
            data = _to_parquet_bytes(records)
            r2._put(
                parquet_key,
                data,
                content_type="application/vnd.apache.parquet",
                metadata={"ticket-id": ticket_id, "type": "ticket"},
            )
            log.info(
                "parquet_ticket_written",
                extra={"action": "write_ticket_archive", "parquet_key": parquet_key},
            )
        except Exception:
            log.exception("parquet_ticket_fallback", extra={"action": "write_ticket_archive"})
            r2._put(
                parquet_key,
                payload,
                content_type="application/json",
                metadata={
                    "ticket-id": ticket_id,
                    "type": "ticket-fallback",
                },
            )
    else:
        r2._put(
            parquet_key,
            payload,
            content_type="application/json",
            metadata={
                "ticket-id": ticket_id,
                "type": "ticket-fallback",
            },
        )

    return {"json": json_key, "parquet": parquet_key}
