"""create heritage_assets table for enriched API data

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-16 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "heritage_assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("heritage_type", sa.String(), nullable=False),
        sa.Column("denomination", sa.String(), nullable=True),
        sa.Column("province", sa.String(), nullable=True),
        sa.Column("municipality", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("image_ids", sa.dialects.postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("protection", sa.String(), nullable=True),
        sa.Column(
            "raw_data",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes for common query patterns
    op.create_index("ix_heritage_assets_heritage_type", "heritage_assets", ["heritage_type"])
    op.create_index("ix_heritage_assets_province", "heritage_assets", ["province"])
    op.execute(
        "CREATE INDEX ix_heritage_assets_raw_data ON heritage_assets USING GIN (raw_data)"
    )


def downgrade() -> None:
    op.drop_table("heritage_assets")
