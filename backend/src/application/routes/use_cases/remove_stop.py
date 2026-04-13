"""Use case: remove a stop from an existing route."""

from __future__ import annotations

import logging
from uuid import UUID

from src.application.routes.dto.routes_dto import RouteStopDTO, VirtualRouteDTO
from src.application.routes.exceptions import RouteNotFoundError
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("iaph.routes.remove_stop")


class RemoveStopUseCase:
    """Removes a stop from an existing route and reorders the remaining ones."""

    def __init__(
        self,
        route_repository: RouteRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._route_repository = route_repository
        self._uow = unit_of_work

    async def execute(
        self, route_id: str, stop_order: int, user_id: str | None = None,
    ) -> VirtualRouteDTO:
        user_uuid = UUID(user_id) if user_id else None
        route_uuid = UUID(route_id)

        async with self._uow:
            route = await self._route_repository.get_route(
                route_uuid, user_id=user_uuid,
            )
            if route is None:
                raise RouteNotFoundError(f"Route not found: {route_id}")

            # Find and remove the stop at the given order
            remaining_stops = [s for s in route.stops if s.order != stop_order]
            if len(remaining_stops) == len(route.stops):
                raise RouteNotFoundError(
                    f"Stop with order {stop_order} not found in route {route_id}",
                )

            # Reorder remaining stops sequentially (1, 2, 3, ...)
            reordered_stops = []
            for idx, stop in enumerate(remaining_stops, start=1):
                reordered_stops.append({
                    "order": idx,
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
                })

            # Rebuild the monolithic narrative from intro + segments + conclusion
            narrative = _rebuild_narrative(
                introduction=route.introduction,
                stops=reordered_stops,
                conclusion=route.conclusion,
            )

            updated_route = await self._route_repository.update_route(
                route_uuid,
                user_uuid,
                stops=reordered_stops,
                narrative=narrative,
                introduction=route.introduction,
                conclusion=route.conclusion,
            )
            if updated_route is None:
                raise RouteNotFoundError(f"Route not found: {route_id}")

        logger.info(
            "Stop removed: route_id=%s stop_order=%d remaining=%d",
            route_id, stop_order, len(reordered_stops),
        )

        return VirtualRouteDTO(
            id=str(updated_route.id),
            title=updated_route.title,
            province=updated_route.province,
            stops=[
                RouteStopDTO(
                    order=s.order,
                    title=s.title,
                    heritage_type=s.heritage_type,
                    province=s.province,
                    municipality=s.municipality,
                    url=s.url,
                    description=s.description,
                    heritage_asset_id=s.heritage_asset_id,
                    narrative_segment=s.narrative_segment,
                    image_url=s.image_url,
                    latitude=s.latitude,
                    longitude=s.longitude,
                )
                for s in updated_route.stops
            ],
            narrative=updated_route.narrative,
            introduction=updated_route.introduction,
            conclusion=updated_route.conclusion,
            created_at=updated_route.created_at.isoformat(),
        )


def _rebuild_narrative(
    introduction: str,
    stops: list[dict],
    conclusion: str,
) -> str:
    """Rebuild the monolithic narrative from introduction + stop segments + conclusion."""
    parts: list[str] = []
    if introduction:
        parts.append(introduction)
    for stop in stops:
        segment = stop.get("narrative_segment", "")
        if segment:
            parts.append(segment)
    if conclusion:
        parts.append(conclusion)
    return "\n\n".join(parts)
