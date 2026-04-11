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
    heritage_asset_id: str | None = None
    narrative_segment: str = ""
    image_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class VirtualRouteSchema(BaseModel):
    id: str
    title: str
    province: str
    stops: list[RouteStopSchema]
    narrative: str
    introduction: str | None = None
    conclusion: str | None = None
    created_at: str


class GuideMessageSchema(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class GuideQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description=(
            "Question about the route or its heritage sites"
        ),
    )
    history: list[GuideMessageSchema] = Field(
        default_factory=list,
        description="Previous conversation messages for context",
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


class AddStopRequest(BaseModel):
    document_id: str = Field(
        ...,
        min_length=1,
        description="Document ID of the heritage asset to add as a stop",
    )
    position: int | None = Field(
        default=None,
        ge=1,
        description="1-indexed position to insert the stop. None = append at end",
    )
    background: bool = Field(
        default=False,
        description="If true, return 202 immediately and generate narrative in background",
    )
