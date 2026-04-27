"""Use case: list the full execution-trace history of a single route."""

from src.application.shared.dto.trace_dto import (
    TraceListDTO,
    TraceSummaryDTO,
)
from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository


class ListRouteHistoryUseCase:
    """Returns the chronological history of all traces for a route_id."""

    def __init__(self, trace_repository: TraceRepository) -> None:
        self._trace_repository = trace_repository

    async def execute(
        self,
        route_id: str,
        *,
        exclude_admin_except: str | None = None,
    ) -> TraceListDTO:
        traces = await self._trace_repository.list_by_execution_id(
            route_id,
            execution_type="route",
            exclude_admin_except=exclude_admin_except,
        )
        summaries = [self._to_summary(t) for t in traces]
        return TraceListDTO(
            traces=summaries,
            total=len(summaries),
            page=1,
            page_size=len(summaries) or 1,
            total_pages=1,
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
