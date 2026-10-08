from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from uuid import uuid4
from zoneinfo import ZoneInfo

from server.models.schemas import ActionCard, ActionExecutionResult, ApprovalStatus, CalendarEventDraft
from server.services.activity import ActivityService
from server.tools.calendar import CalendarTool

SEOUL = ZoneInfo("Asia/Seoul")


class CalendarActionService:
    """Stores approval-gated calendar mutations and permits each action once only."""

    def __init__(self, calendar: CalendarTool, activity: ActivityService | None = None, timezone: ZoneInfo = SEOUL) -> None:
        self.calendar, self.activity, self.timezone = calendar, activity, timezone
        self._actions: dict[str, tuple[ActionCard, CalendarEventDraft | None, str | None]] = {}
        self._lock = Lock()

    def propose_create(self, title: str, day: str, at_time: str) -> ActionCard:
        starts_at = self._resolve_datetime(day, at_time)
        draft = CalendarEventDraft(title=title, starts_at=starts_at, ends_at=starts_at + timedelta(hours=1), calendar_id=self.calendar.provider.status().calendar_id)
        return self._save("calendar_event", "일정 등록", draft, None)

    def propose_update(self, event_id: str, title: str, day: str, at_time: str) -> ActionCard:
        starts_at = self._resolve_datetime(day, at_time)
        draft = CalendarEventDraft(title=title, starts_at=starts_at, ends_at=starts_at + timedelta(hours=1), calendar_id=self.calendar.provider.status().calendar_id)
        return self._save("calendar_update", "일정 변경", draft, event_id)

    def propose_delete(self, event_id: str, title: str, starts_at: datetime) -> ActionCard:
        draft = CalendarEventDraft(title=title, starts_at=starts_at, calendar_id=self.calendar.provider.status().calendar_id)
        return self._save("calendar_delete", "일정 삭제", draft, event_id)

    def approve(self, action_id: str) -> ActionExecutionResult:
        with self._lock:
            item = self._actions.get(action_id)
            if not item:
                raise KeyError("Action not found")
            card, draft, event_id = item
            if card.status == ApprovalStatus.COMPLETED:
                return ActionExecutionResult(action=card, message="이 작업은 이미 완료되었습니다.")
            if card.status == ApprovalStatus.EXECUTING:
                return ActionExecutionResult(action=card, message="작업을 실행 중입니다.")
            if card.status != ApprovalStatus.PENDING_APPROVAL:
                return ActionExecutionResult(action=card, message="실행할 수 없는 작업입니다.")
            card.status = ApprovalStatus.EXECUTING
        try:
            if card.kind == "calendar_event" and draft:
                event = self.calendar.create_event(draft)
                message = f"‘{event.title}’ 일정을 등록했습니다."
                activity_action = "일정 등록"
            elif card.kind == "calendar_update" and draft and event_id:
                event = self.calendar.update_event(event_id, draft)
                message = f"‘{event.title}’ 일정을 변경했습니다."
                activity_action = "일정 수정"
            elif card.kind == "calendar_delete" and event_id:
                self.calendar.delete_event(event_id)
                message = "일정을 삭제했습니다."
                activity_action = "일정 삭제"
            else:
                raise ValueError("Invalid calendar action")
            card.status = ApprovalStatus.COMPLETED
            self._record(activity_action, "사용자 승인 후 Calendar Provider에 반영했습니다.")
        except Exception as error:
            card.status = ApprovalStatus.FAILED
            message = f"일정을 실행하지 못했습니다: {error}"
            self._record("일정 실행 실패", type(error).__name__)
        return ActionExecutionResult(action=card, message=message)

    def _save(self, kind: str, title: str, draft: CalendarEventDraft, event_id: str | None) -> ActionCard:
        action_id = str(uuid4())
        when = "종일" if draft.all_day else draft.starts_at.astimezone(self.timezone).strftime("%Y-%m-%d %H:%M")
        card = ActionCard(action_id=action_id, kind=kind, title=title, fields={"Title": draft.title, "When": when, "Calendar": draft.calendar_id})
        self._actions[action_id] = (card, draft, event_id)
        return card

    def _resolve_datetime(self, day: str, at_time: str) -> datetime:
        cleaned = day.strip()
        now = datetime.now(self.timezone)
        dates = {"오늘": now.date(), "내일": (now + timedelta(days=1)).date(), "모레": (now + timedelta(days=2)).date()}
        if cleaned in dates:
            date = dates[cleaned]
        else:
            weekdays = {"월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3, "금요일": 4, "토요일": 5, "일요일": 6}
            target = weekdays.get(cleaned.removeprefix("다음 주 "))
            if target is None:
                raise ValueError("날짜를 해석하지 못했습니다. 오늘, 내일 또는 요일을 지정해 주세요.")
            days = (target - now.weekday()) % 7
            if cleaned.startswith("다음 주 "):
                days += 7 if days == 0 else 7
            date = (now + timedelta(days=days)).date()
        try:
            hour, minute = (int(part) for part in at_time.strip().split(":", maxsplit=1))
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError
        except ValueError as error:
            raise ValueError("시간은 14:00 형식으로 지정해 주세요.") from error
        return datetime(date.year, date.month, date.day, hour, minute, tzinfo=self.timezone)

    def _record(self, action: str, detail: str) -> None:
        if self.activity:
            self.activity.record(action, detail, "create")
