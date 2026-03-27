from uuid import UUID

from src.domain.routes.ports.route_repository import RouteRepository


class DeleteRouteUseCase:
    """Deletes a virtual route by ID."""

    def __init__(self, route_repository: RouteRepository) -> None:
        self._route_repository = route_repository

    async def execute(self, route_id: str, user_id: str | None = None) -> None:
        user_uuid = UUID(user_id) if user_id else None
        deleted = await self._route_repository.delete_route(UUID(route_id), user_id=user_uuid)
        if not deleted:
            raise ValueError(f"Route not found: {route_id}")
