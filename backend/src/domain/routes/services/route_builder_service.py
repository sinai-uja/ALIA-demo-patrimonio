from uuid import uuid4

from src.domain.routes.value_objects.asset_preview import AssetPreview
from src.domain.routes.value_objects.route_stop import RouteStop
from src.domain.routes.value_objects.virtual_route import VirtualRoute
from src.domain.shared.value_objects.asset_id import extract_asset_id


class RouteBuilderService:
    """Builds a VirtualRoute from retrieved heritage chunks and user preferences.

    Selects unique stops ordered by heritage type diversity and assembles
    the route entity.
    """

    def select_diverse_stops(
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

        by_type: dict[str, list[dict]] = {}
        seen_titles: set[str] = set()

        for chunk in chunks:
            title = chunk.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            h_type = chunk.get("heritage_type", "unknown")
            by_type.setdefault(h_type, []).append(chunk)

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

    def build(
        self,
        selected_chunks: list[dict],
        province: str,
        title: str,
        narrative: str,
        introduction: str = "",
        conclusion: str = "",
        narrative_segments: dict[int, str] | None = None,
        asset_previews: dict[str, AssetPreview] | None = None,
    ) -> VirtualRoute:
        narrative_segments = narrative_segments or {}
        asset_previews = asset_previews or {}

        stops: list[RouteStop] = []
        for idx, chunk in enumerate(selected_chunks, start=1):
            heritage_type = chunk.get("heritage_type", "")
            document_id = chunk.get("document_id", "")
            heritage_asset_id = None
            if document_id:
                extracted = extract_asset_id(document_id)
                if extracted != document_id:
                    heritage_asset_id = extracted

            preview = asset_previews.get(heritage_asset_id, None) if heritage_asset_id else None

            # Prefer heritage asset description over RAG chunk content
            description = (
                preview.description[:500]
                if preview and preview.description
                else chunk.get("content", "")[:500]
            )

            stops.append(
                RouteStop(
                    order=idx,
                    title=chunk.get("title", ""),
                    heritage_type=heritage_type,
                    province=chunk.get("province", province),
                    municipality=(
                        preview.municipality
                        if preview and preview.municipality
                        else chunk.get("municipality")
                    ),
                    url=chunk.get("url", ""),
                    description=description,
                    heritage_asset_id=heritage_asset_id,
                    document_id=document_id or None,
                    narrative_segment=narrative_segments.get(idx, ""),
                    image_url=preview.image_url if preview else None,
                    latitude=preview.latitude if preview else None,
                    longitude=preview.longitude if preview else None,
                )
            )

        return VirtualRoute(
            id=uuid4(),
            title=title,
            province=province,
            stops=stops,
            narrative=narrative,
            introduction=introduction,
            conclusion=conclusion,
        )