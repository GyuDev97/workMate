from fastapi import APIRouter, HTTPException

from server.api.dependencies import agent, dashboard_service, task_service
from server.models.schemas import ChatRequest, ChatResponse, Dashboard, Task, TaskCreate

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
