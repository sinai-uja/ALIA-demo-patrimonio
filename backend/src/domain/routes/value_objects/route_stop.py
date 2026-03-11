from dataclasses import dataclass


@dataclass(frozen=True)
class RouteStop:
    """A single stop in a virtual heritage route."""

    order: int
    title: str
    heritage_type: str
    province: str
    municipality: str | None
    url: str
    description: str
    visit_duration_minutes: int
