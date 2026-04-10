"""drop total_duration_minutes from virtual_routes

Revision ID: abf44d053886
Revises: a980e4d9d33f
Create Date: 2026-04-10 23:31:10.667957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abf44d053886'
down_revision: Union[str, Sequence[str], None] = 'a980e4d9d33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('virtual_routes', 'total_duration_minutes')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'virtual_routes',
        sa.Column('total_duration_minutes', sa.INTEGER(), autoincrement=False, nullable=False),
    )
