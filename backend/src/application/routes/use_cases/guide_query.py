from src.application.routes.dto.routes_dto import GuideQueryDTO, GuideResponseDTO
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.rag_port import RAGPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import GUIDE_SYSTEM_PROMPT, build_guide_prompt


class GuideQueryUseCase:
    """Handles guide-mode questions about a specific route using RAG."""

    def __init__(
        self,
        rag_port: RAGPort,
        llm_port: LLMPort,
        route_repository: RouteRepository,
    ) -> None:
        self._rag_port = rag_port
        self._llm_port = llm_port
        self._route_repository = route_repository

    async def execute(self, dto: GuideQueryDTO) -> GuideResponseDTO:
        from uuid import UUID

        # 1. Load the route
        route = await self._route_repository.get_route(UUID(dto.route_id))
        if route is None:
            raise ValueError(f"Route not found: {dto.route_id}")

        # 2. Build route context from stops
        route_context_parts: list[str] = []
        for stop in route.stops:
            route_context_parts.append(
                f"Parada {stop.order}: {stop.title} ({stop.heritage_type}, "
                f"{stop.province})\n{stop.description}"
            )
        route_context = "\n---\n".join(route_context_parts)

        # 3. Query RAG filtered by province for additional context
        _, chunks = await self._rag_port.query(
            question=dto.question,
            top_k=5,
            province_filter=route.province,
        )

        # 4. Assemble RAG context
        rag_parts: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            rag_parts.append(
                f"[{idx}] {chunk.get('title', '')} "
                f"({chunk.get('heritage_type', '')}, {chunk.get('province', '')})\n"
                f"{chunk.get('content', '')}"
            )
        rag_context = "\n---\n".join(rag_parts)

        # 5. Generate answer with LLM
        user_prompt = build_guide_prompt(
            question=dto.question,
            route_context=route_context,
            rag_context=rag_context,
        )
        answer = await self._llm_port.generate_structured(
            system_prompt=GUIDE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # 6. Build sources list
        sources = [
            {
                "title": chunk.get("title", ""),
                "url": chunk.get("url", ""),
                "heritage_type": chunk.get("heritage_type", ""),
                "province": chunk.get("province", ""),
            }
            for chunk in chunks
        ]

        return GuideResponseDTO(answer=answer, sources=sources)
