from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deployment_id: str
    level: str
    source: str
    message: str
    created_at: datetime
