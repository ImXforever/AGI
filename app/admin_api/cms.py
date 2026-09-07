"""CMS API endpoints (v19)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.cms")

router = APIRouter(prefix="/cms", tags=["admin-cms"])


class PageCreate(BaseModel):
    title: str
    content: str
    slug: str = ""
    meta_description: str = ""
    meta_keywords: str = ""


class PageUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    note: str = ""


@router.get("/pages")
async def list_pages(
    request: Request,
    status: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    if status:
        rows = await pool.fetch(
            "SELECT * FROM cms_pages WHERE status = $1 ORDER BY updated_at DESC", status
        )
    else:
        rows = await pool.fetch("SELECT * FROM cms_pages ORDER BY updated_at DESC LIMIT 100")
    return {"pages": [dict(r) for r in rows], "count": len(rows)}


@router.post("/pages")
async def create_page_endpoint(
    request: Request,
    body: PageCreate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    import json

    from app.core.cms import create_page

    page = create_page(
        title=body.title,
        content=body.content,
        slug=body.slug,
        created_by=admin.get("username", "admin"),
        meta_description=body.meta_description,
        meta_keywords=body.meta_keywords,
    )
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO cms_pages (id, title, slug, content, status, created_by, created_at, updated_at, meta_description, meta_keywords, versions)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """,
        page.id,
        page.title,
        page.slug,
        page.content,
        page.status.value,
        page.created_by,
        page.created_at,
        page.updated_at,
        page.meta_description,
        page.meta_keywords,
        json.dumps([v.as_dict() for v in page.versions]),
    )
    return page.as_dict()


@router.get("/pages/{page_id}")
async def get_page(
    request: Request,
    page_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM cms_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    return dict(row)


@router.put("/pages/{page_id}")
async def update_page_endpoint(
    request: Request,
    page_id: str,
    body: PageUpdate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM cms_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    if body.title is not None:
        updates.append(f"title = ${idx}")
        params.append(body.title)
        idx += 1
    if body.content is not None:
        updates.append(f"content = ${idx}")
        params.append(body.content)
        idx += 1
    if body.meta_description is not None:
        updates.append(f"meta_description = ${idx}")
        params.append(body.meta_description)
        idx += 1
    if body.meta_keywords is not None:
        updates.append(f"meta_keywords = ${idx}")
        params.append(body.meta_keywords)
        idx += 1
    if updates:
        updates.append(f"updated_at = ${idx}")
        params.append(time.time())
        idx += 1
        params.append(page_id)
        await pool.execute(f"UPDATE cms_pages SET {', '.join(updates)} WHERE id = ${idx}", *params)
    return {"id": page_id, "updated": True}


@router.post("/pages/{page_id}/publish")
async def publish_page_endpoint(
    request: Request,
    page_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM cms_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    await pool.execute(
        "UPDATE cms_pages SET status = 'published', published_at = $1, updated_at = $1 WHERE id = $2",
        time.time(),
        page_id,
    )
    return {"id": page_id, "status": "published"}


@router.post("/pages/{page_id}/archive")
async def archive_page_endpoint(
    request: Request,
    page_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("UPDATE cms_pages SET status = 'archived' WHERE id = $1", page_id)
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Page not found")
    return {"id": page_id, "status": "archived"}


@router.delete("/pages/{page_id}")
async def delete_page_endpoint(
    request: Request,
    page_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM cms_pages WHERE id = $1", page_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Page not found")
    return {"id": page_id, "deleted": True}


@router.get("/pages/{page_id}/preview")
async def preview_page_endpoint(
    request: Request,
    page_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM cms_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(status_code=404, detail="Page not found")
    from app.core.cms import Page, PageStatus

    page = Page(
        id=row["id"],
        title=row["title"],
        slug=row["slug"],
        content=row["content"],
        status=PageStatus(row["status"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row.get("published_at"),
        meta_description=row.get("meta_description", ""),
        meta_keywords=row.get("meta_keywords", ""),
    )
    return {"html": page.to_html()}
