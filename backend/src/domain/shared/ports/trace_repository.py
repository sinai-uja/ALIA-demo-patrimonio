"""Port for persisting and querying execution traces."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.shared.entities.execution_trace import ExecutionTrace


class TraceRepository(ABC):
    """Abstract repository for execution trace persistence."""

    @abstractmethod
    async def save(self, trace: ExecutionTrace) -> None: ...

    @abstractmethod
    async def list_traces(
        self,
        *,
        execution_type: str | None = None,
        user_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        query: str | None = None,
        exclude_admin_except: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExecutionTrace], int]: ...

    @abstractmethod
    async def get_by_id(
        self, trace_id: UUID, *, exclude_admin_except: str | None = None,
    ) -> ExecutionTrace | None: ...
