from fastapi import APIRouter, BackgroundTasks, HTTPException

from server.api.dependencies import agent, calendar_action_service, calendar_provider, dashboard_service, knowledge_service, task_service
from server.models.schemas import ActionExecutionResult, CalendarConnectionStatus, ChatRequest, ChatResponse, Dashboard, KnowledgeArtifact, KnowledgeArtifactDetail, KnowledgeSource, KnowledgeSourceCreate, SyncRun, Task, TaskCreate

router = APIRouter(prefix="/api/v1")


@router.get("/dashboard", response_model=Dashboard)
def dashboard() -> Dashboard:
    return dashboard_service().get_dashboard()


@router.get("/tasks", response_model=list[Task])
def list_tasks() -> list[Task]:
    return task_service().list_tasks()


@router.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate) -> Task:
    return task_service().create_task(payload)


@router.post("/tasks/{task_id}/complete", response_model=Task)
def complete_task(task_id: str) -> Task:
    task = task_service().complete_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return agent().respond(payload.message, payload.conversation_id)


@router.get("/calendar/status", response_model=CalendarConnectionStatus)
def calendar_status() -> CalendarConnectionStatus:
    return calendar_provider().status()


@router.post("/calendar/connect", response_model=CalendarConnectionStatus)
def calendar_connect() -> CalendarConnectionStatus:
    try:
        return calendar_provider().connect()
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/calendar/verify", response_model=CalendarConnectionStatus)
def calendar_verify() -> CalendarConnectionStatus:
    try:
        return calendar_provider().verify()
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/calendar/disconnect", response_model=CalendarConnectionStatus)
def calendar_disconnect() -> CalendarConnectionStatus:
    return calendar_provider().disconnect()


@router.post("/actions/{action_id}/approve", response_model=ActionExecutionResult)
def approve_action(action_id: str) -> ActionExecutionResult:
    try:
        return calendar_action_service().approve(action_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Action not found") from error


@router.get("/knowledge/sources", response_model=list[KnowledgeSource])
def list_knowledge_sources() -> list[KnowledgeSource]:
    return knowledge_service().list_sources()


@router.post("/knowledge/sources", response_model=KnowledgeSource, status_code=201)
def create_knowledge_source(payload: KnowledgeSourceCreate) -> KnowledgeSource:
    try:
        return knowledge_service().create_source(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/knowledge/sources/{source_id}/scan", response_model=SyncRun)
def scan_knowledge_source(source_id: str, background_tasks: BackgroundTasks) -> SyncRun:
    try:
        run = knowledge_service().start_scan(source_id)
        background_tasks.add_task(knowledge_service().scan, source_id, run.id)
        return run
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/knowledge/sync-runs/{run_id}", response_model=SyncRun)
def knowledge_sync_run(run_id: str) -> SyncRun:
    try: return knowledge_service().get_run(run_id)
    except KeyError as error: raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/knowledge/sync-runs/{run_id}/cancel", response_model=SyncRun)
def cancel_knowledge_sync_run(run_id: str) -> SyncRun:
    try: return knowledge_service().cancel(run_id)
    except KeyError as error: raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/knowledge/sources/{source_id}/artifacts", response_model=list[KnowledgeArtifact])
def list_knowledge_artifacts(source_id: str) -> list[KnowledgeArtifact]:
    return knowledge_service().list_artifacts(source_id)


@router.get("/knowledge/artifacts/{artifact_id}", response_model=KnowledgeArtifactDetail)
def knowledge_artifact(artifact_id: str) -> KnowledgeArtifactDetail:
    try:
        return knowledge_service().artifact(artifact_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
