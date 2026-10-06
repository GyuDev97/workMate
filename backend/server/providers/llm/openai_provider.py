from __future__ import annotations

import json
import logging
from typing import Any

from server.agent.contracts import ProviderTurn, ToolCall

logger = logging.getLogger("workmate.openai")


class OpenAIProvider:
    """OpenAI Responses API adapter; imported lazily so Mock mode has no SDK requirement."""
    name = "OpenAI"
    mode = "openai"

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self.api_key, self.model = api_key, model
        self._client = client

    def respond(self, *, instructions: str, input_items: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, timeout=30.0, max_retries=1)
        logger.info("openai_request model=%s input_items=%d tool_definitions=%d", self.model, len(input_items), len(tools))
        response = self._client.responses.create(model=self.model, instructions=instructions, input=input_items, tools=tools, tool_choice="auto", store=False)
        calls = [ToolCall(call_id=item.call_id, name=item.name, arguments=json.loads(item.arguments)) for item in response.output if item.type == "function_call"]
        text = self._text_from_response(response)
        logger.info("openai_response response_id=%s output_items=%d tool_calls=%d text_chars=%d", getattr(response, "id", "unknown"), len(response.output), len(calls), len(text))
        return ProviderTurn(text=text, tool_calls=calls, provider_items=[item.model_dump(exclude_none=True) for item in response.output])

    @staticmethod
    def _text_from_response(response: Any) -> str:
        """Support the SDK convenience field and the canonical output message items."""
        convenience_text = getattr(response, "output_text", None)
        if isinstance(convenience_text, str) and convenience_text.strip():
            return convenience_text.strip()
        parts: list[str] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) == "output_text":
                    text = getattr(content, "text", "")
                    if text: parts.append(text)
        return "\n".join(parts).strip()
