from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: str) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list_for_user(self, user_id: str) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self, *, user_id: str, name: str, repository_url: str, branch: str
    ) -> Project:
        project = Project(
            user_id=user_id, name=name, repository_url=repository_url, branch=branch
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
