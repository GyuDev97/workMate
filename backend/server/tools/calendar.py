from datetime import datetime, timedelta, timezone

from server.models.schemas import Event


class CalendarTool:
    name = "calendar"
    description = "Read and create calendar events. V0.1 uses mock Google Calendar data."

    def today_events(self) -> list[Event]:
        # Mock times represent the user's local workday, not UTC timestamps.
        today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            Event(id="event-poc", title="AI PoC 회의", starts_at=today + timedelta(hours=10), ends_at=today + timedelta(hours=11)),
            Event(id="event-server", title="서버 점검", starts_at=today + timedelta(hours=13, minutes=30), ends_at=today + timedelta(hours=14, minutes=30)),
            Event(id="event-rag", title="RAG 결과 확인", starts_at=today + timedelta(hours=16), ends_at=today + timedelta(hours=16, minutes=30)),
        ]

    def execute(self, **kwargs: object) -> list[Event]:
        return self.today_events()

    def tomorrow_events(self) -> list[Event]:
        return [event.model_copy(update={"id": f"tomorrow-{event.id}", "starts_at": event.starts_at + timedelta(days=1), "ends_at": event.ends_at + timedelta(days=1) if event.ends_at else None}) for event in self.today_events()]

    def search_events(self, query: str) -> list[Event]:
        needle = query.lower().strip()
        return [event for event in self.today_events() + self.tomorrow_events() if not needle or needle in event.title.lower()]
