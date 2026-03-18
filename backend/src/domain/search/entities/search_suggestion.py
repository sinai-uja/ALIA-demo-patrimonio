from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedEntity:
    """An entity detected in a search query (province, municipality, heritage type)."""

    entity_type: str  # "province", "municipality", "heritage_type"
    value: str  # normalized value
    display_label: str  # e.g. "Provincia: Malaga"
    matched_text: str = ""  # the text fragment matched in the query


@dataclass(frozen=True)
class SearchSuggestion:
    """A search suggestion with detected entities from the query."""

    query: str
    search_label: str
    detected_entities: list[DetectedEntity]
