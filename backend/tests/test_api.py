from fastapi.testclient import TestClient
import pytest
from types import SimpleNamespace
from datetime import datetime
from zoneinfo import ZoneInfo

from server.api import dependencies
from server.agent.agent import WorkMateAgent
from server.providers.llm.openai_provider import OpenAIProvider
from server.providers.calendar.google import GoogleCalendarProvider
from server.providers.calendar.token_store import FileTokenStore
from server.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_task_database(tmp_path, monkeypatch):
    """Keep API tests from writing into the desktop app's local SQLite data."""
    monkeypatch.chdir(tmp_path)
    dependencies.task_service.cache_clear()
    dependencies.knowledge_service.cache_clear()
    dependencies.dashboard_service.cache_clear()
    dependencies.activity_service.cache_clear()
    dependencies.calendar_action_service.cache_clear()
    dependencies.calendar_tool.cache_clear()
    dependencies.calendar_provider.cache_clear()
    dependencies.tool_registry.cache_clear()
    dependencies.llm_provider.cache_clear()
    dependencies.agent.cache_clear()
    yield
    dependencies.task_service.cache_clear()
    dependencies.knowledge_service.cache_clear()
    dependencies.dashboard_service.cache_clear()
    dependencies.activity_service.cache_clear()
    dependencies.calendar_action_service.cache_clear()
    dependencies.calendar_tool.cache_clear()
    dependencies.calendar_provider.cache_clear()
    dependencies.tool_registry.cache_clear()
    dependencies.llm_provider.cache_clear()
    dependencies.agent.cache_clear()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "workMate"}


def test_dashboard_and_chat() -> None:
    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert len(dashboard.json()["events"]) == 3
    response = client.post("/api/v1/chat", json={"message": "오늘 뭐 해야 돼?"})
    assert response.status_code == 200
    assert "오늘" in response.json()["message"]
    assert {item["tool"] for item in response.json()["trace"]} == {"get_today_events", "list_tasks", "get_important_mail"}
    draft = client.post("/api/v1/chat", json={"message": "김대리에게 답장 써줘"})
    assert draft.json()["action"]["kind"] == "mail_draft"


def test_conversation_context_and_approval_action() -> None:
    first = client.post("/api/v1/chat", json={"conversation_id": "mail-thread", "message": "김대리가 보낸 메일 찾아봐."})
    assert first.json()["trace"][0]["tool"] == "search_mail"
    draft = client.post("/api/v1/chat", json={"conversation_id": "mail-thread", "message": "그거 답장 써봐. 오늘 오후에 확인한다고 해."})
    assert draft.json()["action"]["status"] == "pending_approval"
    assert "보내기" in draft.json()["message"]


def test_agent_task_and_calendar_proposal() -> None:
    task = client.post("/api/v1/chat", json={"message": "RAG 테스트 결과 확인하는 거 업무로 등록해."}).json()
    assert task["trace"][0]["tool"] == "create_task"
    proposal = client.post("/api/v1/chat", json={"message": "금요일 오후 2시에 회의 등록해."}).json()
    assert proposal["action"]["kind"] == "calendar_event"
    assert proposal["action"]["status"] == "pending_approval"


def test_openai_no_tool_message_output_reaches_agent() -> None:
    """Regression: a Responses `message/output_text` must not become an empty agent reply."""
    class OutputText:
        type = "output_text"
        text = "안녕하세요. 저는 업무 일정, 메일, 할 일을 정리하는 workMate입니다."

    class Message:
        type = "message"
        content = [OutputText()]

        @staticmethod
        def model_dump(**_kwargs):
            return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": OutputText.text}]}

    response = SimpleNamespace(output_text="", output=[Message()])
    fake_client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_kwargs: response))
    provider = OpenAIProvider("test-key", "test-model", client=fake_client)
    agent = WorkMateAgent(provider, dependencies.tool_registry())
    result = agent.respond("안녕 너는 누구야", "no-tool")
    assert result.message == OutputText.text
    assert result.trace == []


def test_mock_no_tool_responses_are_direct_and_grounded() -> None:
    greeting = client.post("/api/v1/chat", json={"message": "안녕 너는 누구야"}).json()
    assert "workMate" in greeting["message"]
    assert greeting["trace"] == []
    weather = client.post("/api/v1/chat", json={"message": "내일 날씨 뭐임"}).json()
    assert "Tool이 연결되어 있지 않습니다" in weather["message"]


def test_task_lifecycle() -> None:
    created = client.post("/api/v1/tasks", json={"title": "테스트 업무", "priority": "HIGH"})
    assert created.status_code == 201
    completed = client.post(f"/api/v1/tasks/{created.json()['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "DONE"


def test_local_folder_knowledge_collection_and_document_preview(tmp_path) -> None:
    folder = tmp_path / "documents"
    folder.mkdir()
    (folder / "notes.md").write_text("# 회의 메모\n\n다음 주까지 검토 결과를 공유합니다.", encoding="utf-8")
    (folder / ".env").write_text("SECRET=never-collect", encoding="utf-8")
    source = client.post("/api/v1/knowledge/sources", json={"name": "테스트 문서", "local_path": str(folder)})
    assert source.status_code == 201
    run = client.post(f"/api/v1/knowledge/sources/{source.json()['id']}/scan")
    assert run.status_code == 200
    assert run.json()["scanned"] == 1 and run.json()["parsed"] == 1
    artifacts = client.get(f"/api/v1/knowledge/sources/{source.json()['id']}/artifacts").json()
    assert len(artifacts) == 1 and artifacts[0]["chunk_count"] >= 1
    preview = client.get(f"/api/v1/knowledge/artifacts/{artifacts[0]['id']}")
    assert preview.status_code == 200 and "검토 결과" in preview.json()["content"]


def test_calendar_action_approval_and_duplicate_prevention() -> None:
    proposal = client.post("/api/v1/chat", json={"message": "금요일 오후 2시에 회의 등록해."}).json()["action"]
    assert proposal["status"] == "pending_approval"
    action_id = proposal["action_id"]
    completed = client.post(f"/api/v1/actions/{action_id}/approve")
    assert completed.status_code == 200
    assert completed.json()["action"]["status"] == "completed"
    repeated = client.post(f"/api/v1/actions/{action_id}/approve")
    assert repeated.json()["message"] == "이 작업은 이미 완료되었습니다."


def test_calendar_update_and_delete_proposals_are_approval_gated() -> None:
    actions = dependencies.calendar_action_service()
    starts_at = datetime(2026, 10, 9, 14, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    update = actions.propose_update("event-1", "AI PoC 회의", "금요일", "15:00")
    deletion = actions.propose_delete("event-1", "AI PoC 회의", starts_at)
    assert update.kind == "calendar_update" and update.status.value == "pending_approval"
    assert deletion.kind == "calendar_delete" and deletion.status.value == "pending_approval"


def test_google_calendar_normalizes_timed_and_all_day_events() -> None:
    timezone = ZoneInfo("Asia/Seoul")
    timed = GoogleCalendarProvider.normalize({"id": "timed", "summary": "회의", "start": {"dateTime": "2026-10-09T14:00:00+09:00"}, "end": {"dateTime": "2026-10-09T15:00:00+09:00"}}, "primary", timezone)
    all_day = GoogleCalendarProvider.normalize({"id": "day", "summary": "연차", "start": {"date": "2026-10-10"}, "end": {"date": "2026-10-11"}}, "primary", timezone)
    assert timed.starts_at.hour == 14 and timed.all_day is False
    assert all_day.starts_at == datetime(2026, 10, 10, tzinfo=timezone) and all_day.all_day is True


def test_google_calendar_without_oauth_configuration_stays_offline(tmp_path) -> None:
    provider = GoogleCalendarProvider(credentials_path=str(tmp_path / "missing.json"), token_store=FileTokenStore(tmp_path / "token.json"))
    assert provider.status().state == "offline"
    with pytest.raises(Exception, match="Google Calendar 계정을 먼저 연결"):
        provider.today_events()
