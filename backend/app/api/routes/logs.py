import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.api.deps import CurrentUser, RedisDep, SessionDep
from app.repositories.deployment_repo import DeploymentRepo
from app.repositories.log_repo import LogRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.log import LogEntryResponse
from app.services.deployment_service import (
    DeploymentNotFoundError,
    DeploymentService,
)
from app.services.log_stream_service import LogStreamService

router = APIRouter(prefix="/deployments", tags=["logs"])


@router.get("/{deployment_id}/logs", response_model=list[LogEntryResponse])
async def get_deployment_logs(
    deployment_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> list[LogEntryResponse]:
    service = DeploymentService(session, DeploymentRepo(session), ProjectRepo(session))
    try:
        await service.get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    logs = await LogRepo(session).list_for_deployment(deployment_id)
    return [LogEntryResponse.model_validate(log) for log in logs]


@router.get("/{deployment_id}/logs/stream")
async def stream_deployment_logs(
    deployment_id: str,
    session: SessionDep,
    redis: RedisDep,
    current_user: CurrentUser,
) -> EventSourceResponse:
    """Server-Sent Events stream of live log lines from the worker.

    Flow: client GETs this endpoint with their JWT, the API verifies
    ownership, subscribes to `logs:{deployment_id}` on Redis, and forwards
    every published message as an SSE event. Disconnects auto-clean.
    """
    service = DeploymentService(session, DeploymentRepo(session), ProjectRepo(session))
    try:
        await service.get_owned(
            deployment_id=deployment_id, user_id=current_user.id
        )
    except DeploymentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    stream = LogStreamService(redis)

    async def event_gen() -> AsyncIterator[dict[str, str]]:
        async for entry in stream.subscribe(deployment_id):
            yield {"event": "log", "data": json.dumps(entry)}

    return EventSourceResponse(event_gen())
