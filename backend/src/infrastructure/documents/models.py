import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config import settings
from src.db.base import Base


class DocumentChunkModel(Base):
    __tablename__ = settings.chunks_table_name

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("heritage_assets.id"), nullable=False
    )
    heritage_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    province: Mapped[str] = mapped_column(String, nullable=False)
    municipality: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding = mapped_column(Vector(768), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(f"ix_{settings.chunks_table_name}_document_id", "document_id"),
    )


class HeritageAssetModel(Base):
    """Enriched heritage asset data from the IAPH API.

    Linked to document_chunks via FK: chunk.document_id → heritage_assets.id.
    """

    __tablename__ = "heritage_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    heritage_type: Mapped[str] = mapped_column(String, nullable=False)
    denomination: Mapped[str | None] = mapped_column(String, nullable=True)
    province: Mapped[str | None] = mapped_column(String, nullable=True)
    municipality: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    image_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    protection: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
