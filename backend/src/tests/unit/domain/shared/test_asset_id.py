"""Unit tests for extract_asset_id — pure domain, zero mocks."""

import pytest

from src.domain.shared.value_objects.asset_id import extract_asset_id


class TestExtractAssetId:
    @pytest.mark.parametrize("input_id,expected", [
        ("ficha-inmueble-123", "123"),
        ("ficha-mueble-456", "456"),
        ("ficha-inmueble-0", "0"),
        ("ficha-mueble-999999", "999999"),
    ])
    def test_strips_known_prefixes(self, input_id, expected):
        assert extract_asset_id(input_id) == expected

    def test_no_prefix_returns_input_unchanged(self):
        assert extract_asset_id("plain-id-789") == "plain-id-789"

    def test_empty_string_returns_empty(self):
        assert extract_asset_id("") == ""

    def test_numeric_only_returns_unchanged(self):
        assert extract_asset_id("12345") == "12345"
