from __future__ import annotations

from collections import defaultdict, deque
import logging
from typing import Any

from server.agent.contracts import ToolCallingProvider
from server.agent.tool_registry import ToolRegistry
from server.models.schemas import ActionCard, ChatResponse, ToolTrace
from server.services.activity import ActivityService

SYSTEM_INSTRUCTIONS = """You are workMate, a Korean personal work assistant. Answer greetings and general questions directly when no tool is needed. Use tools for facts about mail, calendar, tasks, and WorkMemory. Ground structured claims only in tool outputs. If the user asks for real-time or external data and no matching tool exists (for example, weather), clearly say it is not connected; never invent it. Never claim a tool succeeded if it failed. Never send mail or change an external calendar: produce approval-required proposals instead. Keep the final answer concise and helpful in Korean."""
logger = logging.getLogger("workmate.agent")


class WorkMateAgent:
    """Bounded application-side tool loop; providers decide calls, application enforces tools."""

    def __init__(self, provider: ToolCallingProvider, tools: ToolRegistry, activity: ActivityService | None = None, max_tool_rounds: int = 3) -> None:
        self.provider, self.tools, self.max_tool_rounds = provider, tools, max_tool_rounds
        self.activity = activity
        self._history: dict[str, deque[dict[str, str]]] = defaultdict(lambda: deque(maxlen=8))

    def respond(self, message: str, conversation_id: str = "default") -> ChatResponse:
        history = self._history[conversation_id]
        items: list[dict[str, Any]] = [{"role": item["role"], "content": item["content"]} for item in history]
        items.append({"role": "user", "content": message})
        traces: list[ToolTrace] = []
        action: ActionCard | None = None
        failures: list[str] = []
        final_text = ""
        logger.info("agent_request provider=%s conversation=%s chars=%d history=%d", self.provider.mode, conversation_id, len(message), len(history))
        for _round in range(self.max_tool_rounds):
            try:
                turn = self.provider.respond(instructions=SYSTEM_INSTRUCTIONS, input_items=items, tools=self.tools.schemas())
            except Exception as error:
                logger.warning("agent_provider_error provider=%s type=%s", self.provider.mode, type(error).__name__)
                final_text = "LLM 연결 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
                break
            items.extend(turn.provider_items)
            if not turn.tool_calls:
                final_text = turn.text or "요청을 처리했지만 응답을 생성하지 못했습니다."
                logger.info("agent_response provider=%s round=%d text_chars=%d", self.provider.mode, _round + 1, len(final_text))
                break
            logger.info("agent_tools_selected provider=%s round=%d tools=%s", self.provider.mode, _round + 1, ",".join(call.name for call in turn.tool_calls))
            for call in turn.tool_calls:
                result, trace = self.tools.execute(call.name, call.arguments)
                traces.append(trace)
                if self.activity: self.activity.record_tool_trace(trace)
                if not trace.success: failures.append(call.name)
                possible_action = self.tools.action_from(result)
                if possible_action: action = possible_action
                items.append({"type": "function_call_output", "call_id": call.call_id, "name": call.name, "output": self.tools.serialize(result)})
                logger.info("agent_tool_result tool=%s risk=%s success=%s duration_ms=%d", trace.tool, trace.risk.value, trace.success, trace.duration_ms)
        else:
            final_text = "요청 처리 중 도구 호출 한도에 도달했습니다. 필요한 정보를 좁혀 다시 요청해 주세요."
        if failures and final_text and "오류" not in final_text:
            final_text += "\n\n일부 정보 조회에 실패해, 확인된 결과만 안내했습니다."
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": final_text})
        sources = sorted({trace.tool for trace in traces if trace.success})
        logger.info("agent_complete provider=%s tools=%d action=%s", self.provider.mode, len(traces), action.kind if action else "none")
        return ChatResponse(message=final_text, action=action, sources=sources, trace=traces, metadata={"provider": self.provider.mode})
