"""Route narrative value object.

Represents the structured narrative content produced by an LLM for a
generated virtual route. Pure domain type: frozen, framework-agnostic,
with no dependencies beyond the standard library.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteNarrative:
    """Structured narrative for a virtual route.

    Attributes:
        title: Human-readable title for the route.
        introduction: Opening narrative text presented before the stops.
        segments: Mapping of stop ``order`` (1-indexed) to its narrative
            text. Stops without a narrative are simply absent.
        conclusion: Closing narrative text presented after the stops.
    """

    title: str
    introduction: str
    segments: dict[int, str] = field(default_factory=dict)
    conclusion: str = ""
    raw_response: str | None = None
    parse_method: str | None = None
