from pydantic import BaseModel, Field


class GenerateRouteRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Natural language description of the desired route"
        ),
    )
    num_stops: int = Field(default=5, ge=2, le=15)
    heritage_type_filter: list[str] | None = None
    province_filter: list[str] | None = None
    municipality_filter: list[str] | None = None


class RouteStopSchema(BaseModel):
    order: int
    title: str
    heritage_type: str
    province: str
    municipality: str | None
    url: str
    description: str
    visit_duration_minutes: int


class VirtualRouteSchema(BaseModel):
    id: str
    title: str
    province: str
    stops: list[RouteStopSchema]
    total_duration_minutes: int
    narrative: str
    created_at: str


class GuideQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description=(
            "Question about the route or its heritage sites"
        ),
    )


class GuideResponseSchema(BaseModel):
    answer: str
    sources: list[dict]


class DetectedEntitySchema(BaseModel):
    entity_type: str
    value: str
    display_label: str
    matched_text: str


class RouteSuggestionResponse(BaseModel):
    query: str
    search_label: str
    detected_entities: list[DetectedEntitySchema]


class RouteFilterValuesResponse(BaseModel):
    heritage_types: list[str]
    provinces: list[str]
    municipalities: list[str]
