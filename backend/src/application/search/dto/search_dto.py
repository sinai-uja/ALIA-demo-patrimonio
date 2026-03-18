from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimilaritySearchDTO:
    """Input DTO for similarity search."""

    query: str
    top_k: int = 10
    heritage_type_filter: list[str] | None = None
    province_filter: list[str] | None = None
    municipality_filter: list[str] | None = None


@dataclass(frozen=True)
class SearchResultDTO:
    """A single search result."""

    chunk_id: str
    document_id: str
    title: str
    heritage_type: str
    province: str
    municipality: str | None
    url: str
    content: str
    score: float


@dataclass(frozen=True)
class SimilaritySearchResponseDTO:
    """Response DTO for similarity search."""

    results: list[SearchResultDTO]
    query: str
    total_results: int


@dataclass(frozen=True)
class DetectedEntityDTO:
    """DTO for a detected entity in a search query."""

    entity_type: str
    value: str
    display_label: str
    matched_text: str = ""


@dataclass(frozen=True)
class SuggestionResponseDTO:
    """Response DTO for search suggestions."""

    query: str
    search_label: str
    detected_entities: list[DetectedEntityDTO]


@dataclass(frozen=True)
class FilterValuesDTO:
    """Response DTO for available filter values."""

    heritage_types: list[str] = field(default_factory=list)
    provinces: list[str] = field(default_factory=list)
    municipalities: list[str] = field(default_factory=list)
