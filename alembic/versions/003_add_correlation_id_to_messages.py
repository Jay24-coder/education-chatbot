"""Add correlation_id to messages for request-flow tracing.

Revision ID: 003_correlation_id
Revises: 002_updated_at
Create Date: 2025-03-05

Mirrors app/db/migrations/002_add_correlation_id_to_messages.sql.
Uses IF NOT EXISTS so safe to run on DBs that already have the column.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "003_correlation_id"
down_revision: Union[str, None] = "002_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(255) NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_correlation_id
            ON messages (correlation_id) WHERE correlation_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_messages_correlation_id")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS correlation_id")
