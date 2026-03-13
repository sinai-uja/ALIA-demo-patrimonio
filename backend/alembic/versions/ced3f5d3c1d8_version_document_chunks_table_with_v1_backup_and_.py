"""version document_chunks table with v1 backup and v2 for new chunking

Revision ID: ced3f5d3c1d8
Revises: ce98c0e62f84
Create Date: 2026-03-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'ced3f5d3c1d8'
down_revision: Union[str, Sequence[str], None] = 'ce98c0e62f84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Rename existing document_chunks -> document_chunks_v1
    #    PostgreSQL carries over all indexes, triggers, constraints, etc.
    # ------------------------------------------------------------------
    op.rename_table("document_chunks", "document_chunks_v1")

    # ------------------------------------------------------------------
    # 2. Create document_chunks_v2 with the same schema
    # ------------------------------------------------------------------
    op.create_table(
        "document_chunks_v2",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("heritage_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("municipality", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # 3. Index on document_id
    # ------------------------------------------------------------------
    op.create_index(
        "ix_document_chunks_v2_document_id",
        "document_chunks_v2",
        ["document_id"],
    )

    # ------------------------------------------------------------------
    # 4. Add search_vector tsvector column
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE document_chunks_v2 "
        "ADD COLUMN search_vector tsvector"
    )

    # ------------------------------------------------------------------
    # 5. GIN index on search_vector
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_document_chunks_v2_search_vector "
        "ON document_chunks_v2 USING GIN (search_vector)"
    )

    # ------------------------------------------------------------------
    # 6. Trigger function for auto-updating search_vector on v2
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_search_vector_v2() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('spanish', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('spanish', coalesce(NEW.content, '')), 'B');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    # ------------------------------------------------------------------
    # 7. Attach trigger to document_chunks_v2
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TRIGGER trg_update_search_vector_v2
          BEFORE INSERT OR UPDATE ON document_chunks_v2
          FOR EACH ROW EXECUTE FUNCTION update_search_vector_v2()
        """
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Reverse: drop v2 entirely, rename v1 back to document_chunks
    # ------------------------------------------------------------------

    # 1. Drop trigger and function for v2
    op.execute(
        "DROP TRIGGER IF EXISTS trg_update_search_vector_v2 ON document_chunks_v2"
    )
    op.execute("DROP FUNCTION IF EXISTS update_search_vector_v2()")

    # 2. Drop the v2 table (indexes are dropped automatically with the table)
    op.drop_table("document_chunks_v2")

    # 3. Rename v1 back to original name
    op.rename_table("document_chunks_v1", "document_chunks")
