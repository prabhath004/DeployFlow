from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment_log import DeploymentLog
from app.models.enums import LogLevel


class LogRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_deployment(
        self, deployment_id: str, limit: int = 500
    ) -> list[DeploymentLog]:
        result = await self.session.execute(
            select(DeploymentLog)
            .where(DeploymentLog.deployment_id == deployment_id)
            .order_by(DeploymentLog.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def append(
        self,
        *,
        deployment_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        source: str = "worker",
    ) -> DeploymentLog:
        log = DeploymentLog(
            deployment_id=deployment_id,
            level=level.value,
            source=source,
            message=message,
        )
        self.session.add(log)
        await self.session.flush()
        return log
