"""Unit tests for EntityDetectionService — pure domain, zero mocks."""

import pytest

from src.domain.search.services.entity_detection_service import EntityDetectionService

PROVINCES = ["Jaén", "Sevilla", "Córdoba", "Málaga", "Granada", "Almería", "Cádiz", "Huelva"]
MUNICIPALITIES = ["Úbeda", "Baeza", "Linares", "Andújar", "Jaén"]
HERITAGE_TYPES = [
    "patrimonio_inmueble", "patrimonio_mueble",
    "patrimonio_inmaterial", "paisaje_cultural",
]


@pytest.fixture
def service():
    return EntityDetectionService()


class TestHeritageTypeDetection:
    @pytest.mark.parametrize("keyword,expected_type", [
        ("castillo", "patrimonio_inmueble"),
        ("iglesia", "patrimonio_inmueble"),
        ("retablo", "patrimonio_mueble"),
        ("escultura", "patrimonio_mueble"),
        ("flamenco", "patrimonio_inmaterial"),
        ("fiesta", "patrimonio_inmaterial"),
        ("paisaje", "paisaje_cultural"),
        ("dehesa", "paisaje_cultural"),
    ])
    def test_detects_heritage_type_by_keyword(self, service, keyword, expected_type):
        entities = service.detect(keyword, PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        type_entities = [e for e in entities if e.entity_type == "heritage_type"]
        assert len(type_entities) >= 1
        assert type_entities[0].value == expected_type

    def test_heritage_type_deduplicated(self, service):
        # "castillo" and "iglesia" both map to patrimonio_inmueble
        entities = service.detect("castillo e iglesia", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        type_entities = [e for e in entities if e.entity_type == "heritage_type"]
        assert len(type_entities) == 1
        assert type_entities[0].value == "patrimonio_inmueble"


class TestProvinceDetection:
    def test_detects_province(self, service):
        entities = service.detect(
            "monumentos en Sevilla", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES,
        )

        prov_entities = [e for e in entities if e.entity_type == "province"]
        assert len(prov_entities) == 1
        assert prov_entities[0].value == "Sevilla"

    def test_province_word_boundary(self, service):
        # "Se" is < 3 chars — not a valid province. Ensure no false positives.
        entities = service.detect("Se fue al parque", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        prov_entities = [e for e in entities if e.entity_type == "province"]
        assert len(prov_entities) == 0

    def test_province_min_3_chars(self, service):
        # Short province-like strings should not match
        entities = service.detect("algo en AB", ["AB"], [], HERITAGE_TYPES)

        prov_entities = [e for e in entities if e.entity_type == "province"]
        assert len(prov_entities) == 0


class TestMunicipalityDetection:
    def test_detects_municipality(self, service):
        entities = service.detect("patrimonio en Úbeda", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        muni_entities = [e for e in entities if e.entity_type == "municipality"]
        assert len(muni_entities) == 1
        assert muni_entities[0].value == "Úbeda"

    def test_longest_first_matching(self, service):
        # If municipalities list has both "San Fernando" and "San", the longer one wins
        municipalities = ["San Fernando", "San"]
        entities = service.detect("vivo en San Fernando", PROVINCES, municipalities, HERITAGE_TYPES)

        muni_entities = [e for e in entities if e.entity_type == "municipality"]
        values = [e.value for e in muni_entities]
        assert "San Fernando" in values


class TestAccentInsensitiveMatching:
    def test_jaen_matches_jaen_with_accent(self, service):
        entities = service.detect("castillos en jaen", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        prov_entities = [e for e in entities if e.entity_type == "province"]
        assert len(prov_entities) == 1
        assert prov_entities[0].value == "Jaén"

    def test_malaga_matches_without_accent(self, service):
        entities = service.detect("monumentos en malaga", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        prov_entities = [e for e in entities if e.entity_type == "province"]
        assert len(prov_entities) == 1
        assert prov_entities[0].value == "Málaga"


class TestEdgeCases:
    def test_empty_query_returns_empty(self, service):
        entities = service.detect("", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        assert entities == []

    def test_whitespace_only_query_returns_empty(self, service):
        entities = service.detect("   ", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        assert entities == []

    def test_multiple_entity_types_in_single_query(self, service):
        entities = service.detect("castillos en Sevilla", PROVINCES, MUNICIPALITIES, HERITAGE_TYPES)

        entity_types = {e.entity_type for e in entities}
        assert "heritage_type" in entity_types
        assert "province" in entity_types
