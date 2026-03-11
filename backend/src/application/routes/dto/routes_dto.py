from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerateRouteDTO:
    """Input DTO for generating a virtual route."""

    province: str
    num_stops: int = 5
    heritage_types: list[str] = field(default_factory=lambda: ["ALL"])
    user_interests: str = ""


@dataclass(frozen=True)
class RouteStopDTO:
    """Output DTO for a single route stop."""

    order: int
    title: str
    heritage_type: str
    province: str
    municipality: str | None
    url: str
    description: str
    visit_duration_minutes: int


@dataclass(frozen=True)
class VirtualRouteDTO:
    """Output DTO for a complete virtual route."""

    id: str
    title: str
    province: str
    stops: list[RouteStopDTO]
    total_duration_minutes: int
    narrative: str
    created_at: str


@dataclass(frozen=True)
class GuideQueryDTO:
    """Input DTO for a guide question about a specific route."""

    route_id: str
    question: str


@dataclass(frozen=True)
class GuideResponseDTO:
    """Output DTO for a guide answer."""

    answer: str
    sources: list[dict] = field(default_factory=list)
