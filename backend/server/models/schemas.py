from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ToolRisk(str, Enum):
    READ = "READ"
    WRITE_LOCAL = "WRITE_LOCAL"
    PROPOSED_EXTERNAL_WRITE = "PROPOSED_EXTERNAL_WRITE"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class Event(BaseModel):
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str = ""
    all_day: bool = False
    location: str = ""
    calendar_id: str = "primary"
    source: str = "mock"


class CalendarEventDraft(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    starts_at: datetime
    ends_at: datetime | None = None
    description: str = ""
    all_day: bool = False
    location: str = ""
    calendar_id: str = "primary"


class CalendarConnectionStatus(BaseModel):
    provider: Literal["mock", "google"]
    state: Literal["connected", "mock", "offline"]
    detail: str
    calendar_id: str = "primary"


class MailSummary(BaseModel):
    id: str
    sender: str
    subject: str
    received_at: datetime
    is_unread: bool = True
    needs_reply: bool = False
    preview: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    priority: Priority = Priority.MEDIUM
    due_at: datetime | None = None
    source: str = "manual"


class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    priority: Priority
    due_at: datetime | None = None
    status: TaskStatus
    source: str
    created_at: datetime
    updated_at: datetime


class ProviderStatus(BaseModel):
    name: str
    state: Literal["connected", "mock", "offline"]
    detail: str


class Activity(BaseModel):
    id: str
    occurred_at: datetime
    action: str
    detail: str
    category: Literal["read", "create", "system", "reminder"] = "system"


class Briefing(BaseModel):
    greeting: str
    date_label: str
    overview: list[str]
    priorities: list[str]


class Dashboard(BaseModel):
    briefing: Briefing
    events: list[Event]
    mails: list[MailSummary]
    tasks: list[Task]
    providers: list[ProviderStatus]
    activities: list[Activity]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    conversation_id: str = Field(default="default", min_length=1, max_length=100)


class ActionCard(BaseModel):
    action_id: str | None = None
    kind: Literal["mail_draft", "calendar_event", "calendar_update", "calendar_delete", "task"]
    title: str
    fields: dict[str, str]
    requires_confirmation: bool = True
    status: ApprovalStatus = ApprovalStatus.PENDING_APPROVAL


class ActionExecutionResult(BaseModel):
    action: ActionCard
    message: str


class ToolTrace(BaseModel):
    tool: str
    risk: ToolRisk
    success: bool
    duration_ms: int


class ChatResponse(BaseModel):
    message: str
    sources: list[str] = []
    action: ActionCard | None = None
    trace: list[ToolTrace] = []
    metadata: dict[str, Any] = {}
