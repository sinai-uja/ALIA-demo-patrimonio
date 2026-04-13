"""Port for pinging external service health endpoints."""

from abc import ABC, abstractmethod


class ServiceHealthPort(ABC):
    """Port for checking the health of an external service."""

    @abstractmethod
    async def ping(self, service_url: str, service_type: str, *, timeout: float = 300) -> str:
        """Ping a service and return its status.

        Returns one of: ``"ok"``, ``"warming"``, ``"down"``.

        Args:
            timeout: HTTP timeout in seconds (default 300 for cold starts).
        """
        ...
