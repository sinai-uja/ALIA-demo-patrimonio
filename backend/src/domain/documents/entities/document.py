from dataclasses import dataclass, field

from src.domain.documents.value_objects.heritage_type import HeritageType


@dataclass(frozen=True)
class Document:
    """Immutable value object representing an IAPH heritage document."""

    id: str
    url: str
    title: str
    province: str
    heritage_type: HeritageType
    text: str
    municipality: str | None = None
    metadata: dict = field(default_factory=dict)
