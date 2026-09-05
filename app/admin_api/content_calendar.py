"""Content calendar CRUD API endpoints (v18)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.content_calendar")

router = APIRouter(prefix="/content", tags=["admin-content-calendar"])


class ContentPostCreate(BaseModel):
    title: str
    caption: str
    platform: str
    scheduled_at: float
    media_url: str = ""
    hashtags: list[str] = []
    notes: str = ""


class ContentPostUpdate(BaseModel):
    title: str | None = None
    caption: str | None = None
    scheduled_at: float | None = None
    media_url: str | None = None
    hashtags: list[str] | None = None
    notes: str | None = None


@router.get("/")
async def list_posts(
    request: Request,
    platform: str = "",
    status: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    query = "SELECT * FROM content_calendar WHERE 1=1"
    params: list[Any] = []
    idx = 1
    if platform:
        query += f" AND platform = ${idx}"
        params.append(platform)
        idx += 1
    if status:
        query += f" AND status = ${idx}"
        params.append(status)
        idx += 1
    query += " ORDER BY scheduled_at ASC LIMIT 100"
    rows = await pool.fetch(query, *params)
    return {"posts": [dict(r) for r in rows], "count": len(rows)}


@router.post("/")
async def create_post(
    request: Request,
    body: ContentPostCreate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    import json

    from app.core.content_calendar import create_calendar_post

    post = create_calendar_post(
        title=body.title,
        caption=body.caption,
        platform=body.platform,
        scheduled_at=body.scheduled_at,
        media_url=body.media_url,
        hashtags=body.hashtags,
        created_by=admin.get("username", "admin"),
        notes=body.notes,
    )
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO content_calendar (id, title, caption, platform, scheduled_at, status, created_at, media_url, hashtags, created_by, notes)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """,
        post.id,
        post.title,
        post.caption,
        post.platform.value,
        post.scheduled_at,
        post.status.value,
        post.created_at,
        post.media_url,
        json.dumps(list(post.hashtags)),
        post.created_by,
        post.notes,
    )
    return post.as_dict()


@router.get("/{post_id}")
async def get_post(
    request: Request,
    post_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM content_calendar WHERE id = $1", post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return dict(row)


@router.put("/{post_id}")
async def update_post(
    request: Request,
    post_id: str,
    body: ContentPostUpdate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM content_calendar WHERE id = $1", post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    if body.title is not None:
        updates.append(f"title = ${idx}")
        params.append(body.title)
        idx += 1
    if body.caption is not None:
        updates.append(f"caption = ${idx}")
        params.append(body.caption)
        idx += 1
    if body.scheduled_at is not None:
        updates.append(f"scheduled_at = ${idx}")
        params.append(body.scheduled_at)
        idx += 1
    if body.media_url is not None:
        updates.append(f"media_url = ${idx}")
        params.append(body.media_url)
        idx += 1
    if body.notes is not None:
        updates.append(f"notes = ${idx}")
        params.append(body.notes)
        idx += 1
    if updates:
        params.append(post_id)
        await pool.execute(
            f"UPDATE content_calendar SET {', '.join(updates)} WHERE id = ${idx}", *params
        )
    return {"id": post_id, "updated": True}


@router.post("/{post_id}/cancel")
async def cancel_post(
    request: Request,
    post_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute(
        "UPDATE content_calendar SET status = 'cancelled' WHERE id = $1", post_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Post not found")
    return {"id": post_id, "status": "cancelled"}


@router.delete("/{post_id}")
async def delete_post(
    request: Request,
    post_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM content_calendar WHERE id = $1", post_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Post not found")
    return {"id": post_id, "deleted": True}


@router.get("/upcoming/list")
async def upcoming_posts(
    request: Request,
    hours: int = 24,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    cutoff = time.time() + hours * 3600
    rows = await pool.fetch(
        "SELECT * FROM content_calendar WHERE status = 'scheduled' AND scheduled_at <= $1 ORDER BY scheduled_at",
        cutoff,
    )
    return {"posts": [dict(r) for r in rows], "count": len(rows)}
