from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.repositories.project_repo import ProjectRepo
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def _service(session) -> ProjectService:
    return ProjectService(ProjectRepo(session))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
)
async def create_project(
    payload: ProjectCreateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectResponse:
    project = await _service(session).create(
        user_id=current_user.id,
        name=payload.name,
        repository_url=str(payload.repository_url),
        branch=payload.branch,
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[ProjectResponse]:
    projects = await _service(session).list_for_user(current_user.id)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectResponse:
    try:
        project = await _service(session).get_owned(
            project_id=project_id, user_id=current_user.id
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectResponse:
    service = _service(session)
    try:
        project = await service.get_owned(
            project_id=project_id, user_id=current_user.id
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    project = await service.update(project, name=payload.name, branch=payload.branch)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    service = _service(session)
    try:
        project = await service.get_owned(
            project_id=project_id, user_id=current_user.id
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    await service.delete(project)
