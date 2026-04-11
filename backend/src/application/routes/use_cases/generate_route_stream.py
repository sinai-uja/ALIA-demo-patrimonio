"""Use case: generate a route with SSE streaming events at each pipeline step."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from uuid import UUID

from src.application.routes.dto.routes_dto import GenerateRouteDTO
from datetime import datetime, timezone
from uuid import uuid4
from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.rag_port import RAGPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import (
    CONCLUSION_SYSTEM_PROMPT,
    QUERY_EXTRACTION_SYSTEM_PROMPT,
    SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
    TITLE_INTRO_SYSTEM_PROMPT,
    build_conclusion_prompt,
    build_query_extraction_prompt,
    build_single_stop_narrative_prompt,
    build_title_intro_prompt,
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

logger = logging.getLogger("iaph.routes.generate_route_stream")


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting and LLM meta-text artifacts."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # Remove LLM echo prefixes like "Narrativa para...: " or "Conclusión para...: "
    text = re.sub(
        r'^(?:Narrativa|Conclusion|Conclusión)\s+para\s+.*?:\s*',
        '', text, count=1, flags=re.IGNORECASE,
    )
    # Remove trailing parenthetical meta-instructions
    text = re.sub(
        r'\s*\((?:Transición|Transicion)\s+natural\b[^)]*\)\s*$',
        '', text, flags=re.IGNORECASE,
    )
    return text.strip().strip('"')


class GenerateRouteStreamUseCase:
    """Orchestrates route generation as an async generator yielding SSE events."""

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

    async def execute(
        self, dto: GenerateRouteDTO,
    ) -> AsyncGenerator[dict, None]:
        t0 = time.monotonic()

        try:
            # Timing + trace data collection
            t_extract = time.perf_counter()

            # --- Step 1: Query extraction ---
            yield {
                "event": "step",
                "data": {"step": "query_extraction", "status": "running"},
            }

            cleaned_text = self._query_extraction_service.clean_query_text(
                user_text=dto.query,
                province_filters=dto.province_filter,
                municipality_filters=dto.municipality_filter,
            )
            extraction_prompt = build_query_extraction_prompt(
                cleaned_text=cleaned_text,
                province_filter=dto.province_filter,
                municipality_filter=dto.municipality_filter,
            )
            raw_extraction = await self._llm_port.generate_structured(
                system_prompt=QUERY_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=extraction_prompt,
            )
            extracted_query = raw_extraction.strip().strip('"').strip("'")
            extracted_query = extracted_query.split("\n")[0].strip()

            extract_ms = (time.perf_counter() - t_extract) * 1000

            yield {
                "event": "step",
                "data": {
                    "step": "query_extraction",
                    "status": "done",
                    "extracted_query": extracted_query,
                },
            }

            # --- Step 2: RAG ---
            t_rag = time.perf_counter()
            yield {
                "event": "step",
                "data": {"step": "rag", "status": "running"},
            }

            _, chunks, _rag_steps = await self._rag_port.query(
                question=extracted_query,
                top_k=dto.num_stops * 3,
                heritage_type_filter=dto.heritage_type_filter,
                province_filter=dto.province_filter,
                municipality_filter=dto.municipality_filter,
            )

            rag_ms = (time.perf_counter() - t_rag) * 1000

            yield {
                "event": "step",
                "data": {
                    "step": "rag",
                    "status": "done",
                    "chunks": len(chunks),
                },
            }

            # --- Step 3: Stop selection ---
            t_select = time.perf_counter()
            yield {
                "event": "step",
                "data": {"step": "stop_selection", "status": "running"},
            }

            selected_chunks = self._route_builder_service.select_diverse_stops(
                chunks=chunks,
                num_stops=dto.num_stops,
            )

            select_ms = (time.perf_counter() - t_select) * 1000

            yield {
                "event": "step",
                "data": {
                    "step": "stop_selection",
                    "status": "done",
                    "count": len(selected_chunks),
                },
            }

            # --- Step 4: Asset lookup ---
            t_lookup = time.perf_counter()
            yield {
                "event": "step",
                "data": {"step": "asset_lookup", "status": "running"},
            }

            province_label = (
                dto.province_filter[0]
                if dto.province_filter
                else selected_chunks[0].get("province", "Andalucia")
                if selected_chunks
                else "Andalucia"
            )

            asset_ids = []
            for chunk in selected_chunks:
                doc_id = chunk.get("document_id", "")
                if doc_id:
                    asset_ids.append(extract_asset_id(doc_id))

            asset_previews = await self._heritage_asset_lookup_port.get_asset_previews(
                [aid for aid in asset_ids if aid],
            )

            lookup_ms = (time.perf_counter() - t_lookup) * 1000

            yield {
                "event": "step",
                "data": {
                    "step": "asset_lookup",
                    "status": "done",
                    "previews": len(asset_previews),
                },
            }

            # --- Step 5: Emit each stop (before narratives) ---
            for i, chunk in enumerate(selected_chunks, 1):
                doc_id = chunk.get("document_id", "")
                heritage_asset_id = extract_asset_id(doc_id) if doc_id else None
                preview = (
                    asset_previews.get(heritage_asset_id)
                    if heritage_asset_id
                    else None
                )

                stop_data = {
                    "order": i,
                    "title": chunk.get("title", ""),
                    "heritage_type": chunk.get("heritage_type", ""),
                    "province": chunk.get("province", ""),
                    "municipality": (
                        preview.municipality
                        if preview and preview.municipality
                        else chunk.get("municipality")
                    ),
                    "image_url": preview.image_url if preview else None,
                    "latitude": preview.latitude if preview else None,
                    "longitude": preview.longitude if preview else None,
                }
                yield {"event": "stop", "data": stop_data}

            # --- Build stops context for prompts ---
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

            # --- Step 6: Generate title + introduction ---
            t_narrative = time.perf_counter()
            narrative_llm_calls: list[dict] = []  # collect all LLM calls for trace
            yield {
                "event": "step",
                "data": {
                    "step": "narrative",
                    "status": "running",
                    "detail": "introduction",
                },
            }

            title_intro_prompt = build_title_intro_prompt(
                query=extracted_query,
                stops_context=stops_context,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            raw_title_intro = await self._llm_port.generate_structured(
                system_prompt=TITLE_INTRO_SYSTEM_PROMPT,
                user_prompt=title_intro_prompt,
                max_tokens=500,
            )

            title, introduction = _parse_title_intro(
                raw_title_intro, province_label,
            )
            title = _strip_markdown(title)
            introduction = _strip_markdown(introduction)
            narrative_llm_calls.append({
                "call": "title_introduction",
                "system_prompt": TITLE_INTRO_SYSTEM_PROMPT,
                "user_prompt": title_intro_prompt,
                "raw_response": raw_title_intro,
                "parsed_title": title,
                "parsed_introduction": introduction,
            })

            yield {
                "event": "narrative",
                "data": {
                    "order": 0,
                    "type": "introduction",
                    "title": title,
                    "text": introduction,
                },
            }

            # --- Step 7: Generate narrative for each stop ---
            narrative_segments: dict[int, str] = {}

            for i, chunk in enumerate(selected_chunks, 1):
                yield {
                    "event": "step",
                    "data": {
                        "step": "narrative",
                        "status": "running",
                        "detail": f"stop_{i}",
                    },
                }

                prev_title = (
                    selected_chunks[i - 2].get("title", "")
                    if i > 1
                    else None
                )
                next_title = (
                    selected_chunks[i].get("title", "")
                    if i < len(selected_chunks)
                    else None
                )

                narrative_prompt = build_single_stop_narrative_prompt(
                    route_title=title,
                    stop_title=chunk.get("title", ""),
                    stop_type=chunk.get("heritage_type", ""),
                    stop_province=chunk.get("province", ""),
                    stop_description=chunk.get("content", "")[:2000],
                    previous_stop_title=prev_title,
                    next_stop_title=next_title,
                )
                raw_narrative = await self._llm_port.generate_structured(
                    system_prompt=SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
                    user_prompt=narrative_prompt,
                    max_tokens=300,
                )
                narrative_text = _strip_markdown(raw_narrative)
                narrative_segments[i] = narrative_text
                narrative_llm_calls.append({
                    "call": f"stop_{i}",
                    "system_prompt": SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
                    "user_prompt": narrative_prompt,
                    "raw_response": raw_narrative,
                    "parsed_narrative": narrative_text,
                })

                yield {
                    "event": "narrative",
                    "data": {
                        "order": i,
                        "type": "stop",
                        "text": narrative_text,
                    },
                }

            # --- Step 8: Generate conclusion ---
            yield {
                "event": "step",
                "data": {
                    "step": "narrative",
                    "status": "running",
                    "detail": "conclusion",
                },
            }

            conclusion_prompt = build_conclusion_prompt(
                route_title=title,
                stops_context=stops_context,
            )
            raw_conclusion = await self._llm_port.generate_structured(
                system_prompt=CONCLUSION_SYSTEM_PROMPT,
                user_prompt=conclusion_prompt,
                max_tokens=300,
            )
            conclusion = _strip_markdown(raw_conclusion)
            narrative_llm_calls.append({
                "call": "conclusion",
                "system_prompt": CONCLUSION_SYSTEM_PROMPT,
                "user_prompt": conclusion_prompt,
                "raw_response": raw_conclusion,
                "parsed_conclusion": conclusion,
            })

            yield {
                "event": "narrative",
                "data": {
                    "order": len(selected_chunks) + 1,
                    "type": "conclusion",
                    "text": conclusion,
                },
            }

            # --- Step 9: Build and save route ---
            yield {
                "event": "step",
                "data": {"step": "saving", "status": "running"},
            }

            # Compose monolithic narrative for backward compat
            narrative_parts = [introduction]
            for i in range(1, len(selected_chunks) + 1):
                if i in narrative_segments:
                    narrative_parts.append(narrative_segments[i])
            narrative_parts.append(conclusion)
            narrative = "\n\n".join(p for p in narrative_parts if p)

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

            user_uuid = UUID(dto.user_id) if dto.user_id else None
            async with self._uow:
                saved_route = await self._route_repository.save_route(
                    route, user_id=user_uuid,
                )

            elapsed_ms = (time.monotonic() - t0) * 1000
            narrative_ms = (time.perf_counter() - t_narrative) * 1000
            logger.info(
                "Route stream generation complete: route_id=%s title=%r "
                "stops=%d %.0fms",
                saved_route.id, title[:60], len(selected_chunks), elapsed_ms,
            )

            # --- Trace instrumentation (same as generate_route.py) ---
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
                    trace_steps.extend(
                        s for s in (_rag_steps or []) if s.get("step") != "llm_generate"
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
                                "mode": "streaming_per_stop",
                                "stops_context_chars": len(stops_context),
                                "llm_calls_count": len(narrative_llm_calls),
                            },
                            "output": {
                                "title": title,
                                "segments": len(narrative_segments),
                                "narrative_chars": len(introduction or "") + sum(len(s) for s in narrative_segments.values()) + len(conclusion or ""),
                                "parsed_introduction": introduction or "",
                                "parsed_conclusion": conclusion or "",
                                "llm_calls": narrative_llm_calls,
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
                        pipeline_mode="route_generation_stream",
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

            yield {
                "event": "complete",
                "data": {
                    "route_id": str(saved_route.id),
                    "title": title,
                    "stops": len(selected_chunks),
                },
            }

        except Exception as exc:
            logger.exception("Route stream generation failed")
            yield {
                "event": "error",
                "data": {
                    "message": str(exc),
                    "step": "unknown",
                },
            }


def _parse_title_intro(
    raw_response: str, fallback_province: str,
) -> tuple[str, str]:
    """Parse the title+introduction JSON from the LLM response.

    Returns (title, introduction). Falls back gracefully on parse errors.
    """
    text = raw_response.strip()
    # Strip markdown code fences if present
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                text = stripped
                break

    # Extract the JSON object even if surrounded by extra text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]

    try:
        data = json.loads(text)
        title = _strip_markdown(data.get("title", f"Ruta por {fallback_province}"))
        introduction = _strip_markdown(data.get("introduction", ""))
        # Strip "Título:" prefix if LLM added it
        for prefix in ("Título:", "Titulo:", "título:", "titulo:"):
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
                break
        return title, introduction
    except (json.JSONDecodeError, AttributeError):
        # If we can't parse JSON, use the whole text as introduction
        logger.warning(
            "Failed to parse title+intro JSON, using fallback. Raw: %s",
            text[:200],
        )
        return f"Ruta por {fallback_province}", _strip_markdown(text)
