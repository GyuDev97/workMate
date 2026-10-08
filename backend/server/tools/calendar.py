from server.models.schemas import CalendarEventDraft, Event
from server.providers.calendar.base import CalendarProvider


class CalendarTool:
    name = "calendar"
    description = "Read and create calendar events through the selected calendar provider."

    def __init__(self, provider: CalendarProvider) -> None:
        self.provider = provider

    def today_events(self) -> list[Event]:
        return self.provider.today_events()

    def execute(self, **kwargs: object) -> list[Event]:
        return self.today_events()

    def tomorrow_events(self) -> list[Event]:
        return self.provider.tomorrow_events()

    def search_events(self, query: str) -> list[Event]:
        return self.provider.search_events(query)

    def create_event(self, draft: CalendarEventDraft) -> Event:
        return self.provider.create_event(draft)

    def update_event(self, event_id: str, draft: CalendarEventDraft) -> Event:
        return self.provider.update_event(event_id, draft)

    def delete_event(self, event_id: str) -> None:
        self.provider.delete_event(event_id)
