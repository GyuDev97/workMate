from collections import deque
from datetime import datetime
from uuid import uuid4

from server.models.schemas import Activity, ToolTrace


class ActivityService:
    """Small in-memory audit stream; intentionally excludes prompts, secrets and mail bodies."""
    def __init__(self) -> None:
        self._items: deque[Activity] = deque(maxlen=50)

    def record_tool_trace(self, trace: ToolTrace) -> None:
        label = "완료" if trace.success else "실패"
        self._items.appendleft(Activity(id=str(uuid4()), occurred_at=datetime.now().astimezone(), action=f"{trace.tool} {label}", detail=f"{trace.risk.value} · {trace.duration_ms}ms", category="read" if trace.risk.value == "READ" else "create"))

    def record(self, action: str, detail: str, category: str = "system") -> None:
        safe_category = category if category in {"read", "create", "system", "reminder"} else "system"
        self._items.appendleft(Activity(id=str(uuid4()), occurred_at=datetime.now().astimezone(), action=action, detail=detail, category=safe_category))

    def recent(self) -> list[Activity]:
        return list(self._items)
