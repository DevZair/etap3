from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_session
from app.repositories.tasks import TaskRepository
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_redis(request: Request) -> Redis | None:
    return getattr(request.app.state, "redis", None)


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis | None, Depends(get_redis)],
) -> TaskService:
    return TaskService(TaskRepository(session), redis, get_settings().cache_ttl_seconds)


Service = Annotated[TaskService, Depends(get_service)]


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, service: Service) -> TaskRead:
    return await service.create(data)


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    service: Service,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TaskRead]:
    return await service.list(offset, limit)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, service: Service) -> TaskRead:
    return await service.get(task_id)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, data: TaskUpdate, service: Service) -> TaskRead:
    return await service.update(task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, service: Service) -> None:
    await service.delete(task_id)

