"""Initial schema: conversations, messages, jobs.

Revision ID: 001_initial
Revises:
Create Date: 2025-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "idx_messages_correlation_id",
        "messages",
        ["correlation_id"],
        unique=False,
        postgresql_where=sa.text("correlation_id IS NOT NULL"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), server_default="PENDING", nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("result", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_jobs_status_created_at",
        "jobs",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_status_created_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("idx_messages_correlation_id", table_name="messages")
    op.drop_index("idx_messages_conversation_id_created_at", table_name="messages")
    op.drop_table("messages")
    op.drop_table("conversations")
