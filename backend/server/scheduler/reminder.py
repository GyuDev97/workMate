from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from server.models.schemas import Event, Task


@dataclass(frozen=True)
class Reminder:
    title: str
    body: str
    due_at: datetime


class ReminderScheduler:
    """Pure reminder planner; a later host can invoke it on an interval safely."""

    def due_reminders(self, events: list[Event], tasks: list[Task], now: datetime | None = None) -> list[Reminder]:
        current = now or datetime.now(timezone.utc)
        horizon = current + timedelta(minutes=30)
        reminders = [Reminder(event.title, "30분 뒤 일정이 있습니다.", event.starts_at) for event in events if current <= event.starts_at <= horizon]
        reminders.extend(Reminder(task.title, "기한이 임박한 업무입니다.", task.due_at) for task in tasks if task.due_at and task.status.value != "DONE" and task.due_at <= horizon)
        return reminders
