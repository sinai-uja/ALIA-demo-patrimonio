"""Unit tests for routes application use cases."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.application.routes.dto.routes_dto import (
    GenerateRouteDTO,
    RouteFilterValuesDTO,
)
from src.application.routes.use_cases.generate_route import GenerateRouteUseCase
from src.application.routes.use_cases.route_filter_values import RouteFilterValuesUseCase
from src.application.routes.use_cases.route_suggestions import RouteSuggestionsUseCase
from src.domain.routes.services.query_extraction_service import QueryExtractionService
from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.domain.routes.value_objects.detected_entity import DetectedEntityResult
from src.domain.routes.value_objects.route_stop import RouteStop
from src.domain.routes.value_objects.virtual_route import VirtualRoute

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
            visit_duration_minutes=60,
        )
        for i in range(1, num_stops + 1)
    ]
    return VirtualRoute(
        id=uuid4(),
        title=title,
        province=province,
        stops=stops,
        total_duration_minutes=60 * num_stops,
        narrative=narrative,
        introduction=introduction,
        conclusion=conclusion,
    )


def _make_narrative_json(
    title: str = "Ruta por Granada",
    introduction: str = "Introduccion de la ruta.",
    conclusion: str = "Conclusion de la ruta.",
    num_stops: int = 2,
) -> str:
    """Build a JSON string matching the structured narrative format."""
    stops = [
        {"order": i, "narrative": f"Narrativa parada {i}"}
        for i in range(1, num_stops + 1)
    ]
    return json.dumps({
        "title": title,
        "introduction": introduction,
        "stops": stops,
        "conclusion": conclusion,
    })


class TestGenerateRouteUseCase:
    def setup_method(self):
        self.rag_port = AsyncMock()
        self.llm_port = AsyncMock()
        self.route_repository = AsyncMock()
        self.route_builder_service = MagicMock(spec=RouteBuilderService)
        self.query_extraction_service = MagicMock(spec=QueryExtractionService)
        self.heritage_asset_lookup_port = AsyncMock()

        self.use_case = GenerateRouteUseCase(
            rag_port=self.rag_port,
            llm_port=self.llm_port,
            route_repository=self.route_repository,
            route_builder_service=self.route_builder_service,
            query_extraction_service=self.query_extraction_service,
            heritage_asset_lookup_port=self.heritage_asset_lookup_port,
        )

    def _setup_defaults(self, chunks=None, route=None, num_stops=2):
        """Configure mocks with sensible defaults."""
        if chunks is None:
            chunks = [_make_chunk(), _make_chunk(title="Generalife")]
        if route is None:
            route = _make_virtual_route()

        self.query_extraction_service.clean_query_text.return_value = "alhambra"
        self.llm_port.generate_structured.side_effect = [
            "alhambra patrimonio",  # extraction call
            _make_narrative_json(num_stops=num_stops),  # structured narrative JSON
        ]
        self.rag_port.query.return_value = ("answer text", chunks)
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

        assert self.llm_port.generate_structured.await_count == 2

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
        # The second LLM call returns structured JSON with a title
        self.llm_port.generate_structured.side_effect = [
            "query extraida",
            _make_narrative_json(title="Descubriendo Granada"),
        ]
        dto = GenerateRouteDTO(query="alhambra", num_stops=2)

        await self.use_case.execute(dto)

        build_kwargs = self.route_builder_service.build.call_args.kwargs
        assert build_kwargs["title"] == "Descubriendo Granada"

    async def test_fallback_title_when_empty_narrative(self):
        route = _make_virtual_route()
        self._setup_defaults(route=route)
        self.llm_port.generate_structured.side_effect = [
            "query extraida",
            "",  # empty narrative (not valid JSON -> fallback)
        ]
        dto = GenerateRouteDTO(
            query="ruta",
            num_stops=2,
            province_filter=["Malaga"],
        )

        await self.use_case.execute(dto)

        build_kwargs = self.route_builder_service.build.call_args.kwargs
        assert build_kwargs["title"] == "Ruta cultural por Malaga"
