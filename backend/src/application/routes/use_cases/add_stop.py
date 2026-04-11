"""Use case: add a new stop to an existing route."""

from __future__ import annotations

import logging
from uuid import UUID

from src.application.routes.dto.routes_dto import RouteStopDTO, VirtualRouteDTO
from src.application.routes.exceptions import RouteNotFoundError
from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import (
    SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
    build_single_stop_narrative_prompt,
)
from src.domain.shared.ports.unit_of_work import UnitOfWork
from src.domain.shared.value_objects.asset_id import extract_asset_id

logger = logging.getLogger("iaph.routes.add_stop")


class AddStopUseCase:
    """Adds a new stop to an existing route with LLM-generated narrative."""

    def __init__(
        self,
        route_repository: RouteRepository,
        heritage_asset_lookup_port: HeritageAssetLookupPort,
        llm_port: LLMPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._route_repository = route_repository
        self._heritage_asset_lookup = heritage_asset_lookup_port
        self._llm_port = llm_port
        self._uow = unit_of_work

    async def execute(
        self,
        route_id: str,
        document_id: str,
        position: int | None = None,
        user_id: str | None = None,
    ) -> VirtualRouteDTO:
        user_uuid = UUID(user_id) if user_id else None
        route_uuid = UUID(route_id)

        async with self._uow:
            route = await self._route_repository.get_route(
                route_uuid, user_id=user_uuid,
            )
            if route is None:
                raise RouteNotFoundError(f"Route not found: {route_id}")

            # Look up the heritage asset
            asset_id = extract_asset_id(document_id)
            previews = await self._heritage_asset_lookup.get_asset_previews(
                [asset_id],
            )
            descriptions = await self._heritage_asset_lookup.get_asset_full_descriptions(
                [asset_id],
            )

            preview = previews.get(asset_id)
            description_text = descriptions.get(asset_id, "")

            # Build the stop list as dicts for manipulation
            current_stops = [
                {
                    "order": s.order,
                    "title": s.title,
                    "heritage_type": s.heritage_type,
                    "province": s.province,
                    "municipality": s.municipality,
                    "url": s.url,
                    "description": s.description,
                    "heritage_asset_id": s.heritage_asset_id,
                    "document_id": s.document_id,
                    "narrative_segment": s.narrative_segment,
                    "image_url": s.image_url,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                }
                for s in route.stops
            ]

            # Determine insert position (1-indexed)
            num_stops = len(current_stops)
            if position is None or position > num_stops + 1:
                insert_idx = num_stops  # append at end (0-indexed)
            else:
                insert_idx = max(0, position - 1)  # convert 1-indexed to 0-indexed

            # Determine neighbour titles for context
            prev_title = current_stops[insert_idx - 1]["title"] if insert_idx > 0 else None
            next_title = current_stops[insert_idx]["title"] if insert_idx < num_stops else None

            # Extract asset info for the new stop
            # We need title, type, province from the heritage_assets table
            # Use a separate query to get denomination, heritage_type, province
            asset_info = await self._lookup_asset_info(asset_id)
            stop_title = asset_info.get("title", document_id)
            stop_type = asset_info.get("heritage_type", "")
            stop_province = asset_info.get("province", route.province)
            stop_municipality = preview.municipality if preview else asset_info.get("municipality")
            stop_url = asset_info.get("url", "")

            # Truncate description for prompt (max ~2000 chars to keep prompt short)
            prompt_description = description_text[:2000] if description_text else stop_title

            # Generate narrative for this single stop via LLM
            narrative_prompt = build_single_stop_narrative_prompt(
                route_title=route.title,
                stop_title=stop_title,
                stop_type=stop_type,
                stop_province=stop_province,
                stop_description=prompt_description,
                previous_stop_title=prev_title,
                next_stop_title=next_title,
            )
            raw_narrative = await self._llm_port.generate_structured(
                system_prompt=SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
                user_prompt=narrative_prompt,
                max_tokens=300,
            )
            # Strip markdown formatting (LLM may add **bold**, ### headings, etc.)
            import re
            narrative_segment = raw_narrative.strip()
            narrative_segment = re.sub(r"\*\*([^*]+)\*\*", r"\1", narrative_segment)
            narrative_segment = re.sub(r"\*([^*]+)\*", r"\1", narrative_segment)
            narrative_segment = re.sub(r"^#+\s*", "", narrative_segment, flags=re.MULTILINE)
            narrative_segment = re.sub(r"^---+$", "", narrative_segment, flags=re.MULTILINE)
            narrative_segment = narrative_segment.strip()

            # Build the new stop dict
            new_stop = {
                "order": 0,  # will be set during reorder
                "title": stop_title,
                "heritage_type": stop_type,
                "province": stop_province,
                "municipality": stop_municipality,
                "url": stop_url,
                "description": description_text[:500] if description_text else "",
                "heritage_asset_id": asset_id,
                "document_id": document_id,
                "narrative_segment": narrative_segment,
                "image_url": preview.image_url if preview else None,
                "latitude": preview.latitude if preview else None,
                "longitude": preview.longitude if preview else None,
            }

            # Insert at position
            current_stops.insert(insert_idx, new_stop)

            # Reorder all stops sequentially (1, 2, 3, ...)
            for idx, stop in enumerate(current_stops, start=1):
                stop["order"] = idx

            # Rebuild the monolithic narrative
            narrative = _rebuild_narrative(
                introduction=route.introduction,
                stops=current_stops,
                conclusion=route.conclusion,
            )

            updated_route = await self._route_repository.update_route(
                route_uuid,
                user_uuid,
                stops=current_stops,
                narrative=narrative,
                introduction=route.introduction,
                conclusion=route.conclusion,
            )
            if updated_route is None:
                raise RouteNotFoundError(f"Route not found: {route_id}")

        logger.info(
            "Stop added: route_id=%s document_id=%s position=%d total_stops=%d",
            route_id, document_id, insert_idx + 1, len(current_stops),
        )

        return VirtualRouteDTO(
            id=str(updated_route.id),
            title=updated_route.title,
            province=updated_route.province,
            stops=[
                RouteStopDTO(
                    order=s.order,
                    title=s.title,
                    heritage_type=s.heritage_type,
                    province=s.province,
                    municipality=s.municipality,
                    url=s.url,
                    description=s.description,
                    heritage_asset_id=s.heritage_asset_id,
                    narrative_segment=s.narrative_segment,
                    image_url=s.image_url,
                    latitude=s.latitude,
                    longitude=s.longitude,
                )
                for s in updated_route.stops
            ],
            narrative=updated_route.narrative,
            introduction=updated_route.introduction,
            conclusion=updated_route.conclusion,
            created_at=updated_route.created_at.isoformat(),
        )

    async def _lookup_asset_info(self, asset_id: str) -> dict:
        """Look up basic asset metadata (title, type, province) from the heritage asset lookup.

        This reuses the full descriptions port to extract denomination info.
        The descriptions dict already contains 'Nombre oficial: ...' lines.
        We parse the structured text to extract what we need.
        """
        descriptions = await self._heritage_asset_lookup.get_asset_full_descriptions(
            [asset_id],
        )
        text = descriptions.get(asset_id, "")
        info: dict = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("Nombre oficial:"):
                info["title"] = line.replace("Nombre oficial:", "").strip()
            elif line.startswith("Ubicacion:"):
                loc = line.replace("Ubicacion:", "").strip()
                parts = [p.strip() for p in loc.split(",")]
                if len(parts) >= 2:
                    info["municipality"] = parts[0]
                    info["province"] = parts[1]
                elif len(parts) == 1:
                    info["province"] = parts[0]
        # heritage_type and url are not in the full descriptions output,
        # set sensible defaults
        info.setdefault("title", asset_id)
        info.setdefault("heritage_type", "")
        info.setdefault("province", "")
        info.setdefault("url", "")
        return info


def _rebuild_narrative(
    introduction: str,
    stops: list[dict],
    conclusion: str,
) -> str:
    """Rebuild the monolithic narrative from introduction + stop segments + conclusion."""
    parts: list[str] = []
    if introduction:
        parts.append(introduction)
    for stop in stops:
        segment = stop.get("narrative_segment", "")
        if segment:
            parts.append(segment)
    if conclusion:
        parts.append(conclusion)
    return "\n\n".join(parts)
