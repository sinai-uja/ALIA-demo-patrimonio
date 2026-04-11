"""Composition root for execution trace dependencies."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.shared.services.trace_application_service import (
    TraceApplicationService,
)
from src.application.shared.use_cases.get_trace import GetTraceUseCase
from src.application.shared.use_cases.list_traces import ListTracesUseCase
from src.application.shared.use_cases.save_trace import SaveTraceUseCase
from src.infrastructure.shared.repositories.trace_repository import (
    SqlAlchemyTraceRepository,
)


def build_trace_repository(db: AsyncSession) -> SqlAlchemyTraceRepository:
    """Build a trace repository bound to the given session."""
    return SqlAlchemyTraceRepository(db)


def build_trace_application_service(
    db: AsyncSession,
) -> TraceApplicationService:
    """Wire all trace dependencies and return the application service."""
    repo = build_trace_repository(db)
    return TraceApplicationService(
        save_trace_use_case=SaveTraceUseCase(trace_repository=repo),
        list_traces_use_case=ListTracesUseCase(trace_repository=repo),
        get_trace_use_case=GetTraceUseCase(trace_repository=repo),
    )
