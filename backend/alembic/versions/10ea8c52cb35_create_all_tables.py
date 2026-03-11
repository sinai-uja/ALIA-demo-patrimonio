"""create all tables

Revision ID: 10ea8c52cb35
Revises: ecfb8a0665c7
Create Date: 2026-03-10 23:17:10.918533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '10ea8c52cb35'
down_revision: Union[str, Sequence[str], None] = 'ecfb8a0665c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
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
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    # HNSW index for fast cosine similarity search on embeddings
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    # --- virtual_routes ---
    op.create_table(
        "virtual_routes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("stops", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_virtual_routes_province", "virtual_routes", ["province"])

    # --- chat_sessions ---
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    # Drop in reverse order to respect foreign key dependencies
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_index("ix_virtual_routes_province", table_name="virtual_routes")
    op.drop_table("virtual_routes")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
