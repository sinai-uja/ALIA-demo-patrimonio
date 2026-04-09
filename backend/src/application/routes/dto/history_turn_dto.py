"""Typed conversation-history turn DTO for the routes guide use case."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryTurnDTO:
    """A single previous turn in a guide conversation."""

    role: str
    content: str
