"""Nightly backup background task: pg_dump → gzip → R2."""

from __future__ import annotations

import asyncio
import gzip
from datetime import UTC, datetime

from app.config import get_config
from app.logging_setup import get_logger
from app.storage.r2 import R2Archive

log = get_logger(__name__)

_DEFAULT_BACKUP_HOUR_UTC = 3  # 03:00 UTC


async def _pg_dump_bytes() -> bytes:
    """Run pg_dump via subprocess and return the gzipped output."""
    import os
    import shutil

    if shutil.which("pg_dump") is None:
        raise FileNotFoundError("pg_dump is not installed in this image; install postgresql-client")

    from urllib.parse import urlparse

    cfg = get_config()
    dsn = cfg.storage.database_url
    parsed = urlparse(dsn)

    env = os.environ.copy()
    env["PGSSLMODE"] = "require"
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)
    dbname = (parsed.path or "/").lstrip("/")
    username = parsed.username or ""

    log.info("pg_dump_starting", extra={"action": "pg_dump"})

    proc = await asyncio.create_subprocess_exec(
        "pg_dump",
        "--no-owner",
        "--no-privileges",
        "--format=plain",
        "--no-password",
        "-h", host,
        "-p", port,
        "-U", username,
        "-d", dbname,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace").strip()
        log.error(
            "pg_dump_failed",
            extra={"action": "pg_dump", "returncode": proc.returncode, "stderr": error_msg[:500]},
        )
        raise RuntimeError(f"pg_dump failed with code {proc.returncode}: {error_msg[:300]}")

    raw = stdout
    compressed = gzip.compress(raw, compresslevel=6)

    log.info(
        "pg_dump_complete",
        extra={"action": "pg_dump", "raw_bytes": len(raw), "compressed_bytes": len(compressed)},
    )
    return compressed


def _seconds_until_next(hour: int) -> float:
    """Return seconds until the next occurrence of ``hour`` (0-23) UTC."""
    now = datetime.now(UTC)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        import datetime as dt_mod

        target += dt_mod.timedelta(days=1)
    return (target - now).total_seconds()


async def _run_single_backup(r2: R2Archive, retention_days: int) -> None:
    """Execute one backup cycle: dump → compress → upload → cleanup."""
    try:
        compressed = await _pg_dump_bytes()
        key = r2.write_backup(compressed)
        log.info(
            "nightly_backup_uploaded",
            extra={"action": "nightly_backup", "key": key, "size": len(compressed)},
        )
    except Exception:
        log.exception("nightly_backup_failed", extra={"action": "nightly_backup"})
        return

    try:
        cleaned = r2.cleanup_old_backups(retention_days)
        if cleaned:
            log.info(
                "old_backups_cleaned",
                extra={"action": "nightly_backup", "deleted": cleaned},
            )
    except Exception:
        log.exception("backup_cleanup_failed", extra={"action": "nightly_backup_cleanup"})


async def start_nightly_backup() -> None:
    """Background loop that runs a nightly pg_dump → R2 backup.

    This coroutine **never** returns.  It is designed to be launched as a
    background task (e.g. ``asyncio.create_task(start_nightly_backup())``)
    at application startup.

    The first backup runs immediately on startup (useful after deploys),
    then subsequent backups run at ``BACKUP_HOUR`` UTC each day.
    """
    cfg = get_config()
    if not cfg.ops.backup_enabled:
        log.info("nightly_backup_disabled", extra={"action": "nightly_backup_loop"})
        return
    backup_hour = cfg.ops.backup_hour
    retention_days = cfg.storage.pg_dump_retention_days

    r2 = R2Archive()
    try:
        r2.ensure_bucket()
    except Exception:
        # Object storage may be unreachable (e.g. local dev without R2).
        # Backups are best-effort; do not crash the background task.
        log.warning("backup_bucket_unavailable", extra={"action": "nightly_backup_loop"})

    log.info(
        "nightly_backup_loop_started",
        extra={
            "action": "nightly_backup_loop",
            "backup_hour": backup_hour,
            "retention_days": retention_days,
        },
    )

    # Run once immediately at startup
    log.info("nightly_backup_initial_run", extra={"action": "nightly_backup_loop"})
    await _run_single_backup(r2, retention_days)

    while True:
        wait = _seconds_until_next(backup_hour)
        log.info(
            "nightly_backup_sleeping",
            extra={"action": "nightly_backup_loop", "next_run_in_seconds": int(wait)},
        )
        await asyncio.sleep(wait)
        await _run_single_backup(r2, retention_days)
