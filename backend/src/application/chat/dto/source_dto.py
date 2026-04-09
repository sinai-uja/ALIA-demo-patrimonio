"""Typed source reference DTO for chat responses."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDTO:
    """A single retrieved-source reference attached to an assistant message."""

    title: str
    url: str
    score: float
    heritage_type: str
    province: str
    municipality: str | None = None
    metadata: dict | None = None
