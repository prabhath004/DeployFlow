from datetime import datetime, timezone

from app.models.deployment import Deployment
from app.models.enums import DeploymentStatus
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.project_repo import ProjectRepo
from app.services.deployment_state_machine import (
    TERMINAL,
    assert_transition,
)


class DeploymentNotFoundError(Exception): ...
class DeploymentNotRetryableError(Exception): ...
class DeploymentNotCancellableError(Exception): ...
class ProjectNotFoundError(Exception): ...


class DeploymentService:
    """All deployment writes go through this service so the state machine
    is enforced in exactly one place."""

    def __init__(
        self,
        deployment_repo: DeploymentRepo,
        project_repo: ProjectRepo,
    ) -> None:
        self.deployment_repo = deployment_repo
        self.project_repo = project_repo

    async def trigger(
        self, *, project_id: str, user_id: str, branch_override: str | None
    ) -> Deployment:
        """Create a deployment row in QUEUED state.

        Phase 6 will additionally enqueue a job to Redis/SQS at the end of
        this method via the queue_service abstraction.
        """
        project = await self.project_repo.get(project_id)
        if project is None or project.user_id != user_id:
            raise ProjectNotFoundError(project_id)

        deployment = await self.deployment_repo.create(
            project_id=project.id,
            user_id=user_id,
            branch=branch_override or project.branch,
        )
        # PENDING -> QUEUED via the state machine.
        await self._set_status(deployment, DeploymentStatus.QUEUED)
        return deployment

    async def get_owned(
        self, *, deployment_id: str, user_id: str
    ) -> Deployment:
        deployment = await self.deployment_repo.get(deployment_id)
        if deployment is None or deployment.user_id != user_id:
            raise DeploymentNotFoundError(deployment_id)
        return deployment

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
        # FAILED -> RETRYING -> QUEUED, both legal per the state machine.
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
