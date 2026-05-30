from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from ulid import ULID


class Base(DeclarativeBase):
    """Single declarative base for all ORM models."""


def new_id(prefix: str) -> str:
    """Generate a prefixed ULID identifier, e.g. `usr_01HZ...`.

    ULIDs are 26-char Crockford base32, time-sortable, and collision-resistant.
    The prefix makes IDs self-describing in logs and API responses.
    """
    return f"{prefix}_{ULID()}"


class TimestampMixin:
    """Reusable created_at / updated_at columns.

    `server_default=func.now()` lets Postgres own the timestamp so the value is
    consistent regardless of which process inserted the row.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
