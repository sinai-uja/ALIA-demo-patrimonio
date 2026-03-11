from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.value_objects.route_stop import RouteStop
from src.domain.routes.value_objects.virtual_route import VirtualRoute
from src.infrastructure.routes.models import VirtualRouteModel


class SqlAlchemyRouteRepository(RouteRepository):
    """Async SQLAlchemy implementation of the RouteRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_route(self, route: VirtualRoute) -> VirtualRoute:
        stops_json = [
            {
                "order": stop.order,
                "title": stop.title,
                "heritage_type": stop.heritage_type,
                "province": stop.province,
                "municipality": stop.municipality,
                "url": stop.url,
                "description": stop.description,
                "visit_duration_minutes": stop.visit_duration_minutes,
            }
            for stop in route.stops
        ]

        model = VirtualRouteModel(
            id=route.id,
            title=route.title,
            province=route.province,
            narrative=route.narrative,
            total_duration_minutes=route.total_duration_minutes,
            stops=stops_json,
            created_at=route.created_at,
        )

        self._db.add(model)
        await self._db.commit()
        await self._db.refresh(model)

        return self._to_entity(model)

    async def get_route(self, route_id: UUID) -> VirtualRoute | None:
        stmt = select(VirtualRouteModel).where(VirtualRouteModel.id == route_id)
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def list_routes(self, province: str | None = None) -> list[VirtualRoute]:
        stmt = select(VirtualRouteModel).order_by(VirtualRouteModel.created_at.desc())

        if province is not None:
            stmt = stmt.where(VirtualRouteModel.province == province)

        result = await self._db.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: VirtualRouteModel) -> VirtualRoute:
        stops = [
            RouteStop(
                order=s["order"],
                title=s["title"],
                heritage_type=s["heritage_type"],
                province=s["province"],
                municipality=s.get("municipality"),
                url=s["url"],
                description=s["description"],
                visit_duration_minutes=s["visit_duration_minutes"],
            )
            for s in (model.stops or [])
        ]

        return VirtualRoute(
            id=model.id,
            title=model.title,
            province=model.province,
            stops=stops,
            total_duration_minutes=model.total_duration_minutes,
            narrative=model.narrative,
            created_at=model.created_at,
        )
