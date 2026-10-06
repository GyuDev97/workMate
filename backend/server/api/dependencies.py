from functools import lru_cache
import os

from server.agent.agent import WorkMateAgent
from server.agent.tool_registry import ToolRegistry
from server.database.repository import TaskRepository
from server.services.dashboard import DashboardService
from server.services.tasks import TaskService
from server.services.activity import ActivityService
from server.tools.calendar import CalendarTool
from server.tools.mail import MailTool
from server.tools.memory import MemoryTool
from server.providers.llm.mock import MockLLMProvider
from server.providers.llm.openai_provider import OpenAIProvider


@lru_cache
def task_service() -> TaskService:
    return TaskService(TaskRepository())


@lru_cache
def activity_service() -> ActivityService:
    return ActivityService()


@lru_cache
def dashboard_service() -> DashboardService:
    return DashboardService(task_service(), CalendarTool(), MailTool(), activity_service())


@lru_cache
def tool_registry() -> ToolRegistry:
    return ToolRegistry(task_service(), CalendarTool(), MailTool(), MemoryTool())


@lru_cache
def llm_provider():
    requested = os.getenv("WORKMATE_LLM_PROVIDER", "mock").lower()
    api_key = os.getenv("OPENAI_API_KEY", "")
    if requested == "openai" and api_key:
        return OpenAIProvider(api_key, os.getenv("WORKMATE_LLM_MODEL", "gpt-4.1-mini"))
    return MockLLMProvider()


@lru_cache
def agent() -> WorkMateAgent:
    return WorkMateAgent(llm_provider(), tool_registry(), activity_service())
