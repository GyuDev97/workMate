from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from server.models.schemas import Priority, Task, TaskCreate, TaskStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskRepository:
    """Small SQLite repository: portable, zero-service setup, and easy to replace later."""

    def __init__(self, database_path: str | Path = "data/workmate.db") -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                    priority TEXT NOT NULL, due_at TEXT, status TEXT NOT NULL,
                    source TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )"""
            )
            # Fresh installations are useful immediately without polluting an existing user's list.
            if connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
                now = utcnow()
                examples = [
                    ("RAG 테스트 결과 확인", "김대리에게 검토 의견을 공유하기", Priority.HIGH, now + timedelta(hours=5)),
                    ("김대리 메일 답장", "검토 완료 예정 시각을 회신하기", Priority.HIGH, now + timedelta(hours=3)),
                    ("API 문서 확인", "Bizmeka 연동 전 필요한 항목 정리", Priority.MEDIUM, now + timedelta(days=1)),
                    ("주간 업무 정리", "WorkMemory 연동 전 주요 결정 기록 준비", Priority.LOW, now + timedelta(days=2)),
                ]
                for title, description, priority, due_at in examples:
                    connection.execute(
                        "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid4()), title, description, priority.value, due_at.isoformat(), TaskStatus.TODO.value,
                         "mock", now.isoformat(), now.isoformat()),
                    )

    def list(self) -> list[Task]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks ORDER BY CASE status WHEN 'DONE' THEN 1 ELSE 0 END, due_at IS NULL, due_at, created_at DESC"
            ).fetchall()
        return [self._to_task(row) for row in rows]

    def create(self, payload: TaskCreate) -> Task:
        now = utcnow()
        task = Task(
            id=str(uuid4()), title=payload.title, description=payload.description,
            priority=payload.priority, due_at=payload.due_at, status=TaskStatus.TODO,
            source=payload.source, created_at=now, updated_at=now,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task.id, task.title, task.description, task.priority.value,
                 task.due_at.isoformat() if task.due_at else None, task.status.value,
                 task.source, task.created_at.isoformat(), task.updated_at.isoformat()),
            )
        return task

    def update_status(self, task_id: str, status: TaskStatus) -> Task | None:
        now = utcnow().isoformat()
        with self._connect() as connection:
            cursor = connection.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status.value, now, task_id))
            if not cursor.rowcount:
                return None
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._to_task(row)

    @staticmethod
    def _to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"], title=row["title"], description=row["description"], priority=Priority(row["priority"]),
            due_at=datetime.fromisoformat(row["due_at"]) if row["due_at"] else None,
            status=TaskStatus(row["status"]), source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )
