"""Unit tests for QueryExtractionService."""

import pytest

from src.domain.routes.services.query_extraction_service import QueryExtractionService


class TestCleanQueryText:
    """Tests for QueryExtractionService.clean_query_text."""

    def setup_method(self):
        self.service = QueryExtractionService()

    def test_removes_province_name_from_text(self):
        result = self.service.clean_query_text(
            "cuevas del sacromonte de granada",
            province_filters=["Granada"],
        )
        assert result == "cuevas del sacromonte"

    def test_removes_municipality_name_from_text(self):
        result = self.service.clean_query_text(
            "monumentos de sevilla capital",
            municipality_filters=["Sevilla"],
        )
        assert result == "monumentos de capital"

    def test_keeps_heritage_type_terms(self):
        result = self.service.clean_query_text(
            "patrimonio inmueble en granada",
            province_filters=["Granada"],
        )
        assert "patrimonio inmueble" in result

    def test_handles_dangling_prepositions_at_end(self):
        result = self.service.clean_query_text(
            "ruta por granada",
            province_filters=["Granada"],
        )
        assert result == "ruta"

    def test_handles_consecutive_dangling_prepositions(self):
        result = self.service.clean_query_text(
            "ruta por de granada",
            province_filters=["Granada"],
        )
        # After removing "granada": "ruta por de" -> trailing "de" removed -> "ruta por"
        # Then trailing "por" is not removed in second pass (only one trailing pass)
        # Actually the regex removes trailing preposition, so "ruta por de" -> "ruta por"
        assert result == "ruta por"

    def test_empty_filters_no_change(self):
        original = "cuevas del sacromonte"
        result = self.service.clean_query_text(original)
        assert result == original

    def test_none_filters_no_change(self):
        original = "cuevas del sacromonte"
        result = self.service.clean_query_text(
            original,
            province_filters=None,
            municipality_filters=None,
        )
        assert result == original

    def test_case_insensitive_removal(self):
        result = self.service.clean_query_text(
            "monumentos de GRANADA",
            province_filters=["granada"],
        )
        assert "granada" not in result.lower()
        assert "monumentos" in result

    def test_multiple_spaces_collapsed(self):
        result = self.service.clean_query_text(
            "monumentos   de   sevilla   en   granada",
            province_filters=["Granada"],
        )
        assert "  " not in result

    def test_both_province_and_municipality_removed(self):
        result = self.service.clean_query_text(
            "iglesias de jaen en la provincia de jaen",
            province_filters=["Jaen"],
            municipality_filters=["Jaen"],
        )
        assert "jaen" not in result.lower()
        assert "iglesias" in result

    def test_empty_text_returns_empty(self):
        result = self.service.clean_query_text("")
        assert result == ""

    def test_text_with_only_filter_terms_returns_empty(self):
        result = self.service.clean_query_text(
            "de granada",
            province_filters=["Granada"],
        )
        assert result == ""

    @pytest.mark.parametrize(
        ("text", "province_filters", "expected"),
        [
            ("rutas en cordoba", ["Cordoba"], "rutas"),
            ("patrimonio de malaga", ["Malaga"], "patrimonio"),
            ("castillos en almeria", ["Almeria"], "castillos"),
        ],
    )
    def test_various_provinces_with_trailing_preposition(
        self, text, province_filters, expected,
    ):
        result = self.service.clean_query_text(
            text, province_filters=province_filters,
        )
        assert result == expected
