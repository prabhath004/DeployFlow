from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.deployment import DeploymentResponse, DeploymentTriggerRequest
from app.services.cache_service import CacheService
from app.services.deployment_service import (
    DeploymentNotCancellableError,
    DeploymentNotFoundError,
    DeploymentNotRetryableError,
    DeploymentService,
    ProjectNotFoundError,
)
from app.services.queue_service import RedisStreamQueue
from app.services.rate_limit_service import (
    RateLimitExceededError,
    RateLimitService,
)


def _service(session, redis, settings) -> DeploymentService:
    return DeploymentService(
        session,
        DeploymentRepo(session),
        ProjectRepo(session),
        cache=CacheService(redis, settings),
        rate_limit=RateLimitService(redis, settings),
        queue=RedisStreamQueue(redis),
    )


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
    redis: RedisDep,
    settings: SettingsDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    try:
        deployment = await _service(session, redis, settings).trigger(
            project_id=project_id,
            user_id=current_user.id,
            branch_override=payload.branch,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many deployments — slow down",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return DeploymentResponse.model_validate(deployment)


@project_router.get("", response_model=list[DeploymentResponse])
async def list_deployments(
    project_id: str,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    current_user: CurrentUser,
) -> list[DeploymentResponse]:
    try:
        deployments = await _service(session, redis, settings).list_for_project(
            project_id=project_id, user_id=current_user.id
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return [DeploymentResponse.model_validate(d) for d in deployments]


deployment_router = APIRouter(prefix="/deployments", tags=["deployments"])


@deployment_router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    try:
        deployment = await _service(session, redis, settings).get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return DeploymentResponse.model_validate(deployment)


@deployment_router.get("/{deployment_id}/status")
async def get_deployment_status(
    deployment_id: str,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    current_user: CurrentUser,
) -> dict[str, str]:
    """Lightweight, cache-first status endpoint — for polling without
    pulling the whole deployment row."""
    try:
        status_value = await _service(session, redis, settings).get_status_cached(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deployment_id": deployment_id, "status": status_value}


@deployment_router.post("/{deployment_id}/retry", response_model=DeploymentResponse)
async def retry_deployment(
    deployment_id: str,
    session: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    service = _service(session, redis, settings)
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
    redis: RedisDep,
    settings: SettingsDep,
    current_user: CurrentUser,
) -> DeploymentResponse:
    service = _service(session, redis, settings)
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
