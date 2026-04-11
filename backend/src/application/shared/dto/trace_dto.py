"""Application-layer DTOs for execution traces."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TraceFilterDTO:
    """Input DTO for filtering execution traces."""

    execution_type: str | None = None
    user_id: str | None = None
    since: str | None = None
    until: str | None = None
    query: str | None = None
    exclude_admin_except: str | None = None
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True)
class TraceSummaryDTO:
    """Summary DTO for trace list items."""

    id: str
    execution_type: str
    execution_id: str
    user_id: str | None
    username: str | None
    user_profile_type: str | None
    query: str
    pipeline_mode: str | None
    status: str
    feedback_value: int | None
    total_results: int | None
    elapsed_ms: float | None
    top_score: float | None
    created_at: str


@dataclass(frozen=True)
class TraceListDTO:
    """Paginated list of trace summaries."""

    traces: list[TraceSummaryDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


@dataclass(frozen=True)
class TraceDetailDTO:
    """Full detail DTO for a single trace."""

    id: str
    execution_type: str
    execution_id: str
    user_id: str | None
    username: str | None
    user_profile_type: str | None
    query: str
    pipeline_mode: str | None
    steps: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    feedback_value: int | None = None
    status: str = "success"
    created_at: str = ""
