"""Application service facade for execution trace operations."""

from uuid import UUID

from src.application.shared.dto.trace_dto import (
    TraceDetailDTO,
    TraceFilterDTO,
    TraceListDTO,
)
from src.application.shared.use_cases.get_trace import GetTraceUseCase
from src.application.shared.use_cases.list_route_history import (
    ListRouteHistoryUseCase,
)
from src.application.shared.use_cases.list_traces import ListTracesUseCase
from src.application.shared.use_cases.save_trace import SaveTraceUseCase
from src.domain.shared.entities.execution_trace import ExecutionTrace


class TraceApplicationService:
    """Facade coordinating trace-related use cases."""

    def __init__(
        self,
        save_trace_use_case: SaveTraceUseCase,
        list_traces_use_case: ListTracesUseCase,
        get_trace_use_case: GetTraceUseCase,
        list_route_history_use_case: ListRouteHistoryUseCase,
    ) -> None:
        self._save = save_trace_use_case
        self._list = list_traces_use_case
        self._get = get_trace_use_case
        self._route_history = list_route_history_use_case

    async def save_trace(self, trace: ExecutionTrace) -> None:
        await self._save.execute(trace)

    async def list_traces(self, filters: TraceFilterDTO) -> TraceListDTO:
        return await self._list.execute(filters)

    async def get_trace(
        self, trace_id: UUID, *, exclude_admin_except: str | None = None,
    ) -> TraceDetailDTO:
        return await self._get.execute(
            trace_id, exclude_admin_except=exclude_admin_except,
        )

    async def list_route_history(
        self,
        route_id: str,
        *,
        exclude_admin_except: str | None = None,
    ) -> TraceListDTO:
        return await self._route_history.execute(
            route_id, exclude_admin_except=exclude_admin_except,
        )
