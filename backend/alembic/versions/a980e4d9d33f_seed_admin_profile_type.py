"""seed admin profile type

Revision ID: a980e4d9d33f
Revises: c3399e3f1d59
Create Date: 2026-03-29 09:43:17.342345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a980e4d9d33f'
down_revision: Union[str, Sequence[str], None] = 'c3399e3f1d59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert the 'admin' profile type if it doesn't already exist."""
    op.execute(
        """
        INSERT INTO user_profile_types (id, name, created_at)
        VALUES (gen_random_uuid(), 'admin', now())
        ON CONFLICT (name) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Remove the 'admin' profile type."""
    op.execute(
        """
        DELETE FROM user_profile_types WHERE name = 'admin';
        """
    )
