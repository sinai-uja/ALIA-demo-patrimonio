"""Use case: remove a stop from an existing route."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.routes.dto.routes_dto import RouteStopDTO, VirtualRouteDTO
from src.application.routes.exceptions import RouteNotFoundError
from src.domain.routes.ports.llm_port import LLMPort
from src.domain.routes.ports.route_repository import RouteRepository
from src.domain.routes.prompts import (
    CONCLUSION_SYSTEM_PROMPT,
    INTRO_REGEN_SYSTEM_PROMPT,
    build_conclusion_prompt,
    build_intro_regen_prompt,
)
from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository
from src.domain.shared.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("iaph.routes.remove_stop")


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting and LLM meta-text artifacts."""
    text = text.strip()
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    text = re.sub(
        r"^(?:Narrativa|Conclusion|Conclusión|Introduccion|Introducción)"
        r"\s+para\s+.*?:\s*",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
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


class RemoveStopUseCase:
    """Removes a stop from an existing route and reorders the remaining ones."""

    def __init__(
        self,
        route_repository: RouteRepository,
        unit_of_work: UnitOfWork,
        llm_port: LLMPort | None = None,
        trace_repository: TraceRepository | None = None,
        route_builder_service: RouteBuilderService | None = None,
    ) -> None:
        self._route_repository = route_repository
        self._uow = unit_of_work
        self._llm_port = llm_port
        self._trace_repo = trace_repository
        self._route_builder_service = (
            route_builder_service or RouteBuilderService()
        )

    async def execute(
        self,
        route_id: str,
        stop_order: int,
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

            # Capture metadata of the stop being removed for tracing
            removed_stop = next((s for s in route.stops if s.order == stop_order), None)
            removed_stop_title = removed_stop.title if removed_stop else "?"
            removed_stop_type = removed_stop.heritage_type if removed_stop else ""
            removed_document_id = removed_stop.document_id if removed_stop else ""

            # Find and remove the stop at the given order
            remaining_stops = [s for s in route.stops if s.order != stop_order]
            if len(remaining_stops) == len(route.stops):
                raise RouteNotFoundError(
                    f"Stop with order {stop_order} not found in route {route_id}",
                )

            # Reorder remaining stops sequentially (1, 2, 3, ...)
            reordered_stops = []
            for idx, stop in enumerate(remaining_stops, start=1):
                reordered_stops.append({
                    "order": idx,
                    "title": stop.title,
                    "heritage_type": stop.heritage_type,
                    "province": stop.province,
                    "municipality": stop.municipality,
                    "url": stop.url,
                    "description": stop.description,
                    "heritage_asset_id": stop.heritage_asset_id,
                    "document_id": stop.document_id,
                    "narrative_segment": stop.narrative_segment,
                    "image_url": stop.image_url,
                    "latitude": stop.latitude,
                    "longitude": stop.longitude,
                })

            # --- Regenerate intro + conclusion based on the FINAL stop list ---
            new_introduction = route.introduction
            new_conclusion = route.conclusion
            raw_intro = ""
            raw_conclusion = ""
            intro_fallback_used = False
            conclusion_fallback_used = False
            regen_ms = 0.0
            intro_prompt = ""
            conclusion_prompt = ""

            if self._llm_port is not None and reordered_stops:
                stops_context = _build_stops_context(reordered_stops)
                intro_prompt = build_intro_regen_prompt(
                    route_title=route.title,
                    stops_context=stops_context,
                )
                conclusion_prompt = build_conclusion_prompt(
                    route_title=route.title,
                    stops_context=stops_context,
                )

                t_regen = time.perf_counter()
                raw_intro, raw_conclusion = await asyncio.gather(
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
                regen_ms = (time.perf_counter() - t_regen) * 1000

                new_introduction_candidate = _strip_markdown(raw_intro)
                new_conclusion_candidate = _strip_markdown(raw_conclusion)

                if not new_introduction_candidate.strip():
                    logger.warning(
                        "Intro regeneration returned empty; keeping previous "
                        "introduction (route_id=%s)",
                        route_id,
                    )
                    intro_fallback_used = True
                else:
                    new_introduction = new_introduction_candidate
                if not new_conclusion_candidate.strip():
                    logger.warning(
                        "Conclusion regeneration returned empty; keeping previous "
                        "conclusion (route_id=%s)",
                        route_id,
                    )
                    conclusion_fallback_used = True
                else:
                    new_conclusion = new_conclusion_candidate

            # Rebuild the monolithic narrative from intro + segments + conclusion
            segments_by_order: dict[int, str] = {
                s["order"]: s.get("narrative_segment", "") or ""
                for s in reordered_stops
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
                stops=reordered_stops,
                narrative=narrative,
                introduction=new_introduction,
                conclusion=new_conclusion,
            )
            if updated_route is None:
                raise RouteNotFoundError(f"Route not found: {route_id}")
            update_ms = (time.perf_counter() - t_update) * 1000

        logger.info(
            "Stop removed: route_id=%s stop_order=%d remaining=%d",
            route_id, stop_order, len(reordered_stops),
        )

        total_ms = (time.monotonic() - t0) * 1000

        # --- Trace instrumentation ---
        if self._trace_repo is not None:
            try:
                trace_steps: list[dict] = [
                    {
                        "step": "stop_removal",
                        "input": {
                            "route_id": route_id,
                            "stop_order": stop_order,
                        },
                        "output": {
                            "removed_stop_title": removed_stop_title,
                            "removed_stop_type": removed_stop_type,
                            "removed_document_id": removed_document_id,
                            "stops_before": len(route.stops),
                            "stops_after": len(reordered_stops),
                        },
                    },
                ]
                if self._llm_port is not None and reordered_stops:
                    trace_steps.append({
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
                        "elapsed_ms": round(regen_ms, 1),
                    })
                trace_steps.append({
                    "step": "route_update",
                    "output": {
                        "route_id": str(updated_route.id),
                        "total_stops": len(updated_route.stops),
                        "narrative_chars": len(updated_route.narrative or ""),
                    },
                    "elapsed_ms": round(update_ms, 1),
                })
                trace = ExecutionTrace(
                    id=uuid4(),
                    execution_type="route",
                    execution_id=str(updated_route.id),
                    user_id=user_id,
                    username=username,
                    user_profile_type=user_profile_type,
                    query=f"- {removed_stop_title} (posición {stop_order})",
                    pipeline_mode="route_remove_stop",
                    steps=trace_steps,
                    summary={
                        "action": "remove_stop",
                        "removed_stop_title": removed_stop_title,
                        "removed_order": stop_order,
                        "stops_before": len(route.stops),
                        "stops_after": len(reordered_stops),
                        "elapsed_ms": round(total_ms, 1),
                    },
                    feedback_value=None,
                    status="success",
                    created_at=datetime.now(UTC),
                )
                await self._trace_repo.save(trace)
            except Exception:
                logger.warning("Failed to save remove_stop execution trace", exc_info=True)

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
