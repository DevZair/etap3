from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, offset: int, limit: int) -> list[Task]:
        result = await self.session.execute(
            select(Task).order_by(Task.id).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def create(self, values: dict) -> Task:
        task = Task(**values)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def update(self, task: Task, values: dict) -> Task:
        for name, value in values.items():
            setattr(task, name, value)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.commit()

