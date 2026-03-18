"""add FK document_id to heritage_assets

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_chunks_heritage_asset",
        "document_chunks_v3",
        "heritage_assets",
        ["document_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chunks_heritage_asset",
        "document_chunks_v3",
        type_="foreignkey",
    )
