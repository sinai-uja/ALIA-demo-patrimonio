from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

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

if TYPE_CHECKING:
    from src.domain.shared.ports.trace_repository import TraceRepository

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
        trace_repository: TraceRepository | None = None,
    ) -> None:
        self._rag_port = rag_port
        self._llm_port = llm_port
        self._route_repository = route_repository
        self._route_builder_service = route_builder_service
        self._query_extraction_service = query_extraction_service
        self._heritage_asset_lookup_port = heritage_asset_lookup_port
        self._uow = unit_of_work
        self._trace_repo = trace_repository

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
        t_extract = time.perf_counter()
        raw_extraction = await self._llm_port.generate_structured(
            system_prompt=QUERY_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=extraction_prompt,
        )
        extract_ms = (time.perf_counter() - t_extract) * 1000
        extracted_query = (
            raw_extraction.strip().strip('"').strip("'")
        )
        # Keep only first line (LLM sometimes adds "Nota:" explanations)
        extracted_query = extracted_query.split("\n")[0].strip()
        logger.info(
            "Route generation: user=%s extracted_query=%r from user_query=%r",
            user_label, extracted_query, dto.query[:80],
        )

        # 3. Single RAG call with extracted query + filters
        t_rag = time.perf_counter()
        _, chunks, rag_pipeline_steps = await self._rag_port.query(
            question=extracted_query,
            top_k=dto.num_stops * 3,
            heritage_type_filter=dto.heritage_type_filter,
            province_filter=dto.province_filter,
            municipality_filter=dto.municipality_filter,
        )

        rag_ms = (time.perf_counter() - t_rag) * 1000
        logger.info(
            "Route generation: RAG returned %d chunks for query=%r",
            len(chunks), extracted_query,
        )

        # 4. SELECT STOPS FIRST (before narrative generation)
        t_select = time.perf_counter()
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

        select_ms = (time.perf_counter() - t_select) * 1000

        # 5. Resolve province label
        province_label = (
            dto.province_filter[0]
            if dto.province_filter
            else selected_chunks[0].get("province", "Andalucia")
            if selected_chunks
            else "Andalucia"
        )

        # 6. Look up heritage asset previews (images, coordinates)
        t_lookup = time.perf_counter()
        asset_ids = []
        for chunk in selected_chunks:
            doc_id = chunk.get("document_id", "")
            if doc_id:
                asset_ids.append(extract_asset_id(doc_id))
        asset_previews = await self._heritage_asset_lookup_port.get_asset_previews(
            [aid for aid in asset_ids if aid]
        )

        lookup_ms = (time.perf_counter() - t_lookup) * 1000

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
        t_narrative = time.perf_counter()
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
        narrative_ms = (time.perf_counter() - t_narrative) * 1000
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
        t_build = time.perf_counter()
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

        build_ms = (time.perf_counter() - t_build) * 1000

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

        # --- Trace instrumentation ---
        if self._trace_repo:
            try:
                from src.domain.shared.entities.execution_trace import ExecutionTrace

                trace_steps = [
                    {
                        "step": "query_extraction",
                        "input": {
                            "original_query": dto.query,
                            "cleaned_query": cleaned_text,
                            "system_prompt": QUERY_EXTRACTION_SYSTEM_PROMPT,
                            "user_prompt": extraction_prompt,
                        },
                        "output": {
                            "extracted_query": extracted_query,
                            "raw_response": raw_extraction,
                        },
                        "elapsed_ms": round(extract_ms, 1),
                    },
                ]
                # Insert RAG pipeline steps (embedding, vector_search, reranker)
                # Filter out llm_generate — routes don't use the RAG answer
                trace_steps.extend(
                    s for s in (rag_pipeline_steps or []) if s.get("step") != "llm_generate"
                )
                trace_steps.extend([
                    {
                        "step": "stop_selection",
                        "input": {"candidates": len(chunks), "num_stops": dto.num_stops},
                        "output": {"selected": len(selected_chunks)},
                        "results": [
                            {"rank": i, "title": c.get("title", "")[:60],
                             "type": c.get("heritage_type", ""),
                             "province": c.get("province", "")}
                            for i, c in enumerate(selected_chunks, 1)
                        ],
                        "elapsed_ms": round(select_ms, 1),
                    },
                    {
                        "step": "heritage_asset_lookup",
                        "input": {"asset_ids": len(asset_ids)},
                        "output": {"previews_found": len(asset_previews)},
                        "elapsed_ms": round(lookup_ms, 1),
                    },
                    {
                        "step": "narrative_generation",
                        "input": {
                            "system_prompt": ROUTE_SYSTEM_PROMPT,
                            "user_prompt": route_prompt,
                            "stops_context_chars": len(stops_context),
                        },
                        "output": {
                            "title": title,
                            "segments": len(narrative_segments),
                            "narrative_chars": len(introduction or "") + sum(len(s) for s in narrative_segments.values()) + len(conclusion or ""),
                            "raw_response": route_narrative.raw_response if route_narrative.raw_response else None,
                            "parse_method": route_narrative.parse_method,
                            "parsed_introduction": introduction or "",
                            "parsed_conclusion": conclusion or "",
                        },
                        "elapsed_ms": round(narrative_ms, 1),
                    },
                    {
                        "step": "route_build",
                        "output": {
                            "route_id": str(saved_route.id),
                            "stops": len(route.stops),
                            "province": province_label,
                        },
                        "elapsed_ms": round(build_ms, 1),
                    },
                ])
                trace = ExecutionTrace(
                    id=uuid4(),
                    execution_type="route",
                    execution_id=str(saved_route.id),
                    user_id=dto.user_id,
                    username=dto.username,
                    user_profile_type=dto.user_profile_type,
                    query=dto.query,
                    pipeline_mode="route_generation",
                    steps=trace_steps,
                    summary={
                        "total_results": len(selected_chunks),
                        "elapsed_ms": round(elapsed_ms, 1),
                        "route_title": title[:80],
                        "stops_count": len(selected_chunks),
                    },
                    feedback_value=None,
                    status="success",
                    created_at=datetime.now(timezone.utc),
                )
                await self._trace_repo.save(trace)
            except Exception:
                logger.warning("Failed to save execution trace", exc_info=True)

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
