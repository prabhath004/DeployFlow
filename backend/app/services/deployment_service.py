from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.enums import DeploymentStatus
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.project_repo import ProjectRepo
from app.observability import metrics as obs_metrics
from app.observability.tracing import tracer
from app.services.cache_service import CacheService
from app.services.deployment_state_machine import (
    TERMINAL,
    assert_transition,
)
from app.services.queue_service import QueueService
from app.services.rate_limit_service import RateLimitService


class DeploymentNotFoundError(Exception): ...
class DeploymentNotRetryableError(Exception): ...
class DeploymentNotCancellableError(Exception): ...
class ProjectNotFoundError(Exception): ...


class DeploymentService:
    """All deployment writes go through this service so the state machine
    is enforced in exactly one place. Cache and rate-limit are optional
    collaborators — pass None to disable (handy in tests)."""

    def __init__(
        self,
        session: AsyncSession,
        deployment_repo: DeploymentRepo,
        project_repo: ProjectRepo,
        cache: CacheService | None = None,
        rate_limit: RateLimitService | None = None,
        queue: QueueService | None = None,
    ) -> None:
        self.session = session
        self.deployment_repo = deployment_repo
        self.project_repo = project_repo
        self.cache = cache
        self.rate_limit = rate_limit
        self.queue = queue

    async def trigger(
        self, *, project_id: str, user_id: str, branch_override: str | None
    ) -> Deployment:
        # Phase 5: check the per-user rate limit before doing any DB work.
        if self.rate_limit is not None:
            await self.rate_limit.hit_deploy(user_id)

        project = await self.project_repo.get(project_id)
        if project is None or project.user_id != user_id:
            raise ProjectNotFoundError(project_id)

        deployment = await self.deployment_repo.create(
            project_id=project.id,
            user_id=user_id,
            branch=branch_override or project.branch,
        )
        await self._set_status(deployment, DeploymentStatus.QUEUED)

        # Phase 6: hand the job off to the worker. Payload matches PRD §9.7.
        # CRITICAL ORDERING: commit FIRST so the worker can see the row when
        # it consumes the message.
        if self.queue is not None:
            await self.session.commit()
            with tracer.start_as_current_span("queue.publish") as span:
                span.set_attribute("deployflow.deployment_id", deployment.id)
                with obs_metrics.timed_publish():
                    await self.queue.publish(
                        {
                            "deployment_id": deployment.id,
                            "project_id": project.id,
                            "user_id": user_id,
                            "repository_url": project.repository_url,
                            "branch": deployment.branch,
                            "attempt": deployment.attempt,
                        }
                    )
        obs_metrics.inc_triggered()
        return deployment

    async def get_owned(
        self, *, deployment_id: str, user_id: str
    ) -> Deployment:
        deployment = await self.deployment_repo.get(deployment_id)
        if deployment is None or deployment.user_id != user_id:
            raise DeploymentNotFoundError(deployment_id)
        return deployment

    async def get_status_cached(self, *, deployment_id: str, user_id: str) -> str:
        """Cache-aside read: Redis → DB fallback. Always verifies ownership
        against the DB row, since the cache key alone doesn't authenticate."""
        deployment = await self.get_owned(
            deployment_id=deployment_id, user_id=user_id
        )
        if self.cache is not None:
            cached = await self.cache.get_deployment_status(deployment_id)
            if cached is not None:
                return cached
            await self.cache.set_deployment_status(deployment_id, deployment.status)
        return deployment.status

    async def list_for_project(
        self, *, project_id: str, user_id: str
    ) -> list[Deployment]:
        project = await self.project_repo.get(project_id)
        if project is None or project.user_id != user_id:
            raise ProjectNotFoundError(project_id)
        return await self.deployment_repo.list_for_project(project_id)

    async def retry(self, deployment: Deployment) -> Deployment:
        current = DeploymentStatus(deployment.status)
        if current != DeploymentStatus.FAILED:
            raise DeploymentNotRetryableError(deployment.id)
        project = await self.project_repo.get(deployment.project_id)
        if project is None or project.user_id != deployment.user_id:
            raise ProjectNotFoundError(deployment.project_id)
        await self._set_status(deployment, DeploymentStatus.RETRYING)
        deployment.attempt += 1
        deployment.error_message = None
        deployment.started_at = None
        deployment.finished_at = None
        await self._set_status(deployment, DeploymentStatus.QUEUED)
        if self.queue is not None:
            await self.session.commit()
            with tracer.start_as_current_span("queue.publish_retry") as span:
                span.set_attribute("deployflow.deployment_id", deployment.id)
                with obs_metrics.timed_publish():
                    await self.queue.publish(
                        {
                            "deployment_id": deployment.id,
                            "project_id": project.id,
                            "user_id": deployment.user_id,
                            "repository_url": project.repository_url,
                            "branch": deployment.branch,
                            "attempt": deployment.attempt,
                        }
                    )
        return deployment

    async def cancel(self, deployment: Deployment) -> Deployment:
        current = DeploymentStatus(deployment.status)
        if current in TERMINAL:
            raise DeploymentNotCancellableError(deployment.id)
        await self._set_status(deployment, DeploymentStatus.CANCELLED)
        deployment.finished_at = datetime.now(timezone.utc)
        return deployment

    async def _set_status(
        self, deployment: Deployment, new_status: DeploymentStatus
    ) -> None:
        current = DeploymentStatus(deployment.status)
        assert_transition(current, new_status)
        deployment.status = new_status.value
        now = datetime.now(timezone.utc)
        if new_status == DeploymentStatus.RUNNING and deployment.started_at is None:
            deployment.started_at = now
        if new_status in (
            DeploymentStatus.SUCCEEDED,
            DeploymentStatus.FAILED,
            DeploymentStatus.CANCELLED,
        ):
            deployment.finished_at = now
        # Cache-aside write: DB row is already mutated; mirror to Redis.
        # Failure here is non-fatal — cache can rebuild on next read miss.
        if self.cache is not None:
            try:
                await self.cache.set_deployment_status(deployment.id, new_status.value)
            except Exception:
                pass
