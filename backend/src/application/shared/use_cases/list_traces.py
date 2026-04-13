"""Use case: list execution traces with filters and pagination."""

import math

from src.application.shared.dto.trace_dto import (
    TraceFilterDTO,
    TraceListDTO,
    TraceSummaryDTO,
)
from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository


class ListTracesUseCase:
    """Returns a paginated list of execution trace summaries."""

    def __init__(self, trace_repository: TraceRepository) -> None:
        self._trace_repository = trace_repository

    async def execute(self, filters: TraceFilterDTO) -> TraceListDTO:
        traces, total = await self._trace_repository.list_traces(
            execution_type=filters.execution_type,
            user_id=filters.user_id,
            since=filters.since,
            until=filters.until,
            query=filters.query,
            exclude_admin_except=filters.exclude_admin_except,
            page=filters.page,
            page_size=filters.page_size,
        )
        total_pages = max(1, math.ceil(total / filters.page_size))
        return TraceListDTO(
            traces=[self._to_summary(t) for t in traces],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
        )

    def _to_summary(self, trace: ExecutionTrace) -> TraceSummaryDTO:
        summary = trace.summary or {}
        return TraceSummaryDTO(
            id=str(trace.id),
            execution_type=trace.execution_type,
            execution_id=trace.execution_id,
            user_id=trace.user_id,
            username=trace.username,
            user_profile_type=trace.user_profile_type,
            query=trace.query,
            pipeline_mode=trace.pipeline_mode,
            status=trace.status,
            feedback_value=trace.feedback_value,
            total_results=summary.get("total_results"),
            elapsed_ms=summary.get("elapsed_ms"),
            top_score=summary.get("top_score"),
            created_at=trace.created_at.isoformat() if trace.created_at else "",
        )
