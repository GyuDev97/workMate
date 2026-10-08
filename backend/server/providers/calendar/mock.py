from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from server.models.schemas import CalendarConnectionStatus, CalendarEventDraft, Event

SEOUL = ZoneInfo("Asia/Seoul")


class MockCalendarProvider:
    """Offline provider with the same mutation contract as Google Calendar."""

    def __init__(self) -> None:
        self._created: list[Event] = []

    def status(self) -> CalendarConnectionStatus:
        return CalendarConnectionStatus(provider="mock", state="mock", detail="Google Calendar mock", calendar_id="primary")

    def connect(self) -> CalendarConnectionStatus:
        return self.status()

    def disconnect(self) -> CalendarConnectionStatus:
        return self.status()

    def verify(self) -> CalendarConnectionStatus:
        return self.status()

    def _base_events(self) -> list[Event]:
        today = datetime.now(SEOUL).replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            Event(id="event-poc", title="AI PoC 회의", starts_at=today + timedelta(hours=10), ends_at=today + timedelta(hours=11)),
            Event(id="event-server", title="서버 점검", starts_at=today + timedelta(hours=13, minutes=30), ends_at=today + timedelta(hours=14, minutes=30)),
            Event(id="event-rag", title="RAG 결과 확인", starts_at=today + timedelta(hours=16), ends_at=today + timedelta(hours=16, minutes=30)),
        ]

    def today_events(self) -> list[Event]:
        day = datetime.now(SEOUL).date()
        return sorted([event for event in self._base_events() + self._created if event.starts_at.astimezone(SEOUL).date() == day], key=lambda event: event.starts_at)

    def tomorrow_events(self) -> list[Event]:
        tomorrow = datetime.now(SEOUL).date() + timedelta(days=1)
        base = [event.model_copy(update={"id": f"tomorrow-{event.id}", "starts_at": event.starts_at + timedelta(days=1), "ends_at": event.ends_at + timedelta(days=1) if event.ends_at else None}) for event in self._base_events()]
        return sorted([event for event in base + self._created if event.starts_at.astimezone(SEOUL).date() == tomorrow], key=lambda event: event.starts_at)

    def search_events(self, query: str) -> list[Event]:
        needle = query.lower().strip()
        events = self._base_events() + self._created
        return [event for event in events if not needle or needle in event.title.lower()]

    def create_event(self, draft: CalendarEventDraft) -> Event:
        event = Event(id=f"mock-{uuid4()}", source="mock", **draft.model_dump())
        self._created.append(event)
        return event

    def update_event(self, event_id: str, draft: CalendarEventDraft) -> Event:
        for index, event in enumerate(self._created):
            if event.id == event_id:
                updated = Event(id=event_id, source="mock", **draft.model_dump())
                self._created[index] = updated
                return updated
        raise KeyError("Event not found")

    def delete_event(self, event_id: str) -> None:
        before = len(self._created)
        self._created = [event for event in self._created if event.id != event_id]
        if len(self._created) == before:
            raise KeyError("Event not found")
