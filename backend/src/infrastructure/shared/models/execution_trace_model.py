"""SQLAlchemy ORM model for the execution_traces table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.infrastructure.shared.persistence.base import Base


class ExecutionTraceModel(Base):
    __tablename__ = "execution_traces"

    id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_type = Column(String(32), nullable=False)
    execution_id = Column(String(128), nullable=False)
    user_id = Column(PgUUID(as_uuid=True), nullable=True)
    username = Column(String(128), nullable=True)
    user_profile_type = Column(String(64), nullable=True)
    query = Column(Text, nullable=True)
    pipeline_mode = Column(String(32), nullable=True)
    steps = Column(JSONB, nullable=False, server_default="[]")
    summary = Column(JSONB, nullable=False, server_default="{}")
    feedback_value = Column(SmallInteger, nullable=True)
    status = Column(String(16), server_default="success")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_execution_traces_type_date",
            "execution_type",
            created_at.desc(),
        ),
        Index(
            "ix_execution_traces_user",
            "user_id",
            created_at.desc(),
        ),
        Index("ix_execution_traces_execution_id", "execution_id"),
    )

    def to_domain(self) -> ExecutionTrace:
        """Map ORM model to domain entity."""
        return ExecutionTrace(
            id=self.id,
            execution_type=self.execution_type,
            execution_id=self.execution_id,
            user_id=str(self.user_id) if self.user_id else None,
            username=self.username,
            user_profile_type=self.user_profile_type,
            query=self.query or "",
            pipeline_mode=self.pipeline_mode,
            steps=self.steps or [],
            summary=self.summary or {},
            feedback_value=self.feedback_value,
            status=self.status or "success",
            created_at=self.created_at,
        )
