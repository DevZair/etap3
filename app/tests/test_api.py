from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.tasks import get_service
from app.main import app
from app.services.tasks import TaskService


class MemoryRepository:
    def __init__(self) -> None:
        self.items = {}
        self.next_id = 1

    async def list(self, offset: int, limit: int):
        return list(self.items.values())[offset : offset + limit]

    async def get(self, task_id: int):
        return self.items.get(task_id)

    async def create(self, values: dict):
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(id=self.next_id, created_at=now, updated_at=now, **values)
        self.items[item.id] = item
        self.next_id += 1
        return item

    async def update(self, item, values: dict):
        for name, value in values.items():
            setattr(item, name, value)
        item.updated_at = datetime.now(timezone.utc)
        return item

    async def delete(self, item) -> None:
        del self.items[item.id]


def test_task_crud() -> None:
    service = TaskService(MemoryRepository(), None, 30)
    app.dependency_overrides[get_service] = lambda: service
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/tasks", json={"title": "  Learn DevOps  "})
            assert created.status_code == 201
            task_id = created.json()["id"]
            assert created.json()["title"] == "Learn DevOps"
            assert client.get(f"/api/v1/tasks/{task_id}").status_code == 200
            assert len(client.get("/api/v1/tasks").json()) == 1
            updated = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
            assert updated.status_code == 200
            assert updated.json()["status"] == "done"
            assert client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
            assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_validation_and_health() -> None:
    service = TaskService(MemoryRepository(), None, 30)
    app.dependency_overrides[get_service] = lambda: service
    try:
        with TestClient(app) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert client.post("/api/v1/tasks", json={"title": "   "}).status_code == 422
            assert client.post("/api/v1/tasks", json={"title": "ok", "status": "bad"}).status_code == 422
            assert client.get("/api/v1/tasks?limit=101").status_code == 422
            assert client.patch("/api/v1/tasks/1", json={"title": None}).status_code == 422
    finally:
        app.dependency_overrides.clear()

