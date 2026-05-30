from app.models.project import Project
from app.repositories.project_repo import ProjectRepo


class ProjectNotFoundError(Exception): ...


class ProjectService:
    def __init__(self, project_repo: ProjectRepo) -> None:
        self.project_repo = project_repo

    async def create(
        self, *, user_id: str, name: str, repository_url: str, branch: str
    ) -> Project:
        return await self.project_repo.create(
            user_id=user_id,
            name=name,
            repository_url=repository_url,
            branch=branch,
        )

    async def list_for_user(self, user_id: str) -> list[Project]:
        return await self.project_repo.list_for_user(user_id)

    async def get_owned(self, *, project_id: str, user_id: str) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None or project.user_id != user_id:
            # Same shape for "not yours" and "doesn't exist" — see ensure_owner.
            raise ProjectNotFoundError(project_id)
        return project

    async def update(
        self, project: Project, *, name: str | None, branch: str | None
    ) -> Project:
        if name is not None:
            project.name = name
        if branch is not None:
            project.branch = branch
        return project

    async def delete(self, project: Project) -> None:
        await self.project_repo.delete(project)
