from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.routes.value_objects.virtual_route import VirtualRoute


class RouteRepository(ABC):
    """Port for persisting and retrieving virtual routes."""

    @abstractmethod
    async def save_route(
        self, route: VirtualRoute, user_id: UUID | None = None,
    ) -> VirtualRoute: ...

    @abstractmethod
    async def get_route(
        self, route_id: UUID, user_id: UUID | None = None,
    ) -> VirtualRoute | None: ...

    @abstractmethod
    async def list_routes(
        self, province: str | None = None, user_id: UUID | None = None,
    ) -> list[VirtualRoute]: ...

    @abstractmethod
    async def delete_route(
        self, route_id: UUID, user_id: UUID | None = None,
    ) -> bool:
        """Delete a route by ID. Returns True if it existed."""
        ...
