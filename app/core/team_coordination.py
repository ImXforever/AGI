"""Team task coordination system (v19).

Assign tasks to team members, track progress, cross-link related tasks,
and auto-escalate stale tasks.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.team_coordination")


class TeamTaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


class TeamTaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TeamTask:
    id: str
    title: str
    description: str
    assignee: str
    department: str
    priority: TeamTaskPriority
    status: TeamTaskStatus
    created_by: str
    created_at: float
    due_at: float
    completed_at: float | None
    cross_links: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    escalated_at: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "department": self.department,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "due_at": self.due_at,
            "completed_at": self.completed_at,
            "cross_links": self.cross_links,
            "notes": self.notes,
            "escalated_at": self.escalated_at,
        }

    def to_text(self) -> str:
        import datetime

        due = datetime.datetime.fromtimestamp(self.due_at).strftime("%Y-%m-%d %H:%M")
        return (
            f"[{self.priority.value.upper()}] {self.title}\n"
            f"  Assignee: {self.assignee}\n"
            f"  Department: {self.department}\n"
            f"  Status: {self.status.value}\n"
            f"  Due: {due}"
        )


def _gen_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


def create_team_task(
    title: str,
    description: str,
    assignee: str,
    department: str,
    *,
    priority: str = "normal",
    created_by: str = "admin",
    due_hours: int = 24,
    cross_links: list[str] | None = None,
) -> TeamTask:
    """Create a new team task."""
    now = time.time()
    return TeamTask(
        id=_gen_id(),
        title=title,
        description=description,
        assignee=assignee,
        department=department,
        priority=TeamTaskPriority(priority),
        status=TeamTaskStatus.PENDING,
        created_by=created_by,
        created_at=now,
        due_at=now + due_hours * 3600,
        completed_at=None,
        cross_links=cross_links or [],
    )


def assign_task(task: TeamTask, assignee: str, department: str = "") -> TeamTask:
    """Reassign a task to a different team member."""
    task.assignee = assignee
    if department:
        task.department = department
    return task


def start_task(task: TeamTask) -> TeamTask:
    """Mark a task as in progress."""
    task.status = TeamTaskStatus.IN_PROGRESS
    return task


def complete_task(task: TeamTask) -> TeamTask:
    """Mark a task as completed."""
    task.status = TeamTaskStatus.COMPLETED
    task.completed_at = time.time()
    return task


def block_task(task: TeamTask, note: str = "") -> TeamTask:
    """Mark a task as blocked."""
    task.status = TeamTaskStatus.BLOCKED
    if note:
        task.notes.append(f"[{time.strftime('%Y-%m-%d %H:%M')}] BLOCKED: {note}")
    return task


def review_task(task: TeamTask) -> TeamTask:
    """Mark a task as in review."""
    task.status = TeamTaskStatus.REVIEW
    return task


def escalate_task(task: TeamTask, note: str = "") -> TeamTask:
    """Escalate a task to management."""
    task.status = TeamTaskStatus.ESCALATED
    task.escalated_at = time.time()
    if note:
        task.notes.append(f"[{time.strftime('%Y-%m-%d %H:%M')}] ESCALATED: {note}")
    return task


def add_note(task: TeamTask, note: str) -> TeamTask:
    """Add a note to a task."""
    task.notes.append(f"[{time.strftime('%Y-%m-%d %H:%M')}] {note}")
    return task


def cross_link(task_a: TeamTask, task_b: TeamTask) -> tuple[TeamTask, TeamTask]:
    """Cross-link two related tasks."""
    if task_b.id not in task_a.cross_links:
        task_a.cross_links.append(task_b.id)
    if task_a.id not in task_b.cross_links:
        task_b.cross_links.append(task_a.id)
    return task_a, task_b


def is_stale(task: TeamTask, grace_hours: int = 24) -> bool:
    """Check if a task is overdue (stale)."""
    if task.status in (TeamTaskStatus.COMPLETED, TeamTaskStatus.ESCALATED):
        return False
    return time.time() > task.due_at + grace_hours * 3600


def get_stale_tasks(tasks: list[TeamTask], grace_hours: int = 24) -> list[TeamTask]:
    """Get all stale (overdue) tasks."""
    return [t for t in tasks if is_stale(t, grace_hours)]


def get_tasks_by_assignee(tasks: list[TeamTask], assignee: str) -> list[TeamTask]:
    """Get tasks assigned to a specific person."""
    return [t for t in tasks if t.assignee == assignee and t.status != TeamTaskStatus.COMPLETED]


def get_tasks_by_department(tasks: list[TeamTask], department: str) -> list[TeamTask]:
    """Get tasks for a specific department."""
    return [t for t in tasks if t.department == department and t.status != TeamTaskStatus.COMPLETED]


def get_team_overview(tasks: list[TeamTask]) -> dict[str, Any]:
    """Get a summary overview of all team tasks."""
    active = [
        t for t in tasks if t.status not in (TeamTaskStatus.COMPLETED, TeamTaskStatus.ESCALATED)
    ]
    overdue = get_stale_tasks(tasks)
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    by_assignee: dict[str, int] = {}
    for t in active:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1
        by_assignee[t.assignee] = by_assignee.get(t.assignee, 0) + 1
    return {
        "total_active": len(active),
        "total_overdue": len(overdue),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_assignee": by_assignee,
    }
