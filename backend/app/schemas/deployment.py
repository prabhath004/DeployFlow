from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeploymentTriggerRequest(BaseModel):
    branch: str | None = Field(default=None, max_length=120)


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    user_id: str
    status: str
    branch: str
    commit_sha: str | None
    image_uri: str | None
    deployment_url: str | None
    error_message: str | None
    attempt: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
