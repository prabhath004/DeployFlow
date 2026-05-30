from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import WorkerStatus


class WorkerHeartbeat(Base):
    """Periodically updated by each worker process. The API uses last_seen_at
    to detect dead workers and re-queue their in-flight jobs in Phase 6.

    Phase 5 will additionally mirror heartbeats in Redis with a short TTL for
    cheap liveness checks; this table is the durable record.
    """

    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkerStatus.IDLE.value
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
