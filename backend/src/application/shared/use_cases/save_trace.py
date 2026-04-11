"""Use case: persist a single execution trace."""

import logging

from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository

logger = logging.getLogger("iaph.trace.save")


class SaveTraceUseCase:
    """Receives trace data and persists it via the repository."""

    def __init__(self, trace_repository: TraceRepository) -> None:
        self._trace_repository = trace_repository

    async def execute(self, trace: ExecutionTrace) -> None:
        await self._trace_repository.save(trace)
