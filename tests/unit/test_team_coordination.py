"""Tests for v19 team coordination."""

from __future__ import annotations

from app.core.team_coordination import (
    TeamTaskPriority,
    TeamTaskStatus,
    add_note,
    assign_task,
    block_task,
    complete_task,
    create_team_task,
    cross_link,
    escalate_task,
    get_stale_tasks,
    get_tasks_by_assignee,
    get_tasks_by_department,
    get_team_overview,
    is_stale,
    review_task,
    start_task,
)


class TestTeamTaskCreation:
    def test_create_basic(self):
        task = create_team_task("Fix bug", "Fix login issue", "alice", "engineering")
        assert task.status == TeamTaskStatus.PENDING
        assert task.assignee == "alice"
        assert task.department == "engineering"

    def test_create_with_priority(self):
        task = create_team_task("Urgent fix", "Fix crash", "bob", "engineering", priority="urgent")
        assert task.priority == TeamTaskPriority.URGENT

    def test_create_with_cross_links(self):
        task = create_team_task("Task", "Desc", "alice", "eng", cross_links=["task-1", "task-2"])
        assert len(task.cross_links) == 2


class TestTeamTaskStatus:
    def test_start_task(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = start_task(task)
        assert task.status == TeamTaskStatus.IN_PROGRESS

    def test_complete_task(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = complete_task(task)
        assert task.status == TeamTaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_block_task(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = block_task(task, note="Waiting for API key")
        assert task.status == TeamTaskStatus.BLOCKED
        assert len(task.notes) == 1

    def test_review_task(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = review_task(task)
        assert task.status == TeamTaskStatus.REVIEW

    def test_escalate_task(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = escalate_task(task, note="Critical issue")
        assert task.status == TeamTaskStatus.ESCALATED
        assert task.escalated_at is not None


class TestTeamTaskAssignment:
    def test_assign_task(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = assign_task(task, "bob", "design")
        assert task.assignee == "bob"
        assert task.department == "design"


class TestTeamTaskNotes:
    def test_add_note(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        task = add_note(task, "Progress update")
        assert len(task.notes) == 1


class TestTeamCrossLink:
    def test_cross_link(self):
        t1 = create_team_task("Task 1", "Desc", "alice", "eng")
        t2 = create_team_task("Task 2", "Desc", "bob", "design")
        t1, t2 = cross_link(t1, t2)
        assert t2.id in t1.cross_links
        assert t1.id in t2.cross_links


class TestTeamStaleness:
    def test_is_stale(self):
        task = create_team_task("Task", "Desc", "alice", "eng", due_hours=-24)
        assert is_stale(task)

    def test_not_stale_when_completed(self):
        task = create_team_task("Task", "Desc", "alice", "eng", due_hours=-24)
        task = complete_task(task)
        assert not is_stale(task)

    def test_get_stale_tasks(self):
        t1 = create_team_task("T1", "D", "a", "eng", due_hours=-48)
        t2 = create_team_task("T2", "D", "b", "eng", due_hours=24)
        stale = get_stale_tasks([t1, t2])
        assert len(stale) == 1


class TestTeamFiltering:
    def test_get_by_assignee(self):
        t1 = create_team_task("T1", "D", "alice", "eng")
        t2 = create_team_task("T2", "D", "bob", "eng")
        result = get_tasks_by_assignee([t1, t2], "alice")
        assert len(result) == 1

    def test_get_by_department(self):
        t1 = create_team_task("T1", "D", "alice", "eng")
        t2 = create_team_task("T2", "D", "bob", "design")
        result = get_tasks_by_department([t1, t2], "eng")
        assert len(result) == 1


class TestTeamOverview:
    def test_overview(self):
        t1 = create_team_task("T1", "D", "alice", "eng")
        t2 = create_team_task("T2", "D", "bob", "design")
        overview = get_team_overview([t1, t2])
        assert overview["total_active"] == 2
        assert "by_assignee" in overview
        assert "by_priority" in overview


class TestTeamTaskSerialization:
    def test_as_dict(self):
        task = create_team_task("Task", "Desc", "alice", "eng")
        d = task.as_dict()
        assert "id" in d
        assert "assignee" in d
        assert d["assignee"] == "alice"

    def test_to_text(self):
        task = create_team_task("Task", "Desc", "alice", "engineering")
        text = task.to_text()
        assert "Task" in text
        assert "alice" in text
