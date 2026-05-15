"""Unit tests for RelevanceFilterService — pure domain, zero mocks."""


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


class TestFilterWithOverrideThreshold:
    def test_override_is_stricter_than_default(self):
        service = RelevanceFilterService(score_threshold=0.5)
        chunks = [
            _make_chunk("c1", 0.20),
            _make_chunk("c2", 0.35),
            _make_chunk("c3", 0.45),
        ]

        result = service.filter(chunks, override_threshold=0.30)

        assert [c.chunk_id for c in result] == ["c1"]

    def test_override_is_more_permissive_than_default(self):
        service = RelevanceFilterService(score_threshold=0.3)
        chunks = [
            _make_chunk("c1", 0.20),
            _make_chunk("c2", 0.50),
            _make_chunk("c3", 0.90),
        ]

        result = service.filter(chunks, override_threshold=0.60)

        assert [c.chunk_id for c in result] == ["c1", "c2"]

    def test_override_none_uses_constructor_default(self):
        service = RelevanceFilterService(score_threshold=0.30)
        chunks = [_make_chunk("c1", 0.25), _make_chunk("c2", 0.40)]

        result = service.filter(chunks, override_threshold=None)

        assert [c.chunk_id for c in result] == ["c1"]

    def test_override_zero_filters_everything_above_zero(self):
        service = RelevanceFilterService(score_threshold=0.50)
        chunks = [_make_chunk("c1", 0.0), _make_chunk("c2", 0.01)]

        result = service.filter(chunks, override_threshold=0.0)

        assert [c.chunk_id for c in result] == ["c1"]

    def test_has_sufficient_evidence_honors_override(self):
        service = RelevanceFilterService(score_threshold=0.5)
        chunks = [_make_chunk("c1", 0.4)]

        assert service.has_sufficient_evidence(chunks) is True
        assert (
            service.has_sufficient_evidence(chunks, override_threshold=0.30)
            is False
        )
