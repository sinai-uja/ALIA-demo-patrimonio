from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    RouteStopDTO,
    VirtualRouteDTO,
)
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.rag_port import RAGPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import ROUTE_SYSTEM_PROMPT, build_route_prompt
from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.domain.routes.value_objects.heritage_type_filter import HeritageTypeFilter


class GenerateRouteUseCase:
    """Orchestrates the full route generation pipeline."""

    def __init__(
        self,
        rag_port: RAGPort,
        llm_port: LLMPort,
        route_repository: RouteRepository,
        route_builder_service: RouteBuilderService,
    ) -> None:
        self._rag_port = rag_port
        self._llm_port = llm_port
        self._route_repository = route_repository
        self._route_builder_service = route_builder_service

    async def execute(self, dto: GenerateRouteDTO) -> VirtualRouteDTO:
        # 1. Build base RAG query
        base_query = f"patrimonio historico {dto.province}"
        if dto.user_interests:
            base_query = f"{base_query} {dto.user_interests}"

        # 2. Resolve heritage types to filter values
        heritage_types = self._resolve_heritage_types(dto.heritage_types)

        # 3. For each heritage type, query RAG with filter and collect chunks
        all_chunks: list[dict] = []
        for h_type in heritage_types:
            type_filter = None if h_type == HeritageTypeFilter.ALL else h_type
            _, chunks = await self._rag_port.query(
                question=base_query,
                top_k=3,
                heritage_type_filter=type_filter,
                province_filter=dto.province,
            )
            all_chunks.extend(chunks)

        # 4. Build context string from all collected chunks
        context_parts: list[str] = []
        for idx, chunk in enumerate(all_chunks, start=1):
            part = (
                f"[{idx}] {chunk.get('title', '')} "
                f"({chunk.get('heritage_type', '')}, {chunk.get('province', '')})\n"
                f"{chunk.get('content', '')}\n"
                f"Fuente: {chunk.get('url', '')}"
            )
            context_parts.append(part)
        context = "\n---\n".join(context_parts)

        # 5. Generate route narrative with LLM
        type_labels = [h.value if hasattr(h, "value") else str(h) for h in heritage_types]
        user_prompt = build_route_prompt(
            province=dto.province,
            num_stops=dto.num_stops,
            heritage_types=type_labels,
            context=context,
        )
        narrative = await self._llm_port.generate_structured(
            system_prompt=ROUTE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # 6. Extract a title from the narrative (first line) or use a default
        title = self._extract_title(narrative, dto.province)

        # 7. Build VirtualRoute entity via domain service
        route = self._route_builder_service.build(
            chunks=all_chunks,
            province=dto.province,
            num_stops=dto.num_stops,
            narrative=narrative,
            title=title,
        )

        # 8. Save route
        saved_route = await self._route_repository.save_route(route)

        # 9. Map to output DTO
        return self._to_dto(saved_route)

    def _resolve_heritage_types(self, types: list[str]) -> list[str]:
        """Resolve heritage type strings to HeritageTypeFilter values."""
        if not types or "ALL" in types:
            return [
                HeritageTypeFilter.PAISAJE_CULTURAL,
                HeritageTypeFilter.PATRIMONIO_INMATERIAL,
                HeritageTypeFilter.PATRIMONIO_INMUEBLE,
                HeritageTypeFilter.PATRIMONIO_MUEBLE,
            ]
        resolved = []
        for t in types:
            try:
                resolved.append(HeritageTypeFilter(t))
            except ValueError:
                resolved.append(t)
        return resolved

    def _extract_title(self, narrative: str, province: str) -> str:
        """Extract a title from the first line of the narrative."""
        if narrative:
            first_line = narrative.strip().split("\n")[0].strip()
            # Remove markdown-style headers
            clean = first_line.lstrip("#").strip().strip('"').strip("*").strip()
            if clean and len(clean) < 200:
                return clean
        return f"Ruta cultural por {province}"

    def _to_dto(self, route) -> VirtualRouteDTO:
        return VirtualRouteDTO(
            id=str(route.id),
            title=route.title,
            province=route.province,
            stops=[
                RouteStopDTO(
                    order=stop.order,
                    title=stop.title,
                    heritage_type=stop.heritage_type,
                    province=stop.province,
                    municipality=stop.municipality,
                    url=stop.url,
                    description=stop.description,
                    visit_duration_minutes=stop.visit_duration_minutes,
                )
                for stop in route.stops
            ],
            total_duration_minutes=route.total_duration_minutes,
            narrative=route.narrative,
            created_at=route.created_at.isoformat(),
        )
