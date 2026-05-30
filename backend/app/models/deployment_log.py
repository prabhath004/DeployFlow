from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_id
from app.models.enums import LogLevel


class DeploymentLog(Base):
    __tablename__ = "deployment_logs"

    id: Mapped[str] = mapped_column(
        String(40), primary_key=True, default=lambda: new_id("log")
    )
    deployment_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    level: Mapped[str] = mapped_column(String(10), nullable=False, default=LogLevel.INFO.value)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="worker")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
