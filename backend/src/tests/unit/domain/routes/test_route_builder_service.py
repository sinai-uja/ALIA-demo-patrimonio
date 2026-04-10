"""Unit tests for RouteBuilderService — pure domain, zero mocks."""

import pytest

from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.domain.routes.value_objects.asset_preview import AssetPreview


def _make_stop_chunk(
    title: str = "Castillo",
    heritage_type: str = "patrimonio_inmueble",
    document_id: str = "ficha-inmueble-123",
    province: str = "Jaén",
) -> dict:
    return {
        "title": title,
        "heritage_type": heritage_type,
        "document_id": document_id,
        "province": province,
        "municipality": "Jaén",
        "url": "https://example.com",
        "content": "Descripción del bien patrimonial",
    }


class TestSelectDiverseStops:
    def test_deduplicates_by_title(self):
        service = RouteBuilderService()
        chunks = [
            _make_stop_chunk(title="Castillo"),
            _make_stop_chunk(title="Castillo"),
            _make_stop_chunk(title="Catedral"),
        ]

        result = service.select_diverse_stops(chunks, num_stops=10)

        titles = [c["title"] for c in result]
        assert titles == ["Castillo", "Catedral"]

    def test_round_robin_by_heritage_type(self):
        service = RouteBuilderService()
        chunks = [
            _make_stop_chunk(title="A1", heritage_type="patrimonio_inmueble"),
            _make_stop_chunk(title="A2", heritage_type="patrimonio_inmueble"),
            _make_stop_chunk(title="B1", heritage_type="patrimonio_mueble"),
            _make_stop_chunk(title="B2", heritage_type="patrimonio_mueble"),
        ]

        result = service.select_diverse_stops(chunks, num_stops=3)

        types = [c["heritage_type"] for c in result]
        # Round-robin: first inmueble, then mueble, then inmueble again
        assert types[0] == "patrimonio_inmueble"
        assert types[1] == "patrimonio_mueble"
        assert len(result) == 3

    def test_num_stops_limits_output(self):
        service = RouteBuilderService()
        chunks = [_make_stop_chunk(title=f"Stop {i}") for i in range(10)]

        result = service.select_diverse_stops(chunks, num_stops=3)

        assert len(result) == 3

    def test_empty_chunks_returns_empty(self):
        service = RouteBuilderService()

        result = service.select_diverse_stops([], num_stops=5)

        assert result == []

    def test_fewer_unique_chunks_than_num_stops(self):
        service = RouteBuilderService()
        chunks = [_make_stop_chunk(title="A"), _make_stop_chunk(title="B")]

        result = service.select_diverse_stops(chunks, num_stops=10)

        assert len(result) == 2


class TestBuild:
    @pytest.mark.parametrize("heritage_type,expected_duration", [
        ("patrimonio_inmueble", 60),
        ("patrimonio_mueble", 30),
        ("paisaje_cultural", 90),
        ("patrimonio_inmaterial", 45),
    ])
    def test_assigns_correct_duration_by_heritage_type(self, heritage_type, expected_duration):
        service = RouteBuilderService()
        chunks = [_make_stop_chunk(heritage_type=heritage_type)]

        route = service.build(chunks, province="Jaén", title="Test Route", narrative="Narrative")

        assert route.stops[0].visit_duration_minutes == expected_duration

    def test_unknown_heritage_type_gets_default_duration(self):
        service = RouteBuilderService()
        chunks = [_make_stop_chunk(heritage_type="unknown_type")]

        route = service.build(chunks, province="Jaén", title="Route", narrative="N")

        assert route.stops[0].visit_duration_minutes == 45  # _DEFAULT_DURATION

    def test_total_duration_is_sum_of_stops(self):
        service = RouteBuilderService()
        chunks = [
            _make_stop_chunk(title="A", heritage_type="patrimonio_inmueble"),   # 60
            _make_stop_chunk(title="B", heritage_type="patrimonio_mueble"),     # 30
        ]

        route = service.build(chunks, province="Jaén", title="Route", narrative="N")

        assert route.total_duration_minutes == 90

    def test_extract_asset_id_strips_prefix(self):
        service = RouteBuilderService()
        chunks = [_make_stop_chunk(document_id="ficha-inmueble-456")]

        route = service.build(chunks, province="Jaén", title="Route", narrative="N")

        assert route.stops[0].heritage_asset_id == "456"

    def test_asset_preview_used_when_available(self):
        service = RouteBuilderService()
        chunks = [_make_stop_chunk(document_id="ficha-inmueble-789")]
        previews = {
            "789": AssetPreview(
                id="789",
                image_url="https://img.com/photo.jpg",
                latitude=37.5,
                longitude=-3.7,
                description="Vista panorámica",
                municipality="Úbeda",
            )
        }

        route = service.build(
            chunks, province="Jaén", title="Route", narrative="N",
            asset_previews=previews,
        )

        stop = route.stops[0]
        assert stop.image_url == "https://img.com/photo.jpg"
        assert stop.latitude == 37.5
        assert stop.description == "Vista panorámica"
        assert stop.municipality == "Úbeda"
