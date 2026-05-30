from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    repository_url: HttpUrl
    branch: str = Field(default="main", min_length=1, max_length=120)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    branch: str | None = Field(default=None, min_length=1, max_length=120)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    repository_url: str
    branch: str
    status: str
    created_at: datetime
    updated_at: datetime
