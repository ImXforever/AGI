"""Google Calendar API client (v17).

Provides read/write access to Google Calendar for task syncing,
meeting creation, and schedule queries.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.calendar_client")


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    summary: str
    description: str
    start_time: str
    end_time: str
    location: str
    attendees: tuple[str, ...]
    status: str
    html_link: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location": self.location,
            "attendees": list(self.attendees),
            "status": self.status,
            "html_link": self.html_link,
        }

    def to_text(self) -> str:
        attendees_str = ", ".join(self.attendees) if self.attendees else "None"
        return (
            f"{self.summary}\n"
            f"  Start: {self.start_time}\n"
            f"  End: {self.end_time}\n"
            f"  Location: {self.location or 'N/A'}\n"
            f"  Attendees: {attendees_str}\n"
            f"  Status: {self.status}"
        )


@dataclass
class CalendarClient:
    """Google Calendar client.

    In production, this uses the Google Calendar API v3.
    In mock mode, it returns simulated data.
    """

    credentials_json: str = ""
    calendar_id: str = "primary"
    mock_mode: bool = True
    _events: list[CalendarEvent] = field(default_factory=list)

    async def get_today_schedule(self) -> list[CalendarEvent]:
        """Get today's events from the calendar."""
        if self.mock_mode:
            return self._mock_today()
        return await self._fetch_events_today()

    async def get_week_schedule(self) -> list[CalendarEvent]:
        """Get this week's events."""
        if self.mock_mode:
            return self._mock_week()
        return await self._fetch_events_week()

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        *,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        """Create a new calendar event."""
        if self.mock_mode:
            return self._mock_create(
                summary, start_time, end_time, description, location, attendees or []
            )
        return await self._api_create(
            summary, start_time, end_time, description, location, attendees or []
        )

    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        if self.mock_mode:
            self._events = [e for e in self._events if e.id != event_id]
            return True
        return await self._api_delete(event_id)

    async def sync_tasks_to_calendar(self, tasks: list[dict[str, Any]]) -> list[CalendarEvent]:
        """Sync task deadlines to calendar events."""
        created: list[CalendarEvent] = []
        for task in tasks:
            due = task.get("due_date", "")
            title = task.get("title", "Untitled Task")
            if not due:
                continue
            event = await self.create_event(
                summary=f"[Task] {title}",
                start_time=due,
                end_time=due,
                description=task.get("description", ""),
            )
            created.append(event)
        return created

    async def _fetch_events_today(self) -> list[CalendarEvent]:
        """Fetch today's events from Google Calendar API."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events",
                    headers={"Authorization": f"Bearer {self.credentials_json}"},
                    params={
                        "timeMin": time.strftime("%Y-%m-%dT00:00:00Z"),
                        "singleEvents": "true",
                        "maxResults": "20",
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                return [self._parse_event(item) for item in data.get("items", [])]
        except Exception as exc:
            log.error(
                "calendar_fetch_failed", extra={"action": "calendar.today", "error": str(exc)}
            )
            return []

    async def _fetch_events_week(self) -> list[CalendarEvent]:
        """Fetch this week's events from Google Calendar API."""
        import datetime

        import httpx

        now = datetime.datetime.utcnow()
        week_end = now + datetime.timedelta(days=7)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events",
                    headers={"Authorization": f"Bearer {self.credentials_json}"},
                    params={
                        "timeMin": now.strftime("%Y-%m-%dT00:00:00Z"),
                        "timeMax": week_end.strftime("%Y-%m-%dT23:59:59Z"),
                        "singleEvents": "true",
                        "maxResults": "50",
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                return [self._parse_event(item) for item in data.get("items", [])]
        except Exception as exc:
            log.error("calendar_fetch_failed", extra={"action": "calendar.week", "error": str(exc)})
            return []

    async def _api_create(
        self, summary: str, start: str, end: str, desc: str, loc: str, attendees: list[str]
    ) -> CalendarEvent:
        """Create event via Google Calendar API."""
        import httpx

        body: dict[str, Any] = {
            "summary": summary,
            "description": desc,
            "location": loc,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if attendees:
            body["attendees"] = [{"email": a} for a in attendees]
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events",
                    headers={
                        "Authorization": f"Bearer {self.credentials_json}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=10,
                )
                resp.raise_for_status()
                return self._parse_event(resp.json())
        except Exception as exc:
            log.error(
                "calendar_create_failed", extra={"action": "calendar.create", "error": str(exc)}
            )
            raise

    async def _api_delete(self, event_id: str) -> bool:
        """Delete event via Google Calendar API."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events/{event_id}",
                    headers={"Authorization": f"Bearer {self.credentials_json}"},
                    timeout=10,
                )
                resp.raise_for_status()
                return True
        except Exception as exc:
            log.error(
                "calendar_delete_failed", extra={"action": "calendar.delete", "error": str(exc)}
            )
            return False

    def _parse_event(self, data: dict[str, Any]) -> CalendarEvent:
        """Parse a Google Calendar event into CalendarEvent."""
        start = data.get("start", {})
        end = data.get("end", {})
        attendees = tuple(a.get("email", "") for a in data.get("attendees", []))
        return CalendarEvent(
            id=data.get("id", ""),
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            start_time=start.get("dateTime", start.get("date", "")),
            end_time=end.get("dateTime", end.get("date", "")),
            location=data.get("location", ""),
            attendees=attendees,
            status=data.get("status", "confirmed"),
            html_link=data.get("htmlLink", ""),
        )

    def _mock_today(self) -> list[CalendarEvent]:
        """Return mock today schedule."""
        return [
            CalendarEvent(
                id="mock-1",
                summary="Team Standup",
                description="Daily sync meeting",
                start_time=time.strftime("%Y-%m-%dT09:00:00"),
                end_time=time.strftime("%Y-%m-%dT09:30:00"),
                location="Conference Room A",
                attendees=("alice@company.com", "bob@company.com"),
                status="confirmed",
                html_link="",
            ),
            CalendarEvent(
                id="mock-2",
                summary="Client Call - PetroCorp",
                description="Quarterly review",
                start_time=time.strftime("%Y-%m-%dT14:00:00"),
                end_time=time.strftime("%Y-%m-%dT15:00:00"),
                location="Zoom",
                attendees=("client@petrocorp.com",),
                status="confirmed",
                html_link="",
            ),
        ]

    def _mock_week(self) -> list[CalendarEvent]:
        """Return mock week schedule."""
        return self._mock_today()

    def _mock_create(
        self, summary: str, start: str, end: str, desc: str, loc: str, attendees: list[str]
    ) -> CalendarEvent:
        """Return mock created event."""
        event = CalendarEvent(
            id=_gen_event_id(),
            summary=summary,
            description=desc,
            start_time=start,
            end_time=end,
            location=loc,
            attendees=tuple(attendees),
            status="confirmed",
            html_link="",
        )
        self._events.append(event)
        return event


def _gen_event_id() -> str:
    import hashlib
    import os

    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


_calendar_client: CalendarClient | None = None


def get_calendar_client() -> CalendarClient:
    """Get or create the global calendar client singleton."""
    global _calendar_client
    if _calendar_client is None:
        from app.config import get_config

        try:
            cfg = get_config()
            _calendar_client = CalendarClient(
                credentials_json=getattr(cfg, "calendar_credentials", ""),
                calendar_id=getattr(cfg, "calendar_id", "primary"),
                mock_mode=not bool(getattr(cfg, "calendar_credentials", "")),
            )
        except Exception:
            _calendar_client = CalendarClient(mock_mode=True)
    return _calendar_client
