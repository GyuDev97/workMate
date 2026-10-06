from server.models.schemas import TaskCreate
from server.services.tasks import TaskService


class TaskTool:
    name = "task"
    description = "Create and update workMate tasks."

    def __init__(self, service: TaskService) -> None:
        self.service = service

    def execute(self, **kwargs: object):
        return self.service.create_task(TaskCreate(**kwargs))
