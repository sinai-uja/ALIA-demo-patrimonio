"""Use case: retrieve a single execution trace by id."""

from uuid import UUID

from src.application.shared.dto.trace_dto import TraceDetailDTO
from src.application.shared.exceptions import ResourceNotFoundError
from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository


class GetTraceUseCase:
    """Returns full detail for a single execution trace."""

    def __init__(self, trace_repository: TraceRepository) -> None:
        self._trace_repository = trace_repository

    async def execute(
        self, trace_id: UUID, *, exclude_admin_except: str | None = None,
    ) -> TraceDetailDTO:
        trace = await self._trace_repository.get_by_id(
            trace_id, exclude_admin_except=exclude_admin_except,
        )
        if trace is None:
            raise ResourceNotFoundError(f"Trace {trace_id} not found")
        return self._to_detail(trace)

    def _to_detail(self, trace: ExecutionTrace) -> TraceDetailDTO:
        return TraceDetailDTO(
            id=str(trace.id),
            execution_type=trace.execution_type,
            execution_id=trace.execution_id,
            user_id=trace.user_id,
            username=trace.username,
            user_profile_type=trace.user_profile_type,
            query=trace.query,
            pipeline_mode=trace.pipeline_mode,
            steps=trace.steps,
            summary=trace.summary,
            feedback_value=trace.feedback_value,
            status=trace.status,
            created_at=trace.created_at.isoformat() if trace.created_at else "",
        )
