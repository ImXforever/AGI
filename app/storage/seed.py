"""Seed data loader: reads JSON files from ``db/seed/`` and inserts them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.logging_setup import get_logger
from app.storage.pg import get_pool

log = get_logger(__name__)

_SEED_DIR = Path(__file__).resolve().parent.parent.parent / "db" / "seed"


def _discover_seeds() -> list[tuple[int, str, Path]]:
    """Return sorted list of (order, table_name, file_path) from the seed dir."""
    if not _SEED_DIR.is_dir():
        log.info("seed_dir_not_found", extra={"action": "load_seeds", "path": str(_SEED_DIR)})
        return []

    seeds: list[tuple[int, str, Path]] = []
    for path in sorted(_SEED_DIR.glob("*.json")):
        stem = path.stem  # e.g. "001_products"
        parts = stem.split("_", 1)
        try:
            order = int(parts[0])
        except (ValueError, IndexError):
            log.warning("skip_bad_seed_name", extra={"action": "load_seeds", "file": path.name})
            continue
        table = parts[1] if len(parts) > 1 else stem
        seeds.append((order, table, path))
    return seeds


def _load_json(path: Path) -> list[dict[str, Any]]:
    """Load and return the JSON array from a seed file."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict):
        # Support {"table_name": [...]} wrapper
        for value in data.values():
            if isinstance(value, list):
                return value
        return [data]
    if isinstance(data, list):
        return data
    log.warning("unexpected_seed_format", extra={"action": "load_seeds", "file": path.name})
    return []


async def load_seeds(*, force: bool = False) -> int:
    """Read every ``db/seed/*.json`` file and upsert rows into matching tables.

    Files are processed in lexicographic order (prefixed with a numeric order
    tag, e.g. ``001_products.json``).  Each file contains a JSON array of
    row objects.

    If the target table is empty (or ``force=True``), rows are inserted.
    Existing rows with the same ``id`` column are updated (upserted).

    Returns the total number of rows inserted/updated.
    """
    seeds = _discover_seeds()
    if not seeds:
        log.info("no_seeds_found", extra={"action": "load_seeds"})
        return 0

    pool = await get_pool()
    total_rows = 0

    for order, table_name, path in seeds:
        rows = _load_json(path)
        if not rows:
            log.debug("empty_seed_file", extra={"action": "load_seeds", "table": table_name})
            continue

        # Determine columns from the first row
        columns = list(rows[0].keys())
        if not columns:
            log.warning("seed_no_columns", extra={"action": "load_seeds", "table": table_name})
            continue

        col_list = ", ".join(columns)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
        update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col != "id")

        # Only do upsert if 'id' column exists; otherwise plain insert
        if "id" in columns:
            sql = f"""
                INSERT INTO {table_name} ({col_list})
                VALUES ({placeholders})
                ON CONFLICT (id) DO UPDATE SET {update_clause}
            """
        else:
            sql = f"""
                INSERT INTO {table_name} ({col_list})
                VALUES ({placeholders})
            """

        inserted = 0
        try:
            async with pool.acquire() as conn, conn.transaction():
                for row in rows:
                    values = [
                        json.dumps(row[col], ensure_ascii=False)
                        if isinstance(row.get(col), dict | list)
                        else row.get(col)
                        for col in columns
                    ]
                    await conn.execute(sql, *values)
                    inserted += 1
            total_rows += inserted
            log.info(
                "seed_loaded",
                extra={
                    "action": "load_seeds",
                    "table": table_name,
                    "rows": inserted,
                    "file": path.name,
                },
            )
        except Exception:
            log.exception(
                "seed_load_failed",
                extra={
                    "action": "load_seeds",
                    "table": table_name,
                    "file": path.name,
                    "rows_attempted": len(rows),
                },
            )

    log.info("seeds_load_complete", extra={"action": "load_seeds", "total_rows": total_rows})
    return total_rows
