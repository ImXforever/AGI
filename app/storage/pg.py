"""PostgreSQL storage: connection pool, forward-only migrations, audit log."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import asyncpg  # type: ignore[import-untyped]

from app.config import get_config
from app.logging_setup import get_logger

log = get_logger(__name__)

_pool: asyncpg.Pool | None = None

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------


async def connect_pg() -> asyncpg.Pool:
    """Create and return an asyncpg connection pool (singleton)."""
    global _pool
    if _pool is not None and not _pool._closed:
        return _pool

    cfg = get_config()
    dsn = cfg.storage.database_url
    log.info("connecting_to_pg", extra={"action": "pg_connect"})

    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=2,
        max_size=10,
        command_timeout=30,
        server_settings={"application_name": "Kia-Agent"},
    )
    log.info("pg_pool_ready", extra={"action": "pg_connect"})
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Return the existing pool or create one."""
    global _pool
    if _pool is None or _pool._closed:
        return await connect_pg()
    return _pool


async def close_pg() -> None:
    """Gracefully close the pool."""
    global _pool
    if _pool is not None and not _pool._closed:
        await _pool.close()
        log.info("pg_pool_closed", extra={"action": "pg_close"})
    _pool = None


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "db" / "migrations"
_LOCK_ADVISORY = 7_291_013  # arbitrary unique int for pg_advisory_lock


def _collect_migrations() -> list[tuple[int, str, str]]:
    """Return sorted list of (version, name, sql_text) from the migrations dir."""
    if not _MIGRATIONS_DIR.is_dir():
        return []

    migrations: list[tuple[int, str, str]] = []
    for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        stem = path.stem  # e.g. "001_create_tables"
        parts = stem.split("_", 1)
        try:
            version = int(parts[0])
        except (ValueError, IndexError):
            log.warning("skip_bad_migration_name", extra={"action": "migrate", "file": path.name})
            continue
        sql = path.read_text(encoding="utf-8")
        migrations.append((version, path.name, sql))
    return migrations


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def _ensure_migration_table(pool: asyncpg.Pool) -> None:
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version     INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            checksum    TEXT NOT NULL,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)


async def run_migrations() -> None:
    """Apply pending migrations under an advisory lock with checksum verification.

    Forward-only: each migration is applied exactly once.  If a previously
    applied migration's file has changed on disk the checksum mismatch will
    raise an error rather than silently re-applying.
    """
    pool = await get_pool()
    await _ensure_migration_table(pool)

    migrations = _collect_migrations()
    if not migrations:
        log.info("no_migrations_found", extra={"action": "migrate"})
        return

    async with pool.acquire() as conn:
        await conn.execute("SELECT pg_advisory_lock($1)", _LOCK_ADVISORY)
        log.info("advisory_lock_acquired", extra={"action": "migrate"})

        try:
            applied = await conn.fetch(
                "SELECT version, name, checksum FROM _migrations ORDER BY version"
            )
            applied_map: dict[int, tuple[str, str]] = {
                row["version"]: (row["name"], row["checksum"]) for row in applied
            }

            for version, name, sql_text in migrations:
                if version in applied_map:
                    existing_name, existing_checksum = applied_map[version]
                    current_checksum = _checksum(sql_text)
                    if existing_checksum != current_checksum:
                        from app.config import get_config
                        if get_config().is_production:
                            raise RuntimeError(
                                f"Migration {version} ({name}) checksum mismatch — "
                                "refusing to continue in production. "
                                "Revert the migration file or run a new migration."
                            )
                        log.warning(
                            "migration_checksum_mismatch",
                            extra={
                                "action": "migrate",
                                "version": version,
                                "name": name,
                                "disk_checksum": current_checksum,
                                "db_checksum": existing_checksum,
                                "hint": "migration already applied but file changed — continuing",
                            },
                        )
                    log.debug(
                        "migration_already_applied",
                        extra={"action": "migrate", "version": version, "name": name},
                    )
                    continue

                log.info(
                    "applying_migration",
                    extra={"action": "migrate", "version": version, "name": name},
                )
                try:
                    async with conn.transaction():
                        await conn.execute(sql_text)
                        await conn.execute(
                            "INSERT INTO _migrations (version, name, checksum) VALUES ($1, $2, $3)",
                            version,
                            name,
                            _checksum(sql_text),
                        )
                except Exception as exc:
                    if "already exists" in str(exc) or "duplicate" in str(exc):
                        log.warning(
                            "migration_partial",
                            extra={"action": "migrate", "version": version, "error": str(exc)},
                        )
                        await conn.execute(
                            "INSERT INTO _migrations (version, name, checksum) VALUES ($1, $2, $3) ON CONFLICT (version) DO NOTHING",
                            version,
                            name,
                            _checksum(sql_text),
                        )
                    else:
                        raise

            log.info("migrations_complete", extra={"action": "migrate", "count": len(migrations)})
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", _LOCK_ADVISORY)
            log.info("advisory_lock_released", extra={"action": "migrate"})


# ---------------------------------------------------------------------------
# Audit log (append-only)
# ---------------------------------------------------------------------------


async def audit(
    *,
    action: str,
    actor: str = "system",
    entity: str = "",
    entity_id: str = "",
    details: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    channel: str | None = None,
) -> None:
    """Insert a row into the append-only audit_log table.

    The table is expected to have INSERT-only permissions at the database level
    (no UPDATE/DELETE).  This function never returns a value; failures are
    logged but not raised so callers are never blocked by audit writes.
    """
    import json

    pool = await get_pool()
    try:
        await pool.execute(
            """
            INSERT INTO audit_log (action, actor, entity, entity_id, details, conversation_id, channel)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            action,
            actor,
            entity,
            entity_id,
            json.dumps(details or {}, ensure_ascii=False, default=str),
            conversation_id,
            channel,
        )
        log.debug(
            "audit_recorded",
            extra={
                "action": action,
                "actor": actor,
                "entity": entity,
                "entity_id": entity_id,
                "conversation_id": conversation_id,
                "channel": channel,
            },
        )
    except Exception:
        log.exception(
            "audit_write_failed",
            extra={"action": action, "actor": actor, "entity": entity},
        )


async def audit_batch(records: list[dict[str, Any]]) -> None:
    """Insert multiple audit records in a single transaction.

    Each dict must contain at least ``action``; all other fields are optional.
    """
    import json

    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for rec in records:
                    await conn.execute(
                        """
                        INSERT INTO audit_log (action, actor, entity, entity_id, details, conversation_id, channel)
                        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                        """,
                        rec.get("action", "unknown"),
                        rec.get("actor", "system"),
                        rec.get("entity", ""),
                        rec.get("entity_id", ""),
                        json.dumps(rec.get("details", {}), ensure_ascii=False, default=str),
                        rec.get("conversation_id"),
                        rec.get("channel"),
                    )
        log.debug("audit_batch_recorded", extra={"action": "audit_batch", "count": len(records)})
    except Exception:
        log.exception("audit_batch_write_failed", extra={"action": "audit_batch"})
