from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.deployment import DeploymentResponse, DeploymentTriggerRequest
from app.services.deployment_service import (
    DeploymentNotCancellableError,
    DeploymentNotFoundError,
    DeploymentNotRetryableError,
    DeploymentService,
    ProjectNotFoundError,
)


def _service(session) -> DeploymentService:
    return DeploymentService(DeploymentRepo(session), ProjectRepo(session))


# Trigger and list live under /projects/{project_id}/deployments
project_router = APIRouter(prefix="/projects/{project_id}/deployments", tags=["deployments"])


@project_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DeploymentResponse,
)
async def trigger_deployment(
    project_id: str,
    payload: DeploymentTriggerRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    try:
        deployment = await _service(session).trigger(
            project_id=project_id,
            user_id=current_user.id,
            branch_override=payload.branch,
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return DeploymentResponse.model_validate(deployment)


@project_router.get("", response_model=list[DeploymentResponse])
async def list_deployments(
    project_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[DeploymentResponse]:
    try:
        deployments = await _service(session).list_for_project(
            project_id=project_id, user_id=current_user.id
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return [DeploymentResponse.model_validate(d) for d in deployments]


# Single-deployment ops live under /deployments/{deployment_id}
deployment_router = APIRouter(prefix="/deployments", tags=["deployments"])


@deployment_router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    try:
        deployment = await _service(session).get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return DeploymentResponse.model_validate(deployment)


@deployment_router.post("/{deployment_id}/retry", response_model=DeploymentResponse)
async def retry_deployment(
    deployment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    service = _service(session)
    try:
        deployment = await service.get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        deployment = await service.retry(deployment)
    except DeploymentNotRetryableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only FAILED deployments can be retried",
        )
    return DeploymentResponse.model_validate(deployment)


@deployment_router.post("/{deployment_id}/cancel", response_model=DeploymentResponse)
async def cancel_deployment(
    deployment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    service = _service(session)
    try:
        deployment = await service.get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        deployment = await service.cancel(deployment)
    except DeploymentNotCancellableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deployment is already in a terminal state",
        )
    return DeploymentResponse.model_validate(deployment)
