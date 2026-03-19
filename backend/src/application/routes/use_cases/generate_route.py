from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    RouteStopDTO,
    VirtualRouteDTO,
)
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.rag_port import RAGPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import (
    QUERY_EXTRACTION_SYSTEM_PROMPT,
    ROUTE_SYSTEM_PROMPT,
    build_query_extraction_prompt,
    build_route_prompt,
)
from src.domain.routes.services.query_extraction_service import (
    QueryExtractionService,
)
from src.domain.routes.services.route_builder_service import (
    RouteBuilderService,
)


class GenerateRouteUseCase:
    """Orchestrates the full route generation pipeline."""

    def __init__(
        self,
        rag_port: RAGPort,
        llm_port: LLMPort,
        route_repository: RouteRepository,
        route_builder_service: RouteBuilderService,
        query_extraction_service: QueryExtractionService,
    ) -> None:
        self._rag_port = rag_port
        self._llm_port = llm_port
        self._route_repository = route_repository
        self._route_builder_service = route_builder_service
        self._query_extraction_service = query_extraction_service

    async def execute(self, dto: GenerateRouteDTO) -> VirtualRouteDTO:
        # 1. Clean user text (remove geographic filter terms)
        cleaned_text = self._query_extraction_service.clean_query_text(
            user_text=dto.query,
            province_filters=dto.province_filter,
            municipality_filters=dto.municipality_filter,
        )

        # 2. Extract concise RAG query via LLM
        extraction_prompt = build_query_extraction_prompt(
            cleaned_text=cleaned_text,
            province_filter=dto.province_filter,
            municipality_filter=dto.municipality_filter,
        )
        extracted_query = await self._llm_port.generate_structured(
            system_prompt=QUERY_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=extraction_prompt,
        )
        extracted_query = (
            extracted_query.strip().strip('"').strip("'")
        )

        # 3. Single RAG call with extracted query + filters
        _, chunks = await self._rag_port.query(
            question=extracted_query,
            top_k=dto.num_stops * 3,
            heritage_type_filter=dto.heritage_type_filter,
            province_filter=dto.province_filter,
            municipality_filter=dto.municipality_filter,
        )

        # 4. Build context string
        context_parts: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            part = (
                f"[{idx}] {chunk.get('title', '')} "
                f"({chunk.get('heritage_type', '')}, "
                f"{chunk.get('province', '')})\n"
                f"{chunk.get('content', '')}\n"
                f"Fuente: {chunk.get('url', '')}"
            )
            context_parts.append(part)
        context = "\n---\n".join(context_parts)

        # 5. Generate rich route narrative via LLM
        route_prompt = build_route_prompt(
            query=extracted_query,
            num_stops=dto.num_stops,
            context=context,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )
        narrative = await self._llm_port.generate_structured(
            system_prompt=ROUTE_SYSTEM_PROMPT,
            user_prompt=route_prompt,
        )

        # 6. Extract title
        province_label = (
            dto.province_filter[0]
            if dto.province_filter
            else chunks[0].get("province", "Andalucia")
            if chunks
            else "Andalucia"
        )
        title = self._extract_title(narrative, province_label)

        # 7. Build route via domain service
        route = self._route_builder_service.build(
            chunks=chunks,
            province=province_label,
            num_stops=dto.num_stops,
            narrative=narrative,
            title=title,
        )

        # 8. Save and return
        saved_route = await self._route_repository.save_route(route)
        return self._to_dto(saved_route)

    def _extract_title(self, narrative: str, province: str) -> str:
        if narrative:
            first_line = narrative.strip().split("\n")[0].strip()
            clean = (
                first_line.lstrip("#")
                .strip()
                .strip('"')
                .strip("*")
                .strip()
            )
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
