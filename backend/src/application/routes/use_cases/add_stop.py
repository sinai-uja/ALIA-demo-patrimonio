"""Use case: add a new stop to an existing route."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.routes.dto.routes_dto import RouteStopDTO, VirtualRouteDTO
from src.application.routes.exceptions import RouteNotFoundError
from src.domain.routes.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import (
    CONCLUSION_SYSTEM_PROMPT,
    INTRO_REGEN_SYSTEM_PROMPT,
    SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
    build_conclusion_prompt,
    build_intro_regen_prompt,
    build_single_stop_narrative_prompt,
)
from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork
from src.domain.shared.value_objects.asset_id import extract_asset_id

logger = logging.getLogger("iaph.routes.add_stop")


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting and LLM meta-text artifacts."""
    text = text.strip()
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # Remove LLM echo prefixes like "Narrativa para...: " or "Conclusión para...: "
    text = re.sub(
        r"^(?:Narrativa|Conclusion|Conclusión|Introduccion|Introducción)"
        r"\s+para\s+.*?:\s*",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    # Remove trailing parenthetical meta-instructions
    text = re.sub(
        r"\s*\((?:Transición|Transicion)\s+natural\b[^)]*\)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip().strip('"')


def _build_stops_context(stops: list[dict]) -> str:
    """Build the stops context block used by intro/conclusion prompts.

    Matches the format used by generate_route_stream.py.
    """
    parts: list[str] = []
    for stop in stops:
        title = stop.get("title", "")
        heritage_type = stop.get("heritage_type", "")
        province = stop.get("province", "")
        description = stop.get("description", "") or ""
        url = stop.get("url", "") or ""
        order = stop.get("order", 0)
        part = (
            f"[Parada {order}] {title} ({heritage_type}, {province})\n"
            f"{description}\n"
            f"Fuente: {url}"
        )
        parts.append(part)
    return "\n---\n".join(parts)


class AddStopUseCase:
    """Adds a new stop to an existing route with LLM-generated narrative."""

    def __init__(
        self,
        route_repository: RouteRepository,
        heritage_asset_lookup_port: HeritageAssetLookupPort,
        llm_port: LLMPort,
        unit_of_work: UnitOfWork,
        trace_repository: TraceRepository | None = None,
        route_builder_service: RouteBuilderService | None = None,
    ) -> None:
        self._route_repository = route_repository
        self._heritage_asset_lookup = heritage_asset_lookup_port
        self._llm_port = llm_port
        self._uow = unit_of_work
        self._trace_repo = trace_repository
        self._route_builder_service = (
            route_builder_service or RouteBuilderService()
        )

    async def execute(
        self,
        route_id: str,
        document_id: str,
        position: int | None = None,
        user_id: str | None = None,
        username: str | None = None,
        user_profile_type: str | None = None,
    ) -> VirtualRouteDTO:
        t0 = time.monotonic()
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
            t_lookup = time.perf_counter()
            previews = await self._heritage_asset_lookup.get_asset_previews(
                [asset_id],
            )
            descriptions = await self._heritage_asset_lookup.get_asset_full_descriptions(
                [asset_id],
            )
            lookup_ms = (time.perf_counter() - t_lookup) * 1000

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
            asset_info = await self._lookup_asset_info(asset_id)
            stop_title = asset_info.get("title", document_id)
            stop_type = asset_info.get("heritage_type", "")
            stop_province = asset_info.get("province", route.province)
            stop_municipality = preview.municipality if preview else asset_info.get("municipality")
            stop_url = asset_info.get("url", "")

            # Truncate description for prompt (max ~2000 chars to keep prompt short)
            prompt_description = description_text[:2000] if description_text else stop_title

            # Build the new stop dict (without narrative yet)
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
                "narrative_segment": "",  # populated after LLM call
                "image_url": preview.image_url if preview else None,
                "latitude": preview.latitude if preview else None,
                "longitude": preview.longitude if preview else None,
            }

            # Compute the final stop list (in memory) BEFORE launching LLM
            # calls so the intro/conclusion prompts see the actual final order.
            final_stops = list(current_stops)
            final_stops.insert(insert_idx, new_stop)
            for idx, stop in enumerate(final_stops, start=1):
                stop["order"] = idx

            # Build stops_context for the final list
            stops_context = _build_stops_context(final_stops)

            # --- Launch THREE LLM calls in parallel ---
            narrative_prompt = build_single_stop_narrative_prompt(
                route_title=route.title,
                stop_title=stop_title,
                stop_type=stop_type,
                stop_province=stop_province,
                stop_description=prompt_description,
                previous_stop_title=prev_title,
                next_stop_title=next_title,
            )
            intro_prompt = build_intro_regen_prompt(
                route_title=route.title,
                stops_context=stops_context,
            )
            conclusion_prompt = build_conclusion_prompt(
                route_title=route.title,
                stops_context=stops_context,
            )

            t_narrative = time.perf_counter()
            raw_narrative, raw_intro, raw_conclusion = await asyncio.gather(
                self._llm_port.generate_structured(
                    system_prompt=SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
                    user_prompt=narrative_prompt,
                    max_tokens=300,
                ),
                self._llm_port.generate_structured(
                    system_prompt=INTRO_REGEN_SYSTEM_PROMPT,
                    user_prompt=intro_prompt,
                    max_tokens=400,
                ),
                self._llm_port.generate_structured(
                    system_prompt=CONCLUSION_SYSTEM_PROMPT,
                    user_prompt=conclusion_prompt,
                    max_tokens=300,
                ),
            )
            narrative_ms = (time.perf_counter() - t_narrative) * 1000

            # Strip markdown/echo artifacts
            narrative_segment = _strip_markdown(raw_narrative)
            new_introduction = _strip_markdown(raw_intro)
            new_conclusion = _strip_markdown(raw_conclusion)

            # Fallback: if intro/conclusion regen returned empty, keep the
            # previous value and log a warning so the operation still succeeds.
            intro_fallback_used = False
            conclusion_fallback_used = False
            if not new_introduction.strip():
                logger.warning(
                    "Intro regeneration returned empty; keeping previous "
                    "introduction (route_id=%s)",
                    route_id,
                )
                new_introduction = route.introduction
                intro_fallback_used = True
            if not new_conclusion.strip():
                logger.warning(
                    "Conclusion regeneration returned empty; keeping previous "
                    "conclusion (route_id=%s)",
                    route_id,
                )
                new_conclusion = route.conclusion
                conclusion_fallback_used = True

            # Attach narrative to the new stop in the final list
            for stop in final_stops:
                if stop["heritage_asset_id"] == asset_id and stop["order"] == insert_idx + 1:
                    stop["narrative_segment"] = narrative_segment
                    break

            # Build segments-by-order dict for narrative rebuild
            segments_by_order: dict[int, str] = {
                s["order"]: s.get("narrative_segment", "") or ""
                for s in final_stops
            }

            narrative = self._route_builder_service.rebuild_narrative(
                introduction=new_introduction,
                segments_by_order=segments_by_order,
                conclusion=new_conclusion,
            )

            t_update = time.perf_counter()
            updated_route = await self._route_repository.update_route(
                route_uuid,
                user_uuid,
                stops=final_stops,
                narrative=narrative,
                introduction=new_introduction,
                conclusion=new_conclusion,
            )
            if updated_route is None:
                raise RouteNotFoundError(f"Route not found: {route_id}")
            update_ms = (time.perf_counter() - t_update) * 1000

        logger.info(
            "Stop added: route_id=%s document_id=%s position=%d total_stops=%d",
            route_id, document_id, insert_idx + 1, len(final_stops),
        )

        total_ms = (time.monotonic() - t0) * 1000

        # --- Trace instrumentation ---
        if self._trace_repo is not None:
            try:
                trace_steps = [
                    {
                        "step": "stop_addition_request",
                        "input": {
                            "route_id": route_id,
                            "document_id": document_id,
                            "requested_position": position,
                        },
                        "output": {
                            "insert_idx": insert_idx + 1,  # 1-indexed
                            "stops_before": num_stops,
                            "stops_after": len(final_stops),
                            "prev_stop_title": prev_title,
                            "next_stop_title": next_title,
                        },
                    },
                    {
                        "step": "heritage_asset_lookup",
                        "input": {"asset_ids": 1, "document_id": document_id},
                        "output": {
                            "preview_found": preview is not None,
                            "description_chars": len(description_text),
                            "stop_title": stop_title,
                            "stop_type": stop_type,
                            "stop_province": stop_province,
                        },
                        "elapsed_ms": round(lookup_ms, 1),
                    },
                    {
                        "step": "narrative_generation",
                        "input": {
                            "system_prompt": SINGLE_STOP_NARRATIVE_SYSTEM_PROMPT,
                            "user_prompt": narrative_prompt,
                            "stop_title": stop_title,
                            "prev_stop_title": prev_title,
                            "next_stop_title": next_title,
                        },
                        "output": {
                            "raw_response": raw_narrative,
                            "narrative_segment": narrative_segment,
                            "narrative_chars": len(narrative_segment),
                        },
                        "elapsed_ms": round(narrative_ms, 1),
                    },
                    {
                        "step": "narrative_regeneration",
                        "input": {
                            "intro_system_prompt": INTRO_REGEN_SYSTEM_PROMPT,
                            "intro_user_prompt": intro_prompt,
                            "conclusion_system_prompt": CONCLUSION_SYSTEM_PROMPT,
                            "conclusion_user_prompt": conclusion_prompt,
                        },
                        "output": {
                            "raw_intro": raw_intro,
                            "raw_conclusion": raw_conclusion,
                            "introduction": new_introduction,
                            "conclusion": new_conclusion,
                            "intro_fallback_used": intro_fallback_used,
                            "conclusion_fallback_used": conclusion_fallback_used,
                        },
                        "elapsed_ms": round(narrative_ms, 1),
                    },
                    {
                        "step": "route_update",
                        "output": {
                            "route_id": str(updated_route.id),
                            "total_stops": len(updated_route.stops),
                            "narrative_chars": len(updated_route.narrative or ""),
                        },
                        "elapsed_ms": round(update_ms, 1),
                    },
                ]
                trace = ExecutionTrace(
                    id=uuid4(),
                    execution_type="route",
                    execution_id=str(updated_route.id),
                    user_id=user_id,
                    username=username,
                    user_profile_type=user_profile_type,
                    query=f"+ {stop_title} (posición {insert_idx + 1})",
                    pipeline_mode="route_add_stop",
                    steps=trace_steps,
                    summary={
                        "action": "add_stop",
                        "document_id": document_id,
                        "stop_title": stop_title,
                        "position": insert_idx + 1,
                        "stops_before": num_stops,
                        "stops_after": len(final_stops),
                        "narrative_chars": len(narrative_segment),
                        "elapsed_ms": round(total_ms, 1),
                    },
                    feedback_value=None,
                    status="success",
                    created_at=datetime.now(UTC),
                )
                await self._trace_repo.save(trace)
            except Exception:
                logger.warning("Failed to save add_stop execution trace", exc_info=True)

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
        for raw_line in text.split("\n"):
            line = raw_line.strip()
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
