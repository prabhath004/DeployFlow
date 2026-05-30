from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.log_repo import LogRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.log import LogEntryResponse
from app.services.deployment_service import (
    DeploymentNotFoundError,
    DeploymentService,
)

# Phase 4: GET /deployments/{id}/logs returns the stored log history.
# Phase 6: /logs/stream (Server-Sent Events) will join Redis pub/sub.
router = APIRouter(prefix="/deployments", tags=["logs"])


@router.get("/{deployment_id}/logs", response_model=list[LogEntryResponse])
async def get_deployment_logs(
    deployment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[LogEntryResponse]:
    service = DeploymentService(DeploymentRepo(session), ProjectRepo(session))
    try:
        await service.get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    logs = await LogRepo(session).list_for_deployment(deployment_id)
    return [LogEntryResponse.model_validate(log) for log in logs]
