from pydantic import BaseModel, Field


class GenerateRouteRequest(BaseModel):
    province: str = Field(
        ...,
        min_length=1,
        description="Andalusian province for the route",
        examples=["Jaen", "Sevilla", "Granada"],
    )
    num_stops: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of stops in the route",
    )
    heritage_types: list[str] = Field(
        default=["ALL"],
        description=(
            "Heritage types to include: paisaje_cultural, patrimonio_inmaterial, "
            "patrimonio_inmueble, patrimonio_mueble, or ALL"
        ),
    )
    user_interests: str = Field(
        default="",
        description="Optional free-text description of user interests",
    )


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
        description="Question about the route or its heritage sites",
    )


class GuideResponseSchema(BaseModel):
    answer: str
    sources: list[dict]
