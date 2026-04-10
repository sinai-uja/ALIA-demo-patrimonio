import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.value_objects.route_stop import RouteStop
from src.domain.routes.value_objects.virtual_route import VirtualRoute
from src.infrastructure.routes.models import VirtualRouteModel

logger = logging.getLogger("iaph.routes.repository")


class SqlAlchemyRouteRepository(RouteRepository):
    """Async SQLAlchemy implementation of the RouteRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_route(
        self, route: VirtualRoute, user_id: UUID | None = None,
    ) -> VirtualRoute:
        stops_json = [
            {
                "order": stop.order,
                "title": stop.title,
                "heritage_type": stop.heritage_type,
                "province": stop.province,
                "municipality": stop.municipality,
                "url": stop.url,
                "description": stop.description,
                "heritage_asset_id": stop.heritage_asset_id,
                "document_id": stop.document_id,
                "narrative_segment": stop.narrative_segment,
                "image_url": stop.image_url,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
            }
            for stop in route.stops
        ]

        model = VirtualRouteModel(
            id=route.id,
            title=route.title,
            province=route.province,
            narrative=route.narrative,
            introduction=route.introduction,
            conclusion=route.conclusion,
            stops=stops_json,
            created_at=route.created_at,
            user_id=user_id,
        )

        self._db.add(model)
        try:
            await self._db.flush()
            await self._db.refresh(model)
        except Exception:
            logger.error(
                "Failed to save route route_id=%s user_id=%s",
                route.id, user_id, exc_info=True,
            )
            raise

        return self._to_entity(model)

    async def get_route(
        self, route_id: UUID, user_id: UUID | None = None,
    ) -> VirtualRoute | None:
        stmt = select(VirtualRouteModel).where(VirtualRouteModel.id == route_id)
        if user_id is not None:
            stmt = stmt.where(VirtualRouteModel.user_id == user_id)
        try:
            result = await self._db.execute(stmt)
        except Exception:
            logger.error(
                "Failed to get route route_id=%s user_id=%s",
                route_id, user_id, exc_info=True,
            )
            raise
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def list_routes(
        self, province: str | None = None, user_id: UUID | None = None,
    ) -> list[VirtualRoute]:
        stmt = select(VirtualRouteModel).order_by(VirtualRouteModel.created_at.desc())

        if province is not None:
            stmt = stmt.where(VirtualRouteModel.province == province)
        if user_id is not None:
            stmt = stmt.where(VirtualRouteModel.user_id == user_id)

        try:
            result = await self._db.execute(stmt)
        except Exception:
            logger.error(
                "Failed to list routes province=%r user_id=%s",
                province, user_id, exc_info=True,
            )
            raise
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def delete_route(
        self, route_id: UUID, user_id: UUID | None = None,
    ) -> bool:
        stmt = select(VirtualRouteModel).where(VirtualRouteModel.id == route_id)
        if user_id is not None:
            stmt = stmt.where(VirtualRouteModel.user_id == user_id)
        try:
            result = await self._db.execute(stmt)
        except Exception:
            logger.error(
                "Failed to fetch route for deletion route_id=%s user_id=%s",
                route_id, user_id, exc_info=True,
            )
            raise
        model = result.scalar_one_or_none()

        if model is None:
            return False

        await self._db.delete(model)
        try:
            await self._db.flush()
        except Exception:
            logger.error("Failed to delete route route_id=%s", route_id, exc_info=True)
            raise
        return True

    def _to_entity(self, model: VirtualRouteModel) -> VirtualRoute:
        stops = [
            RouteStop(
                order=s["order"],
                title=s["title"],
                heritage_type=s["heritage_type"],
                province=s["province"],
                municipality=s.get("municipality"),
                url=s.get("url", ""),
                description=s.get("description", ""),
                heritage_asset_id=s.get("heritage_asset_id"),
                document_id=s.get("document_id"),
                narrative_segment=s.get("narrative_segment", ""),
                image_url=s.get("image_url"),
                latitude=s.get("latitude"),
                longitude=s.get("longitude"),
            )
            for s in (model.stops or [])
        ]

        return VirtualRoute(
            id=model.id,
            title=model.title,
            province=model.province,
            stops=stops,
            narrative=model.narrative,
            introduction=getattr(model, "introduction", None) or "",
            conclusion=getattr(model, "conclusion", None) or "",
            created_at=model.created_at,
        )
