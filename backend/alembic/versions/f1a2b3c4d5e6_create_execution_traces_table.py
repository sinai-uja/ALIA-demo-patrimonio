"""create execution_traces table

Revision ID: f1a2b3c4d5e6
Revises: abf44d053886
Create Date: 2026-04-11 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "abf44d053886"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_type", sa.String(32), nullable=False),
        sa.Column("execution_id", sa.String(128), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("username", sa.String(128), nullable=True),
        sa.Column("user_profile_type", sa.String(64), nullable=True),
        sa.Column("query", sa.Text, nullable=True),
        sa.Column("pipeline_mode", sa.String(32), nullable=True),
        sa.Column(
            "steps",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "summary",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("feedback_value", sa.SmallInteger, nullable=True),
        sa.Column("status", sa.String(16), server_default="success"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_execution_traces_type_date",
        "execution_traces",
        ["execution_type", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_execution_traces_user",
        "execution_traces",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_execution_traces_execution_id",
        "execution_traces",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_execution_traces_execution_id", table_name="execution_traces")
    op.drop_index("ix_execution_traces_user", table_name="execution_traces")
    op.drop_index("ix_execution_traces_type_date", table_name="execution_traces")
    op.drop_table("execution_traces")
