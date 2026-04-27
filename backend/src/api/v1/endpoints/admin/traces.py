"""Admin endpoints for execution trace inspection."""

import uuid as _uuid

from fastapi import APIRouter, Depends, Query

from src.api.v1.endpoints.admin.trace_schemas import (
    RouteHistoryResponse,
    RouteHistorySummaryAgg,
    TraceDetailResponse,
    TraceListResponse,
    TraceSummaryResponse,
)
from src.api.v1.endpoints.auth.deps import get_current_admin
from src.application.shared.dto.trace_dto import TraceFilterDTO
from src.application.shared.services.trace_application_service import (
    TraceApplicationService,
)
from src.composition.database import get_db
from src.composition.trace_composition import (
    build_trace_application_service,
    build_trace_repository,
)
from src.domain.auth.entities.user import User

router = APIRouter(prefix="/admin/traces", tags=["admin-traces"])


async def _get_trace_service(
    db=Depends(get_db),
) -> TraceApplicationService:
    return build_trace_application_service(db)


@router.get("", response_model=TraceListResponse)
async def list_traces(
    admin: User = Depends(get_current_admin),
    service: TraceApplicationService = Depends(_get_trace_service),
    type: str | None = Query(None, alias="type"),
    since: str | None = Query(None),
    until: str | None = Query(None),
    user_id: str | None = Query(None),
    query: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    filters = TraceFilterDTO(
        execution_type=type,
        user_id=user_id,
        since=since,
        until=until,
        query=query,
        exclude_admin_except=str(admin.id),
        page=page,
        page_size=page_size,
    )
    result = await service.list_traces(filters)
    return TraceListResponse(
        traces=[
            TraceSummaryResponse(
                id=t.id,
                execution_type=t.execution_type,
                execution_id=t.execution_id,
                user_id=t.user_id,
                username=t.username,
                user_profile_type=t.user_profile_type,
                query=t.query,
                pipeline_mode=t.pipeline_mode,
                status=t.status,
                feedback_value=t.feedback_value,
                total_results=t.total_results,
                elapsed_ms=t.elapsed_ms,
                top_score=t.top_score,
                created_at=t.created_at,
            )
            for t in result.traces
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get("/by-route/{route_id}", response_model=RouteHistoryResponse)
async def list_route_history(
    route_id: str,
    admin: User = Depends(get_current_admin),
    service: TraceApplicationService = Depends(_get_trace_service),
):
    """Return the chronological history of all traces for a single route.

    Includes the initial generation plus every add_stop / remove_stop event,
    ordered from oldest to newest. Other admins' traces are excluded.
    """
    result = await service.list_route_history(
        route_id, exclude_admin_except=str(admin.id),
    )
    summaries = [
        TraceSummaryResponse(
            id=t.id,
            execution_type=t.execution_type,
            execution_id=t.execution_id,
            user_id=t.user_id,
            username=t.username,
            user_profile_type=t.user_profile_type,
            query=t.query,
            pipeline_mode=t.pipeline_mode,
            status=t.status,
            feedback_value=t.feedback_value,
            total_results=t.total_results,
            elapsed_ms=t.elapsed_ms,
            top_score=t.top_score,
            created_at=t.created_at,
        )
        for t in result.traces
    ]
    additions = sum(
        1 for t in result.traces if t.pipeline_mode == "route_add_stop"
    )
    removals = sum(
        1 for t in result.traces if t.pipeline_mode == "route_remove_stop"
    )
    generations = sum(
        1
        for t in result.traces
        if t.pipeline_mode in ("route_generation", "route_generation_stream")
    )
    return RouteHistoryResponse(
        route_id=route_id,
        traces=summaries,
        aggregate=RouteHistorySummaryAgg(
            total_events=len(summaries),
            generation_count=generations,
            additions_count=additions,
            removals_count=removals,
        ),
    )


@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    admin: User = Depends(get_current_admin),
    service: TraceApplicationService = Depends(_get_trace_service),
    db=Depends(get_db),
):
    uid = _uuid.UUID(trace_id)
    detail = await service.get_trace(
        uid, exclude_admin_except=str(admin.id),
    )

    # Enrich with per-result feedbacks for search traces
    result_feedbacks: dict[str, int] | None = None
    feedback_value = detail.feedback_value
    if detail.execution_type == "search" and detail.execution_id:
        repo = build_trace_repository(db)
        result_feedbacks = await repo.get_result_feedbacks(detail.execution_id) or None
    elif detail.execution_type == "route" and detail.execution_id:
        repo = build_trace_repository(db)
        fb_row = await repo.get_route_feedback(detail.execution_id)
        if fb_row is not None:
            feedback_value = fb_row

    return TraceDetailResponse(
        id=detail.id,
        execution_type=detail.execution_type,
        execution_id=detail.execution_id,
        user_id=detail.user_id,
        username=detail.username,
        user_profile_type=detail.user_profile_type,
        query=detail.query,
        pipeline_mode=detail.pipeline_mode,
        steps=detail.steps,
        summary=detail.summary,
        feedback_value=feedback_value,
        result_feedbacks=result_feedbacks,
        status=detail.status,
        created_at=detail.created_at,
    )
