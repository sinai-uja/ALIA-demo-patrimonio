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

        result = service.fuse(vector, text, top_k=10, lexical_weight=0.5)

        # "shared" appears in both lists, should be ranked first (score closest to 0).
        assert result[0].chunk_id == "shared"
        assert result[0].score < result[1].score

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


class TestLexicalWeight:
    """Verify the per-call slider semantics of `lexical_weight`."""

    def test_lexical_weight_zero_matches_vector_ranking(self):
        """`lexical_weight=0.0` → ranking driven entirely by vector results."""
        service = HybridSearchService()
        vector = [_make_chunk("v1"), _make_chunk("v2"), _make_chunk("v3")]
        # Text list has disjoint chunks — must not influence the order of
        # the vector chunks at all.
        text = [_make_chunk("t1"), _make_chunk("t2"), _make_chunk("t3")]

        result = service.fuse(vector, text, top_k=10, lexical_weight=0.0)

        # First three slots must be exactly the vector ranking.
        assert [c.chunk_id for c in result[:3]] == ["v1", "v2", "v3"]

    def test_lexical_weight_one_matches_text_ranking(self):
        """`lexical_weight=1.0` → ranking driven entirely by text results."""
        service = HybridSearchService()
        vector = [_make_chunk("v1"), _make_chunk("v2"), _make_chunk("v3")]
        text = [_make_chunk("t1"), _make_chunk("t2"), _make_chunk("t3")]

        result = service.fuse(vector, text, top_k=10, lexical_weight=1.0)

        # First three slots must be exactly the text ranking.
        assert [c.chunk_id for c in result[:3]] == ["t1", "t2", "t3"]

    def test_lexical_weight_balanced_prefers_chunks_present_in_both_lists(self):
        """A chunk that appears in both lists must beat chunks present in only one."""
        service = HybridSearchService()
        shared = _make_chunk("shared")
        vector = [shared, _make_chunk("v_only")]
        text = [shared, _make_chunk("t_only")]

        result = service.fuse(vector, text, top_k=10, lexical_weight=0.5)

        assert result[0].chunk_id == "shared"
        other_ids = {c.chunk_id for c in result[1:]}
        assert other_ids == {"v_only", "t_only"}

    def test_lexical_weight_out_of_range_is_clamped(self):
        """Defensive clamping so the formula stays well-defined."""
        service = HybridSearchService()
        vector = [_make_chunk("v1")]
        text = [_make_chunk("t1")]

        # Negative weight → behaves like 0.0 (vector-only).
        result_neg = service.fuse(vector, text, top_k=10, lexical_weight=-1.0)
        assert result_neg[0].chunk_id == "v1"

        # Weight > 1.0 → behaves like 1.0 (text-only).
        result_high = service.fuse(vector, text, top_k=10, lexical_weight=5.0)
        assert result_high[0].chunk_id == "t1"

    def test_high_lexical_weight_favours_text_results(self):
        """Sanity check on the slider direction."""
        service = HybridSearchService()
        vector = [_make_chunk("v1")]
        text = [_make_chunk("t1")]

        # Very lexical-heavy mix → text wins.
        result = service.fuse(vector, text, top_k=10, lexical_weight=0.9)
        assert result[0].chunk_id == "t1"

        # Very semantic-heavy mix → vector wins.
        result = service.fuse(vector, text, top_k=10, lexical_weight=0.1)
        assert result[0].chunk_id == "v1"

    def test_default_weight_preserves_legacy_text_weight_15_behavior(self):
        """Without explicit `lexical_weight` the service must keep RAG's
        legacy ranking (previous implementation used text_weight=1.5)."""
        service = HybridSearchService()
        vector = [_make_chunk("v1")]
        text = [_make_chunk("t1")]

        result = service.fuse(vector, text, top_k=10)

        # Legacy ratio favoured the text result.
        assert result[0].chunk_id == "t1"
