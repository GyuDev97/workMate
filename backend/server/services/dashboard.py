from datetime import datetime, timezone
import os

from server.models.schemas import Activity, Briefing, Dashboard, ProviderStatus
from server.services.tasks import TaskService
from server.services.activity import ActivityService
from server.tools.calendar import CalendarTool
from server.tools.mail import MailTool


class DashboardService:
    def __init__(self, tasks: TaskService, calendar: CalendarTool, mail: MailTool, activity: ActivityService | None = None) -> None:
        self.tasks = tasks
        self.calendar = calendar
        self.mail = mail
        self.activity = activity

    def get_dashboard(self) -> Dashboard:
        events = self.calendar.today_events()
        mails = self.mail.important_mail()
        tasks = self.tasks.list_tasks()
        open_tasks = [task for task in tasks if task.status.value != "DONE"]
        now = datetime.now().astimezone()
        return Dashboard(
            briefing=Briefing(
                greeting="좋은 아침입니다.",
                date_label=now.astimezone().strftime("%Y년 %m월 %d일"),
                overview=[f"오늘 일정 {len(events)}건", f"처리할 업무 {len(open_tasks)}건", f"중요 메일 {len(mails)}건"],
                priorities=["10:00 AI PoC 회의", "RAG 테스트 결과 확인", "김대리 메일 회신"],
            ),
            events=events, mails=mails, tasks=tasks,
            providers=[
                ProviderStatus(name="LLM", state="connected" if os.getenv("WORKMATE_LLM_PROVIDER") == "openai" and os.getenv("OPENAI_API_KEY") else "mock", detail="OpenAI Responses API" if os.getenv("WORKMATE_LLM_PROVIDER") == "openai" and os.getenv("OPENAI_API_KEY") else "Mock provider (set OPENAI_API_KEY to enable OpenAI)"),
                ProviderStatus(name="Mail", state="mock", detail="Bizmeka mock"),
                ProviderStatus(name="Calendar", state="mock", detail="Google Calendar mock"),
                ProviderStatus(name="Memory", state="offline", detail="WorkMemory 연결 대기"),
            ],
            activities=(self.activity.recent() if self.activity and self.activity.recent() else [
                Activity(id="a-1", occurred_at=now, action="오늘 일정 조회", detail="Mock Google Calendar에서 3건을 확인했습니다.", category="read"),
                Activity(id="a-2", occurred_at=now, action="중요 메일 확인", detail="회신이 필요한 메일 1건을 분류했습니다.", category="read"),
                Activity(id="a-3", occurred_at=now, action="Reminder 엔진 준비", detail="다음 예정 일정과 미완료 업무를 감시할 구조가 준비되었습니다.", category="system"),
            ]),
        )
