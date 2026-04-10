import logging
import time
from uuid import UUID

from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    RouteStopDTO,
    VirtualRouteDTO,
)
from src.config import settings
from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
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
from src.domain.shared.ports.unit_of_work import UnitOfWork
from src.domain.shared.value_objects.asset_id import extract_asset_id

logger = logging.getLogger("iaph.routes.generate_route")


class GenerateRouteUseCase:
    """Orchestrates the full route generation pipeline."""

    def __init__(
        self,
        rag_port: RAGPort,
        llm_port: LLMPort,
        route_repository: RouteRepository,
        route_builder_service: RouteBuilderService,
        query_extraction_service: QueryExtractionService,
        heritage_asset_lookup_port: HeritageAssetLookupPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._rag_port = rag_port
        self._llm_port = llm_port
        self._route_repository = route_repository
        self._route_builder_service = route_builder_service
        self._query_extraction_service = query_extraction_service
        self._heritage_asset_lookup_port = heritage_asset_lookup_port
        self._uow = unit_of_work

    async def execute(self, dto: GenerateRouteDTO) -> VirtualRouteDTO:
        t0 = time.monotonic()
        user_label = dto.username or "anonymous"

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
        logger.info(
            "Route generation: user=%s extracted_query=%r from user_query=%r",
            user_label, extracted_query, dto.query[:80],
        )

        # 3. Single RAG call with extracted query + filters
        _, chunks = await self._rag_port.query(
            question=extracted_query,
            top_k=dto.num_stops * 3,
            heritage_type_filter=dto.heritage_type_filter,
            province_filter=dto.province_filter,
            municipality_filter=dto.municipality_filter,
        )

        logger.info(
            "Route generation: RAG returned %d chunks for query=%r",
            len(chunks), extracted_query,
        )

        # 4. SELECT STOPS FIRST (before narrative generation)
        selected_chunks = self._route_builder_service.select_diverse_stops(
            chunks=chunks,
            num_stops=dto.num_stops,
        )

        for i, chunk in enumerate(selected_chunks, 1):
            logger.info(
                "Route stop #%d: title=%s | type=%s | province=%s",
                i, chunk.get("title", "")[:60],
                chunk.get("heritage_type", ""), chunk.get("province", ""),
            )

        # 5. Resolve province label
        province_label = (
            dto.province_filter[0]
            if dto.province_filter
            else selected_chunks[0].get("province", "Andalucia")
            if selected_chunks
            else "Andalucia"
        )

        # 6. Look up heritage asset previews (images, coordinates)
        asset_ids = []
        for chunk in selected_chunks:
            doc_id = chunk.get("document_id", "")
            if doc_id:
                asset_ids.append(extract_asset_id(doc_id))
        asset_previews = await self._heritage_asset_lookup_port.get_asset_previews(
            [aid for aid in asset_ids if aid]
        )

        # 7. Build context string ONLY from selected stops
        stops_context_parts: list[str] = []
        for idx, chunk in enumerate(selected_chunks, start=1):
            part = (
                f"[Parada {idx}] {chunk.get('title', '')} "
                f"({chunk.get('heritage_type', '')}, "
                f"{chunk.get('province', '')})\n"
                f"{chunk.get('content', '')}\n"
                f"Fuente: {chunk.get('url', '')}"
            )
            stops_context_parts.append(part)
        stops_context = "\n---\n".join(stops_context_parts)

        # 8. Generate per-stop narrative via LLM (structured JSON)
        route_prompt = build_route_prompt(
            query=extracted_query,
            stops_context=stops_context,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )
        route_narrative = await self._llm_port.generate_route_narrative(
            system_prompt=ROUTE_SYSTEM_PROMPT,
            user_prompt=route_prompt,
            province_label=province_label,
            max_tokens=min(
                len(selected_chunks) * 400 + 500,
                settings.llm_route_narrative_max_tokens,
            ),
        )
        title = route_narrative.title
        introduction = route_narrative.introduction
        narrative_segments = route_narrative.segments
        conclusion = route_narrative.conclusion

        # 9. Compose monolithic narrative for backward compatibility
        narrative_parts = [introduction]
        for i in range(1, len(selected_chunks) + 1):
            if i in narrative_segments:
                narrative_parts.append(narrative_segments[i])
        narrative_parts.append(conclusion)
        narrative = "\n\n".join(p for p in narrative_parts if p)

        # 10. Build route entity with enriched data
        route = self._route_builder_service.build(
            selected_chunks=selected_chunks,
            province=province_label,
            title=title,
            narrative=narrative,
            introduction=introduction,
            conclusion=conclusion,
            narrative_segments=narrative_segments,
            asset_previews=asset_previews,
        )

        # 11. Save and return
        user_uuid = UUID(dto.user_id) if dto.user_id else None
        async with self._uow:
            saved_route = await self._route_repository.save_route(
                route, user_id=user_uuid,
            )
            result = self._to_dto(saved_route)
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "Route generation complete: route_id=%s user=%s title=%r stops=%d %.0fms",
            saved_route.id, user_label, title[:60], len(selected_chunks), elapsed_ms,
        )
        return result

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
                    heritage_asset_id=stop.heritage_asset_id,
                    narrative_segment=stop.narrative_segment,
                    image_url=stop.image_url,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                )
                for stop in route.stops
            ],

            narrative=route.narrative,
            introduction=route.introduction,
            conclusion=route.conclusion,
            created_at=route.created_at.isoformat(),
        )
