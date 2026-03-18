from pydantic import BaseModel, Field


class SimilaritySearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, description="Search query text",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results to return",
    )
    heritage_type_filter: list[str] | None = Field(
        default=None,
        description="Filter by heritage type(s) — multiple values act as OR",
    )
    province_filter: list[str] | None = Field(
        default=None,
        description="Filter by Andalusian province(s) — multiple values act as OR",
    )
    municipality_filter: list[str] | None = Field(
        default=None,
        description="Filter by municipality/ies — multiple values act as OR",
    )


class SearchResultSchema(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    heritage_type: str
    province: str
    municipality: str | None = None
    url: str
    content: str
    score: float


class SimilaritySearchResponse(BaseModel):
    results: list[SearchResultSchema]
    query: str
    total_results: int


class DetectedEntitySchema(BaseModel):
    entity_type: str
    value: str
    display_label: str
    matched_text: str = ""


class SuggestionResponse(BaseModel):
    query: str
    search_label: str
    detected_entities: list[DetectedEntitySchema]


class FilterValuesResponse(BaseModel):
    heritage_types: list[str]
    provinces: list[str]
    municipalities: list[str]
