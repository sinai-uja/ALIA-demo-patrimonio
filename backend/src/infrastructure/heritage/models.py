from datetime import datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.shared.persistence.base import Base


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
