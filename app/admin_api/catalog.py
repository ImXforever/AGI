"""Admin catalog management endpoints: products, categories, stock, discounts."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_superadmin, require_writer
from app.logging_setup import get_logger

log = get_logger("app.admin_api.catalog")

router = APIRouter(prefix="/catalog", tags=["admin-catalog"])


class ProductCreate(BaseModel):
    sku: str
    name_ar: str
    name_en: str
    description_ar: str = ""
    description_en: str = ""
    category: str = ""
    unit_price: float = Field(..., gt=0)
    currency: str = "SAR"
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
    description_ar: str | None = None
    description_en: str | None = None
    category: str | None = None
    unit_price: float | None = None
    stock_qty: int | None = None
    reorder_point: int | None = None
    discount_tiers: list[dict[str, Any]] | None = None
    is_active: bool | None = None


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
            f"OR p.sku ILIKE '%' || ${idx} || '%')"
        )
        args.append(search)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    args.extend([max(0, offset), max(1, min(limit, 200))])

    total = await pool.fetchval(f"SELECT COUNT(*) FROM products p {where}", *args[:-2])
    rows = await pool.fetch(
        f"""
        SELECT p.id, p.sku, p.name_ar, p.name_en, p.category,
               p.unit_price, p.currency, p.stock_qty, p.reorder_point,
               p.is_active, p.discount_tiers, p.created_at, p.updated_at
        FROM products p {where}
        ORDER BY p.name_en
        OFFSET ${idx} LIMIT ${idx + 1}
        """,
        *args,
    )
    return {
        "total": total,
        "items": [dict(r) for r in rows],
        "limit": limit,
        "offset": offset,
    }


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
    return dict(row)


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

    row = await pool.fetchrow(
        """
        INSERT INTO products (
            sku, name_ar, name_en, description_ar, description_en,
            category, unit_price, currency, stock_qty, reorder_point,
            discount_tiers, is_active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12)
        RETURNING id, created_at
        """,
        req.sku,
        req.name_ar,
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

    return {"product_id": row["id"], "created_at": str(row["created_at"])}


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
        "description_ar",
        "description_en",
        "category",
        "unit_price",
        "stock_qty",
        "reorder_point",
        "is_active",
    ):
        value = getattr(req, field_name)
        if value is not None:
            sets.append(f"{field_name} = ${idx}")
            args.append(value)
            idx += 1

    if req.discount_tiers is not None:
        sets.append(f"discount_tiers = ${idx}::jsonb")
        args.append(json.dumps(req.discount_tiers, ensure_ascii=False))
        idx += 1

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
