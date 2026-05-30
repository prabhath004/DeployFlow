from datetime import datetime, timezone

from app.models.deployment import Deployment
from app.models.enums import DeploymentStatus
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.project_repo import ProjectRepo
from app.services.cache_service import CacheService
from app.services.deployment_state_machine import (
    TERMINAL,
    assert_transition,
)
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
        deployment_repo: DeploymentRepo,
        project_repo: ProjectRepo,
        cache: CacheService | None = None,
        rate_limit: RateLimitService | None = None,
    ) -> None:
        self.deployment_repo = deployment_repo
        self.project_repo = project_repo
        self.cache = cache
        self.rate_limit = rate_limit

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
        await self._set_status(deployment, DeploymentStatus.RETRYING)
        await self._set_status(deployment, DeploymentStatus.QUEUED)
        deployment.attempt += 1
        deployment.error_message = None
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
        import sys
        print(f"[diag] _set_status cache={self.cache is not None} dep={deployment.id} new={new_status.value}", file=sys.stderr, flush=True)
        if self.cache is not None:
            try:
                await self.cache.set_deployment_status(deployment.id, new_status.value)
                print(f"[diag] cache.set OK key=deployment:{deployment.id}:status", file=sys.stderr, flush=True)
            except Exception as exc:
                print(f"[cache write failed] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
