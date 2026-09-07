"""Admin catalog management endpoints: products, categories, stock, discounts."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_superadmin, require_writer
from app.logging_setup import get_logger

log = get_logger("app.admin_api.catalog")

router = APIRouter(prefix="/catalog", tags=["admin-catalog"])


class ProductCreate(BaseModel):
    """1.4.0: English is the reference language; ``name_ar`` is optional."""

    sku: str
    name_en: str
    name_ar: str = ""
    code: str = ""
    title_en: str = ""
    names: dict[str, str] = Field(default_factory=dict)
    titles: dict[str, str] = Field(default_factory=dict)
    description_ar: str = ""
    description_en: str = ""
    category: str = ""
    unit: str = "metric ton"
    unit_price: float = Field(default=0, ge=0)
    currency: str = "USD"
    image_url: str = ""
    sort_order: int = 100
    stock_qty: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=10, ge=0)
    discount_tiers: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True
    technical_specs: dict[str, Any] | None = None
    safety_data: str | None = None
    compliance_notes: str | None = None


class ProductUpdate(BaseModel):
    name_ar: str | None = None
    name_en: str | None = None
    code: str | None = None
    title_en: str | None = None
    names: dict[str, str] | None = None
    titles: dict[str, str] | None = None
    description_ar: str | None = None
    description_en: str | None = None
    category: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    currency: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    stock_qty: int | None = None
    reorder_point: int | None = None
    discount_tiers: list[dict[str, Any]] | None = None
    is_active: bool | None = None


class CategoryUpsert(BaseModel):
    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name_en: str = ""
    names: dict[str, str] = Field(default_factory=dict)
    icon: str = ""
    sort_order: int = 100
    is_active: bool = True


class FAQCreate(BaseModel):
    question_ar: str
    question_en: str = ""
    answer_ar: str
    answer_en: str = ""
    category: str = ""
    language: str = "ar"


class TroubleshootingCreate(BaseModel):
    title_ar: str
    title_en: str = ""
    problem_ar: str
    problem_en: str = ""
    solution_ar: str
    solution_en: str = ""
    category: str = ""
    severity: int = Field(default=1, ge=1, le=5)


class MSDSCreate(BaseModel):
    product_id: str
    title_ar: str
    title_en: str = ""
    r2_key: str
    version: int = 1
    language: str = "ar"


# ---------------------------------------------------------------------------
# Categories & product images (1.4.0)
# ---------------------------------------------------------------------------

IMAGE_MAX_BYTES = 2 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/categories")
async def list_categories(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch(
        """
        SELECT c.key, c.name_en, c.names, c.icon, c.sort_order, c.is_active,
               (SELECT COUNT(*) FROM products p WHERE p.category = c.key AND p.is_active) AS products
        FROM catalog_categories c
        ORDER BY c.sort_order, c.key
        """
    )
    return {"items": [_json_row(r) for r in rows]}


@router.put("/categories/{key}")
async def upsert_category(
    key: str,
    req: CategoryUpsert,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    if key != req.key:
        raise HTTPException(status_code=400, detail="key in path and body must match")
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO catalog_categories (key, name_en, names, icon, sort_order, is_active)
        VALUES ($1, $2, $3::jsonb, $4, $5, $6)
        ON CONFLICT (key) DO UPDATE SET
            name_en = EXCLUDED.name_en, names = EXCLUDED.names, icon = EXCLUDED.icon,
            sort_order = EXCLUDED.sort_order, is_active = EXCLUDED.is_active, updated_at = NOW()
        """,
        req.key,
        req.name_en,
        json.dumps(req.names, ensure_ascii=False),
        req.icon[:8],
        req.sort_order,
        req.is_active,
    )
    log.info(
        "category saved", extra={"action": "catalog.category.save", "entity": f"category:{req.key}"}
    )
    return {"ok": True, "key": req.key}


@router.delete("/categories/{key}")
async def delete_category(
    key: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    in_use = await pool.fetchval("SELECT COUNT(*) FROM products WHERE category = $1", key)
    if in_use:
        raise HTTPException(status_code=409, detail=f"{in_use} product(s) still use this category")
    await pool.execute("DELETE FROM catalog_categories WHERE key = $1", key)
    return {"ok": True}


@router.get("/languages")
async def catalog_languages(admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Language codes the catalog editor offers for translations."""
    from app.core.languages import SUPPORTED_MENU_LANGUAGES

    return {
        "reference": "en",
        "items": [
            {"code": lang.code, "name": lang.native_name}
            for lang in SUPPORTED_MENU_LANGUAGES
            if lang.code != "en"
        ],
    }


@router.post("/products/{product_id}/image")
async def upload_product_image(
    product_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    """Raw image body (JPEG/PNG/WebP ≤ 2 MB). Stored in Postgres; the bot sends it."""
    pool = request.app.state.services["pg"]
    mime = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if mime not in IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="send image/jpeg, image/png or image/webp")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty body")
    if len(body) > IMAGE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="image larger than 2 MB")
    exists = await pool.fetchval("SELECT id FROM products WHERE id = $1", product_id)
    if exists is None:
        raise HTTPException(status_code=404, detail="product not found")
    await pool.execute(
        """
        INSERT INTO product_images (product_id, mime, data, size, updated_by, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (product_id) DO UPDATE SET
            mime = EXCLUDED.mime, data = EXCLUDED.data, size = EXCLUDED.size,
            updated_by = EXCLUDED.updated_by, updated_at = NOW()
        """,
        product_id,
        mime,
        body,
        len(body),
        str(admin.get("username") or "")[:80],
    )
    await pool.execute(
        "UPDATE products SET image_url = $2, updated_at = NOW() WHERE id = $1",
        product_id,
        f"/admin/api/catalog/products/{product_id}/image",
    )
    log.info(
        "product image saved",
        extra={"action": "catalog.image.save", "entity": f"product:{product_id}"},
    )
    return {"ok": True, "size": len(body), "mime": mime}


@router.get("/products/{product_id}/image")
async def get_product_image(
    product_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> Response:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        "SELECT mime, data FROM product_images WHERE product_id = $1", product_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="no image")
    return Response(
        content=bytes(row["data"]),
        media_type=str(row["mime"] or "image/jpeg"),
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.delete("/products/{product_id}/image")
async def delete_product_image(
    product_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    await pool.execute("DELETE FROM product_images WHERE product_id = $1", product_id)
    await pool.execute(
        "UPDATE products SET image_url = '' WHERE id = $1 AND image_url LIKE '/admin/api/catalog/%'",
        product_id,
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


@router.get("/products")
async def list_products(
    request: Request,
    category: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    conditions: list[str] = []
    args: list[Any] = []
    idx = 1

    if category:
        conditions.append(f"p.category = ${idx}")
        args.append(category)
        idx += 1

    if is_active is not None:
        conditions.append(f"p.is_active = ${idx}")
        args.append(is_active)
        idx += 1

    if search:
        conditions.append(
            f"(p.name_ar ILIKE '%' || ${idx} || '%' "
            f"OR p.name_en ILIKE '%' || ${idx} || '%' "
            f"OR p.code ILIKE '%' || ${idx} || '%' "
            f"OR p.sku ILIKE '%' || ${idx} || '%')"
        )
        args.append(search)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    args.extend([max(0, offset), max(1, min(limit, 200))])

    total = await pool.fetchval(f"SELECT COUNT(*) FROM products p {where}", *args[:-2])
    rows = await pool.fetch(
        f"""
        SELECT p.id, p.sku, p.code, p.name_ar, p.name_en, p.title_en, p.names, p.titles,
               p.category, p.unit, p.unit_price, p.currency, p.image_url, p.sort_order,
               p.stock_qty, p.reorder_point, p.is_active, p.discount_tiers,
               p.created_at, p.updated_at,
               EXISTS (SELECT 1 FROM product_images i WHERE i.product_id = p.id) AS has_image
        FROM products p {where}
        ORDER BY p.sort_order, p.name_en
        OFFSET ${idx} LIMIT ${idx + 1}
        """,
        *args,
    )
    return {
        "total": total,
        "items": [_json_row(r) for r in rows],
        "limit": limit,
        "offset": offset,
    }


def _json_row(record: Any) -> dict[str, Any]:
    """asyncpg returns jsonb as str unless a codec is set — decode for the UI."""
    data = dict(record)
    for key in ("names", "titles", "discount_tiers"):
        raw = data.get(key)
        if isinstance(raw, (str, bytes)) and raw:
            try:
                data[key] = json.loads(raw)
            except (ValueError, TypeError):
                pass
    return data


async def _next_code(pool: Any) -> str:
    """Smallest free numeric customer code ≥ 101."""
    used = {
        str(r["code"]) for r in await pool.fetch("SELECT code FROM products WHERE code IS NOT NULL")
    }
    n = 101
    while str(n) in used:
        n += 1
    return str(n)


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """
        SELECT p.*, s.technical_specs, s.safety_data, s.compliance_notes
        FROM products p
        LEFT JOIN product_specs s ON s.product_id = p.id
        WHERE p.id = $1
        """,
        product_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    return _json_row(row)


@router.post("/products")
async def create_product(
    req: ProductCreate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]

    existing = await pool.fetchval("SELECT id FROM products WHERE sku = $1", req.sku)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"SKU {req.sku!r} already exists")
    code = (req.code or "").strip() or await _next_code(pool)
    code_taken = await pool.fetchval("SELECT id FROM products WHERE code = $1", code)
    if code_taken is not None:
        raise HTTPException(status_code=409, detail=f"product code {code!r} already exists")

    row = await pool.fetchrow(
        """
        INSERT INTO products (
            sku, name_ar, name_en, description_ar, description_en,
            category, unit_price, currency, stock_qty, reorder_point,
            discount_tiers, is_active, code, title_en, names, titles, unit,
            image_url, sort_order
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12,
                  $13, $14, $15::jsonb, $16::jsonb, $17, $18, $19)
        RETURNING id, created_at
        """,
        req.sku,
        req.name_ar or "",
        req.name_en,
        req.description_ar,
        req.description_en,
        req.category,
        req.unit_price,
        req.currency,
        req.stock_qty,
        req.reorder_point,
        json.dumps(req.discount_tiers, ensure_ascii=False),
        req.is_active,
        code,
        req.title_en,
        json.dumps(req.names, ensure_ascii=False),
        json.dumps(req.titles, ensure_ascii=False),
        req.unit,
        req.image_url,
        req.sort_order,
    )
    if req.category:
        await pool.execute(
            """INSERT INTO catalog_categories (key, name_en)
               VALUES ($1, initcap(replace($1, '-', ' '))) ON CONFLICT (key) DO NOTHING""",
            req.category,
        )

    if (
        req.technical_specs is not None
        or req.safety_data is not None
        or req.compliance_notes is not None
    ):
        await pool.execute(
            """
            INSERT INTO product_specs (product_id, technical_specs, safety_data, compliance_notes)
            VALUES ($1, $2::jsonb, $3, $4)
            ON CONFLICT (product_id) DO UPDATE SET
                technical_specs = COALESCE(EXCLUDED.technical_specs, product_specs.technical_specs),
                safety_data = COALESCE(EXCLUDED.safety_data, product_specs.safety_data),
                compliance_notes = COALESCE(EXCLUDED.compliance_notes, product_specs.compliance_notes)
            """,
            row["id"],
            json.dumps(req.technical_specs, ensure_ascii=False)
            if req.technical_specs is not None
            else None,
            req.safety_data,
            req.compliance_notes,
        )

    log.info(
        "product created",
        extra={"action": "catalog.product.create", "entity": f"product:{row['id']}"},
    )

    return {"product_id": row["id"], "code": code, "created_at": str(row["created_at"])}


@router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    req: ProductUpdate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    existing = await pool.fetchval("SELECT id FROM products WHERE id = $1", product_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="product not found")

    sets: list[str] = []
    args: list[Any] = []
    idx = 1

    for field_name in (
        "name_ar",
        "name_en",
        "code",
        "title_en",
        "description_ar",
        "description_en",
        "category",
        "unit",
        "unit_price",
        "currency",
        "image_url",
        "sort_order",
        "stock_qty",
        "reorder_point",
        "is_active",
    ):
        value = getattr(req, field_name)
        if value is not None:
            if field_name == "code":
                value = str(value).strip()
                if not value:
                    continue
                clash = await pool.fetchval(
                    "SELECT id FROM products WHERE code = $1 AND id <> $2", value, product_id
                )
                if clash is not None:
                    raise HTTPException(
                        status_code=409, detail=f"product code {value!r} already exists"
                    )
            sets.append(f"{field_name} = ${idx}")
            args.append(value)
            idx += 1

    for json_field in ("discount_tiers", "names", "titles"):
        value = getattr(req, json_field)
        if value is not None:
            sets.append(f"{json_field} = ${idx}::jsonb")
            args.append(json.dumps(value, ensure_ascii=False))
            idx += 1
    if req.category:
        await pool.execute(
            """INSERT INTO catalog_categories (key, name_en)
               VALUES ($1, initcap(replace($1, '-', ' '))) ON CONFLICT (key) DO NOTHING""",
            req.category,
        )

    if not sets:
        return {"product_id": product_id, "updated_fields": []}

    sets.append("updated_at = NOW()")
    args.append(product_id)

    await pool.execute(
        f"UPDATE products SET {', '.join(sets)} WHERE id = ${idx}",
        *args,
    )

    log.info(
        "product updated",
        extra={"action": "catalog.product.update", "entity": f"product:{product_id}"},
    )

    return {
        "product_id": product_id,
        "updated_fields": [s.split(" =")[0] for s in sets if "updated_at" not in s],
    }


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    result = await pool.execute(
        "UPDATE products SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
        product_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="product not found")

    log.info(
        "product soft-deleted",
        extra={"action": "catalog.product.delete", "entity": f"product:{product_id}"},
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Stock management
# ---------------------------------------------------------------------------


@router.post("/products/{product_id}/stock")
async def update_stock(
    product_id: str,
    request: Request,
    quantity: int = 0,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT id, stock_qty FROM products WHERE id = $1", product_id)
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")

    new_qty = max(0, row["stock_qty"] + quantity)
    await pool.execute(
        "UPDATE products SET stock_qty = $1, updated_at = NOW() WHERE id = $2",
        new_qty,
        product_id,
    )

    log.info(
        "stock updated",
        extra={
            "action": "catalog.stock.update",
            "entity": f"product:{product_id}",
            "old": row["stock_qty"],
            "new": new_qty,
            "delta": quantity,
        },
    )

    return {
        "product_id": product_id,
        "previous_qty": row["stock_qty"],
        "new_qty": new_qty,
        "delta": quantity,
    }


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------


@router.get("/faq")
async def list_faq(
    request: Request,
    category: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    conditions: list[str] = []
    args: list[Any] = []
    idx = 1

    if category:
        conditions.append(f"category = ${idx}")
        args.append(category)
        idx += 1
    if search:
        conditions.append(
            f"(question_ar ILIKE '%' || ${idx} || '%' "
            f"OR answer_ar ILIKE '%' || ${idx} || '%' "
            f"OR question_en ILIKE '%' || ${idx} || '%')"
        )
        args.append(search)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    total = await pool.fetchval(f"SELECT COUNT(*) FROM faq {where}", *args)
    args.extend([max(0, offset), max(1, min(limit, 200))])

    rows = await pool.fetch(
        f"""
        SELECT id, question_ar, question_en, answer_ar, answer_en,
               category, language, created_at
        FROM faq {where}
        ORDER BY category, id
        OFFSET ${idx} LIMIT ${idx + 1}
        """,
        *args,
    )
    return {"total": total, "items": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.post("/faq")
async def create_faq(
    req: FAQCreate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """
        INSERT INTO faq (question_ar, question_en, answer_ar, answer_en, category, language)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at
        """,
        req.question_ar,
        req.question_en,
        req.answer_ar,
        req.answer_en,
        req.category,
        req.language,
    )
    log.info("faq created", extra={"action": "catalog.faq.create", "entity": f"faq:{row['id']}"})
    return {"faq_id": row["id"], "created_at": str(row["created_at"])}


@router.delete("/faq/{faq_id}")
async def delete_faq(
    faq_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM faq WHERE id = $1", faq_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="faq not found")

    log.info("faq deleted", extra={"action": "catalog.faq.delete", "entity": f"faq:{faq_id}"})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Troubleshooting
# ---------------------------------------------------------------------------


@router.get("/troubleshooting")
async def list_troubleshooting(
    request: Request,
    category: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    conditions: list[str] = []
    args: list[Any] = []
    idx = 1

    if category:
        conditions.append(f"category = ${idx}")
        args.append(category)
        idx += 1
    if search:
        conditions.append(
            f"(title_ar ILIKE '%' || ${idx} || '%' "
            f"OR problem_ar ILIKE '%' || ${idx} || '%' "
            f"OR title_en ILIKE '%' || ${idx} || '%')"
        )
        args.append(search)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    total = await pool.fetchval(f"SELECT COUNT(*) FROM troubleshooting {where}", *args)
    args.extend([max(0, offset), max(1, min(limit, 200))])

    rows = await pool.fetch(
        f"""
        SELECT id, title_ar, title_en, problem_ar, problem_en,
               solution_ar, solution_en, category, severity, created_at
        FROM troubleshooting {where}
        ORDER BY severity DESC, title_en
        OFFSET ${idx} LIMIT ${idx + 1}
        """,
        *args,
    )
    return {"total": total, "items": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.post("/troubleshooting")
async def create_troubleshooting(
    req: TroubleshootingCreate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """
        INSERT INTO troubleshooting (
            title_ar, title_en, problem_ar, problem_en,
            solution_ar, solution_en, category, severity
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, created_at
        """,
        req.title_ar,
        req.title_en,
        req.problem_ar,
        req.problem_en,
        req.solution_ar,
        req.solution_en,
        req.category,
        req.severity,
    )
    log.info(
        "troubleshooting created",
        extra={
            "action": "catalog.troubleshooting.create",
            "entity": f"troubleshooting:{row['id']}",
        },
    )
    return {"article_id": row["id"], "created_at": str(row["created_at"])}


@router.delete("/troubleshooting/{article_id}")
async def delete_troubleshooting(
    article_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM troubleshooting WHERE id = $1", article_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="article not found")

    log.info(
        "troubleshooting deleted",
        extra={
            "action": "catalog.troubleshooting.delete",
            "entity": f"troubleshooting:{article_id}",
        },
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# MSDS documents
# ---------------------------------------------------------------------------


@router.get("/msds")
async def list_msds(
    request: Request,
    product_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    conditions: list[str] = []
    args: list[Any] = []
    idx = 1

    if product_id is not None:
        conditions.append(f"d.product_id = ${idx}")
        args.append(product_id)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    total = await pool.fetchval(f"SELECT COUNT(*) FROM msds_documents d {where}", *args)
    args.extend([max(0, offset), max(1, min(limit, 200))])

    rows = await pool.fetch(
        f"""
        SELECT d.id, d.product_id, d.title_ar, d.title_en, d.r2_key,
               d.version, d.language, d.created_at,
               p.name_ar AS product_name_ar, p.name_en AS product_name_en
        FROM msds_documents d
        LEFT JOIN products p ON p.id = d.product_id
        {where}
        ORDER BY d.created_at DESC
        OFFSET ${idx} LIMIT ${idx + 1}
        """,
        *args,
    )
    return {"total": total, "items": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.post("/msds")
async def create_msds(
    req: MSDSCreate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    existing = await pool.fetchval("SELECT id FROM products WHERE id = $1", req.product_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="product not found")

    row = await pool.fetchrow(
        """
        INSERT INTO msds_documents (product_id, title_ar, title_en, r2_key, version, language)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at
        """,
        req.product_id,
        req.title_ar,
        req.title_en,
        req.r2_key,
        req.version,
        req.language,
    )
    log.info("msds created", extra={"action": "catalog.msds.create", "entity": f"msds:{row['id']}"})
    return {"msds_id": row["id"], "created_at": str(row["created_at"])}


@router.delete("/msds/{msds_id}")
async def delete_msds(
    msds_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, bool]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM msds_documents WHERE id = $1", msds_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="msds document not found")

    log.info("msds deleted", extra={"action": "catalog.msds.delete", "entity": f"msds:{msds_id}"})
    return {"ok": True}
