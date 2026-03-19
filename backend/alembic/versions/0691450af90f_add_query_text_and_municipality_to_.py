"""add query_text and municipality to virtual_routes

Revision ID: 0691450af90f
Revises: c3d4e5f6a7b8
Create Date: 2026-03-19 16:09:48.305385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0691450af90f'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("virtual_routes", sa.Column("query_text", sa.String(), nullable=True))
    op.add_column("virtual_routes", sa.Column("municipality", sa.String(), nullable=True))
    op.create_index("ix_virtual_routes_municipality", "virtual_routes", ["municipality"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_virtual_routes_municipality", table_name="virtual_routes")
    op.drop_column("virtual_routes", "municipality")
    op.drop_column("virtual_routes", "query_text")
