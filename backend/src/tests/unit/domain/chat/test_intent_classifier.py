"""Unit tests for IntentClassifier._parse_response — pure domain, zero mocks.

Only the static _parse_response method is tested here (pure logic).
The async classify() method requires an LLM port and belongs in application tests.
"""

import pytest

from src.domain.chat.services.intent_classifier import IntentClassifier, MessageIntent


class TestParseResponse:
    @pytest.mark.parametrize("response,expected_intent", [
        ("SALUDO", MessageIntent.CONVERSATIONAL),
        ("CONSULTA", MessageIntent.RAG_QUERY),
        ("SEGUIMIENTO", MessageIntent.CONTEXTUAL_RAG),
    ])
    def test_maps_known_keywords_to_intents(self, response, expected_intent):
        result = IntentClassifier._parse_response(response)

        assert result == expected_intent

    def test_handles_trailing_punctuation(self):
        result = IntentClassifier._parse_response("SALUDO.")

        assert result == MessageIntent.CONVERSATIONAL

    def test_handles_trailing_colon(self):
        result = IntentClassifier._parse_response("CONSULTA: el usuario pregunta algo")

        assert result == MessageIntent.RAG_QUERY

    def test_handles_leading_whitespace(self):
        result = IntentClassifier._parse_response("  SEGUIMIENTO  ")

        assert result == MessageIntent.CONTEXTUAL_RAG

    def test_unknown_response_defaults_to_rag_query(self):
        result = IntentClassifier._parse_response("SOMETHING_ELSE extra text")

        assert result == MessageIntent.RAG_QUERY

    def test_empty_response_defaults_to_rag_query(self):
        result = IntentClassifier._parse_response("")

        assert result == MessageIntent.RAG_QUERY

    def test_whitespace_only_defaults_to_rag_query(self):
        result = IntentClassifier._parse_response("   ")

        assert result == MessageIntent.RAG_QUERY

    def test_lowercase_not_matched(self):
        # The map uses uppercase keys, input is uppercased via .upper()
        result = IntentClassifier._parse_response("saludo")

        assert result == MessageIntent.CONVERSATIONAL
