from server.database.repository import TaskRepository
from server.models.schemas import Task, TaskCreate, TaskStatus


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def list_tasks(self) -> list[Task]:
        return self.repository.list()

    def create_task(self, payload: TaskCreate) -> Task:
        return self.repository.create(payload)

    def complete_task(self, task_id: str) -> Task | None:
        return self.repository.update_status(task_id, TaskStatus.DONE)
