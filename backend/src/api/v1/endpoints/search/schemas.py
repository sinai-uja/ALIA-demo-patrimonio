from pydantic import BaseModel, Field


class SimilaritySearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, description="Search query text",
    )
    page: int = Field(
        default=1, ge=1, description="Page number (1-based)",
    )
    page_size: int = Field(
        default=10, ge=1, le=50, description="Results per page",
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


class ChunkHitSchema(BaseModel):
    chunk_id: str
    content: str
    score: float


class SearchResultSchema(BaseModel):
    document_id: str
    title: str
    heritage_type: str
    province: str
    municipality: str | None = None
    url: str
    best_score: float
    chunks: list[ChunkHitSchema]
    denomination: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    protection: str | None = None


class SimilaritySearchResponse(BaseModel):
    results: list[SearchResultSchema]
    query: str
    total_results: int
    page: int
    page_size: int
    total_pages: int


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
