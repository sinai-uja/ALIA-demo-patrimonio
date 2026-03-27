import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from src.db.base import Base


class UserFeedbackModel(Base):
    __tablename__ = "user_feedback"

    id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    value = Column(SmallInteger, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "target_type", "target_id",
            name="uq_user_feedback_user_target",
        ),
        Index("ix_user_feedback_target", "target_type", "target_id"),
    )
