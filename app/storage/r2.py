"""Cloudflare R2 (S3-compatible) archive storage."""

from __future__ import annotations

import mimetypes
import time
from datetime import UTC, datetime
from typing import Any, BinaryIO

import boto3  # type: ignore[import-untyped]
from botocore.config import Config as BotoConfig  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.config import get_config
from app.constants import (
    R2_DIR_ATTACHMENTS,
    R2_DIR_BACKUPS,
    R2_DIR_QUOTES,
    R2_DIR_REPORTS,
    R2_DIR_TRANSCRIPTS,
)
from app.logging_setup import get_logger

log = get_logger(__name__)


class R2Archive:
    """Cloudflare R2 object storage client (S3-compatible API via boto3)."""

    def __init__(self) -> None:
        cfg = get_config()
        self._endpoint = cfg.storage.r2_endpoint
        self._bucket = cfg.storage.r2_bucket
        self._prefix = cfg.storage.r2_prefix
        self._signed_ttl = cfg.storage.r2_signed_url_ttl

        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=cfg.storage.r2_access_key_id,
            aws_secret_access_key=cfg.storage.r2_secret_access_key,
            region_name="auto",
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )

    # ------------------------------------------------------------------
    # Bucket management
    # ------------------------------------------------------------------

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not already exist."""
        if not self.bucket_exists():
            try:
                self._client.create_bucket(Bucket=self._bucket)
                log.info(
                    "r2_bucket_created", extra={"action": "ensure_bucket", "bucket": self._bucket}
                )
            except ClientError as exc:
                log.exception("r2_bucket_create_failed", extra={"action": "ensure_bucket"})
                raise RuntimeError(f"Failed to create R2 bucket {self._bucket}: {exc}") from exc

    def bucket_exists(self) -> bool:
        """Check whether the configured bucket exists."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return True
        except ClientError:
            return False

    # ------------------------------------------------------------------
    # Key construction
    # ------------------------------------------------------------------

    def _key(self, directory: str, filename: str) -> str:
        """Build the full object key, including the tenant prefix."""
        parts = [p for p in (self._prefix, directory, filename) if p]
        return "/".join(parts)

    def _date_prefix(self, directory: str) -> str:
        """Directory prefix with a YYYY/MM/DD date partition."""
        now = datetime.now(UTC)
        return f"{directory}/{now.strftime('%Y/%m/%d')}"

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def _put(
        self,
        key: str,
        body: bytes | BinaryIO,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload an object to R2."""
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
        }
        if metadata:
            kwargs["Metadata"] = metadata
        self._client.put_object(**kwargs)
        log.debug(
            "r2_object_put",
            extra={
                "action": "r2_put",
                "key": key,
                "size": getattr(
                    body,
                    "getbuffer",
                    lambda: type("", (), {"nbytes": len(body) if isinstance(body, bytes) else 0})(),
                )().nbytes
                if isinstance(body, bytes)
                else "stream",
            },
        )

    # ------------------------------------------------------------------
    # Public upload methods
    # ------------------------------------------------------------------

    def write_transcript(
        self,
        conversation_id: str,
        data: bytes | BinaryIO,
        *,
        content_type: str = "application/json",
    ) -> str:
        """Store a conversation transcript. Returns the object key."""
        filename = f"{conversation_id}_{int(time.time())}.json"
        key = self._key(self._date_prefix(R2_DIR_TRANSCRIPTS), filename)
        self._put(
            key,
            data,
            content_type=content_type,
            metadata={
                "conversation-id": conversation_id,
                "type": "transcript",
            },
        )
        log.info(
            "r2_transcript_written",
            extra={"action": "write_transcript", "key": key, "conversation_id": conversation_id},
        )
        return key

    def write_attachment(
        self,
        conversation_id: str,
        filename: str,
        data: bytes | BinaryIO,
        *,
        content_type: str | None = None,
    ) -> str:
        """Store a conversation attachment (image, document, etc.).

        Returns the object key.
        """
        if content_type is None:
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        safe_name = f"{conversation_id}_{int(time.time())}_{filename}"
        key = self._key(self._date_prefix(R2_DIR_ATTACHMENTS), safe_name)
        self._put(
            key,
            data,
            content_type=content_type,
            metadata={
                "conversation-id": conversation_id,
                "original-filename": filename,
                "type": "attachment",
            },
        )
        log.info(
            "r2_attachment_written",
            extra={"action": "write_attachment", "key": key, "conversation_id": conversation_id},
        )
        return key

    def write_quote(
        self,
        quote_id: str,
        data: bytes | BinaryIO,
        *,
        content_type: str = "application/pdf",
    ) -> str:
        """Store a generated quote document. Returns the object key."""
        filename = f"{quote_id}_{int(time.time())}.pdf"
        key = self._key(self._date_prefix(R2_DIR_QUOTES), filename)
        self._put(
            key,
            data,
            content_type=content_type,
            metadata={
                "quote-id": quote_id,
                "type": "quote",
            },
        )
        log.info(
            "r2_quote_written", extra={"action": "write_quote", "key": key, "quote_id": quote_id}
        )
        return key

    def write_report(
        self,
        report_name: str,
        data: bytes | BinaryIO,
        *,
        content_type: str = "application/pdf",
    ) -> str:
        """Store an analytics or operations report. Returns the object key."""
        safe_name = f"{report_name}_{int(time.time())}.pdf"
        key = self._key(self._date_prefix(R2_DIR_REPORTS), safe_name)
        self._put(
            key,
            data,
            content_type=content_type,
            metadata={
                "report-name": report_name,
                "type": "report",
            },
        )
        log.info(
            "r2_report_written",
            extra={"action": "write_report", "key": key, "report_name": report_name},
        )
        return key

    def write_backup(
        self,
        data: bytes | BinaryIO,
        *,
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store a pg_dump backup archive. Returns the object key."""
        if filename is None:
            filename = f"pgdump_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.sql.gz"
        key = self._key(f"{R2_DIR_BACKUPS}", filename)
        self._put(
            key,
            data,
            content_type=content_type,
            metadata={
                "type": "pg-backup",
            },
        )
        log.info("r2_backup_written", extra={"action": "write_backup", "key": key})
        return key

    # ------------------------------------------------------------------
    # Signed URLs
    # ------------------------------------------------------------------

    def get_signed_url(self, key: str) -> str:
        """Generate a time-limited pre-signed download URL for an object."""
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=self._signed_ttl,
            )
            log.debug("r2_signed_url", extra={"action": "get_signed_url", "key": key})
            return url
        except ClientError as exc:
            log.exception("r2_signed_url_failed", extra={"action": "get_signed_url", "key": key})
            raise RuntimeError(f"Failed to generate signed URL for {key}: {exc}") from exc

    # ------------------------------------------------------------------
    # Deletion / listing
    # ------------------------------------------------------------------

    def delete_object(self, key: str) -> None:
        """Delete a single object from R2."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            log.debug("r2_object_deleted", extra={"action": "delete_object", "key": key})
        except ClientError:
            log.exception("r2_delete_failed", extra={"action": "delete_object", "key": key})
            raise

    def list_keys(self, prefix: str, *, limit: int = 1000) -> list[str]:
        """List object keys under the given prefix (paginated)."""
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=self._bucket, Prefix=prefix, PaginationConfig={"MaxItems": limit}
        ):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
                if len(keys) >= limit:
                    return keys
        return keys

    def cleanup_old_backups(self, retention_days: int) -> int:
        """Delete backup objects older than ``retention_days``.

        Returns the number of objects deleted.
        """
        cutoff = time.time() - (retention_days * 86400)
        deleted = 0
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=self._bucket,
            Prefix=f"{self._prefix}/{R2_DIR_BACKUPS}" if self._prefix else R2_DIR_BACKUPS,
        ):
            for obj in page.get("Contents", []):
                if obj["LastModified"].timestamp() < cutoff:
                    self.delete_object(obj["Key"])
                    deleted += 1
        if deleted:
            log.info(
                "r2_old_backups_cleaned",
                extra={
                    "action": "cleanup_old_backups",
                    "deleted": deleted,
                    "retention_days": retention_days,
                },
            )
        return deleted
