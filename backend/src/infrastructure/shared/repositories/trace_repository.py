"""SQLAlchemy implementation of TraceRepository."""

import logging
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository
from src.infrastructure.shared.models.execution_trace_model import (
    ExecutionTraceModel,
)

logger = logging.getLogger("iaph.trace.repository")


class SqlAlchemyTraceRepository(TraceRepository):
    """Async SQLAlchemy implementation of the TraceRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, trace: ExecutionTrace) -> None:
        stmt = insert(ExecutionTraceModel.__table__).values(
            id=trace.id,
            execution_type=trace.execution_type,
            execution_id=trace.execution_id,
            user_id=self._parse_uuid(trace.user_id),
            username=trace.username,
            user_profile_type=trace.user_profile_type,
            query=trace.query,
            pipeline_mode=trace.pipeline_mode,
            steps=trace.steps,
            summary=trace.summary,
            feedback_value=trace.feedback_value,
            status=trace.status,
            created_at=trace.created_at,
        )
        await self._db.execute(stmt)
        await self._db.commit()

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
    ) -> tuple[list[ExecutionTrace], int]:
        base = select(ExecutionTraceModel)
        count_base = select(func.count()).select_from(ExecutionTraceModel)

        filters = self._build_filters(
            execution_type=execution_type,
            user_id=user_id,
            since=since,
            until=until,
            query=query,
            exclude_admin_except=exclude_admin_except,
        )
        for f in filters:
            base = base.where(f)
            count_base = count_base.where(f)

        # Total count
        total_result = await self._db.execute(count_base)
        total = total_result.scalar() or 0

        # Paginated results
        offset = (page - 1) * page_size
        stmt = (
            base
            .order_by(ExecutionTraceModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(stmt)
        models = result.scalars().all()
        traces = [m.to_domain() for m in models]
        return traces, total

    async def get_by_id(
        self, trace_id: UUID, *, exclude_admin_except: str | None = None,
    ) -> ExecutionTrace | None:
        stmt = select(ExecutionTraceModel).where(
            ExecutionTraceModel.id == trace_id,
        )
        if exclude_admin_except:
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(
                    ExecutionTraceModel.user_profile_type != "admin",
                    ExecutionTraceModel.user_profile_type.is_(None),
                    ExecutionTraceModel.user_id == self._parse_uuid(exclude_admin_except),
                ),
            )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_domain()

    def _build_filters(
        self,
        *,
        execution_type: str | None,
        user_id: str | None,
        since: str | None,
        until: str | None,
        query: str | None,
        exclude_admin_except: str | None,
    ) -> list:
        from sqlalchemy import or_

        filters = []
        if execution_type:
            filters.append(
                ExecutionTraceModel.execution_type == execution_type,
            )
        if user_id:
            uid = self._parse_uuid(user_id)
            if uid:
                filters.append(ExecutionTraceModel.user_id == uid)
            else:
                filters.append(ExecutionTraceModel.username == user_id)
        if since:
            filters.append(ExecutionTraceModel.created_at >= self._parse_date(since))
        if until:
            filters.append(ExecutionTraceModel.created_at <= self._parse_date(until, end_of_day=True))
        if query:
            filters.append(ExecutionTraceModel.query.ilike(f"%{query}%"))
        if exclude_admin_except:
            # Exclude traces from other admins; show non-admin + own traces
            filters.append(
                or_(
                    ExecutionTraceModel.user_profile_type != "admin",
                    ExecutionTraceModel.user_profile_type.is_(None),
                    ExecutionTraceModel.user_id == self._parse_uuid(exclude_admin_except),
                ),
            )
        return filters

    @staticmethod
    def _parse_uuid(value: str | None) -> UUID | None:
        """Try to parse a string as UUID; return None if not valid."""
        if not value:
            return None
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_date(value: str, *, end_of_day: bool = False) -> datetime:
        """Parse a date string (YYYY-MM-DD) to a datetime for DB comparison."""
        d = date.fromisoformat(value)
        if end_of_day:
            return datetime(d.year, d.month, d.day, 23, 59, 59)
        return datetime(d.year, d.month, d.day)

    async def get_result_feedbacks(self, execution_id: str) -> dict[str, int]:
        """Return {document_id: feedback_value} for search result feedbacks.

        Feedback rows have target_type='search_result' and
        target_id='{execution_id}:{document_id}'.
        """
        from src.infrastructure.feedback.models import UserFeedbackModel

        stmt = select(
            UserFeedbackModel.target_id,
            UserFeedbackModel.value,
        ).where(
            UserFeedbackModel.target_type == "search_result",
            UserFeedbackModel.target_id.like(f"{execution_id}:%"),
        )
        result = await self._db.execute(stmt)
        feedbacks: dict[str, int] = {}
        for row in result:
            # target_id format: "{execution_id}:{document_id}"
            parts = row.target_id.split(":", 1)
            if len(parts) == 2:
                feedbacks[parts[1]] = row.value
        return feedbacks

    async def get_route_feedback(self, execution_id: str) -> int | None:
        """Return the feedback value for a route, or None if no feedback."""
        from src.infrastructure.feedback.models import UserFeedbackModel

        stmt = select(UserFeedbackModel.value).where(
            UserFeedbackModel.target_type == "route",
            UserFeedbackModel.target_id == execution_id,
        ).limit(1)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
