"""create document_chunks_v5 for SINAI 768-dim embeddings

Revision ID: e5f6a7b8c9d0
Revises: f1a2b3c4d5e6
Create Date: 2026-05-15 10:00:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Read embedding dimension from env (default 768 for SINAI/MrBERT, use 1024 for Qwen3)
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "768"))


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create document_chunks_v5
    # ------------------------------------------------------------------
    op.create_table(
        "document_chunks_v5",
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
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
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
        "ix_document_chunks_v5_document_id",
        "document_chunks_v5",
        ["document_id"],
    )

    # ------------------------------------------------------------------
    # 3. HNSW index on embedding for cosine similarity
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_document_chunks_v5_embedding_hnsw "
        "ON document_chunks_v5 USING hnsw (embedding vector_cosine_ops)"
    )

    # ------------------------------------------------------------------
    # 4. search_vector tsvector column
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE document_chunks_v5 "
        "ADD COLUMN search_vector tsvector"
    )

    # ------------------------------------------------------------------
    # 5. GIN index on search_vector
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_document_chunks_v5_search_vector "
        "ON document_chunks_v5 USING GIN (search_vector)"
    )

    # ------------------------------------------------------------------
    # 6. GIN index on metadata JSONB
    # ------------------------------------------------------------------
    op.execute(
        "CREATE INDEX ix_document_chunks_v5_metadata "
        "ON document_chunks_v5 USING GIN (metadata)"
    )

    # ------------------------------------------------------------------
    # 7. Trigger function for auto-updating search_vector
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_search_vector_v5() RETURNS trigger AS $$
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
    # 8. Attach trigger to document_chunks_v5
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TRIGGER trg_update_search_vector_v5
          BEFORE INSERT OR UPDATE ON document_chunks_v5
          FOR EACH ROW EXECUTE FUNCTION update_search_vector_v5()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_update_search_vector_v5 ON document_chunks_v5"
    )
    op.execute("DROP FUNCTION IF EXISTS update_search_vector_v5()")
    op.drop_table("document_chunks_v5")
