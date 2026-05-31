from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_id
from app.models.enums import DeploymentStatus


class Deployment(Base, TimestampMixin):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("dep")
    )
    project_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeploymentStatus.PENDING.value, index=True
    )
    branch: Mapped[str] = mapped_column(String(120), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deployment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
