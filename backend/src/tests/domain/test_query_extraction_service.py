"""Unit tests for QueryExtractionService."""

from src.domain.routes.services.query_extraction_service import QueryExtractionService


class TestCleanQueryText:
    """Tests for QueryExtractionService.clean_query_text."""

    def setup_method(self):
        self.service = QueryExtractionService()

    def test_preserves_province_name_in_text(self):
        result = self.service.clean_query_text(
            "cuevas del sacromonte de granada",
            province_filters=["Granada"],
        )
        assert result == "cuevas del sacromonte de granada"

    def test_preserves_municipality_name_in_text(self):
        result = self.service.clean_query_text(
            "monumentos de sevilla capital",
            municipality_filters=["Sevilla"],
        )
        assert result == "monumentos de sevilla capital"

    def test_keeps_heritage_type_terms(self):
        result = self.service.clean_query_text(
            "patrimonio inmueble en granada",
            province_filters=["Granada"],
        )
        assert result == "patrimonio inmueble en granada"

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

    def test_multiple_spaces_collapsed(self):
        result = self.service.clean_query_text(
            "monumentos   de   sevilla   en   granada",
            province_filters=["Granada"],
        )
        assert "  " not in result

    def test_empty_text_returns_empty(self):
        result = self.service.clean_query_text("")
        assert result == ""
