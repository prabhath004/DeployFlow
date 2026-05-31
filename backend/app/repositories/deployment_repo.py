from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.enums import DeploymentStatus


class DeploymentRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, deployment_id: str) -> Deployment | None:
        return await self.session.get(Deployment, deployment_id)

    async def list_for_project(self, project_id: str, limit: int = 50) -> list[Deployment]:
        result = await self.session.execute(
            select(Deployment)
            .where(Deployment.project_id == project_id)
            .order_by(Deployment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self, *, project_id: str, user_id: str, branch: str
    ) -> Deployment:
        deployment = Deployment(
            project_id=project_id,
            user_id=user_id,
            branch=branch,
            status=DeploymentStatus.PENDING.value,
        )
        self.session.add(deployment)
        await self.session.flush()
        return deployment

    async def update_status(
        self, deployment: Deployment, status: DeploymentStatus
    ) -> None:
        deployment.status = status.value

    async def delete(self, deployment: Deployment) -> None:
        await self.session.delete(deployment)
