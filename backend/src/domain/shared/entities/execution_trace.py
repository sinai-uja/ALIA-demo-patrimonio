"""Domain entity representing a single pipeline execution trace."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ExecutionTrace:
    """Immutable record of a pipeline execution for admin debugging."""

    id: UUID
    execution_type: str  # 'search', 'rag', 'route', 'chat'
    execution_id: str  # search_id, route_id, session_id
    user_id: str | None
    username: str | None
    user_profile_type: str | None
    query: str
    pipeline_mode: str | None
    steps: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    feedback_value: int | None = None
    status: str = "success"
    created_at: datetime = field(default_factory=datetime.utcnow)
