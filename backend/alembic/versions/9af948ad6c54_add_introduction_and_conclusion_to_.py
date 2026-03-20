"""add introduction and conclusion to virtual_routes

Revision ID: 9af948ad6c54
Revises: 0691450af90f
Create Date: 2026-03-20 07:47:22.312773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9af948ad6c54'
down_revision: Union[str, Sequence[str], None] = '0691450af90f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("virtual_routes", sa.Column("introduction", sa.Text(), nullable=True))
    op.add_column("virtual_routes", sa.Column("conclusion", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("virtual_routes", "conclusion")
    op.drop_column("virtual_routes", "introduction")
