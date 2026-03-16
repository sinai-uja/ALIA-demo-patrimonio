"""create document_chunks_v3 with metadata JSONB column

Revision ID: a1b2c3d4e5f6
Revises: ced3f5d3c1d8
Create Date: 2026-03-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ced3f5d3c1d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create document_chunks_v3 (same as v2 + metadata JSONB)
    # ------------------------------------------------------------------
    op.create_table(
        "document_chunks_v3",
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
            "metadata",
            sa.dialects.postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # 2. B-tree index on document_id
    # ------------------------------------------------------------------
    op.create_index(
        "ix_document_chunks_v3_document_id",
        "document_chunks_v3",
        ["document_id"],
    )

    # ------------------------------------------------------------------
    # 3. search_vector tsvector column
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE document_chunks_v3 "
        "ADD COLUMN search_vector tsvector"
    )

    # ------------------------------------------------------------------
    # 4. GIN index on search_vector
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_document_chunks_v3_search_vector "
        "ON document_chunks_v3 USING GIN (search_vector)"
    )

    # ------------------------------------------------------------------
    # 5. GIN index on metadata JSONB
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_document_chunks_v3_metadata "
        "ON document_chunks_v3 USING GIN (metadata)"
    )

    # ------------------------------------------------------------------
    # 6. Trigger function for auto-updating search_vector
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_search_vector_v3() RETURNS trigger AS $$
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
    # 7. Attach trigger to document_chunks_v3
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TRIGGER trg_update_search_vector_v3
          BEFORE INSERT OR UPDATE ON document_chunks_v3
          FOR EACH ROW EXECUTE FUNCTION update_search_vector_v3()
        """
    )


def downgrade() -> None:
    # 1. Drop trigger and function
    op.execute(
        "DROP TRIGGER IF EXISTS trg_update_search_vector_v3 ON document_chunks_v3"
    )
    op.execute("DROP FUNCTION IF EXISTS update_search_vector_v3()")

    # 2. Drop the v3 table
    op.drop_table("document_chunks_v3")
