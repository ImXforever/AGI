"""Tests for v17 reminder system."""

from __future__ import annotations

import time

from app.core.reminder import (
    ReminderStatus,
    RepeatInterval,
    cancel_reminder,
    create_reminder,
    format_reminder_text,
    get_due_reminders,
    get_user_reminders,
    is_due,
    snooze_reminder,
    trigger_reminder,
)


class TestReminderCreation:
    def test_create_basic(self):
        r = create_reminder("user1", "Test", "Message", time.time() + 3600)
        assert r.status == ReminderStatus.ACTIVE
        assert r.user_id == "user1"
        assert r.title == "Test"

    def test_create_with_repeat(self):
        r = create_reminder("user1", "Daily", "Msg", time.time(), repeat=RepeatInterval.DAILY)
        assert r.repeat == RepeatInterval.DAILY

    def test_create_with_channel(self):
        r = create_reminder("user1", "Test", "Msg", time.time(), channel="email")
        assert r.channel == "email"


class TestReminderLogic:
    def test_is_due_when_past(self):
        r = create_reminder("user1", "Test", "Msg", time.time() - 100)
        assert is_due(r)

    def test_is_not_due_when_future(self):
        r = create_reminder("user1", "Test", "Msg", time.time() + 3600)
        assert not is_due(r)

    def test_is_not_due_when_completed(self):
        r = create_reminder("user1", "Test", "Msg", time.time() - 100)
        r.status = ReminderStatus.COMPLETED
        assert not is_due(r)

    def test_trigger_none_completes(self):
        r = create_reminder("user1", "Test", "Msg", time.time() - 100)
        r = trigger_reminder(r)
        assert r.status == ReminderStatus.COMPLETED
        assert r.trigger_count == 1

    def test_trigger_daily_schedules_next(self):
        r = create_reminder("user1", "Test", "Msg", time.time() - 100, repeat=RepeatInterval.DAILY)
        r = trigger_reminder(r)
        assert r.status == ReminderStatus.ACTIVE
        assert r.due_at > time.time()

    def test_snooze(self):
        r = create_reminder("user1", "Test", "Msg", time.time() - 100)
        r = snooze_reminder(r, minutes=30)
        assert r.status == ReminderStatus.SNOOZED
        assert r.snooze_until is not None

    def test_cancel(self):
        r = create_reminder("user1", "Test", "Msg", time.time() + 3600)
        r = cancel_reminder(r)
        assert r.status == ReminderStatus.CANCELLED


class TestReminderFormat:
    def test_format_text(self):
        r = create_reminder("user1", "Meeting", "Team standup", time.time() + 3600)
        text = format_reminder_text(r)
        assert "Meeting" in text
        assert "Team standup" in text

    def test_format_with_repeat(self):
        r = create_reminder("user1", "Daily", "Msg", time.time(), repeat=RepeatInterval.WEEKLY)
        text = format_reminder_text(r)
        assert "weekly" in text


class TestReminderFiltering:
    def test_get_due(self):
        r1 = create_reminder("u1", "T1", "M1", time.time() - 100)
        r2 = create_reminder("u2", "T2", "M2", time.time() + 3600)
        due = get_due_reminders([r1, r2])
        assert len(due) == 1
        assert due[0].title == "T1"

    def test_get_user_reminders(self):
        r1 = create_reminder("user1", "T1", "M1", time.time() + 3600)
        r2 = create_reminder("user2", "T2", "M2", time.time() + 3600)
        result = get_user_reminders([r1, r2], "user1")
        assert len(result) == 1
        assert result[0].user_id == "user1"


class TestReminderSerialization:
    def test_as_dict(self):
        r = create_reminder("user1", "Test", "Msg", time.time())
        d = r.as_dict()
        assert "id" in d
        assert "user_id" in d
        assert "title" in d
        assert "status" in d
