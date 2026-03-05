"""Add updated_at to messages.

Revision ID: 002_updated_at
Revises: 001_initial
Create Date: 2025-03-05

Example upgrade: adds a column so you can see upgrade/downgrade in action.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_updated_at"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False))


def downgrade() -> None:
    op.drop_column("messages", "updated_at")
