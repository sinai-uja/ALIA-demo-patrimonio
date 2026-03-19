from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedEntityResult:
    """Entity detected in a route planning query."""

    entity_type: str
    value: str
    display_label: str
    matched_text: str = ""
