"""add tsvector full-text search to document_chunks

Revision ID: ce98c0e62f84
Revises: 10ea8c52cb35
Create Date: 2026-03-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ce98c0e62f84'
down_revision: Union[str, Sequence[str], None] = '10ea8c52cb35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add tsvector column (nullable so existing rows are valid before backfill)
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )

    # 2. Backfill existing rows with weighted Spanish text search vectors
    op.execute(
        "UPDATE document_chunks SET search_vector = "
        "setweight(to_tsvector('spanish', coalesce(title, '')), 'A') || "
        "setweight(to_tsvector('spanish', coalesce(content, '')), 'B')"
    )

    # 3. Create GIN index for fast full-text search queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_search_vector "
        "ON document_chunks USING GIN (search_vector)"
    )

    # 4. Create trigger function to auto-update search_vector on INSERT/UPDATE
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_search_vector() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('spanish', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('spanish', coalesce(NEW.content, '')), 'B');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    # 5. Attach trigger to document_chunks table (drop first to ensure idempotency)
    op.execute("DROP TRIGGER IF EXISTS trg_update_search_vector ON document_chunks")
    op.execute(
        """
        CREATE TRIGGER trg_update_search_vector
          BEFORE INSERT OR UPDATE ON document_chunks
          FOR EACH ROW EXECUTE FUNCTION update_search_vector()
        """
    )


def downgrade() -> None:
    # Reverse order: drop trigger, function, index, column
    op.execute("DROP TRIGGER IF EXISTS trg_update_search_vector ON document_chunks")
    op.execute("DROP FUNCTION IF EXISTS update_search_vector()")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_search_vector")
    op.drop_column("document_chunks", "search_vector")
