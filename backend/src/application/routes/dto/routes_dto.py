from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerateRouteDTO:
    """Input DTO for generating a virtual route."""

    query: str
    num_stops: int = 5
    heritage_type_filter: list[str] | None = None
    province_filter: list[str] | None = None
    municipality_filter: list[str] | None = None


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
    heritage_asset_id: str | None = None
    narrative_segment: str = ""
    image_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class VirtualRouteDTO:
    """Output DTO for a complete virtual route."""

    id: str
    title: str
    province: str
    stops: list[RouteStopDTO]
    total_duration_minutes: int
    narrative: str
    introduction: str = ""
    conclusion: str = ""
    created_at: str = ""


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


@dataclass(frozen=True)
class DetectedEntityDTO:
    """DTO for a detected entity in a route planning query."""

    entity_type: str
    value: str
    display_label: str
    matched_text: str = ""


@dataclass(frozen=True)
class RouteSuggestionResponseDTO:
    """Response DTO for route suggestions."""

    query: str
    search_label: str
    detected_entities: list[DetectedEntityDTO]


@dataclass(frozen=True)
class RouteFilterValuesDTO:
    """Response DTO for available route filter values."""

    heritage_types: list[str]
    provinces: list[str]
    municipalities: list[str]
