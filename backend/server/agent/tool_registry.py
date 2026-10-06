from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from server.models.schemas import ActionCard, Priority, TaskCreate, ToolRisk, ToolTrace
from server.services.tasks import TaskService
from server.tools.calendar import CalendarTool
from server.tools.mail import MailTool
from server.tools.memory import MemoryTool


class SearchArgs(BaseModel):
    query: str = Field(default="", max_length=300)


class CreateTaskArgs(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    priority: Priority = Priority.MEDIUM


class CompleteTaskArgs(BaseModel):
    task_id: str


class DraftArgs(BaseModel):
    recipient: str = "김대리"
    subject: str = "RE: RAG 테스트 결과 검토"
    body: str = "안녕하세요.\n요청하신 내용을 확인한 뒤 오늘 오후 중 공유드리겠습니다.\n감사합니다."


class CalendarProposalArgs(BaseModel):
    title: str = "회의"
    day: str = "금요일"
    time: str = "14:00"


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    risk: ToolRisk
    arguments_model: type[BaseModel]
    handler: Callable[[BaseModel], Any]

    def schema(self) -> dict[str, Any]:
        parameters = self.arguments_model.model_json_schema()
        parameters["additionalProperties"] = False
        return {
            "type": "function", "name": self.name, "description": self.description,
            "parameters": parameters, "strict": True,
        }


class ToolRegistry:
    """Single source of truth for tool descriptions, validation, risk and execution."""

    def __init__(self, tasks: TaskService, calendar: CalendarTool, mail: MailTool, memory: MemoryTool) -> None:
        self.tasks, self.calendar, self.mail, self.memory = tasks, calendar, mail, memory
        self._tools = {tool.name: tool for tool in self._build_tools()}

    def _build_tools(self) -> list[RegisteredTool]:
        return [
            RegisteredTool("get_today_events", "Get the user's events scheduled for today.", ToolRisk.READ, SearchArgs, lambda _args: self.calendar.today_events()),
            RegisteredTool("get_tomorrow_events", "Get the user's events scheduled for tomorrow.", ToolRisk.READ, SearchArgs, lambda _args: self.calendar.tomorrow_events()),
            RegisteredTool("search_events", "Search calendar events by a query.", ToolRisk.READ, SearchArgs, lambda args: self.calendar.search_events(args.query)),
            RegisteredTool("list_tasks", "List local workMate tasks and their status.", ToolRisk.READ, SearchArgs, lambda _args: self.tasks.list_tasks()),
            RegisteredTool("create_task", "Create a local workMate task. Use only when the user explicitly asks to register a task.", ToolRisk.WRITE_LOCAL, CreateTaskArgs, lambda args: self.tasks.create_task(TaskCreate(**args.model_dump(), source="agent"))),
            RegisteredTool("complete_task", "Mark a local workMate task as completed.", ToolRisk.WRITE_LOCAL, CompleteTaskArgs, lambda args: self.tasks.complete_task(args.task_id) or {"error": "Task not found"}),
            RegisteredTool("get_unread_mail", "Get unread mock mail summaries.", ToolRisk.READ, SearchArgs, lambda _args: self.mail.unread_mail()),
            RegisteredTool("get_important_mail", "Get important mail summaries, including reply-needed mail.", ToolRisk.READ, SearchArgs, lambda _args: self.mail.important_mail()),
            RegisteredTool("search_mail", "Search mail by sender, subject, or text query.", ToolRisk.READ, SearchArgs, lambda args: self.mail.search_mail(args.query)),
            RegisteredTool("get_mail", "Get a single mail summary by ID or query.", ToolRisk.READ, SearchArgs, lambda args: self.mail.get_mail(args.query)),
            RegisteredTool("create_mail_draft", "Prepare a mail draft only. Never sends mail; user approval is required to send.", ToolRisk.PROPOSED_EXTERNAL_WRITE, DraftArgs, self._mail_draft),
            RegisteredTool("propose_calendar_event", "Propose a calendar event only. Never creates an external event without approval.", ToolRisk.PROPOSED_EXTERNAL_WRITE, CalendarProposalArgs, self._calendar_proposal),
            RegisteredTool("search_work_memory", "Search WorkMemory. This provider may be unavailable in V0.2.", ToolRisk.READ, SearchArgs, lambda args: self.memory.search(args.query)),
        ]

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> tuple[Any, ToolTrace]:
        started = time.perf_counter()
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}, ToolTrace(tool=name, risk=ToolRisk.READ, success=False, duration_ms=0)
        try:
            parsed = tool.arguments_model.model_validate(arguments)
            value = tool.handler(parsed)
            success = not (isinstance(value, dict) and "error" in value)
            return value, ToolTrace(tool=name, risk=tool.risk, success=success, duration_ms=round((time.perf_counter() - started) * 1000))
        except Exception as error:  # Tool failures are returned to the model, not hidden.
            return {"error": f"{type(error).__name__}: {error}"}, ToolTrace(tool=name, risk=tool.risk, success=False, duration_ms=round((time.perf_counter() - started) * 1000))

    @staticmethod
    def serialize(value: Any) -> str:
        if isinstance(value, BaseModel): value = value.model_dump(mode="json")
        if isinstance(value, list): value = [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value]
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def action_from(value: Any) -> ActionCard | None:
        return value if isinstance(value, ActionCard) else None

    @staticmethod
    def _mail_draft(args: DraftArgs) -> ActionCard:
        return ActionCard(kind="mail_draft", title="답장 초안", fields={"To": args.recipient, "Subject": args.subject, "Body": args.body})

    @staticmethod
    def _calendar_proposal(args: CalendarProposalArgs) -> ActionCard:
        return ActionCard(kind="calendar_event", title="일정 등록 제안", fields={"Title": args.title, "When": f"{args.day} {args.time}", "Calendar": "Google Calendar (Mock)"})
