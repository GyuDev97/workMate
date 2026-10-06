from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_items: list[dict[str, Any]] = field(default_factory=list)


class ToolCallingProvider(Protocol):
    name: str
    mode: str

    def respond(self, *, instructions: str, input_items: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn: ...
