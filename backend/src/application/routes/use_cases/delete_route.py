from uuid import UUID

from src.application.routes.exceptions import RouteNotFoundError
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork


class DeleteRouteUseCase:
    """Deletes a virtual route by ID."""

    def __init__(
        self,
        route_repository: RouteRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._route_repository = route_repository
        self._uow = unit_of_work

    async def execute(self, route_id: str, user_id: str | None = None) -> None:
        user_uuid = UUID(user_id) if user_id else None
        async with self._uow:
            deleted = await self._route_repository.delete_route(
                UUID(route_id), user_id=user_uuid,
            )
            if not deleted:
                raise RouteNotFoundError(f"Route not found: {route_id}")
