from src.application.routes.dto.routes_dto import GuideQueryDTO, GuideResponseDTO
from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import GUIDE_SYSTEM_PROMPT, build_guide_prompt


class GuideQueryUseCase:
    """Handles guide-mode questions about a specific route.

    Enriches each stop with full heritage asset descriptions instead of
    querying RAG, so the LLM has maximum detail about the route's stops.
    """

    def __init__(
        self,
        llm_port: LLMPort,
        route_repository: RouteRepository,
        heritage_asset_lookup_port: HeritageAssetLookupPort,
    ) -> None:
        self._llm_port = llm_port
        self._route_repository = route_repository
        self._heritage_asset_lookup_port = heritage_asset_lookup_port

    async def execute(self, dto: GuideQueryDTO) -> GuideResponseDTO:
        from uuid import UUID

        # 1. Load the route
        route = await self._route_repository.get_route(UUID(dto.route_id))
        if route is None:
            raise ValueError(f"Route not found: {dto.route_id}")

        # 2. Fetch full descriptions for all stops with heritage_asset_id
        asset_ids = [
            stop.heritage_asset_id
            for stop in route.stops
            if stop.heritage_asset_id
        ]
        full_descriptions = await self._heritage_asset_lookup_port.get_asset_full_descriptions(
            asset_ids,
        )

        # 3. Build enriched route context
        route_context_parts: list[str] = []
        for stop in route.stops:
            parts = [
                f"Parada {stop.order}: {stop.title}",
                f"Tipo: {stop.heritage_type}",
                f"Ubicacion: {stop.municipality or ''}, {stop.province}",
            ]
            # Add full heritage asset description if available
            if stop.heritage_asset_id and stop.heritage_asset_id in full_descriptions:
                desc = full_descriptions[stop.heritage_asset_id]
                if desc:
                    parts.append(f"Informacion del bien:\n{desc}")
            elif stop.description:
                parts.append(f"Descripcion: {stop.description}")

            if stop.narrative_segment:
                parts.append(f"Narrativa de la ruta: {stop.narrative_segment}")

            route_context_parts.append("\n".join(parts))

        route_context = "\n\n---\n\n".join(route_context_parts)

        # 4. Generate answer with LLM (with conversation history)
        user_prompt = build_guide_prompt(
            question=dto.question,
            route_context=route_context,
        )
        answer = await self._llm_port.generate_structured(
            system_prompt=GUIDE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            history=dto.history if dto.history else None,
        )

        return GuideResponseDTO(answer=answer)
