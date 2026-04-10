from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.routes.value_objects.route_stop import RouteStop


@dataclass
class VirtualRoute:
    """A personalized virtual heritage route."""

    id: UUID
    title: str
    province: str
    stops: list[RouteStop]
    narrative: str
    introduction: str = ""
    conclusion: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
