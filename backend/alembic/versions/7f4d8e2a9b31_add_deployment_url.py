"""add deployment url

Revision ID: 7f4d8e2a9b31
Revises: a551dae9dee7
Create Date: 2026-05-30 20:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f4d8e2a9b31"
down_revision: Union[str, None] = "a551dae9dee7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deployments",
        sa.Column("deployment_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deployments", "deployment_url")
