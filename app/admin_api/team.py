"""Team coordination API endpoints (v19)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.team")

router = APIRouter(prefix="/team", tags=["admin-team"])


class TeamTaskCreate(BaseModel):
    title: str
    description: str
    assignee: str
    department: str
    priority: str = "normal"
    due_hours: int = 24
    cross_links: list[str] = []


class TeamTaskUpdate(BaseModel):
    status: str | None = None
    assignee: str | None = None
    priority: str | None = None
    note: str = ""


@router.get("/tasks")
async def list_tasks(
    request: Request,
    assignee: str = "",
    department: str = "",
    status: str = "",
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    query = "SELECT * FROM team_tasks WHERE 1=1"
    params: list[Any] = []
    idx = 1
    if assignee:
        query += f" AND assignee = ${idx}"
        params.append(assignee)
        idx += 1
    if department:
        query += f" AND department = ${idx}"
        params.append(department)
        idx += 1
    if status:
        query += f" AND status = ${idx}"
        params.append(status)
        idx += 1
    query += " ORDER BY created_at DESC LIMIT 100"
    rows = await pool.fetch(query, *params)
    return {"tasks": [dict(r) for r in rows], "count": len(rows)}


@router.post("/tasks")
async def create_task_endpoint(
    request: Request,
    body: TeamTaskCreate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    import hashlib
    import json
    import os

    now = time.time()
    task_id = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
    pool = request.app.state.services["pg"]
    await pool.execute(
        """
        INSERT INTO team_tasks (id, title, description, assignee, department, priority, status, created_by, created_at, due_at, cross_links, notes)
        VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7, $8, $9, $10, $11)
    """,
        task_id,
        body.title,
        body.description,
        body.assignee,
        body.department,
        body.priority,
        admin.get("username", "admin"),
        now,
        now + body.due_hours * 3600,
        json.dumps(body.cross_links),
        json.dumps([]),
    )
    return {"id": task_id, "created": True}


@router.get("/tasks/{task_id}")
async def get_task(
    request: Request,
    task_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM team_tasks WHERE id = $1", task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)


@router.put("/tasks/{task_id}")
async def update_task_endpoint(
    request: Request,
    task_id: str,
    body: TeamTaskUpdate,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow("SELECT * FROM team_tasks WHERE id = $1", task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    updates: list[str] = []
    params: list[Any] = []
    idx = 1
    if body.status is not None:
        updates.append(f"status = ${idx}")
        params.append(body.status)
        idx += 1
        if body.status == "completed":
            updates.append(f"completed_at = ${idx}")
            params.append(time.time())
            idx += 1
    if body.assignee is not None:
        updates.append(f"assignee = ${idx}")
        params.append(body.assignee)
        idx += 1
    if body.priority is not None:
        updates.append(f"priority = ${idx}")
        params.append(body.priority)
        idx += 1
    if updates:
        params.append(task_id)
        await pool.execute(f"UPDATE team_tasks SET {', '.join(updates)} WHERE id = ${idx}", *params)
    return {"id": task_id, "updated": True}


@router.post("/tasks/{task_id}/escalate")
async def escalate_task_endpoint(
    request: Request,
    task_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute(
        "UPDATE team_tasks SET status = 'escalated', escalated_at = $1 WHERE id = $2",
        time.time(),
        task_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": "escalated"}


@router.get("/overview")
async def team_overview(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    rows = await pool.fetch("SELECT * FROM team_tasks WHERE status != 'completed' ORDER BY due_at")
    tasks = [dict(r) for r in rows]
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    by_assignee: dict[str, int] = {}
    overdue = 0
    for t in tasks:
        s = t.get("status", "")
        by_status[s] = by_status.get(s, 0) + 1
        p = t.get("priority", "")
        by_priority[p] = by_priority.get(p, 0) + 1
        a = t.get("assignee", "")
        by_assignee[a] = by_assignee.get(a, 0) + 1
        if t.get("due_at", 0) < time.time() and s not in ("completed", "escalated"):
            overdue += 1
    return {
        "total_active": len(tasks),
        "total_overdue": overdue,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_assignee": by_assignee,
    }


@router.delete("/tasks/{task_id}")
async def delete_task_endpoint(
    request: Request,
    task_id: str,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    result = await pool.execute("DELETE FROM team_tasks WHERE id = $1", task_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "deleted": True}
