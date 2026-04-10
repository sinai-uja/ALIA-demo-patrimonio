"""Unit tests for RelevanceFilterService — pure domain, zero mocks."""

import pytest

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService


def _make_chunk(chunk_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        title=f"Title {chunk_id}",
        heritage_type="patrimonio_inmueble",
        province="Sevilla",
        municipality=None,
        url="https://example.com",
        content="some content",
        score=score,
    )


class TestFilter:
    def test_keeps_chunks_below_threshold(self):
        service = RelevanceFilterService(score_threshold=0.5)
        chunks = [_make_chunk("c1", 0.2), _make_chunk("c2", 0.8)]

        result = service.filter(chunks)

        assert len(result) == 1
        assert result[0].chunk_id == "c1"

    def test_score_exactly_at_threshold_is_included(self):
        service = RelevanceFilterService(score_threshold=0.5)
        chunks = [_make_chunk("c1", 0.5)]

        result = service.filter(chunks)

        assert len(result) == 1

    def test_all_above_threshold_returns_empty(self):
        service = RelevanceFilterService(score_threshold=0.3)
        chunks = [_make_chunk("c1", 0.5), _make_chunk("c2", 0.9)]

        result = service.filter(chunks)

        assert result == []

    def test_empty_input_returns_empty(self):
        service = RelevanceFilterService(score_threshold=0.5)

        result = service.filter([])

        assert result == []


class TestHasSufficientEvidence:
    def test_returns_true_when_relevant_chunks_exist(self):
        service = RelevanceFilterService(score_threshold=0.5)
        chunks = [_make_chunk("c1", 0.2)]

        assert service.has_sufficient_evidence(chunks) is True

    def test_returns_false_when_no_relevant_chunks(self):
        service = RelevanceFilterService(score_threshold=0.3)
        chunks = [_make_chunk("c1", 0.5)]

        assert service.has_sufficient_evidence(chunks) is False
