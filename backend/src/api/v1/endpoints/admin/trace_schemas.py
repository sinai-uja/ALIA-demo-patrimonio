"""Pydantic schemas for trace API endpoints."""

from pydantic import BaseModel, Field


class TraceSummaryResponse(BaseModel):
    """Summary of a single execution trace for list views."""

    id: str
    execution_type: str
    execution_id: str
    user_id: str | None = None
    username: str | None = None
    user_profile_type: str | None = None
    query: str
    pipeline_mode: str | None = None
    status: str
    feedback_value: int | None = None
    total_results: int | None = None
    elapsed_ms: float | None = None
    top_score: float | None = None
    created_at: str


class TraceListResponse(BaseModel):
    """Paginated list of trace summaries."""

    traces: list[TraceSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TraceDetailResponse(BaseModel):
    """Full detail of a single execution trace."""

    id: str
    execution_type: str
    execution_id: str
    user_id: str | None = None
    username: str | None = None
    user_profile_type: str | None = None
    query: str
    pipeline_mode: str | None = None
    steps: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    feedback_value: int | None = None
    result_feedbacks: dict[str, int] | None = None
    status: str = "success"
    created_at: str = ""
