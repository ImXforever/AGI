"""Admin API — whole-database control with JSON versioning (1.5.0).

The console's **Database** page lets a manager browse every business table,
add / edit / delete rows, and move data around as versioned JSON files:

* ``GET    /database/tables``                      → allow-listed tables + row counts
* ``GET    /database/{table}?limit=&offset=&q=``   → rows (newest first), column meta
* ``POST   /database/{table}``                     → insert one row
* ``PUT    /database/{table}/{pk}``                → update one row (partial)
* ``DELETE /database/{table}/{pk}``                → delete one row (superadmin)
* ``GET    /database/{table}/export``              → JSON file ``{"version","table","rows"}``
* ``GET    /database/export/all``                  → one JSON file with every table
* ``POST   /database/{table}/import``              → upsert rows from a JSON file
* ``POST   /database/import``                      → import a multi-table file

Safety
------
Only tables in :data:`TABLES` are reachable — never ``admins`` (password
hashes), ``audit_log`` (append-only) or migration bookkeeping. Column names
are validated against ``information_schema`` on every call, so identifiers in
SQL are always from the database itself, never from the request. Values are
bound parameters. Imports use the same upsert semantics as the seed loader
(``ON CONFLICT (natural key) DO UPDATE``), so a JSON export is a faithful,
re-loadable snapshot. Every write is audited.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_superadmin, require_writer
from app.constants import APP_VERSION
from app.logging_setup import get_logger
from app.storage.seed import _NATURAL_KEYS

log = get_logger("app.admin_api.database")

router = APIRouter(prefix="/database", tags=["admin-database"])

EXPORT_FORMAT = "zenovix-db-json/1"
MAX_IMPORT_BYTES = 25 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000

#: table → (natural key column, human group). Order = order in the console.
TABLES: dict[str, tuple[str, str]] = {
    "products": ("sku", "Catalog"),
    "catalog_categories": ("key", "Catalog"),
    "product_specs": ("product_id", "Catalog"),
    "faq": ("id", "Knowledge"),
    "troubleshooting": ("id", "Knowledge"),
    "fallback_templates": ("key", "Knowledge"),
    "kb_notes": ("id", "Knowledge"),
    "agent_soul": ("id", "Agent"),
    "settings": ("key", "Agent"),
    "customers": ("id", "CRM"),
    "customer_notes": ("id", "CRM"),
    "conversations": ("id", "CRM"),
    "messages": ("id", "CRM"),
    "tickets": ("id", "Operations"),
    "ticket_notes": ("id", "Operations"),
    "quotes": ("id", "Operations"),
    "orders": ("id", "Operations"),
    "order_items": ("id", "Operations"),
    "approvals": ("id", "Operations"),
    "user_memories": ("id", "Memory"),
    "user_profile": ("user_id", "Memory"),
}

#: Columns that are never exported / returned (defence in depth).
HIDDEN_COLUMNS = {"password_hash", "secret", "token"}


def _table(name: str) -> tuple[str, str]:
    if name not in TABLES:
        raise HTTPException(status_code=404, detail=f"table not available: {name}")
    return name, TABLES[name][0]


async def _columns(pg: Any, table: str) -> list[dict[str, Any]]:
    rows = await pg.fetch(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position
        """,
        table,
    )
    return [
        {
            "name": r["column_name"],
            "type": r["data_type"],
            "nullable": r["is_nullable"] == "YES",
            "has_default": r["column_default"] is not None,
        }
        for r in rows
        if r["column_name"] not in HIDDEN_COLUMNS
    ]


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"__bytes__": len(bytes(value))}
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in "[{" and stripped[-1:] in "]}":
            try:
                return json.loads(stripped)
            except ValueError:
                return value
    return value


def _row(record: Any, json_cols: set[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in dict(record).items():
        if k in HIDDEN_COLUMNS:
            continue
        if json_cols and k in json_cols and isinstance(v, str):
            # asyncpg returns json/jsonb as text unless a codec is installed.
            try:
                out[k] = json.loads(v)
                continue
            except ValueError:
                pass
        out[k] = _jsonable(v)
    return out


def _json_cols(cols: list[dict[str, Any]]) -> set[str]:
    return {c["name"] for c in cols if c["type"] in ("jsonb", "json")}


def _bind(col: dict[str, Any], value: Any) -> Any:
    """Coerce a JSON value to something asyncpg accepts for the column type."""
    ctype = str(col.get("type") or "")
    if value is None:
        return None
    if ctype in ("jsonb", "json"):
        return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    if ctype == "ARRAY":
        return list(value) if isinstance(value, (list, tuple)) else [value]
    if ctype in ("timestamp with time zone", "timestamp without time zone"):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return value
    if ctype == "date" and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    if ctype == "uuid":
        return str(value)
    if ctype in ("integer", "bigint", "smallint"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if ctype in ("numeric", "double precision", "real"):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if ctype == "boolean":
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _cast(col: dict[str, Any], idx: int) -> str:
    ctype = str(col.get("type") or "")
    if ctype in ("jsonb", "json"):
        return f"${idx}::{ctype}"
    if ctype == "uuid":
        return f"${idx}::uuid"
    return f"${idx}"


def _friendly_db_error(exc: Exception) -> str:
    """One readable line for the console (no SQL internals)."""
    if isinstance(exc, asyncpg.UniqueViolationError):
        detail = str(getattr(exc, "detail", "") or "")
        return "duplicate value — " + (
            detail[:160] if detail else "a row with this key already exists"
        )
    if isinstance(exc, asyncpg.CheckViolationError):
        return f"value not allowed by rule {getattr(exc, 'constraint_name', '') or ''}".strip()
    if isinstance(exc, asyncpg.NotNullViolationError):
        return f"missing required column {getattr(exc, 'column_name', '') or ''}".strip()
    if isinstance(exc, asyncpg.ForeignKeyViolationError):
        return "referenced row does not exist"
    return str(exc).splitlines()[0][:200]


def _pk_value(col: dict[str, Any] | None, pk: str) -> Any:
    """Bind the path ``pk`` with the key column's real type.

    1.5.0 passed the raw string for every table: fine for ``uuid`` (with an
    explicit cast) and ``text`` keys, but ``bigint`` keys (``kb_notes``,
    ``user_memories``, ``user_profile.user_id``) made asyncpg raise
    ``DataError: invalid input for query argument`` → every edit / delete on
    those tables failed with 400. Garbage ids now become a clean 404.
    """
    ctype = str((col or {}).get("type") or "")
    if ctype in ("integer", "bigint", "smallint"):
        try:
            return int(pk)
        except (TypeError, ValueError):
            raise HTTPException(status_code=404, detail="row not found") from None
    if ctype == "uuid":
        try:
            return str(uuid.UUID(str(pk)))
        except (TypeError, ValueError):
            raise HTTPException(status_code=404, detail="row not found") from None
    return pk


def _pg(request: Request) -> Any:
    pg = getattr(request.app.state, "services", {}).get("pg")
    if pg is None:
        raise HTTPException(status_code=503, detail="database unavailable")
    return pg


def _actor(admin: dict[str, Any]) -> str:
    return str(admin.get("username") or admin.get("sub") or "manager")


async def _audit(
    action: str, actor: str, table: str, entity_id: str, details: dict[str, Any]
) -> None:
    try:
        from app.storage.pg import audit

        await audit(action=action, actor=actor, entity=table, entity_id=entity_id, details=details)
    except Exception:
        log.debug("database_audit_failed", exc_info=True)


# ---------------------------------------------------------------------------
# Browse
# ---------------------------------------------------------------------------


@router.get("/tables")
async def list_tables(
    request: Request, admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    pg = _pg(request)
    out = []
    for name, (key, group) in TABLES.items():
        try:
            count = await pg.fetchval(f'SELECT COUNT(*) FROM "{name}"')  # nosec B608 - allow-listed
        except Exception:
            count = None
        out.append({"table": name, "key": key, "group": group, "rows": count})
    return {"ok": True, "version": APP_VERSION, "format": EXPORT_FORMAT, "tables": out}


@router.get("/export/all")
async def export_all(request: Request, admin: dict[str, Any] = Depends(require_admin)) -> Response:
    pg = _pg(request)
    payload: dict[str, Any] = {
        "format": EXPORT_FORMAT,
        "version": APP_VERSION,
        "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "exported_by": _actor(admin),
        "tables": {},
    }
    for name in TABLES:
        try:
            rows = await pg.fetch(f'SELECT * FROM "{name}"')  # nosec B608 - allow-listed
            jc = _json_cols(await _columns(pg, name))
            payload["tables"][name] = [_row(r, jc) for r in rows]
        except Exception as exc:
            payload["tables"][name] = {"error": str(exc)[:200]}
    await _audit("database.export_all", _actor(admin), "*", "", {"tables": len(TABLES)})
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="zenovix-db-{APP_VERSION}-{stamp}.json"'
        },
    )


@router.get("/{table}/export")
async def export_table(
    table: str, request: Request, admin: dict[str, Any] = Depends(require_admin)
) -> Response:
    name, key = _table(table)
    pg = _pg(request)
    rows = await pg.fetch(f'SELECT * FROM "{name}"')  # nosec B608 - allow-listed
    jc = _json_cols(await _columns(pg, name))
    payload = {
        "format": EXPORT_FORMAT,
        "version": APP_VERSION,
        "table": name,
        "key": key,
        "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "exported_by": _actor(admin),
        "rows": [_row(r, jc) for r in rows],
    }
    await _audit("database.export", _actor(admin), name, "", {"rows": len(rows)})
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}-{APP_VERSION}-{stamp}.json"'
        },
    )


@router.get("/{table}")
async def list_rows(
    table: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str = Query(default="", max_length=120),
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    name, key = _table(table)
    pg = _pg(request)
    cols = await _columns(pg, name)
    if not cols:
        raise HTTPException(status_code=404, detail="table missing in database")
    col_names = [c["name"] for c in cols]
    order = "created_at DESC" if "created_at" in col_names else f'"{key}"'
    where = ""
    params: list[Any] = []
    if q:
        text_cols = [c["name"] for c in cols if c["type"] in ("text", "character varying", "jsonb")]
        if text_cols:
            params.append(f"%{q}%")
            where = " WHERE " + " OR ".join(f'"{c}"::text ILIKE $1' for c in text_cols)
    total = await pg.fetchval(f'SELECT COUNT(*) FROM "{name}"{where}', *params)  # nosec B608
    rows = await pg.fetch(  # nosec B608 - identifiers from information_schema, values bound
        f'SELECT * FROM "{name}"{where} ORDER BY {order} LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}',
        *params,
        limit,
        offset,
    )
    return {
        "ok": True,
        "table": name,
        "key": key,
        "columns": cols,
        "total": total,
        "limit": limit,
        "offset": offset,
        "rows": [_row(r, _json_cols(cols)) for r in rows],
    }


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class RowIn(BaseModel):
    row: dict[str, Any] = Field(default_factory=dict)


def _upsert_sql(
    name: str, key: str, by_name: dict[str, dict[str, Any]], data: dict[str, Any]
) -> tuple[str, list[Any], str]:
    """Build one parameterised upsert (identifiers from information_schema only)."""
    names = list(data)
    values = [_bind(by_name[c], data[c]) for c in names]
    col_list = ", ".join(f'"{c}"' for c in names)
    placeholders = ", ".join(_cast(by_name[c], i + 1) for i, c in enumerate(names))
    conflict = key if key in names else ("id" if "id" in names else "")
    if conflict:
        update_cols = [c for c in names if c not in (conflict, "id")]
        if update_cols:
            set_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
            sql = (
                f'INSERT INTO "{name}" ({col_list}) VALUES ({placeholders}) '
                f'ON CONFLICT ("{conflict}") DO UPDATE SET {set_clause}'
            )
        else:
            sql = (
                f'INSERT INTO "{name}" ({col_list}) VALUES ({placeholders}) '
                f'ON CONFLICT ("{conflict}") DO NOTHING'
            )
    else:
        sql = f'INSERT INTO "{name}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    return sql, values, conflict


async def _upsert_rows(
    pg: Any, name: str, key: str, cols: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> tuple[int, int, list[str]]:
    by_name = {c["name"]: c for c in cols}
    inserted = 0
    skipped = 0
    errors: list[str] = []
    async with pg.acquire() as conn:
        for row in rows:
            if not isinstance(row, dict):
                skipped += 1
                continue
            data = {k: v for k, v in row.items() if k in by_name and k not in HIDDEN_COLUMNS}
            if not data:
                skipped += 1
                continue
            sql, values, conflict = _upsert_sql(name, key, by_name, data)
            try:
                await conn.execute(sql, *values)  # nosec B608 - identifiers validated above
                inserted += 1
            except Exception as exc:
                skipped += 1
                if len(errors) < 20:
                    label = str(data.get(conflict or "id", ""))[:40]
                    errors.append(
                        f"{label}: {_friendly_db_error(exc)}" if label else _friendly_db_error(exc)
                    )
    return inserted, skipped, errors


# 1.6.0: declared BEFORE ``POST /{table}`` — FastAPI matches routes in order,
# so ``POST /database/import`` used to be captured by the generic insert
# route (table="import") and the console's *Import all* always failed with 422.
@router.post("/import")
async def import_all(
    request: Request,
    file: UploadFile = File(...),
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pg = _pg(request)
    payload = await _read_json(file)
    tables = payload.get("tables") if isinstance(payload, dict) else None
    if not isinstance(tables, dict):
        raise HTTPException(
            status_code=422, detail='expected a multi-table export ({"tables": {...}})'
        )
    report: dict[str, Any] = {}
    for name, rows in tables.items():
        if name not in TABLES or not isinstance(rows, list):
            report[name] = {"skipped": True}
            continue
        cols = await _columns(pg, name)
        inserted, skipped, errors = await _upsert_rows(
            pg, name, TABLES[name][0], cols, rows[:MAX_IMPORT_ROWS]
        )
        report[name] = {
            "rows": len(rows),
            "upserted": inserted,
            "skipped": skipped,
            "errors": errors,
        }
        _invalidate(name)
    await _audit(
        "database.import_all",
        _actor(admin),
        "*",
        "",
        {"tables": list(report), "source_version": payload.get("version")},
    )
    return {"ok": True, "report": report}


@router.post("/{table}", status_code=201)
async def insert_row(
    table: str, body: RowIn, request: Request, admin: dict[str, Any] = Depends(require_writer)
) -> dict[str, Any]:
    name, key = _table(table)
    pg = _pg(request)
    cols = await _columns(pg, name)
    by_name = {c["name"]: c for c in cols}
    row = {k: v for k, v in dict(body.row).items() if not (k == "id" and v in (None, ""))}
    if "id" in by_name and not row.get("id") and by_name["id"]["type"] in ("uuid", "text"):
        row["id"] = str(uuid.uuid4())
    data = {k: v for k, v in row.items() if k in by_name and k not in HIDDEN_COLUMNS}
    if not data:
        raise HTTPException(status_code=422, detail="no known columns in row")
    sql, values, _conflict = _upsert_sql(name, key, by_name, data)
    try:
        # 1.6.0: RETURNING * echoes the *stored* row — generated bigint ids,
        # defaults and timestamps — so the console can open it straight away.
        rec = await pg.fetchrow(sql + " RETURNING *", *values)  # nosec B608 - see _upsert_sql
    except (asyncpg.IntegrityConstraintViolationError, asyncpg.DataError) as exc:
        raise HTTPException(status_code=422, detail=_friendly_db_error(exc)) from exc
    except asyncpg.PostgresError as exc:
        raise HTTPException(status_code=422, detail=_friendly_db_error(exc)) from exc
    if rec is None:
        raise HTTPException(status_code=422, detail="row rejected (conflict, nothing to update)")
    stored = _row(rec, _json_cols(cols))
    await _audit(
        "database.insert",
        _actor(admin),
        name,
        str(stored.get(key) or stored.get("id") or ""),
        {"columns": list(data)},
    )
    _invalidate(name)
    return {"ok": True, "table": name, "row": stored}


@router.put("/{table}/{pk}")
async def update_row(
    table: str,
    pk: str,
    body: RowIn,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    name, key = _table(table)
    pg = _pg(request)
    cols = await _columns(pg, name)
    by_name = {c["name"]: c for c in cols}
    changes = {
        k: v
        for k, v in body.row.items()
        if k in by_name and k not in (key, "id") and k not in HIDDEN_COLUMNS
    }
    if not changes:
        raise HTTPException(status_code=422, detail="nothing to update")
    names = list(changes)
    values = [_bind(by_name[c], changes[c]) for c in names]
    set_clause = ", ".join(f'"{c}" = {_cast(by_name[c], i + 1)}' for i, c in enumerate(names))
    if "updated_at" in by_name and "updated_at" not in changes:
        set_clause += ", updated_at = NOW()"
    pk_cast = "::uuid" if by_name.get(key, {}).get("type") == "uuid" else ""
    pk_value = _pk_value(by_name.get(key), pk)
    try:
        status = await pg.execute(  # nosec B608 - identifiers validated, values bound
            f'UPDATE "{name}" SET {set_clause} WHERE "{key}" = ${len(names) + 1}{pk_cast}',
            *values,
            pk_value,
        )
    except (asyncpg.IntegrityConstraintViolationError, asyncpg.DataError) as exc:
        # 1.6.0: a duplicate SKU / bad enum / wrong type is the manager's
        # mistake, not a server crash — say what was wrong instead of 500.
        raise HTTPException(status_code=422, detail=_friendly_db_error(exc)) from exc
    if status.endswith(" 0"):
        raise HTTPException(status_code=404, detail="row not found")
    await _audit("database.update", _actor(admin), name, pk, {"columns": names})
    _invalidate(name)
    return {"ok": True, "table": name, "key": key, "pk": pk, "updated": names}


@router.delete("/{table}/{pk}")
async def delete_row(
    table: str, pk: str, request: Request, admin: dict[str, Any] = Depends(require_superadmin)
) -> dict[str, Any]:
    name, key = _table(table)
    pg = _pg(request)
    cols = await _columns(pg, name)
    by_name = {c["name"]: c for c in cols}
    pk_cast = "::uuid" if by_name.get(key, {}).get("type") == "uuid" else ""
    pk_value = _pk_value(by_name.get(key), pk)
    try:
        status = await pg.execute(  # nosec B608 - identifiers validated, value bound
            f'DELETE FROM "{name}" WHERE "{key}" = $1{pk_cast}', pk_value
        )
    except asyncpg.ForeignKeyViolationError as exc:
        raise HTTPException(
            status_code=409,
            detail="row is referenced by other rows (orders, quotes, notes…) — remove those first",
        ) from exc
    except (asyncpg.IntegrityConstraintViolationError, asyncpg.DataError) as exc:
        raise HTTPException(status_code=422, detail=_friendly_db_error(exc)) from exc
    if status.endswith(" 0"):
        raise HTTPException(status_code=404, detail="row not found")
    await _audit("database.delete", _actor(admin), name, pk, {})
    _invalidate(name)
    return {"ok": True, "table": name, "deleted": pk}


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


async def _read_json(file: UploadFile) -> Any:
    data = await file.read(MAX_IMPORT_BYTES + 1)
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="file too large (max 25 MB)")
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid JSON: {str(exc)[:120]}") from exc


def _rows_from(payload: Any, table: str) -> list[dict[str, Any]]:
    """Accept ``{"rows": [...]}``, ``{"<table>": [...]}``, ``{"tables": {...}}`` or a bare list."""
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("rows"), list):
            if payload.get("table") and payload["table"] != table:
                raise HTTPException(
                    status_code=422,
                    detail=f"file is for table {payload['table']!r}, not {table!r}",
                )
            rows = payload["rows"]
        elif isinstance(payload.get("tables"), dict) and isinstance(
            payload["tables"].get(table), list
        ):
            rows = payload["tables"][table]
        elif isinstance(payload.get(table), list):
            rows = payload[table]
        else:
            raise HTTPException(status_code=422, detail="no rows found for this table")
    else:
        raise HTTPException(status_code=422, detail="unsupported JSON shape")
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(status_code=413, detail=f"too many rows (max {MAX_IMPORT_ROWS})")
    return [r for r in rows if isinstance(r, dict)]


@router.post("/{table}/import")
async def import_table(
    table: str,
    request: Request,
    file: UploadFile = File(...),
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    name, key = _table(table)
    pg = _pg(request)
    payload = await _read_json(file)
    rows = _rows_from(payload, name)
    cols = await _columns(pg, name)
    inserted, skipped, errors = await _upsert_rows(pg, name, key, cols, rows)
    await _audit(
        "database.import",
        _actor(admin),
        name,
        "",
        {
            "rows": len(rows),
            "upserted": inserted,
            "skipped": skipped,
            "source_version": (payload.get("version") if isinstance(payload, dict) else None),
        },
    )
    _invalidate(name)
    return {
        "ok": True,
        "table": name,
        "rows": len(rows),
        "upserted": inserted,
        "skipped": skipped,
        "errors": errors,
    }


def _invalidate(table: str) -> None:
    """Drop in-process caches that shadow the edited table."""
    try:
        if table == "settings":
            from app.core.business_settings import invalidate_cache

            invalidate_cache()
        elif table == "agent_soul":
            from app.core.soul import invalidate_cache as soul_invalidate

            soul_invalidate()
    except Exception:
        log.debug("cache_invalidate_failed", exc_info=True)
