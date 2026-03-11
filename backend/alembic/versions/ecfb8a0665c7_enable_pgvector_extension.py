"""enable_pgvector_extension

Revision ID: ecfb8a0665c7
Revises: 
Create Date: 2026-03-10 17:33:57.355733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecfb8a0665c7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
