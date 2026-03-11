from dataclasses import dataclass
from datetime import datetime

from src.domain.accessibility.value_objects.simplification_level import SimplificationLevel


@dataclass(frozen=True)
class SimplifiedText:
    """Immutable value object representing a simplified text result."""

    original_text: str
    simplified_text: str
    level: SimplificationLevel
    document_id: str | None
    created_at: datetime
