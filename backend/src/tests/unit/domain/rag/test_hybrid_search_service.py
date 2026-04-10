"""Unit tests for HybridSearchService — pure domain, zero mocks."""

import pytest

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.services.hybrid_search_service import HybridSearchService


def _make_chunk(chunk_id: str, score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        title=f"Title {chunk_id}",
        heritage_type="patrimonio_inmueble",
        province="Sevilla",
        municipality="Sevilla",
        url=f"https://example.com/{chunk_id}",
        content=f"Content of {chunk_id}",
        score=score,
    )


class TestRRFFusion:
    def test_disjoint_lists_merge_all_chunks(self):
        service = HybridSearchService()
        vector = [_make_chunk("v1"), _make_chunk("v2")]
        text = [_make_chunk("t1"), _make_chunk("t2")]

        result = service.fuse(vector, text, top_k=10)

        ids = {c.chunk_id for c in result}
        assert ids == {"v1", "v2", "t1", "t2"}

    def test_overlapping_chunks_get_higher_score(self):
        service = HybridSearchService()
        shared = _make_chunk("shared")
        vector = [shared, _make_chunk("v_only")]
        text = [shared, _make_chunk("t_only")]

        result = service.fuse(vector, text, top_k=10)

        # "shared" appears in both lists, should be ranked first (score closest to 0)
        assert result[0].chunk_id == "shared"
        assert result[0].score < result[1].score

    def test_text_weight_boost_favours_text_results(self):
        service = HybridSearchService(text_weight=3.0)
        vector = [_make_chunk("v1")]
        text = [_make_chunk("t1")]

        result = service.fuse(vector, text, top_k=10)

        # With 3x text weight, t1 should rank above v1
        assert result[0].chunk_id == "t1"

    def test_top_k_limits_output(self):
        service = HybridSearchService()
        vector = [_make_chunk(f"v{i}") for i in range(5)]
        text = [_make_chunk(f"t{i}") for i in range(5)]

        result = service.fuse(vector, text, top_k=3)

        assert len(result) == 3

    def test_best_chunk_has_score_zero(self):
        """The top-ranked chunk should have normalized score = 0.0 (best)."""
        service = HybridSearchService()
        vector = [_make_chunk("v1"), _make_chunk("v2")]
        text = [_make_chunk("t1")]

        result = service.fuse(vector, text, top_k=10)

        assert result[0].score == pytest.approx(0.0)

    def test_all_scores_between_zero_and_one(self):
        service = HybridSearchService()
        vector = [_make_chunk(f"v{i}") for i in range(3)]
        text = [_make_chunk(f"t{i}") for i in range(3)]

        result = service.fuse(vector, text, top_k=10)

        for chunk in result:
            assert 0.0 <= chunk.score <= 1.0


class TestRRFEmptyInputs:
    def test_empty_vector_returns_text_only(self):
        service = HybridSearchService()
        text = [_make_chunk("t1"), _make_chunk("t2")]

        result = service.fuse([], text, top_k=10)

        assert len(result) == 2
        assert {c.chunk_id for c in result} == {"t1", "t2"}

    def test_empty_text_returns_vector_only(self):
        service = HybridSearchService()
        vector = [_make_chunk("v1")]

        result = service.fuse(vector, [], top_k=10)

        assert len(result) == 1
        assert result[0].chunk_id == "v1"

    def test_both_empty_returns_empty(self):
        service = HybridSearchService()

        result = service.fuse([], [], top_k=10)

        assert result == []

    def test_top_k_zero_returns_empty(self):
        service = HybridSearchService()
        vector = [_make_chunk("v1")]

        result = service.fuse(vector, [], top_k=0)

        assert result == []
