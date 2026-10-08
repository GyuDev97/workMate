from __future__ import annotations

from datetime import datetime, time, timedelta
import logging
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from server.models.schemas import CalendarConnectionStatus, CalendarEventDraft, Event
from server.providers.calendar.base import CalendarNotConnected, CalendarProviderError
from server.providers.calendar.token_store import FileTokenStore, OAuthTokenStore

logger = logging.getLogger("workmate.calendar")
EVENT_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleCalendarProvider:
    """Google Calendar v3 adapter using the supported Desktop OAuth local-server flow."""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_store: OAuthTokenStore | None = None,
        calendar_id: str | None = None,
        timezone_name: str | None = None,
        service_factory: Any | None = None,
    ) -> None:
        self.credentials_path = Path(credentials_path or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH", "")).expanduser()
        token_path = Path(os.getenv("GOOGLE_CALENDAR_TOKEN_PATH", "data/google_calendar_token.json")).expanduser()
        self.token_store = token_store or FileTokenStore(token_path)
        self.calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.timezone = ZoneInfo(timezone_name or os.getenv("WORKMATE_TIMEZONE", "Asia/Seoul"))
        self._service_factory = service_factory

    def status(self) -> CalendarConnectionStatus:
        if not self.credentials_path or not self.credentials_path.is_file():
            return CalendarConnectionStatus(provider="google", state="offline", detail="OAuth Desktop Client JSON이 설정되지 않았습니다.", calendar_id=self.calendar_id)
        if not self.token_store.read():
            return CalendarConnectionStatus(provider="google", state="offline", detail="Google 계정 연결이 필요합니다.", calendar_id=self.calendar_id)
        return CalendarConnectionStatus(provider="google", state="connected", detail="Google Calendar 연결됨", calendar_id=self.calendar_id)

    def connect(self) -> CalendarConnectionStatus:
        self._service(interactive=True)
        logger.info("calendar_connected provider=google calendar_id=%s", self.calendar_id)
        return self.status()

    def disconnect(self) -> CalendarConnectionStatus:
        # Local logout deliberately removes only this app's local token. OAuth grant revocation is a separate user choice.
        self.token_store.delete()
        logger.info("calendar_disconnected provider=google calendar_id=%s", self.calendar_id)
        return self.status()

    def verify(self) -> CalendarConnectionStatus:
        # An events list is authorized by the narrow calendar.events scope; calendar metadata may require a broader scope.
        self._service().events().list(calendarId=self.calendar_id, maxResults=1, singleEvents=True).execute()
        logger.info("calendar_verified provider=google calendar_id=%s", self.calendar_id)
        return self.status()

    def today_events(self) -> list[Event]:
        now = datetime.now(self.timezone)
        return self._events_between(now.replace(hour=0, minute=0, second=0, microsecond=0), now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))

    def tomorrow_events(self) -> list[Event]:
        start = datetime.now(self.timezone).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return self._events_between(start, start + timedelta(days=1))

    def search_events(self, query: str) -> list[Event]:
        now = datetime.now(self.timezone)
        payload = self._service().events().list(
            calendarId=self.calendar_id,
            q=query.strip() or None,
            timeMin=now.isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return [self.normalize(item, self.calendar_id, self.timezone) for item in payload.get("items", []) if item.get("status") != "cancelled"]

    def create_event(self, draft: CalendarEventDraft) -> Event:
        item = self._service().events().insert(calendarId=draft.calendar_id or self.calendar_id, body=self._draft_body(draft)).execute()
        logger.info("calendar_event_created provider=google calendar_id=%s", draft.calendar_id or self.calendar_id)
        return self.normalize(item, draft.calendar_id or self.calendar_id, self.timezone)

    def update_event(self, event_id: str, draft: CalendarEventDraft) -> Event:
        item = self._service().events().update(calendarId=draft.calendar_id or self.calendar_id, eventId=event_id, body=self._draft_body(draft)).execute()
        logger.info("calendar_event_updated provider=google calendar_id=%s", draft.calendar_id or self.calendar_id)
        return self.normalize(item, draft.calendar_id or self.calendar_id, self.timezone)

    def delete_event(self, event_id: str) -> None:
        self._service().events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
        logger.info("calendar_event_deleted provider=google calendar_id=%s", self.calendar_id)

    def _events_between(self, start: datetime, end: datetime) -> list[Event]:
        try:
            payload = self._service().events().list(
                calendarId=self.calendar_id,
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                maxResults=100,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = [self.normalize(item, self.calendar_id, self.timezone) for item in payload.get("items", []) if item.get("status") != "cancelled"]
            logger.info("calendar_events_read provider=google count=%d calendar_id=%s", len(events), self.calendar_id)
            return events
        except CalendarProviderError:
            raise
        except Exception as error:
            raise self._safe_error(error) from error

    def _service(self, interactive: bool = False) -> Any:
        credentials = self._credentials(interactive=interactive)
        try:
            if self._service_factory:
                return self._service_factory(credentials)
            from googleapiclient.discovery import build
            return build("calendar", "v3", credentials=credentials, cache_discovery=False)
        except ImportError as error:
            raise CalendarProviderError("Google Calendar 라이브러리가 설치되지 않았습니다. requirements를 설치해 주세요.") from error
        except Exception as error:
            raise self._safe_error(error) from error

    def _credentials(self, interactive: bool) -> Any:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as error:
            raise CalendarProviderError("Google Calendar 라이브러리가 설치되지 않았습니다. requirements를 설치해 주세요.") from error

        raw_token = self.token_store.read()
        try:
            credentials = Credentials.from_authorized_user_info(__import__("json").loads(raw_token), [EVENT_SCOPE]) if raw_token else None
        except Exception as error:
            if not interactive:
                raise CalendarNotConnected("Google Calendar 토큰을 읽지 못했습니다. 다시 연결해 주세요.") from error
            credentials = None
        try:
            if credentials and credentials.valid:
                return credentials
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self.token_store.write(credentials.to_json())
                return credentials
        except Exception as error:
            logger.warning("calendar_token_refresh_failed type=%s", type(error).__name__)
            if not interactive:
                raise CalendarNotConnected("Google Calendar 토큰을 갱신하지 못했습니다. 다시 연결해 주세요.") from error
        if not interactive:
            raise CalendarNotConnected("Google Calendar 계정을 먼저 연결해 주세요.")
        if not self.credentials_path or not self.credentials_path.is_file():
            raise CalendarNotConnected("GOOGLE_CALENDAR_CREDENTIALS_PATH에 OAuth Desktop Client JSON 경로를 설정해 주세요.")
        try:
            credentials = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), [EVENT_SCOPE]).run_local_server(port=0, open_browser=True)
            self.token_store.write(credentials.to_json())
            return credentials
        except Exception as error:
            raise self._safe_error(error) from error

    @staticmethod
    def _safe_error(error: Exception) -> CalendarProviderError:
        return CalendarProviderError(f"Google Calendar를 확인할 수 없습니다: {type(error).__name__}")

    @staticmethod
    def _draft_body(draft: CalendarEventDraft) -> dict[str, Any]:
        body: dict[str, Any] = {"summary": draft.title, "description": draft.description, "location": draft.location}
        if draft.all_day:
            body["start"] = {"date": draft.starts_at.date().isoformat()}
            end_date = (draft.ends_at.date() if draft.ends_at else draft.starts_at.date() + timedelta(days=1))
            body["end"] = {"date": end_date.isoformat()}
        else:
            end = draft.ends_at or draft.starts_at + timedelta(hours=1)
            body["start"] = {"dateTime": draft.starts_at.isoformat(), "timeZone": str(draft.starts_at.tzinfo or "Asia/Seoul")}
            body["end"] = {"dateTime": end.isoformat(), "timeZone": str(end.tzinfo or "Asia/Seoul")}
        return body

    @staticmethod
    def normalize(item: dict[str, Any], calendar_id: str, timezone: ZoneInfo) -> Event:
        start, all_day = GoogleCalendarProvider._parse_time(item.get("start", {}), timezone)
        end, _ = GoogleCalendarProvider._parse_time(item.get("end", {}), timezone)
        return Event(
            id=item["id"], title=item.get("summary") or "제목 없음", description=item.get("description") or "",
            starts_at=start, ends_at=end, all_day=all_day, location=item.get("location") or "",
            calendar_id=calendar_id, source="google",
        )

    @staticmethod
    def _parse_time(value: dict[str, str], timezone: ZoneInfo) -> tuple[datetime, bool]:
        if value.get("date"):
            date = datetime.fromisoformat(value["date"]).date()
            return datetime.combine(date, time.min, tzinfo=timezone), True
        raw = value.get("dateTime")
        if not raw:
            raise CalendarProviderError("Google Calendar 이벤트에 시작 시간이 없습니다.")
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (parsed.replace(tzinfo=timezone) if parsed.tzinfo is None else parsed.astimezone(timezone), False)
