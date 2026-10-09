import json
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.repositories.tasks import TaskRepository
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

logger = logging.getLogger(__name__)


class TaskNotFound(Exception):
    pass


class TaskService:
    def __init__(self, repository: TaskRepository, redis: Redis | None, cache_ttl: int) -> None:
        self.repository = repository
        self.redis = redis
        self.cache_ttl = cache_ttl

    async def list(self, offset: int, limit: int) -> list[TaskRead]:
        key = f"tasks:list:{offset}:{limit}"
        if self.redis is not None:
            try:
                cached = await self.redis.get(key)
                if cached is not None:
                    return [TaskRead.model_validate(item) for item in json.loads(cached)]
            except (RedisError, ValueError) as exc:
                logger.warning("cache read failed: %s", exc)

        tasks = [TaskRead.model_validate(task) for task in await self.repository.list(offset, limit)]
        if self.redis is not None:
            try:
                await self.redis.setex(
                    key, self.cache_ttl, json.dumps([task.model_dump(mode="json") for task in tasks])
                )
            except RedisError as exc:
                logger.warning("cache write failed: %s", exc)
        return tasks

    async def get(self, task_id: int) -> TaskRead:
        task = await self.repository.get(task_id)
        if task is None:
            raise TaskNotFound
        return TaskRead.model_validate(task)

    async def create(self, data: TaskCreate) -> TaskRead:
        task = await self.repository.create(data.model_dump(mode="json"))
        await self._invalidate_lists()
        return TaskRead.model_validate(task)

    async def update(self, task_id: int, data: TaskUpdate) -> TaskRead:
        task = await self.repository.get(task_id)
        if task is None:
            raise TaskNotFound
        updated = await self.repository.update(task, data.model_dump(exclude_unset=True, mode="json"))
        await self._invalidate_lists()
        return TaskRead.model_validate(updated)

    async def delete(self, task_id: int) -> None:
        task = await self.repository.get(task_id)
        if task is None:
            raise TaskNotFound
        await self.repository.delete(task)
        await self._invalidate_lists()

    async def _invalidate_lists(self) -> None:
        if self.redis is None:
            return
        try:
            async for key in self.redis.scan_iter(match="tasks:list:*"):
                await self.redis.delete(key)
        except RedisError as exc:
            logger.warning("cache invalidation failed: %s", exc)

