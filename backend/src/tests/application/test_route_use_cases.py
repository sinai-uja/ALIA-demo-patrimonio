"""Unit tests for routes application use cases."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    RouteFilterValuesDTO,
)
from src.application.routes.use_cases.add_stop import AddStopUseCase
from src.application.routes.use_cases.generate_route import GenerateRouteUseCase
from src.application.routes.use_cases.remove_stop import RemoveStopUseCase
from src.application.routes.use_cases.route_filter_values import RouteFilterValuesUseCase
from src.application.routes.use_cases.route_suggestions import RouteSuggestionsUseCase
from src.domain.routes.services.query_extraction_service import QueryExtractionService
from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.domain.routes.value_objects.asset_preview import AssetPreview
from src.domain.routes.value_objects.detected_entity import DetectedEntityResult
from src.domain.routes.value_objects.route_narrative import RouteNarrative
from src.domain.routes.value_objects.route_stop import RouteStop
from src.domain.routes.value_objects.virtual_route import VirtualRoute
from src.domain.shared.entities.execution_trace import ExecutionTrace
from src.domain.shared.ports.trace_repository import TraceRepository

# ---------------------------------------------------------------------------
# RouteSuggestionsUseCase
# ---------------------------------------------------------------------------


class TestRouteSuggestionsUseCase:
    def setup_method(self):
        self.entity_detection_port = AsyncMock()
        self.use_case = RouteSuggestionsUseCase(
            entity_detection_port=self.entity_detection_port,
        )

    async def test_maps_detected_entities_to_dtos(self):
        self.entity_detection_port.detect_entities.return_value = [
            DetectedEntityResult(
                entity_type="province",
                value="granada",
                display_label="Granada",
                matched_text="granada",
            ),
            DetectedEntityResult(
                entity_type="heritage_type",
                value="patrimonio_inmueble",
                display_label="Patrimonio Inmueble",
                matched_text="patrimonio inmueble",
            ),
        ]

        result = await self.use_case.execute("patrimonio inmueble en granada")

        assert len(result.detected_entities) == 2
        assert result.detected_entities[0].entity_type == "province"
        assert result.detected_entities[0].value == "granada"
        assert result.detected_entities[1].display_label == "Patrimonio Inmueble"

    async def test_builds_search_label_with_entity_labels(self):
        self.entity_detection_port.detect_entities.return_value = [
            DetectedEntityResult(
                entity_type="province",
                value="sevilla",
                display_label="Sevilla",
            ),
        ]

        result = await self.use_case.execute("monumentos en sevilla")

        assert result.search_label == (
            "Planificar ruta: monumentos en sevilla (Sevilla)"
        )

    async def test_search_label_with_multiple_entities(self):
        self.entity_detection_port.detect_entities.return_value = [
            DetectedEntityResult(
                entity_type="province",
                value="jaen",
                display_label="Jaen",
            ),
            DetectedEntityResult(
                entity_type="municipality",
                value="ubeda",
                display_label="Ubeda",
            ),
        ]

        result = await self.use_case.execute("ruta por ubeda")

        assert result.search_label == (
            "Planificar ruta: ruta por ubeda (Jaen, Ubeda)"
        )

    async def test_returns_empty_list_when_no_entities(self):
        self.entity_detection_port.detect_entities.return_value = []

        result = await self.use_case.execute("algo generico")

        assert result.detected_entities == []
        assert result.search_label == "Planificar ruta: algo generico"

    async def test_query_is_preserved_in_response(self):
        self.entity_detection_port.detect_entities.return_value = []

        result = await self.use_case.execute("catedrales andaluzas")

        assert result.query == "catedrales andaluzas"


# ---------------------------------------------------------------------------
# RouteFilterValuesUseCase
# ---------------------------------------------------------------------------


class TestRouteFilterValuesUseCase:
    def setup_method(self):
        self.filter_metadata_port = AsyncMock()
        self.use_case = RouteFilterValuesUseCase(
            filter_metadata_port=self.filter_metadata_port,
        )

    async def test_delegates_to_port_and_returns_dto(self):
        self.filter_metadata_port.get_distinct_heritage_types.return_value = [
            "patrimonio_inmueble",
            "patrimonio_mueble",
        ]
        self.filter_metadata_port.get_distinct_provinces.return_value = [
            "Granada",
            "Sevilla",
        ]
        self.filter_metadata_port.get_distinct_municipalities.return_value = [
            "Granada",
            "Motril",
        ]

        result = await self.use_case.execute(provinces=["Granada"])

        assert isinstance(result, RouteFilterValuesDTO)
        assert result.heritage_types == ["patrimonio_inmueble", "patrimonio_mueble"]
        assert result.provinces == ["Granada", "Sevilla"]
        assert result.municipalities == ["Granada", "Motril"]

    async def test_passes_provinces_filter_to_municipalities(self):
        self.filter_metadata_port.get_distinct_heritage_types.return_value = []
        self.filter_metadata_port.get_distinct_provinces.return_value = []
        self.filter_metadata_port.get_distinct_municipalities.return_value = []

        await self.use_case.execute(provinces=["Jaen", "Cordoba"])

        self.filter_metadata_port.get_distinct_municipalities.assert_awaited_once_with(
            ["Jaen", "Cordoba"],
        )

    async def test_no_provinces_filter(self):
        self.filter_metadata_port.get_distinct_heritage_types.return_value = []
        self.filter_metadata_port.get_distinct_provinces.return_value = []
        self.filter_metadata_port.get_distinct_municipalities.return_value = []

        await self.use_case.execute()

        self.filter_metadata_port.get_distinct_municipalities.assert_awaited_once_with(
            None,
        )


# ---------------------------------------------------------------------------
# GenerateRouteUseCase
# ---------------------------------------------------------------------------


def _make_chunk(
    title: str = "La Alhambra",
    heritage_type: str = "patrimonio_inmueble",
    province: str = "Granada",
    municipality: str | None = "Granada",
    content: str = "Complejo palaciego nazari.",
    url: str = "https://guiadigital.iaph.es/alhambra",
    score: float = 0.95,
) -> dict:
    return {
        "title": title,
        "heritage_type": heritage_type,
        "province": province,
        "municipality": municipality,
        "content": content,
        "url": url,
        "score": score,
    }


def _make_virtual_route(
    title: str = "Ruta por Granada",
    province: str = "Granada",
    narrative: str = "Una ruta fascinante...",
    introduction: str = "Introduccion de la ruta.",
    conclusion: str = "Conclusion de la ruta.",
    num_stops: int = 2,
) -> VirtualRoute:
    stops = [
        RouteStop(
            order=i,
            title=f"Parada {i}",
            heritage_type="patrimonio_inmueble",
            province=province,
            municipality=province,
            url=f"https://example.com/stop{i}",
            description=f"Descripcion parada {i}",
        )
        for i in range(1, num_stops + 1)
    ]
    return VirtualRoute(
        id=uuid4(),
        title=title,
        province=province,
        stops=stops,
        narrative=narrative,
        introduction=introduction,
        conclusion=conclusion,
    )


def _make_route_narrative(
    title: str = "Ruta por Granada",
    introduction: str = "Introduccion de la ruta.",
    conclusion: str = "Conclusion de la ruta.",
    num_stops: int = 2,
) -> RouteNarrative:
    """Build a :class:`RouteNarrative` matching the structured format."""
    segments = {i: f"Narrativa parada {i}" for i in range(1, num_stops + 1)}
    return RouteNarrative(
        title=title,
        introduction=introduction,
        segments=segments,
        conclusion=conclusion,
    )


class TestGenerateRouteUseCase:
    def setup_method(self):
        self.rag_port = AsyncMock()
        self.llm_port = AsyncMock()
        self.route_repository = AsyncMock()
        self.route_builder_service = MagicMock(spec=RouteBuilderService)
        self.query_extraction_service = MagicMock(spec=QueryExtractionService)
        self.heritage_asset_lookup_port = AsyncMock()
        self.unit_of_work = AsyncMock()
        self.unit_of_work.__aenter__ = AsyncMock(return_value=self.unit_of_work)
        self.unit_of_work.__aexit__ = AsyncMock(return_value=False)

        self.use_case = GenerateRouteUseCase(
            rag_port=self.rag_port,
            llm_port=self.llm_port,
            route_repository=self.route_repository,
            route_builder_service=self.route_builder_service,
            query_extraction_service=self.query_extraction_service,
            heritage_asset_lookup_port=self.heritage_asset_lookup_port,
            unit_of_work=self.unit_of_work,
        )

    def _setup_defaults(self, chunks=None, route=None, num_stops=2):
        """Configure mocks with sensible defaults."""
        if chunks is None:
            chunks = [_make_chunk(), _make_chunk(title="Generalife")]
        if route is None:
            route = _make_virtual_route()

        self.query_extraction_service.clean_query_text.return_value = "alhambra"
        self.llm_port.generate_structured.return_value = "alhambra patrimonio"
        self.llm_port.generate_route_narrative.return_value = (
            _make_route_narrative(num_stops=num_stops)
        )
        self.rag_port.query.return_value = ("answer text", chunks, [])
        self.route_builder_service.select_diverse_stops.return_value = chunks
        self.route_builder_service.build.return_value = route
        self.route_repository.save_route.return_value = route
        self.heritage_asset_lookup_port.get_asset_previews.return_value = {}

    async def test_calls_clean_query_text_with_filters(self):
        self._setup_defaults()
        dto = GenerateRouteDTO(
            query="alhambra de granada",
            num_stops=3,
            province_filter=["Granada"],
            municipality_filter=["Granada"],
        )

        await self.use_case.execute(dto)

        self.query_extraction_service.clean_query_text.assert_called_once_with(
            user_text="alhambra de granada",
            province_filters=["Granada"],
            municipality_filters=["Granada"],
        )

    async def test_calls_llm_for_extraction_then_narrative(self):
        self._setup_defaults(num_stops=3)
        dto = GenerateRouteDTO(query="alhambra", num_stops=3)

        await self.use_case.execute(dto)

        assert self.llm_port.generate_structured.await_count == 1
        assert self.llm_port.generate_route_narrative.await_count == 1

    async def test_calls_rag_with_extracted_query_and_filters(self):
        self._setup_defaults(num_stops=5)
        dto = GenerateRouteDTO(
            query="alhambra de granada",
            num_stops=5,
            heritage_type_filter=["patrimonio_inmueble"],
            province_filter=["Granada"],
            municipality_filter=["Granada"],
        )

        await self.use_case.execute(dto)

        self.rag_port.query.assert_awaited_once_with(
            question="alhambra patrimonio",
            top_k=15,  # num_stops * 3
            heritage_type_filter=["patrimonio_inmueble"],
            province_filter=["Granada"],
            municipality_filter=["Granada"],
        )

    async def test_top_k_equals_num_stops_times_three(self):
        self._setup_defaults(num_stops=4)
        dto = GenerateRouteDTO(query="castillos", num_stops=4)

        await self.use_case.execute(dto)

        call_kwargs = self.rag_port.query.call_args.kwargs
        assert call_kwargs["top_k"] == 12

    async def test_returns_virtual_route_dto(self):
        route = _make_virtual_route(title="Ruta cultural por Granada")
        self._setup_defaults(route=route)
        dto = GenerateRouteDTO(query="alhambra", num_stops=2)

        result = await self.use_case.execute(dto)

        assert result.title == "Ruta cultural por Granada"
        assert result.province == "Granada"
        assert len(result.stops) == 2
        assert result.stops[0].order == 1

    async def test_saves_route_via_repository(self):
        route = _make_virtual_route()
        self._setup_defaults(route=route)
        dto = GenerateRouteDTO(query="alhambra", num_stops=2)

        await self.use_case.execute(dto)

        self.route_repository.save_route.assert_awaited_once()

    async def test_province_label_from_filter(self):
        route = _make_virtual_route()
        self._setup_defaults(route=route)
        dto = GenerateRouteDTO(
            query="castillos",
            num_stops=2,
            province_filter=["Cordoba"],
        )

        await self.use_case.execute(dto)

        build_kwargs = self.route_builder_service.build.call_args.kwargs
        assert build_kwargs["province"] == "Cordoba"

    async def test_province_label_from_chunks_when_no_filter(self):
        chunks = [_make_chunk(province="Sevilla")]
        route = _make_virtual_route()
        self._setup_defaults(chunks=chunks, route=route)
        dto = GenerateRouteDTO(query="monumentos", num_stops=2)

        await self.use_case.execute(dto)

        build_kwargs = self.route_builder_service.build.call_args.kwargs
        assert build_kwargs["province"] == "Sevilla"

    async def test_extracts_title_from_structured_json(self):
        route = _make_virtual_route()
        self._setup_defaults(route=route)
        self.llm_port.generate_structured.return_value = "query extraida"
        self.llm_port.generate_route_narrative.return_value = (
            _make_route_narrative(title="Descubriendo Granada")
        )
        dto = GenerateRouteDTO(query="alhambra", num_stops=2)

        await self.use_case.execute(dto)

        build_kwargs = self.route_builder_service.build.call_args.kwargs
        assert build_kwargs["title"] == "Descubriendo Granada"

    async def test_fallback_title_when_empty_narrative(self):
        route = _make_virtual_route()
        self._setup_defaults(route=route)
        self.llm_port.generate_structured.return_value = "query extraida"
        # Adapter returns the province-based fallback when parsing fails.
        self.llm_port.generate_route_narrative.return_value = RouteNarrative(
            title="Ruta cultural por Malaga",
            introduction="",
            segments={},
            conclusion="",
        )
        dto = GenerateRouteDTO(
            query="ruta",
            num_stops=2,
            province_filter=["Malaga"],
        )

        await self.use_case.execute(dto)

        build_kwargs = self.route_builder_service.build.call_args.kwargs
        assert build_kwargs["title"] == "Ruta cultural por Malaga"


# ---------------------------------------------------------------------------
# Fake TraceRepository for capturing saved traces in unit tests
# ---------------------------------------------------------------------------


class FakeTraceRepository(TraceRepository):
    """In-memory TraceRepository that records every saved trace."""

    def __init__(self, save_should_raise: Exception | None = None) -> None:
        self.saved: list[ExecutionTrace] = []
        self._save_should_raise = save_should_raise

    async def save(self, trace: ExecutionTrace) -> None:
        if self._save_should_raise is not None:
            raise self._save_should_raise
        self.saved.append(trace)

    async def list_traces(
        self,
        *,
        execution_type=None,
        user_id=None,
        since=None,
        until=None,
        query=None,
        exclude_admin_except=None,
        page=1,
        page_size=20,
    ):
        return ([], 0)

    async def get_by_id(self, trace_id, *, exclude_admin_except=None):
        return None

    async def list_by_execution_id(
        self,
        execution_id,
        *,
        execution_type=None,
        exclude_admin_except=None,
    ):
        return []


# ---------------------------------------------------------------------------
# AddStopUseCase
# ---------------------------------------------------------------------------


def _make_route_with_stops(num_stops: int = 2) -> VirtualRoute:
    """Build a VirtualRoute with `num_stops` populated stops."""
    stops = [
        RouteStop(
            order=i,
            title=f"Parada {i}",
            heritage_type="patrimonio_inmueble",
            province="Granada",
            municipality="Granada",
            url=f"https://example.com/stop{i}",
            description=f"Descripcion {i}",
            heritage_asset_id=f"asset-{i}",
            document_id=f"doc-{i}",
            narrative_segment=f"Segmento narrativo {i}.",
        )
        for i in range(1, num_stops + 1)
    ]
    return VirtualRoute(
        id=uuid4(),
        title="Ruta de prueba",
        province="Granada",
        stops=stops,
        narrative="Narrativa monolitica.",
        introduction="Intro de la ruta.",
        conclusion="Conclusion de la ruta.",
    )


class TestAddStopUseCase:
    def setup_method(self):
        self.route_repository = AsyncMock()
        self.heritage_asset_lookup_port = AsyncMock()
        self.llm_port = AsyncMock()
        self.unit_of_work = AsyncMock()
        self.unit_of_work.__aenter__ = AsyncMock(return_value=self.unit_of_work)
        self.unit_of_work.__aexit__ = AsyncMock(return_value=False)
        self.trace_repo = FakeTraceRepository()

        self.use_case = AddStopUseCase(
            route_repository=self.route_repository,
            heritage_asset_lookup_port=self.heritage_asset_lookup_port,
            llm_port=self.llm_port,
            unit_of_work=self.unit_of_work,
            trace_repository=self.trace_repo,
        )

    def _setup_defaults(self, existing_route: VirtualRoute | None = None):
        """Configure default mock responses for a happy-path add_stop."""
        route = existing_route or _make_route_with_stops(num_stops=2)
        self.route_repository.get_route.return_value = route

        # heritage asset lookup
        preview = AssetPreview(
            id="new-asset-id",
            image_url="https://example.com/img.jpg",
            latitude=37.0,
            longitude=-3.5,
            description=None,
            municipality="Granada",
        )
        self.heritage_asset_lookup_port.get_asset_previews.return_value = {
            "new-asset-id": preview,
        }
        # The use case calls get_asset_full_descriptions twice: once directly
        # (for description_text) and once inside _lookup_asset_info.
        self.heritage_asset_lookup_port.get_asset_full_descriptions.return_value = {
            "new-asset-id": (
                "Nombre oficial: Catedral de Granada\n"
                "Ubicacion: Granada, Granada\n"
                "Descripcion completa del monumento."
            ),
        }

        # LLM returns a raw narrative with markdown that should be stripped.
        self.llm_port.generate_structured.return_value = (
            "**Narrativa para la nueva parada:** Texto generado por el LLM."
        )

        # update_route returns the updated route — for simplicity, return a
        # new VirtualRoute that has one extra stop.
        def _update_route_side_effect(route_uuid, user_uuid, **kwargs):
            new_stops_dicts = kwargs["stops"]
            new_stops = [
                RouteStop(
                    order=s["order"],
                    title=s["title"],
                    heritage_type=s["heritage_type"],
                    province=s["province"],
                    municipality=s["municipality"],
                    url=s["url"],
                    description=s["description"],
                    heritage_asset_id=s.get("heritage_asset_id"),
                    document_id=s.get("document_id"),
                    narrative_segment=s.get("narrative_segment", ""),
                    image_url=s.get("image_url"),
                    latitude=s.get("latitude"),
                    longitude=s.get("longitude"),
                )
                for s in new_stops_dicts
            ]
            return VirtualRoute(
                id=route.id,
                title=route.title,
                province=route.province,
                stops=new_stops,
                narrative=kwargs["narrative"],
                introduction=kwargs["introduction"],
                conclusion=kwargs["conclusion"],
            )

        self.route_repository.update_route.side_effect = _update_route_side_effect
        return route

    async def test_saves_trace_with_expected_metadata(self):
        route = self._setup_defaults()
        user_id = str(uuid4())

        result = await self.use_case.execute(
            route_id=str(route.id),
            document_id="new-asset-id",
            position=2,
            user_id=user_id,
            username="alice",
            user_profile_type="researcher",
        )

        # Returns a VirtualRouteDTO
        assert result.id == str(route.id)

        # Exactly one trace was persisted
        assert len(self.trace_repo.saved) == 1
        trace = self.trace_repo.saved[0]

        assert trace.execution_type == "route"
        assert trace.pipeline_mode == "route_add_stop"
        assert trace.execution_id == str(route.id)
        assert trace.summary["action"] == "add_stop"
        assert trace.summary["position"] == 2
        assert trace.username == "alice"
        assert trace.user_profile_type == "researcher"
        # Steps: request, lookup, narrative, update -> at least 3
        assert len(trace.steps) >= 3
        narrative_steps = [
            s for s in trace.steps if s.get("step") == "narrative_generation"
        ]
        assert len(narrative_steps) == 1
        assert narrative_steps[0]["output"]["raw_response"]

    async def test_succeeds_when_trace_save_raises(self):
        """A failure in the trace repository must NOT bubble up."""
        # Use a repo whose save() blows up.
        failing_repo = FakeTraceRepository(save_should_raise=RuntimeError("db down"))
        self.use_case = AddStopUseCase(
            route_repository=self.route_repository,
            heritage_asset_lookup_port=self.heritage_asset_lookup_port,
            llm_port=self.llm_port,
            unit_of_work=self.unit_of_work,
            trace_repository=failing_repo,
        )
        route = self._setup_defaults()

        # Should not raise: the use case swallows trace persistence errors.
        result = await self.use_case.execute(
            route_id=str(route.id),
            document_id="new-asset-id",
            position=2,
            user_id=str(uuid4()),
            username="alice",
            user_profile_type="researcher",
        )

        assert result.id == str(route.id)
        # Nothing was actually persisted (save raised).
        assert failing_repo.saved == []

    async def test_works_without_trace_repository(self):
        """The use case must work when trace_repository=None."""
        self.use_case = AddStopUseCase(
            route_repository=self.route_repository,
            heritage_asset_lookup_port=self.heritage_asset_lookup_port,
            llm_port=self.llm_port,
            unit_of_work=self.unit_of_work,
            trace_repository=None,
        )
        route = self._setup_defaults()

        result = await self.use_case.execute(
            route_id=str(route.id),
            document_id="new-asset-id",
            position=2,
            user_id=str(uuid4()),
        )

        assert result.id == str(route.id)


# ---------------------------------------------------------------------------
# RemoveStopUseCase
# ---------------------------------------------------------------------------


class TestRemoveStopUseCase:
    def setup_method(self):
        self.route_repository = AsyncMock()
        self.unit_of_work = AsyncMock()
        self.unit_of_work.__aenter__ = AsyncMock(return_value=self.unit_of_work)
        self.unit_of_work.__aexit__ = AsyncMock(return_value=False)
        self.trace_repo = FakeTraceRepository()

        self.use_case = RemoveStopUseCase(
            route_repository=self.route_repository,
            unit_of_work=self.unit_of_work,
            trace_repository=self.trace_repo,
        )

    def _setup_defaults(self, num_stops: int = 3) -> VirtualRoute:
        route = _make_route_with_stops(num_stops=num_stops)
        self.route_repository.get_route.return_value = route

        def _update_route_side_effect(route_uuid, user_uuid, **kwargs):
            new_stops_dicts = kwargs["stops"]
            new_stops = [
                RouteStop(
                    order=s["order"],
                    title=s["title"],
                    heritage_type=s["heritage_type"],
                    province=s["province"],
                    municipality=s["municipality"],
                    url=s["url"],
                    description=s["description"],
                    heritage_asset_id=s.get("heritage_asset_id"),
                    document_id=s.get("document_id"),
                    narrative_segment=s.get("narrative_segment", ""),
                    image_url=s.get("image_url"),
                    latitude=s.get("latitude"),
                    longitude=s.get("longitude"),
                )
                for s in new_stops_dicts
            ]
            return VirtualRoute(
                id=route.id,
                title=route.title,
                province=route.province,
                stops=new_stops,
                narrative=kwargs["narrative"],
                introduction=kwargs["introduction"],
                conclusion=kwargs["conclusion"],
            )

        self.route_repository.update_route.side_effect = _update_route_side_effect
        return route

    async def test_saves_trace_with_expected_metadata(self):
        route = self._setup_defaults(num_stops=3)
        user_id = str(uuid4())

        result = await self.use_case.execute(
            route_id=str(route.id),
            stop_order=2,
            user_id=user_id,
            username="alice",
            user_profile_type="researcher",
        )

        assert result.id == str(route.id)

        assert len(self.trace_repo.saved) == 1
        trace = self.trace_repo.saved[0]

        assert trace.execution_type == "route"
        assert trace.pipeline_mode == "route_remove_stop"
        assert trace.execution_id == str(route.id)
        assert trace.summary["action"] == "remove_stop"
        assert trace.summary["removed_order"] == 2
        assert trace.username == "alice"
        assert trace.user_profile_type == "researcher"

        removal_steps = [
            s for s in trace.steps if s.get("step") == "stop_removal"
        ]
        assert len(removal_steps) == 1
        # The removed stop title must be captured in the step output.
        # Stop with order=2 from _make_route_with_stops has title "Parada 2".
        assert removal_steps[0]["output"]["removed_stop_title"] == "Parada 2"

    async def test_succeeds_when_trace_save_raises(self):
        failing_repo = FakeTraceRepository(save_should_raise=RuntimeError("db down"))
        self.use_case = RemoveStopUseCase(
            route_repository=self.route_repository,
            unit_of_work=self.unit_of_work,
            trace_repository=failing_repo,
        )
        route = self._setup_defaults(num_stops=3)

        result = await self.use_case.execute(
            route_id=str(route.id),
            stop_order=2,
            user_id=str(uuid4()),
            username="alice",
            user_profile_type="researcher",
        )

        assert result.id == str(route.id)
        assert failing_repo.saved == []

    async def test_works_without_trace_repository(self):
        self.use_case = RemoveStopUseCase(
            route_repository=self.route_repository,
            unit_of_work=self.unit_of_work,
            trace_repository=None,
        )
        route = self._setup_defaults(num_stops=3)

        result = await self.use_case.execute(
            route_id=str(route.id),
            stop_order=2,
            user_id=str(uuid4()),
        )

        assert result.id == str(route.id)
