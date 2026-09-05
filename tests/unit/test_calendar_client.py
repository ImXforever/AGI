"""Tests for v17 calendar client."""

from __future__ import annotations

import pytest

from app.core.calendar_client import CalendarClient, CalendarEvent


class TestCalendarClientMock:
    @pytest.mark.asyncio
    async def test_get_today_schedule(self):
        client = CalendarClient(mock_mode=True)
        events = await client.get_today_schedule()
        assert len(events) >= 1
        assert events[0].summary != ""

    @pytest.mark.asyncio
    async def test_get_week_schedule(self):
        client = CalendarClient(mock_mode=True)
        events = await client.get_week_schedule()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_create_event(self):
        client = CalendarClient(mock_mode=True)
        event = await client.create_event(
            summary="Test Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            description="Test description",
            location="Room A",
            attendees=["alice@test.com"],
        )
        assert event.summary == "Test Meeting"
        assert event.location == "Room A"
        assert "alice@test.com" in event.attendees

    @pytest.mark.asyncio
    async def test_delete_event(self):
        client = CalendarClient(mock_mode=True)
        event = await client.create_event("Delete Me", "2025-06-15T10:00:00", "2025-06-15T11:00:00")
        result = await client.delete_event(event.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_sync_tasks_to_calendar(self):
        client = CalendarClient(mock_mode=True)
        tasks = [
            {"title": "Task 1", "due_date": "2025-06-15T09:00:00", "description": "First task"},
            {"title": "Task 2", "due_date": "2025-06-16T09:00:00"},
            {"title": "Task 3"},  # no due_date, should be skipped
        ]
        events = await client.sync_tasks_to_calendar(tasks)
        assert len(events) == 2


class TestCalendarEvent:
    def test_as_dict(self):
        event = CalendarEvent(
            id="test-1",
            summary="Meeting",
            description="Desc",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            location="Room A",
            attendees=("alice@test.com", "bob@test.com"),
            status="confirmed",
            html_link="",
        )
        d = event.as_dict()
        assert d["summary"] == "Meeting"
        assert len(d["attendees"]) == 2

    def test_to_text(self):
        event = CalendarEvent(
            id="test-2",
            summary="Team Call",
            description="Weekly sync",
            start_time="2025-06-15T14:00:00",
            end_time="2025-06-15T15:00:00",
            location="Zoom",
            attendees=("alice@test.com",),
            status="confirmed",
            html_link="",
        )
        text = event.to_text()
        assert "Team Call" in text
        assert "Zoom" in text
        assert "alice@test.com" in text


class TestCalendarClientSingleton:
    def test_get_singleton(self):
        from app.core.calendar_client import get_calendar_client

        c1 = get_calendar_client()
        c2 = get_calendar_client()
        assert c1 is c2
