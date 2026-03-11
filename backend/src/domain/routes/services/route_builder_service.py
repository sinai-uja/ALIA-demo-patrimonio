from uuid import uuid4

from src.domain.routes.value_objects.route_stop import RouteStop
from src.domain.routes.value_objects.virtual_route import VirtualRoute

# Visit duration estimates by heritage type (minutes)
_DURATION_MAP: dict[str, int] = {
    "patrimonio_inmueble": 60,
    "patrimonio_inmaterial": 45,
    "paisaje_cultural": 90,
    "patrimonio_mueble": 30,
}

_DEFAULT_DURATION = 45


class RouteBuilderService:
    """Builds a VirtualRoute from retrieved heritage chunks and user preferences.

    Selects unique stops ordered by heritage type diversity, assigns
    estimated visit durations, and assembles the route entity.
    """

    def build(
        self,
        chunks: list[dict],
        province: str,
        num_stops: int,
        narrative: str,
        title: str,
    ) -> VirtualRoute:
        selected = self._select_diverse_stops(chunks, num_stops)

        stops: list[RouteStop] = []
        for idx, chunk in enumerate(selected, start=1):
            heritage_type = chunk.get("heritage_type", "")
            duration = _DURATION_MAP.get(heritage_type.lower(), _DEFAULT_DURATION)

            stops.append(
                RouteStop(
                    order=idx,
                    title=chunk.get("title", ""),
                    heritage_type=heritage_type,
                    province=chunk.get("province", province),
                    municipality=chunk.get("municipality"),
                    url=chunk.get("url", ""),
                    description=chunk.get("content", "")[:500],
                    visit_duration_minutes=duration,
                )
            )

        total_duration = sum(stop.visit_duration_minutes for stop in stops)

        return VirtualRoute(
            id=uuid4(),
            title=title,
            province=province,
            stops=stops,
            total_duration_minutes=total_duration,
            narrative=narrative,
        )

    def _select_diverse_stops(
        self,
        chunks: list[dict],
        num_stops: int,
    ) -> list[dict]:
        """Select up to num_stops unique chunks, preferring heritage type diversity.

        Uses a round-robin approach over heritage types to maximize variety.
        Deduplicates by title to avoid repeated stops.
        """
        if not chunks:
            return []

        # Group chunks by heritage type, preserving order within each group
        by_type: dict[str, list[dict]] = {}
        seen_titles: set[str] = set()

        for chunk in chunks:
            title = chunk.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            h_type = chunk.get("heritage_type", "unknown")
            by_type.setdefault(h_type, []).append(chunk)

        # Round-robin selection across heritage types
        selected: list[dict] = []
        type_keys = list(by_type.keys())
        type_indices = {k: 0 for k in type_keys}

        while len(selected) < num_stops:
            added_this_round = False
            for h_type in type_keys:
                if len(selected) >= num_stops:
                    break
                idx = type_indices[h_type]
                if idx < len(by_type[h_type]):
                    selected.append(by_type[h_type][idx])
                    type_indices[h_type] = idx + 1
                    added_this_round = True
            if not added_this_round:
                break

        return selected
