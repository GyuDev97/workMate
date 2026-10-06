from __future__ import annotations

import json
from itertools import count
from typing import Any

from server.agent.contracts import ProviderTurn, ToolCall


class MockLLMProvider:
    """Deterministic tool-calling provider for offline development and test coverage."""
    name = "Mock LLM"
    mode = "mock"

    def __init__(self) -> None:
        self._ids = count(1)

    def respond(self, *, instructions: str, input_items: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        tool_outputs = [item for item in input_items if item.get("type") == "function_call_output"]
        if tool_outputs:
            return ProviderTurn(text=self._summarize(tool_outputs), provider_items=[{"role": "assistant", "content": "Tool results summarized."}])
        user_text = next((str(item.get("content", "")) for item in reversed(input_items) if item.get("role") == "user"), "")
        calls = self._choose_tools(user_text)
        if not calls:
            return ProviderTurn(text=self._direct_response(user_text), provider_items=[{"role": "assistant", "content": "Direct response."}])
        return ProviderTurn(tool_calls=calls, provider_items=[{"type": "function_call", "call_id": call.call_id, "name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)} for call in calls])

    def _call(self, name: str, **arguments: Any) -> ToolCall:
        return ToolCall(call_id=f"mock-call-{next(self._ids)}", name=name, arguments=arguments)

    def _choose_tools(self, text: str) -> list[ToolCall]:
        if any(token in text for token in ("답장", "회신", "써봐", "작성")):
            body = "안녕하세요, 김대리님.\n요청하신 RAG 테스트 결과는 확인 후 오늘 오후 중 공유드리겠습니다.\n감사합니다."
            return [self._call("create_mail_draft", recipient="김대리", subject="RE: RAG 테스트 결과 검토", body=body)]
        if any(token in text for token in ("등록", "추가")) and any(token in text for token in ("업무", "할 일", "task")):
            return [self._call("create_task", title="RAG 테스트 결과 확인", description="Assistant 요청으로 등록", priority="MEDIUM")]
        if any(token in text for token in ("등록", "추가", "만들")) and any(token in text for token in ("회의", "일정")):
            return [self._call("propose_calendar_event", title="회의", day="금요일", time="14:00")]
        if "메일" in text and any(token in text for token in ("김대리", "찾", "검색")):
            return [self._call("search_mail", query="김대리")]
        if any(token in text for token in ("오늘", "신경", "해야", "할 일")):
            return [self._call("get_today_events"), self._call("list_tasks"), self._call("get_important_mail")]
        if "내일" in text and "일정" in text: return [self._call("get_tomorrow_events")]
        if "메일" in text: return [self._call("get_important_mail")]
        return []

    @staticmethod
    def _direct_response(text: str) -> str:
        if "날씨" in text:
            return "현재 날씨 정보를 조회할 수 있는 Tool이 연결되어 있지 않습니다."
        if any(token in text for token in ("안녕", "누구", "소개")):
            return "안녕하세요. 저는 업무 일정, 메일, 할 일을 정리하고 업무를 놓치지 않도록 돕는 workMate입니다."
        return "도와드릴 업무를 말씀해 주세요. 일정, 메일, 할 일은 연결된 도구로 확인할 수 있습니다."

    @staticmethod
    def _summarize(outputs: list[dict[str, Any]]) -> str:
        by_name = {item.get("name"): json.loads(item.get("output", "{}")) for item in outputs}
        if "get_today_events" in by_name:
            events, tasks, mails = by_name.get("get_today_events", []), by_name.get("list_tasks", []), by_name.get("get_important_mail", [])
            open_tasks = [task for task in tasks if task.get("status") != "DONE"]
            first_event = events[0] if events else None
            event_text = f"오늘 {first_event['starts_at'][11:16]}에 {first_event['title']}가 있습니다." if first_event else "오늘 일정은 없습니다."
            return f"{event_text}\n처리할 업무는 {len(open_tasks)}건입니다. RAG 테스트 결과 확인을 우선 권장합니다.\n중요 메일은 {len(mails)}건이며 김대리 메일은 오늘 중 회신이 필요합니다."
        if "search_mail" in by_name: return "김대리가 보낸 ‘RAG 테스트 결과 검토 부탁드립니다’ 메일을 찾았습니다." if by_name["search_mail"] else "김대리가 보낸 관련 메일을 찾지 못했습니다."
        if "create_task" in by_name: return f"‘{by_name['create_task'].get('title')}’ 업무를 로컬 workMate에 등록했습니다."
        if "get_tomorrow_events" in by_name: return "내일 일정 조회 결과를 확인했습니다."
        if "get_important_mail" in by_name: return "확인이 필요한 중요 메일을 정리했습니다."
        if "create_mail_draft" in by_name: return "답장 초안을 준비했습니다. 보내기는 사용자가 최종 확인한 뒤에만 가능합니다."
        if "propose_calendar_event" in by_name: return "일정 등록 제안을 준비했습니다. 승인 전에는 캘린더가 변경되지 않습니다."
        return "요청을 처리했습니다."
